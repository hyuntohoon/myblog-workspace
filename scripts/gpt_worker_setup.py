#!/usr/bin/env python3
"""Owner-only loopback setup. Login/model choice never enables background work."""
from __future__ import annotations

import argparse
import html
import hmac
import json
import logging
import secrets
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.gpt_plan_auth import DEFAULT_DIR, PlanAccount, PlanUnavailable, PrivateState

log = logging.getLogger(__name__)
USAGE = 'https://chatgpt.com/settings/usage'


class SetupServer(HTTPServer):
    def __init__(self, state, account=None, new_account=False):
        super().__init__(('127.0.0.1', 0), SetupHandler)
        self.state, self.account = state, account or PlanAccount(state)
        self.csrf, self.pending = secrets.token_urlsafe(32), None
        self.new_account = new_account
        self.models, self.message = [], ''
        self.origin = f'http://127.0.0.1:{self.server_port}'


class SetupHandler(BaseHTTPRequestHandler):
    server: SetupServer

    def log_message(self, *args):
        # Never log callback query/code or authorization URL/id_token_hint.
        pass

    def send_page(self, body, status=200):
        data = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://auth.openai.com; frame-ancestors 'none'; base-uri 'none'")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def trusted(self, mutation=False):
        if self.headers.get('Host') != urlsplit(self.server.origin).netloc:
            self.send_page('잘못된 주소입니다.', 403)
            return False
        if mutation and self.headers.get('Origin') != self.server.origin:
            self.send_page('이 컴퓨터의 설정 화면에서 실행해 주세요.', 403)
            return False
        return True

    def redirect(self, location):
        self.send_response(303)
        self.send_header('Location', location)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def page(self):
        settings = self.server.state.settings()
        record = self.server.state.read(settings['active'] + '.json', {}) if settings.get('active') else {}
        options = ''.join(f'<option value="{html.escape(m["slug"], quote=True)}"'
                          f'{" selected" if m["slug"] == settings.get("model") else ""}>'
                          f'{html.escape(m["display_name"])}</option>' for m in self.server.models)
        hidden = f'<input type="hidden" name="csrf" value="{self.server.csrf}">'
        status = '계정 연결 필요' if not record.get('access_token') else '계정 연결됨'
        if settings.get('model'):
            status += ' · 모델: ' + settings['model']
        status += ' · 자동 처리 ' + ('켜짐' if settings.get('enabled') else '꺼짐')
        pause = settings.get('pause_reason')
        if pause:
            status += ' · 중지 사유: ' + pause
        self.send_page(f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>MyBlog GPT 연결</title><style>body{{font-family:system-ui;max-width:650px;margin:70px auto;padding:20px;line-height:1.65}}button,select,input{{font:inherit;padding:8px;margin:6px 0}}button{{cursor:pointer}}aside{{background:#f3f4f6;padding:18px;border-radius:12px}}label{{display:block}}</style>
<h1>번역 자동 처리 연결</h1><p>{html.escape(status)}</p><p>{html.escape(record.get('email',''))}</p>
<p>{html.escape(self.server.message)}</p><aside>AWS에 쌓인 가사·해설 요청을 이 컴퓨터에서 하나씩 처리합니다.
ChatGPT 플랜의 허용량을 사용하며, 다른 연결 앱과 한도를 공유할 수 있습니다.
로그인하거나 설정을 저장해도 자동 처리가 시작되지는 않습니다.</aside>
<form method="post" action="/login">{hidden}<label><input type="checkbox" name="consent" value="yes" required> ChatGPT 플랜을 사용하여 번역하는 데 동의합니다.</label>
<button>Continue with ChatGPT</button></form>
<form method="post" action="/models">{hidden}<button>이 계정의 모델 확인</button></form>
<form method="post" action="/save">{hidden}<label>번역 모델 <select name="model" required><option value="">선택</option>{options}</select></label>
<label>하루 호출 예산 <input type="number" name="daily_cap" value="{int(settings.get('daily_cap',10))}" min="1" max="10000" required></label>
<p>예산에 도달하면 요청을 남겨 두고 다음 UTC 날짜에 이어서 처리합니다. 같은 원문의 실패는 최대 두 번 시도합니다.</p><button>설정 저장 (자동 실행은 꺼짐)</button></form>
<form method="post" action="/pause">{hidden}<button>자동 처리 중지</button></form>
<p><a href="{USAGE}" target="_blank" rel="noopener noreferrer">ChatGPT 사용량·앱별 권한 설정</a></p>
<p>저장 후 담당 에이전트가 요청 한 건과 결과 화면을 검증한 다음 자동 실행을 켭니다. 계정 토큰은 이 컴퓨터에만 보관됩니다.</p></html>''')

    def do_GET(self):
        if not self.trusted():
            return
        parsed = urlsplit(self.path)
        if parsed.path == '/auth/callback':
            pending, self.server.pending = self.server.pending, None
            try:
                pairs = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=20)
                if not pending or len(parsed.query)>16384 or any(len(v)!=1 for v in pairs.values()):
                    raise PlanUnavailable('Invalid callback')
                # Account replacement is forbidden while an inference tick runs.
                with self.server.state.lock('worker.lock', blocking=False), self.server.state.lock('control.lock'):
                    self.server.account.finish(pending, {k:v[0] for k,v in pairs.items()})
                self.server.message = '계정 연결이 완료되었습니다. 모델을 확인하고 선택해 주세요.'
            except Exception:
                self.server.message = '연결을 완료하지 못했습니다. 권한을 확인하고 다시 로그인해 주세요.'
            self.redirect('/')
        elif parsed.path == '/':
            self.page()
        else:
            self.send_page('페이지가 없습니다.', 404)

    def do_POST(self):
        if not self.trusted(mutation=True):
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length<=0 or length>32768 or self.headers.get('Content-Type','').split(';')[0]!='application/x-www-form-urlencoded':
                raise ValueError()
            fields = parse_qs(self.rfile.read(length).decode(), keep_blank_values=True, max_num_fields=10)
            if any(len(v)!=1 for v in fields.values()) or not hmac.compare_digest(fields.get('csrf',[''])[0], self.server.csrf):
                raise ValueError()
            form = {k:v[0] for k,v in fields.items()}
        except (ValueError, UnicodeError):
            self.send_page('설정 요청을 확인할 수 없습니다.', 403)
            return
        try:
            if self.path == '/login':
                if form.get('consent') != 'yes':
                    raise PlanUnavailable('Consent required')
                settings = self.server.state.settings()
                returning = self.server.state.read(settings['active']+'.json') if settings.get('active') and not self.server.new_account else None
                self.server.pending, location = self.server.account.begin(self.server.origin+'/auth/callback', returning)
                self.redirect(location)
                return
            if self.path == '/models':
                self.server.models = self.server.account.models()
                self.server.message = '현재 계정에서 사용할 수 있는 모델입니다.'
            elif self.path == '/save':
                # Only live, account-provided slugs; never silently substitute a model.
                self.server.models = self.server.account.models()
                model = form.get('model')
                cap = int(form.get('daily_cap','0'))
                if model not in {m['slug'] for m in self.server.models} or not 1<=cap<=10000:
                    raise PlanUnavailable('Invalid selection')
                with self.server.state.lock('worker.lock', blocking=False), self.server.state.lock('control.lock'):
                    settings = self.server.state.settings()
                    settings.update(model=model, daily_cap=cap, enabled=False, pause_reason=None)
                    self.server.state.write('settings.json', settings)
                self.server.message = '설정을 저장했습니다. 자동 처리는 꺼져 있으며, 검증 후 시작합니다.'
            elif self.path == '/pause':
                with self.server.state.lock('control.lock'):
                    settings = self.server.state.settings()
                    settings.update(enabled=False, pause_reason='owner_paused')
                    self.server.state.write('settings.json', settings)
                self.server.message = '자동 처리를 껐습니다. 진행 중인 한 건은 마무리될 수 있습니다.'
            else:
                self.send_page('페이지가 없습니다.',404)
                return
        except Exception:
            self.server.message = '설정을 완료하지 못했습니다. 계정 권한이나 진행 중인 작업을 확인해 주세요.'
        self.redirect('/')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--new-account', action='store_true')
    args = parser.parse_args(argv)
    server = SetupServer(PrivateState(args.state_dir), new_account=args.new_account)
    # Local setup URL contains neither OAuth credentials nor source data.
    log.warning('계정 연결 화면: %s', server.origin)
    try:
        server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    raise SystemExit(main())
