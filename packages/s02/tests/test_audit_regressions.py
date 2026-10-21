"""Portable regressions adapted from the independent a1 audit (seven cases).

Implementation helpers only construct synthetic fixtures. Expected rejections
are derived from draft.3 sections 4.3, 4.4 and 9.1, not production validators.
Each unexpected acceptance is printed and the persisted DB remains in basetemp.
"""
import sqlite3
from pathlib import Path
from copy import deepcopy
import simplejson as json
import pytest

from helpers import Foundation, run, aset, issue, model, trace, part, allscope, uid
from test_lifecycle import add_answer, application_batch, capture
from dacn_s02.repository import Repository, record
from dacn_s02.service import artifact
from dacn_s02.scope import make_scope, permitted_scope
from dacn_s02.errors import S02Error

def outcome(call, repo, extra):
    with sqlite3.connect(repo.path) as connection:
        before = list(connection.iterdump())
    try:
        value = call()
    except S02Error as exc:
        assert exc.error['code'] == 'SCHEMA_INVARIANT'
        Repository(repo.path).verify()
        with sqlite3.connect(repo.path) as connection:
            assert list(connection.iterdump()) == before
        print('AUDIT_OUTCOME ' + json.dumps({'rejected': True, 'error': exc.error}))
        return True
    Repository(repo.path).verify()
    print('AUDIT_OUTCOME ' + json.dumps({'rejected': False, 'db': str(repo.path), **extra()}))
    return False

def test_resolved_issue_requires_application_event(tmp_path):
    f=Foundation(tmp_path);m,a,answer=add_answer(f)
    op=f.operation();f.repo.prepare(op)
    prepared=f.repo.get_command(op['command_id'])['events'][0]
    q=issue(m,'Q-resolved',parent='Q2',status='resolved')
    q['body'].update(answer_ids=[answer['id']],blocking=make_scope('M1'),
        resolution='Synthetic claimed resolution without any application',
        resolution_event_refs=[{'command_id':op['command_id'],'event_id':prepared['event_id']}])
    a2=aset(m,'AS2',a,issues=[q['id']])
    def inspect():
        gate=permitted_scope(m,make_scope('M1',parts=['P1']),allscope(m),
            current_analysis_set_id='AS2',reviewed_analysis_set_id='AS2',issues=[q])
        return {'resolved_issue':f.repo.get_record(q['id']), 'head':f.repo.heads(f.session),
                'event_kinds':[e['kind'] for e in f.repo.get_command(op['command_id'])['events']],
                'allowed_parts':gate['allowed_scope']['mapping_part_ids']}
    rejected=outcome(lambda:f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2')),f.repo,inspect)
    assert rejected, 'Resolved issue accepted a prepared event instead of application_applied; blocker disappeared'

@pytest.mark.parametrize('mutation',['wrong_issue_key','not_in_current_set'])
def test_application_preserves_current_issue_identity(tmp_path,mutation):
    f=Foundation(tmp_path);m,a,answer=add_answer(f)
    op,batch,events=application_batch(f,m,a,answer)
    q=next(r for r in batch if r['type']=='issue')
    newset=next(r for r in batch if r['type']=='analysis_set')
    if mutation=='wrong_issue_key':
        q['body'].update(issue_key='UnrelatedQuestion',supersedes_id=None)
    else:
        newset['body'].update(issue_ids=[],changed_record_ids=[])
    rejected=outcome(lambda:f.repo.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events),f.repo,
        lambda:{'mutation':mutation,'resolved_issue_key':q['body']['issue_key'],
                'requested_issue_key':op['request']['issue_key'],
                'current_issue_ids':f.repo.get_record('AS-M2')['body']['issue_ids'],
                'original_issue_status':f.repo.get_record('Q2')['body']['status'],
                'event_kinds':[e['kind'] for e in f.repo.get_command(op['command_id'])['events']]})
    assert rejected, 'Application committed without resolving the same current issue'

@pytest.mark.parametrize('mutation',['attempt_id','capture_metadata','substitute_prompt'])
def test_final_attempt_bound_to_staging(tmp_path,mutation):
    f=Foundation(tmp_path);op,attempt,items=capture(f);cmd=op['command_id']
    arts=[artifact('Art'+i['blob_id'],i['purpose'],raw,op['reserved_run_id']) for i,raw in items]
    blobs={'Art'+i['blob_id']:raw for i,raw in items}
    at=dict(id=attempt,step=2,base_model_id=None,base_analysis_set_id=None,
        prompt_artifact_id='ArtPrompt',request_artifact_id='ArtRequest',response_artifact_id='ArtResponse',
        provider='local-stub',requested_model='stub',returned_model=None,provider_response_id=None,
        transport_attempt=1,repair_round=0,status='invalid_output',usage=None,elapsed_ms=7)
    if mutation=='attempt_id': at['id']='DifferentAttempt'
    elif mutation=='capture_metadata':
        at.update(requested_model='NeverRequested',returned_model='NeverReturned',
            provider_response_id='InventedResponse',elapsed_ms=999,transport_attempt=42)
    else:
        at['prompt_artifact_id']='OtherPrompt'
        arts.append(artifact('OtherPrompt','prompt',b'Never sent prompt',op['reserved_run_id']))
        blobs['OtherPrompt']=b'Never sent prompt'
    err=dict(code='INVALID_JSON',stage='parse',record_id=None,pointer=None,related_ids=[],message='Synthetic invalid response',details={'reason':'Malformed JSON'})
    rr=run(op,f.context,f.config,status='rejected',attempts=[at],errors=[err])
    promotions=[dict(stage_ref=dict(command_id=cmd,blob_id=i['blob_id']),artifact_id='Art'+i['blob_id']) for i,_ in items]
    rejected=outcome(lambda:f.repo.finalize(cmd,arts+[rr],blobs=blobs,promotions=promotions),f.repo,
        lambda:{'mutation':mutation,'expected_attempt':attempt,'actual_attempt':f.repo.get_record(rr['id'])['body']['attempts'][0],
                'events':f.repo.get_command(cmd)['events']})
    assert rejected, 'Attempt was accepted despite contradicting the committed dispatch/capture evidence'

def test_empty_mandatory_mapping_cannot_pass_scope_gate(tmp_path):
    # Add a separate source constraint. Its mapping is intentionally unfinished.
    import helpers
    original=helpers.source
    def src():
        value=original()
        value['constraints']=[dict(id='K1',text='Synthetic mandatory constraint',priority='must',
            acceptance_criteria=[],constraint=dict(kind='audit',value='Required globally'))]
        return value
    helpers.source=src
    try: f=Foundation(tmp_path)
    finally: helpers.source=original
    op=f.operation();f.repo.prepare(op)
    m=model(f.context,f.snapshot,op['reserved_run_id'])
    q=issue(m,'Q-global',key='GlobalUnassessed',blocked=(),parts=())
    q['body']['reason']='Unassessed global obligation has no Part yet'
    m['body']['mappings'].append(dict(id='MapConstraint',source_ref=dict(snapshot_id=f.snapshot,input_pointer='/constraints/0'),
        parts=[],assessment='not_assessed',issue_ids=['Q-global']))
    a=aset(m,issues=[q['id']])
    f.repo.finalize(op['command_id'],[m,q,a,run(op,f.context,f.config,model_id='M1',set_id='AS1')],head=('M1','AS1'))
    result=permitted_scope(m,make_scope('M1',parts=['P1']),allscope(m),
        current_analysis_set_id='AS1',reviewed_analysis_set_id='AS1',issues=[q])
    print('AUDIT_OUTCOME '+json.dumps({'db':str(f.repo.path),'unassessed_mapping':m['body']['mappings'][-1], 'result':result}))
    assert not result['allowed_scope']['mapping_part_ids'], 'Unassessed mandatory constraint with zero Parts vanished from the gate'
