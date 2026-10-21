"""Additional independent oracles for S02-01..04; synthetic replay only."""
from copy import deepcopy
import sqlite3
import pytest
from dacn_s02.repository import Repository, record
from dacn_s02.service import artifact, staged
from dacn_s02.errors import S02Error
from dacn_s02.scope import make_scope, permitted_scope
from helpers import Foundation, run, aset, issue, model, part, allscope, uid, evidence
from test_lifecycle import add_answer, application_batch, capture
from test_audit_regressions import outcome


def reject(f, call):
    assert outcome(call, f.repo, lambda: {})


def attempt_batch(f, op, attempt_id, items, status='invalid_output'):
    cmd=op['command_id']
    arts=[artifact('Art'+s['blob_id'],s['purpose'],raw,op['reserved_run_id']) for s,raw in items]
    blobs={'Art'+s['blob_id']:raw for s,raw in items}
    promotions=[dict(stage_ref=dict(command_id=cmd,blob_id=s['blob_id']),artifact_id='Art'+s['blob_id']) for s,_ in items]
    at=dict(id=attempt_id,step=2,base_model_id=op['request']['base_model_id'],base_analysis_set_id=op['request']['base_analysis_set_id'],
            prompt_artifact_id='ArtPrompt',request_artifact_id='ArtRequest',response_artifact_id='ArtResponse',
            provider='local-stub',requested_model='stub',returned_model=None,provider_response_id=None,
            transport_attempt=1,repair_round=0,status=status,usage=None,elapsed_ms=7)
    run_status={'invalid_output':'rejected','refused':'failed','incomplete':'failed','stale':'stale',
                'unknown_outcome':'interrupted','transport_failed':'failed','completed':'completed'}[status]
    errors=[] if run_status in ('completed','interrupted') else [dict(code='SYNTHETIC_CALL_RESULT',stage='llm',record_id=None,pointer=None,related_ids=[],message='Synthetic replay classification',details={'status':status})]
    rr=run(op,f.context,f.config,attempts=[at],status=run_status,errors=errors)
    return arts+[rr],blobs,promotions,at


@pytest.mark.parametrize('field,value',[
    ('requested_model','other'),('returned_model','invented'),('provider_response_id','invented'),
    ('usage',dict(input_tokens=1,cached_input_tokens=0,output_tokens=1,cost_usd=None,price_source=None)),
    ('elapsed_ms',999),('transport_attempt',42),('id','OtherAttempt'),
])
def test_each_committed_attempt_fact_is_binding(foundation,field,value):
    f=foundation;op,identity,items=capture(f);batch,blobs,promotions,at=attempt_batch(f,op,identity,items)
    at[field]=value
    reject(f,lambda:f.repo.finalize(op['command_id'],batch,blobs=blobs,promotions=promotions))
    assert Repository(f.repo.path).get_command(op['command_id'])['state']=='captured'


@pytest.mark.parametrize('field,purpose',[('prompt_artifact_id','prompt'),('request_artifact_id','llm_request'),('response_artifact_id','llm_response')])
def test_same_purpose_or_bytes_do_not_replace_pin(foundation,field,purpose):
    f=foundation;op,identity,items=capture(f);batch,blobs,promotions,at=attempt_batch(f,op,identity,items)
    raw=next(raw for s,raw in items if s['purpose']==purpose)
    batch.insert(0,artifact('Substitute',purpose,raw,op['reserved_run_id']));blobs['Substitute']=raw;at[field]='Substitute'
    reject(f,lambda:f.repo.finalize(op['command_id'],batch,blobs=blobs,promotions=promotions))


@pytest.mark.parametrize('status',['completed','refused','invalid_output','incomplete','stale'])
def test_captured_status_keeps_exact_evidence(foundation,status):
    # Status classification is synthetic, not a claim that a provider parser ran.
    f=foundation;op=f.operation();cmd=op['command_id'];identity=uid()
    items=[staged(cmd,'Prompt','prompt',b'Prompt fixture'),staged(cmd,'Request','llm_request',b'{"synthetic":true}')]
    f.repo.prepare(op,staged=items,attempt_id=identity);prep=f.repo.get_command(cmd)['events'][0]
    f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=prep['event_id']),transport_attempt=1))
    raw=b'{ invalid \xff' if status=='invalid_output' else ('{"synthetic_status":"'+status+'"}').encode('ascii')
    response=staged(cmd,'Response','llm_response',raw)
    f.repo.append_event(cmd,'response_received',dict(response=dict(command_id=cmd,blob_id='Response'),http_status=200,safe_headers={},requested_model='stub',returned_model=None,provider_response_id=None,usage=None,elapsed_ms=7),staged=[response])
    items.append(response);batch,blobs,promotions,at=attempt_batch(f,op,identity,items,status)
    f.repo.finalize(op['command_id'],batch,blobs=blobs,promotions=promotions)
    repo=Repository(f.repo.path);repo.verify()
    assert repo.get_record(op['reserved_run_id'])['body']['attempts']==[at]
    assert repo.get_blob('ArtResponse')==items[-1][1]
    evidence('audit_fix_capture',status=status,raw_preserved=True)


@pytest.mark.parametrize('mode',['missing_attempt','extra_attempt','uncaptured_unknown'])
def test_capture_cannot_disappear_from_final_record(foundation,mode):
    f=foundation;op,identity,items=capture(f);batch,blobs,promotions,at=attempt_batch(f,op,identity,items)
    if mode=='missing_attempt':batch[-1]['body']['attempts']=[]
    elif mode=='extra_attempt':
        other=deepcopy(at);other['id']='Extra';batch[-1]['body']['attempts'].append(other)
    else:at['status']='unknown_outcome'
    reject(f,lambda:f.repo.finalize(op['command_id'],batch,blobs=blobs,promotions=promotions))


@pytest.mark.parametrize('status',['unknown_outcome','transport_failed'])
def test_unknown_call_keeps_dispatch_and_null_response(foundation,status):
    f=foundation;op=f.operation();cmd=op['command_id'];identity=uid()
    items=[staged(cmd,'Prompt','prompt',b'Prompt'),staged(cmd,'Request','llm_request',b'{"synthetic":true}')]
    f.repo.prepare(op,staged=items,attempt_id=identity)
    prep=f.repo.get_command(cmd)['events'][0]
    f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=prep['event_id']),transport_attempt=1))
    batch,blobs,promotions,at=attempt_batch(f,op,identity,items,status);at['response_artifact_id']=None
    f.repo.finalize(cmd,batch,blobs=blobs,promotions=promotions)
    reopened=Repository(f.repo.path);reopened.verify()
    assert reopened.get_record(op['reserved_run_id'])['body']['attempts']==[at]
    assert [e['kind'] for e in reopened.get_command(cmd)['events']]==['prepared','dispatch_intent','finalized']


def test_prompt_reuse_requires_t0_pin(foundation):
    f=foundation
    # Create a reusable immutable artifact, with a real existing producer Run.
    old=f.operation();f.repo.prepare(old)
    prompt=artifact('ExistingPrompt','prompt',b'Synthetic reusable prompt',old['reserved_run_id'])
    f.repo.finalize(old['command_id'],[prompt,run(old,f.context,f.config)],blobs={'ExistingPrompt':b'Synthetic reusable prompt'})
    op=f.operation();cmd=op['command_id'];identity=uid()
    items=[staged(cmd,'Request','llm_request',b'{"synthetic":true}')]
    f.repo.prepare(op,staged=items,attempt_id=identity,reused_artifact_ids=['ExistingPrompt',f.config])
    prepared=f.repo.get_command(cmd)['events'][0]
    assert prepared['payload']['reused_artifact_ids']==['ExistingPrompt',f.config]
    f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=prepared['event_id']),transport_attempt=1))
    batch,blobs,promotions,at=attempt_batch(f,op,identity,items,'unknown_outcome')
    at.update(prompt_artifact_id='ExistingPrompt',response_artifact_id=None)
    f.repo.finalize(cmd,batch,blobs=blobs,promotions=promotions)
    repo=Repository(f.repo.path);repo.verify();assert repo.get_record('ExistingPrompt')==prompt
    assert repo.get_record(op['reserved_run_id'])['body']['attempts'][0]['prompt_artifact_id']=='ExistingPrompt'


def test_issue_resolved_from_source_without_fabricated_answer(foundation):
    f=foundation;m,a=f.initial(True);op=f.operation();f.repo.prepare(op)
    resolved=issue(m,'SourceResolved',parent='Q2',status='resolved')
    resolved['body'].update(blocking=make_scope('M1'),resolution='Synthetic source evidence, no Answer received')
    selected=aset(m,'AS2',a,issues=[resolved['id']])
    f.repo.finalize(op['command_id'],[resolved,selected,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    repo=Repository(f.repo.path);repo.verify()
    assert repo.get_record('SourceResolved')==resolved
    assert resolved['body']['answer_ids']==resolved['body']['resolution_event_refs']==[]


@pytest.mark.parametrize('mutation',['wrong_target','wrong_answer','missing_change_backlink','wrong_parent','no_current_issue'])
def test_application_full_identity_chain_rolls_back(foundation,mutation):
    f=foundation;m,a,answer=add_answer(f);op,batch,events=application_batch(f,m,a,answer)
    q=next(r for r in batch if r['type']=='issue');ch=next(r for r in batch if r['type']=='change')
    if mutation=='wrong_target':events[0][1]['resolved_issue_id']='Q2'
    elif mutation=='wrong_answer':
        other=deepcopy(answer);other['id']='OtherAnswer';batch.insert(0,other)
        q['body']['answer_ids']=['OtherAnswer']
    elif mutation=='missing_change_backlink':ch['body']['application_event_refs']=[]
    elif mutation=='wrong_parent':q['body']['supersedes_id']=None
    else:
        # A question can exist in history yet be absent from the selected base.
        # New question is a separate branch with the same key, not current Q2.
        other=issue(m,'NotCurrent',key='Question2');batch.insert(0,other)
        q['body']['supersedes_id']='NotCurrent'
    reject(f,lambda:f.repo.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events))
    repo=Repository(f.repo.path)
    assert repo.heads(f.session)==('M1','AS1') and repo.get_record('M2') is None
    assert repo.get_record('Answer1')==answer


def test_current_pending_issue_can_descend_from_original_answer_issue(foundation):
    f=foundation;m,a,answer=add_answer(f);op=f.operation();f.repo.prepare(op)
    pending=issue(m,'Pending',parent='Q2',status='answered_pending_application');pending['body']['answer_ids']=['Answer1']
    newset=aset(m,'AS2',a,issues=['Pending'])
    f.repo.finalize(op['command_id'],[pending,newset,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    app,batch,events=application_batch(f,m,newset,answer)
    next(r for r in batch if r['type']=='issue')['body']['supersedes_id']='Pending'
    next(r for r in batch if r['type']=='change')['body']['source_record_ids'].append('Pending')
    f.repo.finalize(app['command_id'],batch,head=('M2','AS-M2'),application_events=events)
    repo=Repository(f.repo.path);repo.verify();assert repo.get_record('Q2')['body']['status']=='open'
    # Historical application stays valid after an unrelated AnalysisSet advances.
    finalmodel=repo.get_record('M2');finalset=repo.get_record('AS-M2');later=f.operation();repo.prepare(later)
    nextset=aset(finalmodel,'AS-Later',finalset,issues=['Q2-resolved'],changed=[])
    repo.finalize(later['command_id'],[nextset,run(later,f.context,f.config,set_id='AS-Later')],head=('M2','AS-Later'))
    Repository(repo.path).verify()


def test_issue_event_cannot_cross_session(foundation):
    f=foundation;m,a,answer=add_answer(f)
    # A second legitimate intake creates another session in the same S02 store.
    from dacn_s02.service import Service
    other=Service(f.repo).start(f.s01.path,'synthetic',f.s01env['run']['run_id'])
    foreign=f.repo.get_command(other['command_id'])['events'][0]
    op=f.operation();f.repo.prepare(op)
    q=issue(m,'Resolved',parent='Q2',status='resolved')
    q['body'].update(answer_ids=['Answer1'],resolution='Synthetic',resolution_event_refs=[dict(command_id=foreign['command_id'],event_id=foreign['event_id'])])
    batch=[q,aset(m,'AS2',a,issues=['Resolved']),run(op,f.context,f.config,set_id='AS2')]
    reject(f,lambda:f.repo.finalize(op['command_id'],batch,head=('M1','AS2')))


@pytest.mark.parametrize('collection',['functional_requirements','non_functional_requirements','constraints'])
@pytest.mark.parametrize('criterion',[False,True])
def test_unassessed_requirement_or_criterion_is_storable_but_not_gate_ready(tmp_path,monkeypatch,collection,criterion):
    import helpers
    original=helpers.source
    def source():
        value=original();value[collection].append(dict(id='Additional',text='Synthetic obligation',priority='must',acceptance_criteria=['Synthetic criterion'] if criterion else []))
        return value
    monkeypatch.setattr(helpers,'source',source);f=Foundation(tmp_path);op=f.operation();f.repo.prepare(op)
    m=model(f.context,f.snapshot,op['reserved_run_id']);q=issue(m,'Unassessed',blocked=(),parts=())
    index=1 if collection=='functional_requirements' else 0;pointer=f'/{collection}/{index}'
    if criterion:
        p=part('AssessedGlobal',[],[]);p['target']='system'
        m['body']['mappings'].append(dict(id='Parent',source_ref=dict(snapshot_id=f.snapshot,input_pointer=pointer),parts=[p],assessment='proposed',issue_ids=[]))
        pointer+='/acceptance_criteria/0'
    m['body']['mappings'].append(dict(id='UnassessedMapping',source_ref=dict(snapshot_id=f.snapshot,input_pointer=pointer),parts=[],assessment='not_assessed',issue_ids=[q['id']]))
    a=aset(m,issues=[q['id']]);f.repo.finalize(op['command_id'],[m,q,a,run(op,f.context,f.config,model_id='M1',set_id='AS1')],head=('M1','AS1'))
    repo=Repository(f.repo.path);repo.verify();persisted=repo.get_record('M1')
    result=permitted_scope(persisted,make_scope('M1',parts=['P1']),allscope(m),current_analysis_set_id='AS1',reviewed_analysis_set_id='AS1',issues=[q])
    assert result['allowed_scope']==make_scope('M1')
    assert result['reason_codes']==['MAPPING_NOT_ASSESSED','NO_ALLOWED_FUNCTIONAL_SCOPE']
    assert result['blocked_scope']==make_scope('M1',['A1','A2'],allscope(m)['mapping_part_ids'])
    assert repo.get_record('Unassessed')['body']['blocking']==make_scope('M1')
    evidence('audit_fix_mapping_gate',pointer=pointer,result=result,intermediate_store_valid=True)


@pytest.mark.parametrize('case',['prepared_resolution','wrong_key','not_selected','attempt_identity','attempt_metadata','attempt_prompt'])
def test_checked_read_rejects_previously_unchecked_bad_records(foundation,monkeypatch,case):
    """Manufacture legacy bad stores by disabling *only* gates during fixture setup.

    This is fault injection, not a public API success claim. All checks are
    restored before reopen; production verify must detect these bad histories.
    """
    f=foundation;kwargs={}
    if case.startswith('attempt'):
        op,identity,items=capture(f);batch,blobs,promotions,at=attempt_batch(f,op,identity,items)
        kwargs=dict(blobs=blobs,promotions=promotions)
        if case=='attempt_identity':at['id']='Wrong'
        elif case=='attempt_metadata':at['requested_model']='Wrong'
        else:
            batch.insert(0,artifact('WrongPrompt','prompt',b'wrong',op['reserved_run_id']));blobs['WrongPrompt']=b'wrong';at['prompt_artifact_id']='WrongPrompt'
    else:
        m,a,answer=add_answer(f)
        if case=='prepared_resolution':
            op=f.operation();f.repo.prepare(op);prep=f.repo.get_command(op['command_id'])['events'][0]
            q=issue(m,'Resolved',parent='Q2',status='resolved');q['body'].update(answer_ids=['Answer1'],resolution='Synthetic',resolution_event_refs=[dict(command_id=op['command_id'],event_id=prep['event_id'])])
            batch=[q,aset(m,'AS2',a,issues=['Resolved']),run(op,f.context,f.config,set_id='AS2')];kwargs=dict(head=('M1','AS2'))
        else:
            op,batch,events=application_batch(f,m,a,answer);kwargs=dict(head=('M2','AS-M2'),application_events=events)
            if case=='wrong_key':next(r for r in batch if r['type']=='issue')['body'].update(issue_key='Wrong',supersedes_id=None)
            else:next(r for r in batch if r['type']=='analysis_set')['body'].update(issue_ids=[],changed_record_ids=[])
    with monkeypatch.context() as fake:
        fake.setattr('dacn_s02.repository.validate_record',lambda *a,**k:None)
        fake.setattr('dacn_s02.events.validate_operations',lambda *a,**k:None)
        f.repo.finalize(op['command_id'],batch,**kwargs)
    with pytest.raises(S02Error) as err:Repository(f.repo.path).verify()
    assert err.value.error['code']=='PERSISTENCE_FAILED'
    evidence('audit_fix_checked_read',case=case,rejected=True,fixture_method='validation-bypass fault injection')
