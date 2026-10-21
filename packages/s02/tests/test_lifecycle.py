from copy import deepcopy
import sqlite3
import pytest
from dacn_s02.repository import Repository,record
from dacn_s02.service import staged,artifact
from dacn_s02.codec_boundary import decode
from dacn_s02.errors import S02Error
from dacn_s02.scope import make_scope
from helpers import run,aset,issue,uid,evidence,allscope

def capture(f):
    op=f.operation();cmd=op['command_id'];attempt=uid()
    inputs=[staged(cmd,'Prompt','prompt',b'Prompt fixture'),staged(cmd,'Request','llm_request',b'{"synthetic":true}')]
    f.repo.prepare(op,staged=inputs,attempt_id=attempt)
    e=f.repo.get_command(cmd)['events'][0]
    f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=e['event_id']),transport_attempt=1))
    response=staged(cmd,'Response','llm_response',b'{ invalid \xff')
    f.repo.append_event(cmd,'response_received',dict(response=dict(command_id=cmd,blob_id='Response'),http_status=200,safe_headers={'content-type':'application/json'},requested_model='stub',returned_model=None,provider_response_id=None,usage=None,elapsed_ms=7),staged=[response])
    return op,attempt,inputs+[response]

def test_f02_staging_invalid_capture_reopen_promote(foundation):
    f=foundation;op,attempt,items=capture(f);cmd=op['command_id']
    repo=Repository(f.repo.path);assert repo.get_command(cmd)['state']=='captured'
    with sqlite3.connect(repo.path) as c:
        assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert c.execute('SELECT COUNT(*) FROM records WHERE id=?',(op['reserved_run_id'],)).fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM artifacts WHERE producer_run_id=?',(op['reserved_run_id'],)).fetchone()[0]==0
    # Recovery consists exclusively of checked reads of captured bytes; no send API exists here.
    raw=repo.get_stage(cmd,'Response')['bytes'];assert raw==b'{ invalid \xff'
    with pytest.raises(S02Error): decode(raw)
    arts=[artifact('Art'+i['blob_id'],i['purpose'],raw,op['reserved_run_id']) for i,raw in items]
    blobs={'Art'+i['blob_id']:raw for i,raw in items}
    a=dict(id=attempt,step=2,base_model_id=None,base_analysis_set_id=None,prompt_artifact_id='ArtPrompt',request_artifact_id='ArtRequest',response_artifact_id='ArtResponse',provider='local-stub',requested_model='stub',returned_model=None,provider_response_id=None,transport_attempt=1,repair_round=0,status='invalid_output',usage=None,elapsed_ms=7)
    error=dict(code='INVALID_JSON',stage='parse',record_id=None,pointer=None,related_ids=[],message='Synthetic invalid response',details={'reason':'Malformed JSON'})
    rr=run(op,f.context,f.config,status='rejected',attempts=[a],errors=[error])
    repo.finalize(cmd,arts+[rr],blobs=blobs,promotions=[dict(stage_ref=dict(command_id=cmd,blob_id=i['blob_id']),artifact_id='Art'+i['blob_id']) for i,_ in items])
    reopened=Repository(repo.path);assert reopened.get_command(cmd)['state']=='finalized'
    assert reopened.get_blob('ArtResponse')==raw;assert reopened.get_stage(cmd,'Response')['bytes']==raw
    assert reopened.heads(f.session)==(None,None)
    evidence('F02_invalid_captured',command_id=cmd,raw_hex=raw.hex(),state='finalized',run_status='rejected',heads=[None,None])

def test_f02_prepared_and_dispatch_unknown(foundation):
    f=foundation;op=f.operation();f.repo.prepare(op)
    before=f.repo.get_command(op['command_id']);assert before['state']=='prepared'
    event=before['events'][0];f.repo.append_event(op['command_id'],'dispatch_intent',dict(prepared_event=dict(command_id=op['command_id'],event_id=event['event_id']),transport_attempt=1))
    r=Repository(f.repo.path);assert r.get_command(op['command_id'])['state']=='dispatch_unknown'
    assert r.get_command(op['command_id'])['state']=='dispatch_unknown' # lookup cannot invent a response or retry
    evidence('F02_unknown',state='dispatch_unknown',events=['prepared','dispatch_intent'])

def add_answer(f):
    m,a=f.initial(True);op=f.operation();f.repo.prepare(op)
    answer=record('answer','Answer1',dict(issue_id='Q2',supersedes_answer_id=None,respondent='Synthetic tester',recorded_by='Fixture',text='  Point to existing source only.  ',interpretation='points_to_existing_source',existing_source_refs=[dict(snapshot_id=f.snapshot,input_pointer='/functional_requirements/0')]))
    f.repo.finalize(op['command_id'],[answer,run(op,f.context,f.config)])
    return m,a,answer

def application_batch(f,m,a,answer):
    op=f.operation(kind='apply_answer',answer_id=answer['id'],issue_key='Question2');f.repo.prepare(op)
    interpretation=f.repo.append_event(op['command_id'],'interpretation_selected',dict(answer_id=answer['id'],interpretation='points_to_existing_source',explanation='Synthetic existing-source interpretation',existing_source_refs=answer['body']['existing_source_refs'],proposed_input=None,s01_request=None))
    e_id=uid();e_ref=dict(command_id=op['command_id'],event_id=e_id)
    new=deepcopy(m);new['id']='M2';new['body'].update(revision=2,parent_model_id=m['id'],change_id='CH1',created_by_run_id=op['reserved_run_id'])
    q=issue(new,'Q2-resolved',parent='Q2',status='resolved');q['body'].update(answer_ids=[answer['id']],resolution_event_refs=[e_ref],resolution='Synthetic applied answer; no business confirmation',blocking=make_scope('M2'))
    change=record('change','CH1',dict(base_model_id=m['id'],new_model_id='M2',kind='analysis_edit',old_source_context_id=f.context,new_source_context_id=f.context,reason='Synthetic application fixture only',source_record_ids=[answer['id'],'Q2'],application_event_refs=[e_ref],operations=[],affected=allscope(new),reused=[],reevaluate=[],invalidated_bundle_ids=[]))
    newset=aset(new,'AS-M2',issues=[q['id']]);rr=run(op,f.context,f.config,model_id='M2',set_id='AS-M2')
    payload=dict(answer_id=answer['id'],interpretation_event=dict(command_id=op['command_id'],event_id=interpretation['event_id']),consent_event=None,s01_observation_event=None,change_id=change['id'],new_source_context_id=f.context,resolved_issue_id=q['id'])
    return op,[new,q,change,newset,rr],[('application_applied',payload,e_id)]

def test_f03_immutable_answer_atomic_application_unique(foundation):
    f=foundation;m,a,answer=add_answer(f);op,batch,events=application_batch(f,m,a,answer)
    f.repo.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events)
    r=Repository(f.repo.path);assert r.get_record('Answer1')==answer
    applied=[e for e in r.get_command(op['command_id'])['events'] if e['kind']=='application_applied'];assert len(applied)==1
    assert r.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events)==batch[-1]
    with pytest.raises(S02Error) as e: r.prepare(f.operation(kind='apply_answer',answer_id='Answer1',issue_key='Question2'))
    assert e.value.error['code']=='APPLICATION_CONFLICT'
    with sqlite3.connect(r.path) as c:
        with pytest.raises(sqlite3.IntegrityError): c.execute("UPDATE operation_events SET payload_json='{}'")
    evidence('F03_atomic_application',answer_id='Answer1',applied_events=1,heads=r.heads(f.session),full_business_flow=False)

def test_f03_consent_exact_and_recovery_identity(foundation):
    f=foundation;m,a,answer=add_answer(f);op=f.operation(kind='apply_answer',answer_id='Answer1',issue_key='Question2');cmd=op['command_id'];f.repo.prepare(op)
    input_stage=staged(cmd,'Input','requirement_update_input',f.raw)
    interpretation=f.repo.append_event(cmd,'interpretation_selected',dict(answer_id='Answer1',interpretation='changes_requirements',explanation='Synthetic input proposal, not real user consent',existing_source_refs=[],proposed_input=dict(command_id=cmd,blob_id='Input'),s01_request=dict(mode='update',spec_id=f.s01env['snapshot']['spec_id'],base_revision=1)),staged=[input_stage])
    consent=dict(answer_id='Answer1',interpretation_event=dict(command_id=cmd,event_id=interpretation['event_id']),respondent='Fixture',text='Synthetic consent fixture',approved_input_sha256='0'*64)
    with pytest.raises(S02Error): f.repo.append_event(cmd,'consent_recorded',consent)
    consent['approved_input_sha256']=input_stage[0]['sha256'];ev=f.repo.append_event(cmd,'consent_recorded',consent)
    f.repo.append_event(cmd,'recovery_observed',dict(answer_id='Answer1',related_event=dict(command_id=cmd,event_id=ev['event_id']),reason='Synthetic checked observation'))
    assert f.repo.get_record('Answer1')==answer
    assert f.repo.get_stage(cmd,'Input')['bytes']==f.raw
    with pytest.raises(S02Error): f.repo.append_event(cmd,'s01_dispatch_intent',dict(answer_id='Answer1',consent_event=dict(command_id=cmd,event_id=ev['event_id']),s01_store_key='synthetic',s01_run_id='ReservedRun',s01_request=dict(mode='update',spec_id=f.s01env['snapshot']['spec_id'],base_revision=2),input_stage_ref=dict(command_id=cmd,blob_id='Input')))

def test_f03_failed_application_rolls_back_everything(foundation):
    f=foundation;m,a,answer=add_answer(f);op,batch,events=application_batch(f,m,a,answer)
    def hook(point,c):
        if point=='after_finalize': raise OSError('injected at atomic application')
    r=Repository(f.repo.path,_hook=hook)
    with pytest.raises(S02Error): r.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events)
    clean=Repository(f.repo.path);assert clean.heads(f.session)==('M1','AS1');assert clean.get_record('Q2')['body']['status']=='open'
    assert clean.get_record('M2') is None and clean.get_record('Answer1')==answer
    assert not any(e['kind']=='application_applied' for e in clean.get_command(op['command_id'])['events'])
