"""Direct C-01/02 regressions; synthetic, installed wheel, no oracle edits."""
from hashlib import sha256
import pytest
from dacn_s02.h3_history import HistoryData
from dacn_s02.h3_limits import Budget
from h3_c_fixtures import b_parent,request,projected,units


@pytest.fixture(scope='module')
def stages(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        base=b_parent(tmp_path_factory.mktemp('C-findings-source'),patch,'actor_only')[2]
    result=[base]
    for step in (1,2,3):
        cfg,raw=request(result[-1],step=step)
        _,_,current,plan=projected(result[-1],cfg,raw)
        assert plan['candidate_outcome']=='valid'
        result.append(current)
    return result


def fresh(base):
    h=HistoryData(**base.history.payload(),registry=base.history.registry,store_id=base.history.store_id,budget=Budget())
    return h.view(base.session_id,base.pair,base.pair)


def assert_guard(base,cfg,raw,reason):
    h,b,r,p=projected(base,cfg,raw)
    assert p['candidate_outcome']=='guard_only' and r.context.model()==b.context.model()
    assert not {'model','change'}&{v['type'] for v in p['batch']['records']}
    assert any(reason in q['body']['reason'].split(';') for q in r.issues if q['body']['issue_key'] in p['admission']['guards'])
    for uid in cfg['unit_ids']:
        before=cfg['parent_metadata']['progress_by_unit'][uid];after=p['admission']['progress_by_unit'][uid]
        assert after['work_completed_through']==before['work_completed_through'] and after['outputs']==before['outputs']
        assert after['assessment_state']=='needs_revalidation'
    assert next(v for v in p['batch']['records'] if v['type']=='run')['body']['status']=='blocked'
    for lane in ('candidate','analysis'):
        pin=cfg['inputs'][lane];stage=h._state['stages'][cfg['command_id'],pin['stage_ref']['blob_id']]
        assert stage['bytes']==raw[lane] and stage['sha256']==sha256(raw[lane]).hexdigest()
        aid=next(v['artifact_id'] for v in p['batch']['artifact_sources'] if v['stage_ref']==pin['stage_ref'])
        assert h._state['blobs'][aid]==raw[lane]
    return p


@pytest.mark.parametrize('step,negative',[(1,'held'),(2,'held'),(2,'not_inspected'),(2,'unrepresented')])
def test_C01_raw_negative_is_not_overridden_by_usable_analysis(stages,step,negative):
    base=fresh(stages[step-1])
    def mutate(c,a):
        row=next(r for r in c['inspection'] if r['source_ref']['input_pointer']=='/functional_requirements/1')
        if negative=='unrepresented':c['unrepresented_source_refs']=[row['source_ref']]
        else:row.update(verdict='held',needed_facts=['Synthetic unresolved source fact'])
        if negative=='not_inspected':row['read']='not_inspected'
        assert next(r for r in a['inspections'] if r['source_ref']==row['source_ref'])['verdict']=='usable'
    cfg,raw=request(base,step=step,mutate=mutate)
    assert_guard(base,cfg,raw,'CANDIDATE_SOURCE_HOLD_MISSING')


@pytest.mark.parametrize('negative',['held','unrepresented'])
def test_C01_compatible_U_hold_keeps_independent_V_progress(tmp_path,monkeypatch,negative):
    base=b_parent(tmp_path,monkeypatch,'pending')[2]
    cfg,raw=request(base);_,_,base,_=projected(base,cfg,raw)
    def mutate(c,a):
        row=next(r for r in c['inspection'] if r['source_ref']['input_pointer']=='/functional_requirements/0')
        assert row['verdict']=='held' and next(r for r in a['inspections'] if r['source_ref']==row['source_ref'])['verdict']=='held'
        if negative=='unrepresented':c['unrepresented_source_refs']=[row['source_ref']]
    cfg,raw=request(base,step=2,mutate=mutate);_,_,r,p=projected(base,cfg,raw)
    v=units(r)['/functional_requirements/1'];u=units(r)['/functional_requirements/0']
    assert p['candidate_outcome']=='valid' and r.pair[0]!=base.pair[0]
    assert p['admission']['progress_by_unit'][v]['work_completed_through']==2 and p['admission']['progress_by_unit'][v]['assessment_state']=='current'
    assert p['admission']['progress_by_unit'][u]['assessment_state']!='current'
    assert r.issue('Question2')['body']['resolution_carry']['assessment']=='undetermined'


def test_C02_null_coverage_remains_raw_and_projected_gap_without_new_Model(stages):
    base=fresh(stages[3])
    def mutate(c,a):c['proposals']['mappings'][0]['parts'][0]['covered_portion']=None
    cfg,raw=request(base,step=4,mutate=mutate);p=assert_guard(base,cfg,raw,'PART_GAP')
    rows=p['candidate_projection']['pre_successor_model']['body']['mappings']
    part=next(r for r in rows if r['source_ref']['input_pointer']=='/functional_requirements/1')['parts'][0]
    assert part['covered_portion'] is None and part['assignment']=='proposed' and part['remaining_gap'] is None
