"""LP-01 focused integration: installed handlers, synthetic fake provider only."""
from dataclasses import replace
from pathlib import Path
import pytest

from dacn_s01.repository import Repository as S01Repository
from dacn_s02.codec_boundary import decode, encode
from dacn_s02.errors import S02Error
from dacn_s02.local_io import Settings
from dacn_s02.local_service import LocalService
from dacn_s02.local_transport import Exchange
from dacn_s02.local_work import identity
from dacn_s02.repository import Repository
from h1_fixtures import input_data, mocks


class FakeProvider:
    origin='synthetic_mock'
    def __init__(self, mode='valid'):
        self.calls=[];self.mode=mode
    def configuration(self):return dict(test_fixture='fake_provider',mode=self.mode)
    def pin(self):return dict(model='fake-local',model_digest='f'*64,endpoint='http://127.0.0.1:1',runtime='fake-test-only')
    def bound(self,messages):return dict(eligible=True,input_upper_bound=20000,method='test_fixture_not_real_token_proof')
    def send(self,request,remaining):
        self.calls.append(request)
        messages=decode(request)['messages'];payload=decode(messages[1]['content'].encode())
        step=payload['output_schema']['properties']['step']['const'];snapshot=payload['context']['snapshot']
        candidate=mocks(snapshot)[int(step)-1]
        if self.mode=='held':candidate['inspection'][0]['verdict']='held'
        raw=encode(dict(model='fake-local',message=dict(role='assistant',content=encode(candidate).decode()),done=True,done_reason='stop',prompt_eval_count=10,eval_count=20))
        if self.mode=='invalid':raw=b'{"bad":'
        if self.mode=='partial':return Exchange(200,(),raw[:10],False,True,'timeout',1)
        return Exchange(200,(('content-type','application/json'),),raw,True,True,None,1)


def setup(tmp_path, mode='valid'):
    s01dir=tmp_path/'s01';s01dir.mkdir();s01=s01dir/'s01.sqlite3';S01Repository(s01).initialize()
    state=tmp_path/'s02';state.mkdir();Repository(state/'s02.sqlite3').initialize()
    config=tmp_path/'s02.toml';config.write_text(f'state_dir="{state}"\n[s01_stores]\nlocal="{s01}"\n')
    settings=Settings(config,state,{'local':s01},(),5000)
    source=tmp_path/'input.json';source.write_bytes(encode(input_data()))
    return settings,source,tmp_path/'receipt.json',FakeProvider(mode)


def test_local_fake_four_steps_and_endpointless_finalized_report(tmp_path):
    s,source,receipt,provider=setup(tmp_path)
    service=LocalService(s,provider)
    result=service.analyze(receipt=receipt,store_key='local',input_path=source)
    assert result['status']=='completed' and result['result']['completed_through']==4,result
    assert len(provider.calls)==4
    assert result['result']['semantic_status']=='unreviewed_draft'
    assert result['result']['execution_origin']=='synthetic_mock'
    assert len(result['result']['mappings'])==6
    assert LocalService(s).resume(receipt=receipt)==result
    (s.state/'local-journal.sqlite3').rename(s.state/'journal.saved')
    assert LocalService(s).report(receipt=receipt)==result
    assert len(provider.calls)==4


@pytest.mark.parametrize('mode,status', [('held','blocked'),('invalid','rejected'),('partial','interrupted')])
def test_local_failures_preserve_raw_and_no_resend(tmp_path,mode,status):
    s,source,receipt,provider=setup(tmp_path,mode)
    service=LocalService(s,provider);result=service.analyze(receipt=receipt,store_key='local',input_path=source)
    assert result['status']==status,result
    assert len(provider.calls)==1
    assert LocalService(s).resume(receipt=receipt)==result
    attempt=result['result']['attempts'][0]
    events=service.repo.get_command(result['command_id'])['events']
    if mode=='partial':
        assert attempt['status']=='unknown_outcome' and attempt['response_artifact_id'] is None and attempt['usage'] is None
        assert not any(e['kind']=='response_received' for e in events)
    else:
        assert attempt['response_artifact_id'] is not None
        assert any(e['kind']=='response_received' for e in events)


class Crash(BaseException):pass

@pytest.mark.parametrize('point,calls,terminal', [('after_s01_claim',0,'interrupted'),('after_s01_submit',4,'completed'),('after_intake_prepare',4,'completed'),('after_claim',0,'interrupted'),('after_intent',0,'interrupted'),('after_http',1,'interrupted'),('after_capture',4,'completed'),('after_response_event',4,'completed')])
def test_local_crash_reopen_exact_work(tmp_path,point,calls,terminal):
    s,source,receipt,provider=setup(tmp_path)
    def hook(p):
        if p==point:raise Crash()
    with pytest.raises(Crash):LocalService(s,provider,_hook=hook).analyze(receipt=receipt,store_key='local',input_path=source)
    result=LocalService(s,provider).resume(receipt=receipt)
    assert result['status']==terminal,result
    assert len(provider.calls)==calls


def test_context_gate_is_durable_without_dispatch(tmp_path):
    s,source,receipt,provider=setup(tmp_path)
    provider.bound=lambda messages:dict(eligible=False,input_upper_bound=None,method='test_unknown_tokenizer')
    result=LocalService(s,provider).analyze(receipt=receipt,store_key='local',input_path=source)
    assert result['status']=='blocked' and not provider.calls
    assert result['result']['attempts']==[] and result['errors'][0]['code']=='LOCAL_CONTEXT_BLOCKED'
    assert LocalService(s).resume(receipt=receipt)==result
    assert LocalService(s).report(receipt=receipt)==result


def test_valid_capture_survives_removed_external_s01(tmp_path):
    s,source,receipt,provider=setup(tmp_path)
    def hook(point):
        if point=='after_capture':raise Crash()
    with pytest.raises(Crash):LocalService(s,provider,_hook=hook).analyze(receipt=receipt,store_key='local',input_path=source)
    s.stores['local'].rename(tmp_path/'saved-source.sqlite3')
    result=LocalService(s,provider).resume(receipt=receipt)
    assert result['status']=='completed' and len(provider.calls)==4


def test_changed_journal_blocks_publication(tmp_path):
    s,source,receipt,provider=setup(tmp_path);service=LocalService(s,provider)
    def hook(point):
        if point=='before_publish':
            (s.state/'local-journal.sqlite3').rename(s.state/'removed-journal.sqlite3')
    service.hook=hook
    with pytest.raises(S02Error,match='journal missing'):service.analyze(receipt=receipt,store_key='local',input_path=source)
    assert not provider.calls
    with service.repo._read() as c:
        assert c.execute("SELECT COUNT(*) FROM records WHERE type='model'").fetchone()[0]==0


@pytest.mark.parametrize('change',['request','body','missing'])
def test_pending_capture_integrity_fail_closed(tmp_path,change):
    import sqlite3
    from dacn_s02.repository import digest
    s,source,receipt,provider=setup(tmp_path)
    def hook(point):
        if point=='after_capture':raise Crash()
    with pytest.raises(Crash):LocalService(s,provider,_hook=hook).analyze(receipt=receipt,store_key='local',input_path=source)
    db=s.state/'local-journal.sqlite3'
    if change=='missing':db.rename(s.state/'lost-journal.sqlite3')
    else:
        with sqlite3.connect(db) as c:
            # Update the outer hash too; nested request/capture binding must still catch it.
            c.execute(f'UPDATE work SET {change}=?,{change}_sha=? WHERE step=1',(b'changed',digest(b'changed')))
    with pytest.raises(S02Error):LocalService(s,provider).resume(receipt=receipt)
    assert len(provider.calls)==1


def test_new_receipt_and_input_cannot_reset_campaign(tmp_path):
    s,source,receipt,provider=setup(tmp_path)
    result=LocalService(s,provider).analyze(receipt=receipt,store_key='local',input_path=source)
    assert result['status']=='completed' and len(provider.calls)==4
    with pytest.raises(S02Error,match='campaign_already_bound'):
        LocalService(s,provider).analyze(receipt=tmp_path/'new.json',store_key='local',input_path=source)
    source.write_bytes(encode(dict(input_data(),title='changed')))
    with pytest.raises(S02Error,match='flow_intent_conflict'):
        LocalService(s,provider).analyze(receipt=receipt,store_key='local',input_path=source)
    assert len(provider.calls)==4
