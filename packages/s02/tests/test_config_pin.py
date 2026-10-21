"""S02-05: synthetic T0/T3 config identity, bytes, rollback and checked reads."""
import hashlib
import sqlite3

import pytest

from dacn_s02.errors import S02Error
from dacn_s02.repository import Repository
from dacn_s02.service import artifact, staged
from helpers import aset, evidence, run, uid
from test_audit_guards import attempt_batch


def dump(path):
    with sqlite3.connect(path) as connection:
        return '\n'.join(connection.iterdump())


def prepare(f, pin, *, same_bytes=False, request_pin=None, dispatch=False):
    op=f.operation();op['request']['config_artifact_id']=request_pin
    cmd=op['command_id'];identity=uid()
    raw=f.repo.get_blob(f.config) if same_bytes else b'{"synthetic_config":"T0"}'
    items=[staged(cmd,'Config','config',raw)] if pin=='staged' else []
    if dispatch:
        items += [staged(cmd,'Prompt','prompt',b'Synthetic prompt'),staged(cmd,'Request','llm_request',b'{}')]
    f.repo.prepare(op,staged=items,attempt_id=identity,reused_artifact_ids=[f.config] if pin=='reused' else [])
    if dispatch:
        prep=f.repo.get_command(cmd)['events'][0]
        f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=prep['event_id']),transport_attempt=1))
    arts=[artifact('Art'+s['blob_id'],s['purpose'],data,op['reserved_run_id']) for s,data in items]
    blobs={'Art'+s['blob_id']:data for s,data in items}
    promotions=[dict(stage_ref=dict(command_id=cmd,blob_id=s['blob_id']),artifact_id='Art'+s['blob_id']) for s,_ in items]
    selected='ArtConfig' if pin=='staged' else f.config
    return op,items,arts,blobs,promotions,selected,identity


def result(op,f,config,status):
    errors=[] if status!='failed' else [dict(code='SYNTHETIC_INTERRUPTION',stage='schema',record_id=None,pointer=None,related_ids=[],message='Fixture stopped before dispatch',details={})]
    return run(op,f.context,config,status=status,errors=errors)


def assert_rollback(f,op,batch,blobs,promotions,*,head=None,invariant='attempt_prepared_config'):
    before=dump(f.repo.path);heads=f.repo.heads(f.session)
    with pytest.raises(S02Error) as error:
        f.repo.finalize(op['command_id'],batch,blobs=blobs,promotions=promotions,head=head)
    assert error.value.error['code']=='SCHEMA_INVARIANT'
    assert error.value.error['details']=={'invariant':invariant}
    after=dump(f.repo.path)
    assert after==before  # Independent SQL oracle: all T3 tables, not just Run.
    reopened=Repository(f.repo.path);reopened.verify()
    assert reopened.heads(f.session)==heads
    assert reopened.get_record(op['reserved_run_id']) is None
    assert reopened.get_command(op['command_id'])['state']=='prepared'
    evidence('S02_05_rollback',command_id=op['command_id'],invariant=invariant,
             heads=list(heads),before_sha256=hashlib.sha256(before.encode()).hexdigest(),
             after_sha256=hashlib.sha256(after.encode()).hexdigest(),sql_dump_equal=True)


@pytest.mark.parametrize('pin',['staged','reused','request_only'])
@pytest.mark.parametrize('status',['interrupted','failed'])
def test_config_pin_before_dispatch_positive(foundation,pin,status):
    f=foundation
    op,items,arts,blobs,promotions,selected,_=prepare(f,pin,request_pin=f.config if pin!='staged' else None)
    f.repo.finalize(op['command_id'],arts+[result(op,f,selected,status)],blobs=blobs,promotions=promotions)
    reopened=Repository(f.repo.path);reopened.verify()
    actual=reopened.get_command(op['command_id'])
    assert actual['run']['body']['config_artifact_id']==selected
    assert actual['run']['body']['attempts']==[]
    assert [e['kind'] for e in actual['events']]==['prepared','finalized']
    assert reopened.get_blob(selected)==(items[0][1] if pin=='staged' else f.repo.get_blob(f.config))
    assert reopened.heads(f.session)==(None,None)
    evidence('S02_05_positive',pin=pin,status=status,selected=selected,attempts=[],bytes_preserved=True)


@pytest.mark.parametrize('pin',['staged','reused'])
@pytest.mark.parametrize('same_bytes',[False,True])
@pytest.mark.parametrize('status',['interrupted','failed'])
def test_wrong_identity_rejected_even_if_same_bytes(foundation,pin,same_bytes,status):
    f=foundation;op,items,arts,blobs,promotions,selected,_=prepare(f,pin,same_bytes=same_bytes)
    raw=(items[0][1] if pin=='staged' else f.repo.get_blob(f.config)) if same_bytes else b'{"different":true}'
    arts.append(artifact('Substitute','config',raw,op['reserved_run_id']));blobs['Substitute']=raw
    assert_rollback(f,op,arts+[result(op,f,'Substitute',status)],blobs,promotions)


@pytest.mark.parametrize('pin',['staged','reused'])
def test_config_mismatch_rolls_back_head_publication(foundation,pin):
    f=foundation;m,a=f.initial()
    op,_,arts,blobs,promotions,_,_=prepare(f,pin)
    raw=b'{}';arts.append(artifact('Substitute','config',raw,op['reserved_run_id']));blobs['Substitute']=raw
    new_set=aset(m,'AS2',a,changed=[])
    rr=run(op,f.context,'Substitute',set_id='AS2')
    assert_rollback(f,op,arts+[new_set,rr],blobs,promotions,head=('M1','AS2'))
    assert f.repo.get_record('AS2') is None


@pytest.mark.parametrize('pin',['staged','reused','request_only'])
@pytest.mark.parametrize('choose_request',[False,True])
def test_request_pin_must_agree_with_prepared_and_run(foundation,pin,choose_request):
    f=foundation
    seed=f.operation();f.repo.prepare(seed);raw=f.repo.get_blob(f.config)
    f.repo.finalize(seed['command_id'],[artifact('OtherConfig','config',raw,seed['reserved_run_id']),run(seed,f.context,f.config)],blobs={'OtherConfig':raw})
    op,_,arts,blobs,promotions,selected,_=prepare(f,pin,request_pin='OtherConfig')
    if choose_request and pin=='request_only':
        # Positive: request-only pin, no prepared config and no dispatch.
        f.repo.finalize(op['command_id'],[result(op,f,'OtherConfig','interrupted')])
        Repository(f.repo.path).verify()
    else:
        config='OtherConfig' if choose_request else selected
        invariant='attempt_prepared_config' if choose_request else 'run_intent_config'
        assert_rollback(f,op,arts+[result(op,f,config,'interrupted')],blobs,promotions,invariant=invariant)


@pytest.mark.parametrize('fault',['missing_promotion','wrong_bytes'])
def test_staged_config_requires_exact_promotion(foundation,fault):
    f=foundation;op,_,arts,blobs,promotions,selected,_=prepare(f,'staged')
    if fault=='missing_promotion':promotions=[]
    else:
        blobs[selected]=b'{"substituted":true}'
        arts[0]=artifact(selected,'config',blobs[selected],op['reserved_run_id'])
    assert_rollback(f,op,arts+[result(op,f,selected,'interrupted')],blobs,promotions,
                    invariant='attempt_prepared_config' if fault=='missing_promotion' else 'promotion_exact_bytes')


@pytest.mark.parametrize('pin',['staged','reused'])
def test_checked_read_rejects_bad_pre_dispatch_history(foundation,monkeypatch,pin):
    f=foundation;op,_,arts,blobs,promotions,_,_=prepare(f,pin)
    raw=f.repo.get_blob(f.config)
    arts.append(artifact('Substitute','config',raw,op['reserved_run_id']));blobs['Substitute']=raw
    # Synthetic legacy fixture only: bypass operational gate while writing this
    # temporary DB, then restore it before every checked read. No audit DB edit.
    with monkeypatch.context() as injection:
        injection.setattr('dacn_s02.events.validate_operations',lambda *a,**k:None)
        f.repo.finalize(op['command_id'],arts+[result(op,f,'Substitute','interrupted')],blobs=blobs,promotions=promotions)
    before=dump(f.repo.path);reopened=Repository(f.repo.path)
    for label,call in [('verify',reopened.verify),('get_command',lambda:reopened.get_command(op['command_id'])),
                       ('get_record',lambda:reopened.get_record(op['reserved_run_id']))]:
        with pytest.raises(S02Error) as error:call()
        assert error.value.error['code']=='PERSISTENCE_FAILED'
        assert error.value.__cause__.error['details']=={'invariant':'attempt_prepared_config'}
        assert dump(f.repo.path)==before
        evidence('S02_05_checked_read',pin=pin,lookup=label,rejected=True,fixture='temporary DB operational-gate bypass')


@pytest.mark.parametrize('pin',['staged','reused'])
def test_config_pin_after_dispatch_remains_valid(foundation,pin):
    f=foundation;op,items,_,_,promotions,selected,identity=prepare(f,pin,dispatch=True)
    batch,blobs,promotions,attempt=attempt_batch(f,op,identity,items,'unknown_outcome')
    attempt['response_artifact_id']=None;batch[-1]['body']['config_artifact_id']=selected
    f.repo.finalize(op['command_id'],batch,blobs=blobs,promotions=promotions)
    reopened=Repository(f.repo.path);reopened.verify()
    actual=reopened.get_command(op['command_id'])
    assert actual['run']['body']['config_artifact_id']==selected
    assert actual['run']['body']['attempts']==[attempt]
    assert [e['kind'] for e in actual['events']]==['prepared','dispatch_intent','finalized']
