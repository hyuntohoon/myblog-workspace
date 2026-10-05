"""Synthetic OAuth tokens only; no real account, API key or browser session."""
import base64
import hashlib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from scripts.gpt_plan_auth import ISSUER, TOKEN, PlanAccount, PlanUnavailable, PrivateState, REQUIRED


def integer(value):
    return base64.urlsafe_b64encode(value.to_bytes((value.bit_length()+7)//8, 'big')).decode().rstrip('=')


@pytest.fixture
def auth(tmp_path):
    state = PrivateState(tmp_path / 'account')
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    numbers = private.public_key().public_numbers()
    jwks = {'keys': [{'kty':'RSA','kid':'fixture','use':'sig','alg':'RS256','n':integer(numbers.n),'e':integer(numbers.e)}]}
    replies, requests = [], []
    def handle(request):
        requests.append(request)
        if request.url.path.endswith('/jwks.json'):
            return httpx.Response(200,json=jwks)
        return replies.pop(0)
    account = PlanAccount(state, httpx.Client(transport=httpx.MockTransport(handle),timeout=10))
    return state, account, pem, replies, requests


def tokens(pem, expected_nonce, **claims):
    identity = {'iss':ISSUER,'sub':'owner-fixture','aud':'issued-client','exp':int(time.time())+3600,'nonce':expected_nonce, **claims}
    return {'access_token':'fixture-access','refresh_token':'fixture-refresh','token_type':'Bearer','scope':' '.join(REQUIRED),
            'expires_in':3600,'id_token':jwt.encode(identity,pem,algorithm='RS256',headers={'kid':'fixture'})}


def login(auth, **claims):
    _, account, pem, replies, _ = auth
    pending, url = account.begin('http://127.0.0.1:12345/auth/callback')
    response = tokens(pem,pending['nonce'],**claims)
    replies.append(httpx.Response(200,json=response))
    return account.finish(pending,{'state':pending['state'],'code':'fixture-code','client_id':'issued-client'})


def test_private_files_pkce_stable_host_and_disabled_login(auth):
    state, account, _, _, requests = auth
    pending, url = account.begin('http://127.0.0.1:12345/auth/callback')
    fields = parse_qs(urlsplit(url).query)
    assert fields['client_id']==['dynamic_agent_client']
    assert fields['code_challenge']==[base64.urlsafe_b64encode(hashlib.sha256(pending['verifier'].encode()).digest()).decode().rstrip('=')]
    assert fields['ext_agent_host_id']==[state.host_id()]
    key, _ = login(auth)
    assert state.settings()['active']==key and state.settings()['enabled'] is False
    assert os.stat(state.directory / (key+'.json')).st_mode & 0o777 == 0o600
    assert os.stat(state.directory).st_mode & 0o777 == 0o700
    exchange = next(r for r in requests if r.url==TOKEN)
    assert parse_qs(exchange.content.decode())['client_id']==['issued-client']
    assert 'client_secret' not in exchange.content.decode()


@pytest.mark.parametrize('change',['state','expired','dynamic','different_client','declined'])
def test_bad_callback_never_exchanges(auth,change):
    _, account, _, _, requests = auth
    pending, _ = account.begin('http://127.0.0.1:12345/auth/callback')
    query={'state':pending['state'],'code':'fixture-code','client_id':'issued-client'}
    if change=='state':query['state']='wrong'
    if change=='expired':pending['created']-=601
    if change=='dynamic':query['client_id']='dynamic_agent_client'
    if change=='different_client':pending['client_id']='returning-client'
    if change=='declined':query['error']='access_denied'
    with pytest.raises(PlanUnavailable):account.finish(pending,query)
    assert not requests


@pytest.mark.parametrize('bad',[{'iss':'https://wrong.invalid'},{'aud':'wrong'},{'exp':1},{'nonce':'wrong'},{'sub':None}])
def test_identity_fail_closed_does_not_save(auth,bad):
    state, *_ = auth
    with pytest.raises(PlanUnavailable): login(auth,**bad)
    assert state.settings()['active'] is None


@pytest.mark.parametrize('bad',['resource.invoke','',[],None])
def test_returned_plan_scope_required(auth,bad):
    state, account, pem, replies, requests = auth
    pending, _ = account.begin('http://127.0.0.1:12345/auth/callback')
    response=tokens(pem,pending['nonce']);response['scope']=bad
    replies.append(httpx.Response(200,json=response))
    with pytest.raises(PlanUnavailable):account.finish(pending,{'state':pending['state'],'code':'code','client_id':'issued-client','scope':' '.join(REQUIRED)})
    assert state.settings()['active'] is None


def test_returning_account_cannot_be_overwritten(auth):
    state, account, pem, replies, _ = auth
    key, record=login(auth)
    pending,_=account.begin('http://127.0.0.1:12345/auth/callback',record)
    replies.append(httpx.Response(200,json=tokens(pem,pending['nonce'],sub='someone-else')))
    with pytest.raises(PlanUnavailable):account.finish(pending,{'state':pending['state'],'code':'code'})
    assert state.read(key+'.json')['subject']=='owner-fixture'


def test_refresh_is_serial_and_rotates_token(auth):
    state, account, pem, replies, requests = auth
    key,record=login(auth);record['expires_at']=0;state.write(key+'.json',record)
    refresh=tokens(pem,'unused');refresh['refresh_token']='rotated';refresh.pop('scope')
    replies.append(httpx.Response(200,json=refresh))
    with ThreadPoolExecutor(max_workers=2) as pool:
        outputs=list(pool.map(lambda _:account.credentials(), range(2)))
    assert all(o['refresh_token']=='rotated' for o in outputs)
    posts=[r for r in requests if r.method=='POST']
    assert len(posts)==2
    refresh_body=parse_qs(posts[-1].content.decode())
    assert refresh_body['resource']==['https://api.openai.com/v1'] and 'scope' not in refresh_body


@pytest.mark.parametrize('code,clear',[('invalid_grant',True),('refresh_token_reused',True),('server_error',False)])
def test_refresh_failure_never_falls_back(auth,code,clear):
    state, account, _, replies, requests=auth
    key,record=login(auth);record['expires_at']=0;state.write(key+'.json',record)
    replies.append(httpx.Response(400,json={'error':code}))
    with pytest.raises(PlanUnavailable):account.credentials()
    saved=state.read(key+'.json')
    assert ('refresh_token' not in saved)==clear
    assert saved['client_id']=='issued-client'
    assert len([r for r in requests if r.method=='POST'])==2


def test_models_only_returns_account_visible_slugs(auth):
    _,account,_,replies,_=auth
    login(auth)
    replies.append(httpx.Response(200,json={'models':[{'slug':'account-model','display_name':'Account model','visibility':'list'}, {'slug':'hidden','visibility':'hidden'}]}))
    assert account.models()==[{'slug':'account-model','display_name':'Account model'}]


@pytest.mark.parametrize('redirect',['http://localhost:123/auth/callback','http://127.0.0.1:123/other','https://127.0.0.1:123/auth/callback','http://127.0.0.1:123/auth/callback?x=1'])
def test_redirect_is_fixed_loopback(auth,redirect):
    with pytest.raises(PlanUnavailable):auth[1].begin(redirect)


def test_unsafe_file_and_symlink_are_rejected(tmp_path):
    state=PrivateState(tmp_path/'account')
    path=state.directory/'settings.json';path.write_text('{}');path.chmod(0o644)
    with pytest.raises(PlanUnavailable):state.settings()
    path.unlink();path.symlink_to(tmp_path/'other')
    with pytest.raises(PlanUnavailable):state.settings()
