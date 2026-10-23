"""DB2 review history/selection regressions. All reviews/stores are synthetic."""
from copy import deepcopy
import sqlite3
import pytest
from dacn_s02.repository import Repository,record,digest
from dacn_s02.codec_boundary import encode
from dacn_s02.profiles import E1,L1
from dacn_s02.validation import fields,validate_record
from dacn_s02.errors import S02Error
from dacn_s02.scope import make_scope
from p2_helpers import Foundation
from helpers import operation,run,allscope,evidence
from test_repository import validation
from test_db2 import mixed


def fresh_bundle(tmp_path):
    f=Foundation(tmp_path);m,a=f.initial();op=f.operation();f.repo.prepare(op)
    view=record('view','ReviewView',dict(model_id=m['id'],name='Synthetic',component_ids=['C1','C2'],interface_ids=[],dependency_ids=[],omitted_element_ids=[],scope_note='Not rendered',config_artifact_id=f.config))
    diagram=record('diagram','ReviewDiagram',dict(model_id=m['id'],view_id=view['id'],converter_version='not_run',toolchain_artifact_id=f.config,status='not_run',puml_artifact_id=None,svg_artifact_id=None,aliases=[],validation_id=None))
    v=validation(m,a,'ReviewValidation');v['body'].update(view_id=view['id'],diagram_id=diagram['id'])
    bundle=record('bundle','ReviewBundle',dict(model_id=m['id'],analysis_set_id=a['id'],source_context_id=f.context,scenario_ids=[],characteristic_ids=[],issue_ids=[],answer_ids=[],change_ids=[],view_id=view['id'],diagram_id=diagram['id'],validation_id=v['id'],status='preparing_review',disclosures=['Synthetic; no human acceptance']))
    f.repo.finalize(op['command_id'],[view,diagram,v,bundle,run(op,f.context,f.config)])
    review=record('review','ReviewRoot',dict(bundle_id=bundle['id'],model_id=m['id'],source_context_id=f.context,reviewer='SYNTHETIC',decision='request_changes',supersedes_review_id=None,accepted_scope=make_scope(m['id']),blocked_scope=allscope(m),workflow_choices=[],conditions=[],acknowledged_issue_ids=[],feedback='Synthetic request'))
    return f.repo,dict(session=f.session,context=f.context,config=f.config),review


def prepare(repo,meta):
    op=operation(meta['session'],meta['context'],repo.heads(meta['session']));repo.prepare(op);return op


def publish(repo,meta,review):
    op=prepare(repo,meta)
    repo.finalize(op['command_id'],[review,run(op,meta['context'],meta['config'])])


def successor(old,identity,decision='request_changes'):
    new=deepcopy(old);new['id']=identity
    # Reverse timestamp order deliberately: succession never sorts timestamps.
    new['created_at']='2020-01-01T00:00:00.000Z'
    new['body'].update(supersedes_review_id=old['id'],decision=decision)
    return new


@pytest.fixture(params=['fresh','mixed'])
def history(request,tmp_path):
    if request.param=='mixed':
        repo,meta,_=request.getfixturevalue('mixed');old=repo.get_record('LegacyReview')
    else:
        repo,meta,old=fresh_bundle(tmp_path);publish(repo,meta,old)
    return repo,meta,old


@pytest.mark.parametrize('decision',['request_changes','revoked'])
def test_review_root_contract_and_atomic_rollback(tmp_path,decision):
    repo,meta,review=fresh_bundle(tmp_path);review['body']['decision']=decision
    op=prepare(repo,meta);before=repo.path.read_bytes()
    if decision=='revoked':
        with pytest.raises(S02Error,match='review_revocation_predecessor'):
            repo.finalize(op['command_id'],[review,run(op,meta['context'],meta['config'])])
        assert repo.path.read_bytes()==before
        assert repo.get_record(review['id']) is None
        assert repo.get_command(op['command_id'])['state']=='prepared'
    else:repo.finalize(op['command_id'],[review,run(op,meta['context'],meta['config'])])
    Repository(repo.path).verify()


@pytest.mark.parametrize('decision',['request_changes','revoked'])
def test_unique_tip_is_selected_even_revoked(history,decision):
    repo,meta,old=history;new=successor(old,'NextReview',decision);publish(repo,meta,new)
    reopened=Repository(repo.path);reopened.verify()
    assert reopened.get_record(old['id'])==old and reopened.get_record(new['id'])==new
    with sqlite3.connect(repo.path) as c:
        assert c.execute('SELECT review_id FROM active_reviews WHERE bundle_id=?',(old['body']['bundle_id'],)).fetchone()==(new['id'],)
    with pytest.raises(S02Error):reopened.check_freshness(old['id'])
    if decision=='revoked':
        with pytest.raises(S02Error):reopened.check_freshness(new['id'])
    else:assert reopened.check_freshness(new['id'])==new


@pytest.mark.parametrize('fault',['missing','stale'])
@pytest.mark.parametrize('decision',['request_changes','revoked'])
def test_bad_selection_refused_at_reads_and_before_write(history,fault,decision):
    repo,meta,old=history;new=successor(old,'SelectedTip',decision);publish(repo,meta,new)
    # Capture request pins before corruption: heads is itself a checked read.
    op=operation(meta['session'],meta['context'],repo.heads(meta['session']))
    with sqlite3.connect(repo.path) as c:
        if fault=='missing':c.execute('DELETE FROM active_reviews WHERE bundle_id=?',(old['body']['bundle_id'],))
        else:c.execute('UPDATE active_reviews SET review_id=? WHERE bundle_id=?',(old['id'],old['body']['bundle_id']))
    before=repo.path.read_bytes();reopened=Repository(repo.path)
    for call in [reopened.verify,lambda:reopened.heads(meta['session']),lambda:reopened.get_record(old['id']),lambda:reopened.check_freshness(old['id']),lambda:reopened.prepare(op)]:
        with pytest.raises(S02Error):call()
        assert repo.path.read_bytes()==before
    evidence('review_selection_boundary',fault=fault,decision=decision,database=str(repo.path),synthetic=True)


@pytest.mark.parametrize('fault',['second_root','stale_parent'])
def test_review_cas_rejects_divergent_publication(history,fault):
    repo,meta,old=history;new=successor(old,'CurrentTip');publish(repo,meta,new)
    candidate=successor(old,'ForkCandidate')
    if fault=='second_root':candidate['body']['supersedes_review_id']=None
    op=prepare(repo,meta);before=repo.path.read_bytes()
    with pytest.raises(S02Error,match='active_review_cas'):
        repo.finalize(op['command_id'],[candidate,run(op,meta['context'],meta['config'])])
    assert repo.path.read_bytes()==before
    assert Repository(repo.path).get_record(candidate['id']) is None
    assert repo.get_command(op['command_id'])['state']=='prepared'


@pytest.mark.parametrize('fault',['missing','stale'])
def test_post_mutation_check_rolls_back_selection_damage(history,fault):
    repo,meta,old=history;new=successor(old,'PostCheckTip','revoked');op=prepare(repo,meta)
    before=repo.path.read_bytes()
    def hook(point,c):
        if point=='after_insert':
            if fault=='missing':c.execute('DELETE FROM active_reviews WHERE bundle_id=?',(old['body']['bundle_id'],))
            else:c.execute('UPDATE active_reviews SET review_id=? WHERE bundle_id=?',(old['id'],old['body']['bundle_id']))
    writer=Repository(repo.path,_hook=hook)
    with pytest.raises(S02Error):writer.finalize(op['command_id'],[new,run(op,meta['context'],meta['config'])])
    assert repo.path.read_bytes()==before
    reopened=Repository(repo.path);reopened.verify()
    assert reopened.get_record(new['id']) is None
    assert reopened.check_freshness(old['id'])==old


def inject_history(repo,meta,rows,selected):
    """SQL fault fixture, not a production writer: hashes/links/DDL stay valid."""
    with sqlite3.connect(repo.path) as c:
        c.execute('PRAGMA foreign_keys=ON')
        for review in rows:
            raw=encode(review)
            c.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)',(review['id'],meta['session'],'review',review['created_at'],raw.decode('ascii'),digest(raw),E1))
            for value,spec,path,_ in fields(review,profile=E1):
                if 'x-record' in spec:c.execute('INSERT INTO record_links VALUES (?,?,?)',(review['id'],path,value))
        c.execute('UPDATE active_reviews SET review_id=? WHERE bundle_id=?',(selected,rows[0]['body']['bundle_id']))
        assert c.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('fault',['fork','multiple_roots','disconnected_cycle','self_cycle'])
def test_corrupt_history_rejected_even_with_selected_leaf(history,fault):
    repo,meta,old=history;op=operation(meta['session'],meta['context'],repo.heads(meta['session']))
    one=successor(old,'Extra1');two=successor(old,'Extra2');selected=one['id']
    if fault=='multiple_roots':one['body']['supersedes_review_id']=None;rows=[one]
    elif fault=='disconnected_cycle':
        one['body']['supersedes_review_id']=two['id'];two['body']['supersedes_review_id']=one['id'];rows=[one,two];selected=old['id']
    elif fault=='self_cycle':one['body']['supersedes_review_id']=one['id'];rows=[one];selected=old['id']
    else:rows=[one,two]
    inject_history(repo,meta,rows,selected);before=repo.path.read_bytes()
    for call in [lambda:Repository(repo.path).verify(),lambda:Repository(repo.path).prepare(op)]:
        with pytest.raises(S02Error):call()
        assert repo.path.read_bytes()==before


def test_e1_revocation_gate_does_not_change_l1_record_semantics(tmp_path):
    repo,meta,review=fresh_bundle(tmp_path)
    with repo._read() as c:records=repo._check(c)[0]
    review['body']['decision']='revoked';records[review['id']]=review
    profiles={i:E1 for i in records}
    # Identical payload: explicit L1 preserves its pre-existing gap.
    validate_record(review,records,{},owner_profile=L1,profile_map={**profiles,review['id']:L1})
    with pytest.raises(S02Error,match='review_revocation_predecessor'):
        validate_record(review,records,{},owner_profile=E1,profile_map=profiles)


@pytest.mark.parametrize('fault',['self','other_bundle','missing'])
def test_e1_revocation_needs_valid_same_bundle_predecessor(tmp_path,fault):
    repo,meta,review=fresh_bundle(tmp_path)
    with repo._read() as c:records=repo._check(c)[0]
    other=deepcopy(review);other['id']='OtherReview'
    bundle=deepcopy(records[review['body']['bundle_id']]);bundle['id']='OtherBundle'
    other['body']['bundle_id']=bundle['id'];records.update({other['id']:other,bundle['id']:bundle})
    review['body'].update(decision='revoked',supersedes_review_id={'self':review['id'],'other_bundle':other['id'],'missing':'MissingReview'}[fault]);records[review['id']]=review
    with pytest.raises(S02Error):validate_record(review,records,{},owner_profile=E1,profile_map={i:E1 for i in records})
