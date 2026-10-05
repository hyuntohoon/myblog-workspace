"""Loopback control checks with fake OAuth/model providers."""
import sys
from pathlib import Path
from threading import Thread

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import httpx
import pytest
from scripts.gpt_plan_auth import PrivateState
from scripts.gpt_worker_setup import SetupServer


class FakeAccount:
    def __init__(self):
        self.logins=[];self.finishes=[]
    def begin(self,redirect,returning=None):
        self.logins.append(redirect)
        return {'state':'fixture'},'https://auth.openai.com/api/accounts/authorize?state=fixture'
    def finish(self,pending,query):
        self.finishes.append(query)
    def models(self):
        return [{'slug':'allowed','display_name':'Allowed model'}]


@pytest.fixture
def ui(tmp_path):
    state=PrivateState(tmp_path/'private')
    account=FakeAccount()
    server=SetupServer(state,account)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield server,httpx.Client(base_url=server.origin,timeout=5,follow_redirects=False)
    server.shutdown();thread.join();server.server_close()


def post(ui,path,data,**kwargs):
    server,client=ui
    return client.post(path,data={'csrf':server.csrf,**data},headers={'Origin':server.origin,**kwargs})


def test_login_requires_same_origin_csrf_and_consent(ui):
    server,client=ui
    assert client.post('/login',data={'csrf':server.csrf,'consent':'yes'}).status_code==403
    assert post(ui,'/login',{'csrf':'wrong','consent':'yes'}).status_code==403
    post(ui,'/login',{})
    assert not server.account.logins
    response=post(ui,'/login',{'consent':'yes'})
    assert response.status_code==303
    assert response.headers['location'].startswith('https://auth.openai.com/')
    assert server.account.logins==[server.origin+'/auth/callback']
    assert not server.state.settings()['enabled']


def test_host_validation_and_headers(ui):
    server,client=ui
    assert client.get('/',headers={'Host':'attacker.invalid'}).status_code==403
    response=client.get('/')
    assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert 'https://auth.openai.com' in response.headers['content-security-policy']
    assert 'Continue with ChatGPT' in response.text


def test_model_selection_only_accepts_catalog_and_remains_disabled(ui):
    server,_=ui
    post(ui,'/save',{'model':'forged','daily_cap':'100'})
    assert server.state.settings()['model'] is None
    post(ui,'/save',{'model':'allowed','daily_cap':'8'})
    settings=server.state.settings()
    assert settings['model']=='allowed' and settings['daily_cap']==8 and not settings['enabled']


def test_callback_single_use_duplicate_params_rejected_and_account_switch_locked(ui):
    server,client=ui
    post(ui,'/login',{'consent':'yes'})
    assert client.get('/auth/callback?state=fixture&state=other&code=secret').status_code==303
    assert not server.account.finishes
    post(ui,'/login',{'consent':'yes'})
    with server.state.lock('worker.lock'):
        assert client.get('/auth/callback?state=fixture&code=secret').status_code==303
    assert not server.account.finishes
    post(ui,'/login',{'consent':'yes'})
    client.get('/auth/callback?state=fixture&code=secret')
    client.get('/auth/callback?state=fixture&code=secret')
    assert len(server.account.finishes)==1


def test_pause_preserves_queue_and_model(ui):
    server,_=ui
    server.state.write('settings.json',{'enabled':True,'model':'allowed','daily_cap':8})
    post(ui,'/pause',{})
    settings=server.state.settings()
    assert not settings['enabled'] and settings['pause_reason']=='owner_paused' and settings['model']=='allowed'
