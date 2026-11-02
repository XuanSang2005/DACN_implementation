"""Installed B API effects and checked reopening, with exact DB readbacks."""
from copy import deepcopy
from uuid import uuid4
from hashlib import sha256
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.codec_boundary import encode
from h3_b_runtime_fixtures import BCase,baseline,readback,human_baseline


@pytest.fixture(scope='module')
def source(tmp_path_factory):return baseline(tmp_path_factory.mktemp('b-runtime-source'))


def test_adopt_no_anchor_keep_model_issues_outputs_and_replay_providerless(tmp_path,source):
    c=BCase(tmp_path,source);old=c.repo().get_record(c.pair[0])
    work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    p=c.service().report(command);assert p['status']=='prepared' and p['result']['phase']=='prepared'
    result=c.service(a).resume(command);assert result['status']=='blocked'
    view,plan,identity=readback(c,command)
    assert c.repo().get_record(c.pair[0])==old
    assert plan['batch']['head'][0]==c.pair[0] and plan['batch']['head'][1]!=c.pair[1]
    assert not any(r['type'] in ('model','change','issue') for r in plan['batch']['records'])
    assert set(plan['admission']['tasks'])==set(c.h2.meta['tasks'])
    for key,origin in plan['admission']['tasks'].items():
        assert origin['issue_id']==view['base'].issue(key)['id']
        assert all(origin[k]==c.h2.meta['tasks'][key][k] for k in ('root_issue_id','origin_command_id','predicate','target_step','unit_ids','role'))
    assert all(p['work_completed_through']==0 and p['outputs']==[] for p in plan['admission']['progress_by_unit'].values())
    assert all(view['state']['records'][i]==c.repo().get_record(i) for i in view['base'].analysis_set['body']['issue_ids'])
    checksum=sha256(c.db.read_bytes()).hexdigest();a.path.unlink()
    def bomb():raise AssertionError('finalized report allocated or read clock')
    replay=c.service(_repository_options={'_ids':bomb,'_clock':bomb}).resume(command)
    assert replay==result and sha256(c.db.read_bytes()).hexdigest()==checksum
    c.registry_path.unlink()
    with pytest.raises(S02Error):c.service().report(command)
    c.registry_path.write_bytes(c.registry_raw);assert c.service().report(command)==result


def test_full_anchor_adopt_then_revalidate_keeps_stage_and_exact_parent_assessment(tmp_path,source):
    c=BCase(tmp_path,source);work,a=c.work(anchor=c.anchor());first=c.execute(work,a);firstplan=readback(c,first['command_id'])[1]
    assert firstplan['admission']['progress_by_unit'][c.h2.v]['work_completed_through']==2
    nextwork,a2=c.work(mode='revalidate',step=2,goal='retained_output',unit_ids=[c.h2.v]);second=c.execute(nextwork,a2)
    view,p2,identity=readback(c,second['command_id'])
    assert p2['admission']['progress_by_unit'][c.h2.v]['work_completed_through']==2
    assert p2['admission']['progress_by_unit'][c.h2.v]['outputs']==firstplan['admission']['progress_by_unit'][c.h2.v]['outputs']
    from dacn_s02.h3_limits import digest
    for uid,p in p2['admission']['progress_by_unit'].items():assert p['assessment']['parent_assessment_sha256']==digest(firstplan['admission']['progress_by_unit'][uid]['assessment'])
    assert identity['applications']==[]


@pytest.mark.parametrize('wrong',['missing_authority','denied','wrong_pair','bad_analysis'])
def test_reject_before_T0_has_no_operation_or_receipt(tmp_path,source,wrong):
    c=BCase(tmp_path,source);work,a=c.work(decision='deny' if wrong=='denied' else 'allow');command=str(uuid4())
    if wrong=='missing_authority':a=None
    elif wrong=='wrong_pair':work['expected_pair']=[c.pair[0],'MissingSet']
    elif wrong=='bad_analysis':work['analysis']=b'{"not":"analysis"}'
    with pytest.raises(S02Error):c.prepare(command,work,a)
    assert c.repo().get_command(command) is None and not c.receipts[command].exists()


@pytest.mark.parametrize('changes',[{'mode':'step'},{'mode':'source_switch'},{'step':5},{'goal':'repair_completed_output'}])
def test_E23_out_of_scope_requests_never_prepare_or_edit_outputs(tmp_path,source,changes):
    c=BCase(tmp_path,source);work,a=c.work();work.update(changes);command=str(uuid4())
    checksum=sha256(c.db.read_bytes()).hexdigest()
    with pytest.raises(S02Error):c.prepare(command,work,a)
    assert c.repo().get_command(command) is None and not c.receipts[command].exists()
    assert sha256(c.db.read_bytes()).hexdigest()==checksum


@pytest.fixture(scope='module')
def guard_source(tmp_path_factory):return baseline(tmp_path_factory.mktemp('b-guard-source'),guard=True)


@pytest.mark.parametrize('proof',[True,False])
def test_revalidate_only_published_code_guard_successor_and_keeps_A2_rights(tmp_path,guard_source,proof):
    c=BCase(tmp_path,guard_source);first=c.execute(*c.work())
    before=c.repo().get_command(first['command_id']);base=c.repo().get_record(c.pair[0]);ad=first['result']['last_checked_eligibility'];guards=set(ad['guards']);assert len(guards)==1
    old={k:c.repo().get_record(s['issue_id']) for k,s in ad['selectors'].items()}
    def change(v):
        if not proof:
            for row in v['independence']:row['verdict']='unknown'
    result=c.execute(*c.work(mode='revalidate',step=1,change=change));view,plan,identity=readback(c,result['command_id'])
    assert result['status']=='blocked' and c.repo().get_record(c.pair[0])==base
    assert not any(r['type'] in ('model','change') for r in plan['batch']['records'])
    for key,row in plan['admission']['selectors'].items():
        current=c.repo().get_record(row['issue_id'])
        if key in guards:
            assert current['id']!=old[key]['id'] and current['body']['supersedes_id']==old[key]['id']
            assert current['body']['status']==('resolved' if proof else 'open')
        else:assert current==old[key]
    assert all(p['work_completed_through']==0 for p in plan['admission']['progress_by_unit'].values())
    assert plan['admission']['tasks']==ad['tasks']
    assert c.repo().get_command(first['command_id'])==before


@pytest.mark.parametrize('sealed',[False,True])
@pytest.mark.parametrize('failure',['missing','tampered','different_registry'])
def test_registry_failure_after_T0_or_seal_preserves_intent_and_original_restores(tmp_path,source,sealed,failure):
    from dataclasses import replace
    from dacn_s02.h3_service import HistoryService
    from dacn_s02.codec_boundary import decode
    c=BCase(tmp_path,source);work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    original=c.repo().get_command(command);rid=original['operation']['reserved_run_id'];primary=deepcopy(original['staged_blobs'])
    if sealed:
        def stop(point):
            if point=='after_seal':raise RuntimeError('Synthetic stop after seal')
        with pytest.raises(RuntimeError,match='after seal'):c.service(a,_hook=stop).resume(command)
        assert c.service().report(command)['result']['phase']=='sealed'
    checksum=sha256(c.db.read_bytes()).hexdigest();trust=c.trust
    if failure=='missing':c.registry_path.unlink()
    elif failure=='tampered':c.registry_path.write_bytes(c.registry_raw+b' ')
    else:
        value=decode(c.registry_raw);value['registry_id']='DifferentControl';raw=encode(value);c.registry_path.write_bytes(raw)
        trust=replace(c.trust,expected_sha256=sha256(raw).hexdigest(),expected_registry_id='DifferentControl')
    with pytest.raises(S02Error):HistoryService(c.settings,historical_reviews=trust,authority=a).resume(command)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum
    c.registry_path.write_bytes(c.registry_raw);result=c.service(a).resume(command)
    view,plan,identity=readback(c,command)
    assert identity['run_id']==rid and [x for x in view['command']['staged_blobs'] if x['blob_id'] in {p['blob_id'] for p in primary}]==primary
    assert result==c.service().report(command)


@pytest.fixture(scope='module')
def human_source(tmp_path_factory):return human_baseline(tmp_path_factory.mktemp('b-historical-reviews'))


def test_HR_P_all_store_human_ancestors_and_other_session_restart(tmp_path,human_source):
    c=BCase(tmp_path,human_source);assert len(human_source.historical_entries)==4
    old={i:r for i,r in __import__('h3_b_fixtures').state_of(c.repo())['records'].items()}
    work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    def stop(point):
        if point=='after_seal':raise RuntimeError('Synthetic restart after seal')
    with pytest.raises(RuntimeError):c.service(a,_hook=stop).resume(command)
    prepared=c.repo().get_command(command);reserved=prepared['operation']['reserved_run_id']
    result=c.service(a).resume(command);view,plan,identity=readback(c,command)
    assert identity['run_id']==reserved and len(identity['applications'])==2
    assert identity['applications']==c.applications_before
    assert view['config']['historical_reviews_pin']==plan['bindings']['historical_reviews_pin']
    assert not any(r['type'] in ('issue','model','change') for r in plan['batch']['records'])
    assert all(view['state']['records'][i]==r for i,r in old.items())
    a.path.unlink();checksum=sha256(c.db.read_bytes()).hexdigest()
    assert c.service().resume(command)==result and sha256(c.db.read_bytes()).hexdigest()==checksum


@pytest.mark.parametrize('wrong',['ancestor_missing','other_session_missing','reviewer','dependency','surplus'])
def test_historical_registry_requires_whole_store_exact_external_decisions(tmp_path,human_source,wrong):
    from dataclasses import replace
    from dacn_s02.codec_boundary import decode
    from dacn_s02.h3_service import HistoryService
    c=BCase(tmp_path,human_source);value=decode(c.registry_raw)
    if wrong=='ancestor_missing':value['reviews']=[r for r in value['reviews'] if not r['issue_id'].startswith('Carry-')]
    elif wrong=='other_session_missing':value['reviews']=[r for r in value['reviews'] if not r['issue_id'].startswith('Other.')]
    elif wrong=='reviewer':value['reviews'][0]['reviewer']='Wrong external controller'
    elif wrong=='dependency':value['reviews'][0]['dependency_sha256']='0'*64
    else:value['reviews'].append(dict(issue_id='ZZNeverPublished',reviewer='Synthetic control',assessment='applicable',dependency_sha256='0'*64))
    value['reviews']=sorted(value['reviews'],key=lambda r:r['issue_id']);value['required_issue_ids']=[r['issue_id'] for r in value['reviews']];raw=encode(value);c.registry_path.write_bytes(raw)
    trust=replace(c.trust,expected_sha256=sha256(raw).hexdigest());checksum=sha256(c.db.read_bytes()).hexdigest()
    with pytest.raises(S02Error):HistoryService(c.settings,historical_reviews=trust).inspect(c.parent,expected_pair=c.pair)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum


@pytest.mark.parametrize('bad_tuple',[None,{},'from DB metadata'])
def test_registry_tuple_missing_or_self_claimed_fails_before_repository_read(tmp_path,source,bad_tuple,monkeypatch):
    from dacn_s02.h3_service import HistoryService
    c=BCase(tmp_path,source);checksum=sha256(c.db.read_bytes()).hexdigest()
    def forbidden(*a,**k):raise AssertionError('Repository constructed before external registry tuple validation')
    monkeypatch.setattr('dacn_s02.h3_review_io.Repository',forbidden)
    with pytest.raises(S02Error):HistoryService(c.settings,historical_reviews=bad_tuple).inspect(c.parent,expected_pair=c.pair)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum


def test_registry_same_bytes_at_new_locator_keeps_original_pin_identity(tmp_path,source):
    from dataclasses import replace
    from dacn_s02.h3_service import HistoryService
    c=BCase(tmp_path,source);work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    other=c.path/'relocated-control.json';other.write_bytes(c.registry_raw);c.registry_path.unlink();c.trust=replace(c.trust,path=str(other))
    result=HistoryService(c.settings,historical_reviews=c.trust,authority=a).resume(command)
    assert result['status']=='blocked';view,plan,identity=readback(c,command)
    assert plan['bindings']['historical_reviews_pin']==view['config']['historical_reviews_pin']


@pytest.mark.parametrize('sealed',[False,True])
def test_pending_needs_external_B_authority_and_never_rebuilds_from_metadata(tmp_path,source,sealed):
    c=BCase(tmp_path,source);work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    if sealed:
        def stop(point):
            if point=='after_seal':raise RuntimeError('Synthetic stop')
        with pytest.raises(RuntimeError):c.service(a,_hook=stop).resume(command)
    control=a.path.read_bytes();checksum=sha256(c.db.read_bytes()).hexdigest();a.path.unlink()
    with pytest.raises(S02Error):c.service(a).resume(command)
    with pytest.raises(S02Error):c.service().resume(command)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum
    a.path.write_bytes(control);result=c.service(a).resume(command)
    assert result['status']=='blocked';readback(c,command)


def test_old_H2_or_arbitrary_authority_adapter_is_not_B_authorization(tmp_path,source):
    from dacn_s02.h2_authority import LocalSyntheticAuthority
    c=BCase(tmp_path,source);checksum=sha256(c.db.read_bytes()).hexdigest()
    for obj in (object(),LocalSyntheticAuthority(c.path/'not-used.json','0'*64)):
        with pytest.raises(S02Error):c.service(obj)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum


def test_E23_H1_publisher_without_bridge_is_explicitly_unsupported(tmp_path):
    from h1_fixtures import Case
    src=Case(tmp_path/'source');result=src.advance('bootstrap')
    src.pair=result['result']['result_pair'];c=BCase(tmp_path/'case',src)
    checksum=sha256(c.db.read_bytes()).hexdigest()
    with pytest.raises(S02Error,match='b_h1_bridge_unsupported'):
        c.service().inspect(c.parent,expected_pair=c.pair)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum


def test_existing_workflow_node_edge_aliases_have_exact_B_typed_correspondence(tmp_path):
    src=baseline(tmp_path/'source',workflow=True);c=BCase(tmp_path/'case',src);anchor=c.anchor()
    assert any(a['kind']=='WorkflowNode' for o in anchor['outputs'] for a in o['aliases'].values())
    assert any(a['kind']=='WorkflowEdge' for o in anchor['outputs'] for a in o['aliases'].values())
    model=c.repo().get_record(c.pair[0]);wf=model['body']['workflows'][0];nested={x['id'] for f in ('nodes','edges') for x in wf[f]}
    result=c.execute(*c.work(anchor=anchor));view,plan,identity=readback(c,result['command_id'])
    p=plan['admission']['progress_by_unit'][c.h2.v]
    assert p['work_completed_through']==2 and nested<=set(p['actual_output_ids'])
    assert nested<=set(p['outputs'][1]['output_ids']) and c.repo().get_record(c.pair[0])==model
    assert {a['id'] for a in plan['allocation']['aliases'].values() if a['kind']=='WorkflowNode'}=={x['id'] for x in wf['nodes']}
    for out in anchor['outputs']:
        for key,a in out['aliases'].items():
            if a['kind']=='Issue':
                old=view['state']['records'][a['id']];current=next(q for q in view['base'].issues if q['body']['issue_key']==old['body']['issue_key'])
                assert plan['allocation']['aliases'][key]['id']==current['id']
                assert out['aliases'][key]==a  # historical origin remains exact


@pytest.mark.parametrize('sealed',[False,True])
def test_all_store_R_change_in_other_session_cannot_upgrade_pending_registry(tmp_path,human_source,sealed):
    from dacn_s02.repository import Repository,record
    from dacn_s02.resolution import HumanReviewEvidence,review_digest
    from dacn_s02.s01_adapter import verify_archive
    from dacn_s02.h3_service import HistoryService
    from dacn_s02.h3_history import ReviewTrustContext
    from h3_b_fixtures import state_of
    from helpers import operation,aset,run
    from dacn_s02.profiles import E1
    c=BCase(tmp_path,human_source);work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    if sealed:
        def stop(point):
            if point=='after_seal':raise RuntimeError('Synthetic stop')
        with pytest.raises(RuntimeError):c.service(a,_hook=stop).resume(command)
    old=c.repo().get_command(command);state=state_of(c.repo())
    # This external fixture writer intentionally violates the fixed-R operating
    # precondition. H3 must refuse both R0 and a replacement R1 for this command.
    controls={r['issue_id']:HumanReviewEvidence(r['reviewer'],r['dependency_sha256'],r['assessment']) for r in human_source.historical_entries}
    current=next(r for r in state['records'].values() if r['type']=='issue' and r['id'].startswith('Other.Replacement-'))
    session=state['owners'][current['id']];repo=Repository(c.db,reviews=controls);mid,sid=repo.heads(session);model=state['records'][mid]
    new=deepcopy(current);new['id']='ExternalHuman.'+str(uuid4());new['body']['supersedes_id']=current['id'];new['body']['resolution_replacement'].update(from_issue_id=current['id'],base_analysis_set_id=sid)
    op=operation(session,model['body']['source_context_id'],(mid,sid));selected=[new['id'] if i==current['id'] else i for i in state['records'][sid]['body']['issue_ids']]
    newset=aset(model,'ExternalAS.'+str(uuid4()),state['records'][sid],issues=selected,changed=[new['id']]);cfgid=state['records'][state['commands'][next(c for c,o in state['commands'].items() if o['session_id']==session)]['reserved_run_id']]['body']['config_artifact_id']
    rr=run(op,model['body']['source_context_id'],cfgid,set_id=newset['id']);records={**state['records'],new['id']:new,newset['id']:newset,rr['id']:rr};profiles={**state['record_profiles'],new['id']:E1,newset['id']:E1,rr['id']:E1}
    snapshots={r['body']['snapshot_id']:verify_archive(r,state['records'],state['blobs']) for r in state['records'].values() if r['type']=='source_context'}
    controls[new['id']]=HumanReviewEvidence('SYNTHETIC REVIEWER',review_digest(new,records,snapshots,profiles),'complete')
    controller=Repository(c.db,reviews=controls);controller.prepare(op);controller.finalize(op['command_id'],[new,newset,rr],head=(mid,newset['id']));controller.verify()
    checksum=sha256(c.db.read_bytes()).hexdigest()
    with pytest.raises(S02Error):c.service(a).resume(command)
    entries=[dict(issue_id=i,reviewer=x.reviewer,assessment=x.assessment,dependency_sha256=x.dependency_sha256) for i,x in sorted(controls.items())]
    from dacn_s02.h3_contracts import REGISTRY
    raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='R1',store_id=c.store_id,required_issue_ids=[e['issue_id'] for e in entries],reviews=entries));path=c.path/'new-R1.json';path.write_bytes(raw)
    trust=ReviewTrustContext(str(path),sha256(raw).hexdigest(),'R1',c.store_id)
    with pytest.raises(S02Error):HistoryService(c.settings,historical_reviews=trust,authority=a).resume(command)
    assert sha256(c.db.read_bytes()).hexdigest()==checksum
    after=controller.get_command(command);assert after==old and after['run'] is None
