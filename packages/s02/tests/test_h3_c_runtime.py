"""C API on actual A2 DB2, distinct from detached pure and B-AS evidence."""
from hashlib import sha256
from copy import deepcopy
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from h3_c_runtime_fixtures import CCase,baseline,readback


@pytest.mark.parametrize('branch',['direct','pending','replacement','incomplete','replacement_tasks','obsolete','source_only'])
def test_C_real_A2_effects_and_append_only_API(tmp_path,monkeypatch,branch):
    source=baseline(tmp_path/'source',monkeypatch,branch);c=CCase(tmp_path/'work',source);before=c.base();old=deepcopy(before.history._state['records']);claims=before.history.payload()
    result=c.execute(*c.work());assert result['status']=='blocked'
    v,p,i=readback(c,c.parent);assert i['applications']==c.applications_before and len(i['applications'])==1
    assert all(v['state']['records'][k]==r for k,r in old.items())
    assert not any(r['type'] in ('answer','validation') for r in p['batch']['records'])
    assert p['candidate_outcome']==('guard_only' if branch=='obsolete' else 'valid')
    if branch!='obsolete':
        assert p['batch']['head'][0]!=before.pair[0]
        change=next(r for r in p['batch']['records'] if r['type']=='change');assert change['body']['kind']=='analysis_edit' and change['body']['application_event_refs']==[]
        q=i['current_issues']['Question2']['body'];prior=i['base_issues']['Question2']
        assert q['supersedes_id']==prior['id']
        if branch=='direct':assert q['resolution_carry']['origin_issue_id']=='Q2-resolved' and q['resolution_carry']['assessment']=='applicable'
        if branch=='pending':assert q['resolution_carry']['assessment']=='undetermined' and q['status']=='resolution_pending_revalidation'
        if branch in ('replacement','incomplete','replacement_tasks'):
            proof=q['resolution_replacement'];assert proof['assessment']==('complete' if branch=='replacement' else 'incomplete')
            assert proof['replacement_issue_id']==i['current_issues']['NewDecision']['id']
            assert proof['obsolete_issue_id']==prior['body']['resolution_replacement']['obsolete_issue_id']
    raw=encode(result);checksum=sha256(c.db.read_bytes()).hexdigest();assert encode(c.service().report(c.parent))==raw;assert encode(c.service().resume(c.parent))==raw
    assert sha256(c.db.read_bytes()).hexdigest()==checksum


def test_C_real_steps_1_to_4_and_raw_rejection(tmp_path,monkeypatch):
    c=CCase(tmp_path/'work',baseline(tmp_path/'source',monkeypatch))
    for step in (2,3,4):
        r=c.execute(*c.work(step=step));assert r['result']['candidate_outcome']=='valid';readback(c,c.parent)
    uid=c.work(mode='revalidate',step=4)[0]['unit_ids'][0]
    assert r['result']['progress_by_unit'][uid]['work_completed_through']==4
    with pytest.raises(S02Error):c.execute(*c.work(step=4))


def test_C_API_authority_is_separate_and_exact_raw_bytes(tmp_path,monkeypatch):
    from dacn_s02.h3_review_io import LocalSyntheticCheckpointAuthority
    c=CCase(tmp_path/'work',baseline(tmp_path/'source',monkeypatch));work,a=c.work(raw_suffix=b' \n');cmd='C.RawFidelity';before=sha256(c.db.read_bytes()).hexdigest()
    with pytest.raises(S02Error,match='original external semantic authority|requires external semantic authority'):
        c.service().prepare(cmd,c.parent,receipt=c.path/'no-authority.receipt',**work)
    assert sha256(c.db.read_bytes()).hexdigest()==before and c.repo().get_command(cmd) is None
    with pytest.raises(S02Error):c.service(LocalSyntheticCheckpointAuthority(a.path,a.trust))
    denied,deny=c.work(decision='deny')
    with pytest.raises(S02Error):c.prepare(cmd,denied,deny)
    assert sha256(c.db.read_bytes()).hexdigest()==before and c.repo().get_command(cmd) is None
    c.prepare(cmd,work,a);assert c.service(a).resume(cmd)['status']=='blocked';v,p,i=readback(c,cmd)
    for lane in ('candidate','analysis'):
        assert v['raw'][lane]['bytes']==work[lane] and work[lane].endswith(b' \n')
        aid=next(x['artifact_id'] for x in p['promotions'] if x['stage_ref']==v['config']['inputs'][lane]['stage_ref']);assert v['state']['blobs'][aid]==work[lane]


def test_E05_E24_C_mixed_current_keys_unknown_pending_Answer_keeps_global_hold(tmp_path,monkeypatch):
    c=CCase(tmp_path/'work',baseline(tmp_path/'source',monkeypatch,'mixed'),advance=False);old=c.base();saved=deepcopy(old.history._state['records'])
    # This direct pending Answer has no historical scope proof. Prose labels
    # must not shrink B's unknown selector to let V through.
    r=c.execute(*c.work(step=1));assert r['result']['candidate_outcome']=='guard_only';v,p,i=readback(c,c.parent)
    assert {'Question2','NewDecision','PendingAnswerKey','SourceOnlyKey'}<set(i['current_issues'])
    assert i['current_issues']['PendingAnswerKey']['body']['status']=='answered_pending_application'
    assert i['current_issues']['PendingAnswerKey']['body']['answer_ids']==['PendingAnswer']
    assert i['current_issues']['SourceOnlyKey']['body']['resolution_carry'] is None
    assert i['current_issues']['Question2']['body']['resolution_replacement']['assessment']=='incomplete'
    assert all(v['state']['records'][k]==r for k,r in saved.items()) and i['applications']==c.applications_before
    assert not any(r['type'] in ('answer','model','change') for r in p['batch']['records']) and c.pair[0]==old.pair[0]
    assert all(x['work_completed_through']==0 for x in p['admission']['progress_by_unit'].values())


def test_C_real_guard_origin_promoted_pin_and_revalidate_never_advances_stage(tmp_path,monkeypatch):
    c=CCase(tmp_path/'work',baseline(tmp_path/'source',monkeypatch,'obsolete'));first=c.execute(*c.work());assert first['result']['candidate_outcome']=='guard_only'
    _,p,_=readback(c,c.parent);guard=next(g for g in p['admission']['guards'].values() if g.get('version'));assert guard['origin_plan_sha256'] is None
    stages={u:x['work_completed_through'] for u,x in p['admission']['progress_by_unit'].items()};origin=sha256(encode(p)).hexdigest();old_model=c.pair[0]
    again=c.execute(*c.work(mode='revalidate',step=1));v,q,i=readback(c,c.parent);inherited=q['admission']['guards'][guard['issue_key']]
    assert inherited['origin_plan_sha256']==origin and inherited['origin_plan_artifact_id']==p['allocation']['plan_artifact_id']
    assert {u:x['work_completed_through'] for u,x in q['admission']['progress_by_unit'].items()}==stages and c.pair[0]==old_model
    assert i['current_issues']['Question2']['body']['resolution_carry']['assessment']=='not_applicable'


def test_C_maximum_valid_command_ID_round_trips_all_durable_phases(tmp_path,monkeypatch):
    c=CCase(tmp_path/'work',baseline(tmp_path/'source',monkeypatch));cmd='C'+127*'x';work,a=c.work();c.prepare(cmd,work,a);r=c.service(a).resume(cmd);assert r['status']=='blocked'
    v,p,i=readback(c,cmd);assert p['candidate_outcome']=='valid' and v['config']['command_id']==cmd
    assert c.service().report(cmd)==r and c.service().resume(cmd)==r


def test_C_completed_Run_is_checked_Model_A2_publication_not_forced_blocked(tmp_path,monkeypatch):
    c=CCase(tmp_path/'work',baseline(tmp_path/'source',monkeypatch,'actor_only'));r=c.execute(*c.work());assert r['status']=='completed' and r['result']['candidate_outcome']=='valid'
    v,p,i=readback(c,c.parent);assert p['batch']['head'][0]!=v['base'].pair[0] and i['current_issues']['Question2']['body']['resolution_carry']['assessment']=='applicable'
    assert i['applications']==c.applications_before and all(x['assessment_state']=='current' for x in p['admission']['progress_by_unit'].values())


def test_C_actual_full_H2_anchor_B_bridge_retains_outputs_and_completes_only_pinned_tasks(tmp_path):
    from h3_b_runtime_fixtures import BCase,baseline as h2_baseline
    path=tmp_path/'source';path.mkdir();source=h2_baseline(path);source.historical_entries=[]
    b=BCase(tmp_path/'adopt',source);r=b.execute(*b.work(anchor=b.anchor()));assert r['status']=='blocked'
    c=object.__new__(CCase);c.__dict__=b.__dict__;c.s01=source.s01;c.historical_entries=[]
    before=c.base();parent=c.service().inspect(c.parent,expected_pair=c.pair,step=3,unit_ids=[source.v])['result'];outputs=deepcopy(parent['progress_by_unit'][source.v]['outputs']);assert len(outputs)==2
    for step in (3,4):
        r=c.execute(*c.work(step=step));assert r['result']['candidate_outcome']=='valid';v,p,i=readback(c,c.parent)
        assert p['admission']['progress_by_unit'][source.v]['work_completed_through']==step
        retained=p['admission']['progress_by_unit'][source.v]['outputs'][:2]
        for old,new in zip(outputs,retained):
            assert all(new[k]==old[k] for k in ('unit_id','step','origin_command_id','raw_sha256','source_refs'))
        assert i['applications']==c.applications_before and not any(x['type'] in ('answer','validation') for x in p['batch']['records'])
    assert c.base().context.body['actions']==before.context.body['actions']
