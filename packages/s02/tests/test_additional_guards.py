from copy import deepcopy
import sqlite3
import pytest
from dacn_s02.repository import Repository,record,digest
from dacn_s02.service import artifact,staged
from dacn_s02.errors import S02Error
from dacn_s02.scope import make_scope,closure
from helpers import uid,run,aset,allscope,evidence
from test_lifecycle import capture
from test_scope import branched

def test_selected_action_not_reachable_under_choice():
    m,choice=branched('exclusive');choice['edge_id']='right'
    assert 'SCOPE_UNDETERMINED' in closure(m,make_scope('M1',parts=['P1']),[choice]).reasons

def test_no_future_artifact_run_fk(foundation):
    f=foundation;op=f.operation();f.repo.prepare(op)
    bad=artifact('Premature','llm_request',b'{}',op['reserved_run_id'])
    # A final batch without its reserved Run is rejected even before the FK gate.
    with pytest.raises(S02Error):f.repo.finalize(op['command_id'],[bad],blobs={'Premature':b'{}'})
    assert f.repo.get_record('Premature') is None
    with sqlite3.connect(f.repo.path) as c:
        c.execute('PRAGMA foreign_keys=ON')
        with pytest.raises(sqlite3.IntegrityError):
            c.execute('INSERT INTO artifacts VALUES (?,?,?,?,?)',('NoArtifact',op['reserved_run_id'],digest(b'{}'),2,b'{}'));c.commit()
        c.rollback()

def test_f02_explicit_recovery_has_own_parent_intent_no_resend(foundation):
    f=foundation;op,attempt,items=capture(f);cmd=op['command_id']
    recovery=dict(command_id=uid(),session_id=f.session,parent_command_id=cmd,reserved_run_id=uid(),request=dict(kind='recovery',reason='Read captured bytes only'))
    f.repo.prepare(recovery)
    original=Repository(f.repo.path).get_command(cmd)
    assert original['state']=='captured' and len([e for e in original['events'] if e['kind']=='dispatch_intent'])==1
    assert f.repo.get_stage(cmd,'Response')['bytes']==items[-1][1]
    assert f.repo.get_command(recovery['command_id'])['operation']['parent_command_id']==cmd

@pytest.mark.parametrize('boundary',['prepare','capture'])
def test_lost_ack_staging_boundaries(foundation,boundary):
    f=foundation;op=f.operation();cmd=op['command_id']
    def hook(p,c):
        if p=='after_commit':raise OSError('lost ack after real commit')
    r=Repository(f.repo.path,_hook=hook)
    if boundary=='prepare':
        assert r.prepare(op,staged=[staged(cmd,'Config','config',b'{}')])==cmd
        assert Repository(r.path).get_command(cmd)['state']=='prepared'
    else:
        f.repo.prepare(op);e=f.repo.get_command(cmd)['events'][0]
        f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=e['event_id']),transport_attempt=1))
        raw=b'"\xed\xa0\x80\xed\xb0\x80"'
        event=r.append_event(cmd,'response_received',dict(response=dict(command_id=cmd,blob_id='R'),http_status=200,safe_headers={},requested_model='stub',returned_model=None,provider_response_id=None,usage=None,elapsed_ms=0),staged=[staged(cmd,'R','llm_response',raw)])
        assert event['kind']=='response_received'
        assert Repository(r.path).get_stage(cmd,'R')['bytes']==raw
        from dacn_s02.codec_boundary import decode,encode
        value=decode(raw)
        with pytest.raises(S02Error) as e:encode(value)
        assert e.value.error['code']=='PROCESSING_FAILED'
        assert Repository(r.path).get_command(cmd)['state']=='captured'
    evidence('lost_ack_boundary',boundary=boundary,outcome='reconciled_without_resubmit')

def test_failed_handoff_and_wrong_metadata_rejected(foundation):
    f=foundation;m,a=f.initial();op=f.operation();f.repo.prepare(op)
    # Reference errors cannot be waived by declaring eligible.
    h=record('handoff','H',dict(bundle_id='Missing',review_id=None,model_id=m['id'],analysis_set_id=a['id'],eligible=True,allowed_scope=allscope(m),blocked_scope=make_scope(m['id']),workflow_choices=[],condition_ids=[],reason_codes=[]))
    with pytest.raises(S02Error):f.repo.finalize(op['command_id'],[h,run(op,f.context,f.config)])
    assert f.repo.get_record('H') is None

def test_hash_column_and_link_corruption_detected(foundation):
    f=foundation;f.initial()
    from dacn_s02.storage_schema import DDL
    with sqlite3.connect(f.repo.path) as c:
        c.execute('DROP TRIGGER immutable_records_update');c.execute("UPDATE records SET type='answer' WHERE id='M1'");c.execute(DDL['immutable_records_update'])
    with pytest.raises(S02Error) as e:f.repo.get_record('M1')
    assert e.value.error['code']=='PERSISTENCE_FAILED'

def test_wrong_source_ref_snapshot_not_retargeted(foundation):
    f=foundation;m,a=f.initial();op=f.operation();f.repo.prepare(op)
    from helpers import issue
    q=issue(m);q['body']['trace']['source_refs'][0]['snapshot_id']='DifferentSnapshot'
    a2=aset(m,'AS2',a,issues=['Q2'])
    with pytest.raises(S02Error) as e:f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    assert e.value.error['code']=='SOURCE_REF_INVALID'
    assert f.repo.heads(f.session)==('M1','AS1')
