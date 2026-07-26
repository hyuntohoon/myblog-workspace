#!/usr/bin/env python3
"""Assemble the per-house fragments into one switchable page.

Each house is written by its own agent and owns its whole visual world — including
whether it is light or dark, which is why the shell does not impose a theme on the
stage. The only thing the shell enforces is isolation: every house's CSS must be
prefixed with its own `.h-<slug>` class, checked here rather than trusted, because
six independently-authored stylesheets on one page will otherwise fight.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Paths resolve from this file, so the record stays runnable wherever the repo sits.
# The lyric-bearing data and the assembled page live in the gitignored .
BASE = Path(__file__).resolve().parent
HOUSES = BASE / "houses"
DATA = BASE / "local" / "lux_mock_data.json"
OUT = BASE / "local" / "annotation_houses.html"

ORDER = ["genius", "apple", "spotify", "medium", "notion", "nyt"]

# A rule whose selector may legitimately lack the class prefix.
_ALLOWED_AT = re.compile(r"^\s*@(media|supports|keyframes|font-face|layer|container|charset)\b", re.I)


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def check_namespace(slug: str, css: str) -> list[str]:
    """Every selector must carry `.h-<slug>`. Returns a list of offending selectors."""
    ns = f".h-{slug}"
    bad: list[str] = []
    body = strip_comments(css)

    # Walk brace-balanced blocks so nested at-rules are handled.
    depth = 0
    buf = ""
    at_stack: list[bool] = []          # True where the enclosing at-rule scopes selectors
    for ch in body:
        if ch == "{":
            sel = buf.strip()
            buf = ""
            if _ALLOWED_AT.match(sel):
                # keyframes/font-face bodies hold percentages/descriptors, not selectors
                at_stack.append(sel.lower().startswith(("@keyframes", "@font-face")))
                depth += 1
                continue
            at_stack.append(False)
            depth += 1
            if any(at_stack[:-1]) or not sel:
                continue
            for one in sel.split(","):
                one = one.strip()
                if one and ns not in one:
                    bad.append(one[:90])
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            if at_stack:
                at_stack.pop()
            buf = ""
            continue
        buf += ch

    # Custom properties and keyframes must be namespaced too.
    for m in re.finditer(r"@keyframes\s+([A-Za-z0-9_-]+)", body):
        if not m.group(1).startswith(f"h-{slug}"):
            bad.append(f"@keyframes {m.group(1)} (must start with h-{slug})")
    if re.search(r":root\s*\{", body):
        bad.append(":root (must be scoped to .h-%s)" % slug)
    return bad


def extract(tag: str, text: str) -> list[str]:
    return re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.S | re.I)


def main() -> int:
    data = DATA.read_text()
    styles: list[str] = []
    scripts: list[str] = []
    found: list[str] = []
    problems: dict[str, list[str]] = {}

    for slug in ORDER:
        path = HOUSES / f"{slug}.html"
        if not path.exists():
            print(f"  [skip] {slug}: no file")
            continue
        raw = path.read_text()

        if re.search(r"<(!doctype|html|head|body)\b", raw, re.I):
            problems.setdefault(slug, []).append("contains a page wrapper tag")
        ext = [u for u in re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)""", raw)
               if u.startswith(("http://", "https://", "//"))]
        if ext:
            problems.setdefault(slug, []).append(f"external request: {ext[:2]}")
        if re.search(r"@import\b", raw):
            problems.setdefault(slug, []).append("@import present")

        css = "\n".join(extract("style", raw))
        js = "\n".join(extract("script", raw))
        if not css.strip() or "HOUSES" not in js:
            problems.setdefault(slug, []).append("missing <style> or HOUSES registration")

        leaks = check_namespace(slug, css)
        if leaks:
            problems.setdefault(slug, []).append(f"{len(leaks)} unprefixed selector(s): {leaks[:5]}")

        styles.append(f"/* ===== {slug} ===== */\n{css}")
        scripts.append(f"/* ===== {slug} ===== */\n{js}")
        found.append(slug)

    for slug, errs in problems.items():
        for e in errs:
            print(f"  [FAIL] {slug}: {e}")
    if problems:
        print("\nassembly aborted — fix the fragments above")
        return 1
    if not found:
        print("no fragments found")
        return 1

    OUT.write_text(SHELL.replace("/*__STYLES__*/", "\n".join(styles))
                        .replace("/*__SCRIPTS__*/", "\n".join(scripts))
                        .replace("__DATA__", data)
                        .replace("__ORDER__", json.dumps(found)))
    print(f"\nassembled {len(found)} houses -> {OUT}  ({OUT.stat().st_size // 1024} KB)")
    return 0


SHELL = r"""<title>가사 주석 · 여섯 가지 디자인 언어</title>
<style>
/* ---- shell chrome only. The stage below belongs entirely to each house. ---- */
.shell{font-family:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  color:#1a1a1a;background:#e9e6e0;min-height:100vh;display:flex;flex-direction:column;}
@media (prefers-color-scheme:dark){.shell{color:#ebe7df;background:#0e0d0c;}}
:root[data-theme="dark"] .shell{color:#ebe7df;background:#0e0d0c;}
:root[data-theme="light"] .shell{color:#1a1a1a;background:#e9e6e0;}

.shell-bar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:10px 18px;
  align-items:center;padding:10px 16px;backdrop-filter:blur(12px);
  background:color-mix(in srgb,#e9e6e0 78%,transparent);border-bottom:1px solid rgba(0,0,0,.12);}
@media (prefers-color-scheme:dark){.shell-bar{background:color-mix(in srgb,#0e0d0c 78%,transparent);
  border-bottom-color:rgba(255,255,255,.14);}}
:root[data-theme="dark"] .shell-bar{background:color-mix(in srgb,#0e0d0c 78%,transparent);
  border-bottom-color:rgba(255,255,255,.14);}
:root[data-theme="light"] .shell-bar{background:color-mix(in srgb,#e9e6e0 78%,transparent);
  border-bottom-color:rgba(0,0,0,.12);}

.shell-title{font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.62;
  font-family:'IBM Plex Mono',ui-monospace,monospace;white-space:nowrap;}
.shell-group{display:flex;gap:4px;flex-wrap:wrap;}
.shell-btn{appearance:none;border:1px solid currentColor;background:transparent;color:inherit;
  font:inherit;font-size:12.5px;padding:5px 11px;border-radius:2px;cursor:pointer;opacity:.5;
  transition:opacity .15s;}
.shell-btn:hover{opacity:.85;}
.shell-btn[aria-pressed="true"]{opacity:1;background:currentColor;}
.shell-btn[aria-pressed="true"] span{color:#e9e6e0;mix-blend-mode:normal;}
@media (prefers-color-scheme:dark){.shell-btn[aria-pressed="true"] span{color:#0e0d0c;}}
:root[data-theme="dark"] .shell-btn[aria-pressed="true"] span{color:#0e0d0c;}
:root[data-theme="light"] .shell-btn[aria-pressed="true"] span{color:#e9e6e0;}
.shell-btn:focus-visible{outline:2px solid #c8332b;outline-offset:2px;}

.shell-note{padding:8px 16px 0;font-size:12.5px;line-height:1.65;opacity:.72;max-width:70ch;}
.shell-note b{font-weight:600;opacity:1;}
.shell-stage{flex:1;margin:12px 16px 16px;min-height:78vh;position:relative;overflow:hidden;
  border:1px solid rgba(0,0,0,.14);}
@media (prefers-color-scheme:dark){.shell-stage{border-color:rgba(255,255,255,.14);}}
.shell-foot{padding:0 16px 26px;font-size:12px;line-height:1.7;opacity:.6;max-width:78ch;}
.shell-foot code{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11.5px;}
@media (max-width:520px){.shell-title{display:none;}}
/*__STYLES__*/
</style>

<div class="shell">
  <div class="shell-bar">
    <span class="shell-title">가사 주석 · 디자인 언어 비교</span>
    <div class="shell-group" id="houseBtns" role="group" aria-label="디자인 언어"></div>
    <div class="shell-group" role="group" aria-label="곡">
      <button class="shell-btn" data-track="11" aria-pressed="true"><span>T11 밀집</span></button>
      <button class="shell-btn" data-track="10" aria-pressed="false"><span>T10 드문</span></button>
    </div>
  </div>

  <p class="shell-note" id="houseNote"></p>
  <div class="shell-stage" id="stage"></div>

  <p class="shell-foot">
    각 화면은 유명 제품의 <b>시각 언어를 참조한 디자인 습작</b>이다 — 로고·워드마크를 쓰지 않았고, 해당 회사의
    제품이 아니다. 실제 서체(SF Pro · Circular · Programme 등)는 쓸 수 없어 가장 가까운 시스템 서체로 대체했으므로,
    글자 모양보다 <b>비례·굵기·간격·밀도</b>를 봐 달라. 내용은 ROSALÍA <i>LUX</i>의 실제 가사와 실제 Genius 주석
    (한국어 번역본)이며, 밀집 곡 <code>T11</code>과 드문 곡 <code>T10</code>은 같은 설계가 양 극단에서 어떻게
    버티는지 보기 위한 것이다. 모든 주석은 검증되지 않은 팬 작성이고, 음수 득표는 공동체가 이견을 낸 읽기다.
  </p>
</div>

<script>
const LUX = __DATA__;
const ORDER = __ORDER__;
</script>
<script>
/*__SCRIPTS__*/
</script>
<script>
(function () {
  const stage = document.getElementById('stage');
  const note  = document.getElementById('houseNote');
  const btns  = document.getElementById('houseBtns');
  let house = ORDER[0];
  let track = 11;

  ORDER.forEach(slug => {
    const h = window.HOUSES && window.HOUSES[slug];
    if (!h) return;
    const b = document.createElement('button');
    b.className = 'shell-btn';
    b.dataset.house = slug;
    b.setAttribute('aria-pressed', String(slug === house));
    b.innerHTML = '<span></span>';
    b.firstChild.textContent = h.name || slug;
    btns.appendChild(b);
  });

  function render() {
    const h = window.HOUSES[house];
    stage.innerHTML = '';
    note.innerHTML = '';
    if (!h) { stage.textContent = '이 디자인 언어는 불러오지 못했다.'; return; }
    const bits = [];
    if (h.ref)      bits.push('<b>' + h.ref + '</b>');
    if (h.blurb)    bits.push(h.blurb);
    if (h.gives_up) bits.push('<span style="opacity:.8">포기하는 것 — ' + h.gives_up + '</span>');
    note.innerHTML = bits.join(' · ');
    try { h.mount(stage, LUX, track); }
    catch (e) { stage.textContent = '오류: ' + e.message; }
    btns.querySelectorAll('[data-house]').forEach(b =>
      b.setAttribute('aria-pressed', String(b.dataset.house === house)));
  }

  btns.addEventListener('click', e => {
    const b = e.target.closest('[data-house]'); if (!b) return;
    house = b.dataset.house; render();
  });
  document.querySelectorAll('[data-track]').forEach(b => b.addEventListener('click', () => {
    track = Number(b.dataset.track);
    document.querySelectorAll('[data-track]').forEach(x =>
      x.setAttribute('aria-pressed', String(Number(x.dataset.track) === track)));
    render();
  }));

  render();
})();
</script>
"""


if __name__ == "__main__":
    sys.exit(main())
