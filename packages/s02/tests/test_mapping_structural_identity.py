"""E1 structural reuse retains Part-to-mapping associations; synthetic only."""
from copy import deepcopy
import pytest
import helpers
from dacn_s02.errors import S02Error
from dacn_s02.resolution import _scope_proof, _target_footprint_unchanged
from dacn_s02.scope import make_scope
from profile_fixtures import graph, fullfoot, scope_proof
from test_p1_audit_regressions import replacement_successor


def mapping_graph(tmp_path, monkeypatch, kind):
    source0,model0=helpers.source,helpers.model
    def source():
        value=source0()
        if kind=='requirements':
            second=deepcopy(value['functional_requirements'][0]);second.update(id='R2',text='Distinct obligation R2')
            value['functional_requirements'].append(second)
        else:value['functional_requirements'][0]['acceptance_criteria']=['First criterion','Second criterion']
        return value
    def model(*args,**kwargs):
        m=model0(*args,**kwargs);row=m['body']['mappings'][0];parts=row['parts']
        if kind=='requirements':
            second=deepcopy(row);second.update(id='Map2',parts=[parts[-1]])
            second['source_ref']['input_pointer']='/functional_requirements/1'
            row['parts']=parts[:-1];m['body']['mappings'].append(second)
        else:
            row['parts']=[parts[0]]
            for index,part in enumerate(parts[1:]):
                other=deepcopy(row);other.update(id='Map'+str(index+2),parts=[part])
                other['source_ref']['input_pointer']='/functional_requirements/0/acceptance_criteria/'+str(index)
                m['body']['mappings'].append(other)
        return m
    monkeypatch.setattr(helpers,'source',source);monkeypatch.setattr(helpers,'model',model)
    g=graph(helpers.Foundation(tmp_path));g.check();return g


def cover_sources(proof, rows, branch):
    field='source_checks' if branch=='carry' else 'obligation_checks'
    source_fields=('from_ref','to_ref') if branch=='carry' else ('old_ref','current_ref')
    template=proof[field][0];proof[field]=[]
    for row in rows:
        check=deepcopy(template)
        for key in source_fields:check[key]=deepcopy(row['source_ref'])
        proof[field].append(check)


def candidate(g, branch):
    if branch=='carry':
        q=g.carry(new_model=True);p=q['body']['resolution_carry'];m=g.records[g.model_id]
        cover_sources(p,m['body']['mappings'],branch);g.check()
        return q,m,None
    g.carry('not_applicable','human_review');old,target=g.replacement(True)
    cover_sources(old['body']['resolution_replacement'],g.records[g.model_id]['body']['mappings'],branch)
    g.review(old['id']);g.check()
    q,t,m,items=replacement_successor(g,old,target,new_model=True)
    g.publish(items,[q['id'],t['id']],new_model=m);g.check()
    return q,m,t


def mutate(m, mutation):
    rows=m['body']['mappings'];left,right=rows[-2:]
    if mutation=='swap_sources':left['source_ref'],right['source_ref']=right['source_ref'],left['source_ref']
    elif mutation=='reparent':
        # Keep every row nonempty: move a Part or exchange singleton owners.
        if len(left['parts'])>1:right['parts'].append(left['parts'].pop())
        else:left['parts'][0],right['parts'][0]=right['parts'][0],left['parts'][0]
    elif mutation=='row_identity':left['id']='RenamedMapping'
    elif mutation=='assessment':left['assessment']='not_assessed'
    elif mutation=='reorder':
        rows.reverse()
        for row in rows:
            row['parts'].reverse()
            for p in row['parts']:
                for k in ('action_ids','primary_responsibility_ids','supporting_responsibility_ids','issue_ids'):p[k].reverse()
    elif mutation!='unchanged':raise AssertionError(mutation)


@pytest.mark.parametrize('kind',['requirements','criteria'])
@pytest.mark.parametrize('branch',['carry','replacement'])
@pytest.mark.parametrize('mutation',['swap_sources','reparent','row_identity','assessment','reorder','unchanged'])
def test_mapping_context_controls_structural_release(tmp_path,monkeypatch,kind,branch,mutation):
    g=mapping_graph(tmp_path,monkeypatch,kind);q,m,t=candidate(g,branch);mutate(m,mutation)
    before=deepcopy(g.kwargs())
    if mutation in ('unchanged','reorder'):g.check()
    else:
        with pytest.raises(S02Error,match='carry_structural_proof|replacement_structural_continuation|replacement_target_footprint'):g.check()
    assert g.kwargs()==before


@pytest.mark.parametrize('branch',['carry','replacement'])
@pytest.mark.parametrize('mode',['hold','review','stale_review'])
@pytest.mark.parametrize('kind',['requirements','criteria'])
def test_changed_association_keeps_hold_or_requires_current_review(tmp_path,monkeypatch,branch,mode,kind):
    g=mapping_graph(tmp_path,monkeypatch,kind);q,m,t=candidate(g,branch)
    p=q['body']['resolution_carry' if branch=='carry' else 'resolution_replacement']
    if mode!='hold':
        p['evaluation'].update(method='human_review',evaluator='SYNTHETIC REVIEWER');g.review(q['id'])
    mutate(m,'swap_sources')
    if mode=='hold':
        p['assessment']='undetermined' if branch=='carry' else 'incomplete'
        q['body'].update(status='resolution_pending_revalidation',blocking=fullfoot(m['id']))
    if mode=='review':g.review(q['id'])
    if mode=='stale_review':
        with pytest.raises(S02Error,match='resolution_human_evidence_binding'):g.check()
    else:g.check()


def test_mapping_change_reaches_scope_through_reverse_impact():
    from dacn_s02.resolution import footprint
    from dacn_s02.scope import reverse_impact
    old=helpers.model('Context','Snapshot','Run')
    first=old['body']['mappings'][0];other=deepcopy(first)
    other.update(id='Map2',parts=[first['parts'].pop()])
    other['source_ref']['input_pointer']='/functional_requirements/1'
    old['body']['mappings'].append(other);new=deepcopy(old);new['id']='M2'
    # A1's closure reaches P2 via shared P12 and A2; the seed need not name P2.
    scope,known=footprint(old,make_scope(old['id'],['A1']))
    assert known and 'P2' in scope['mapping_part_ids']
    assert 'A1' in reverse_impact(new,set(),{'P2'})['element_ids']
    a=dict(body=dict(model_id=old['id'],affected=scope))
    b=dict(body=dict(model_id=new['id'],affected=fullfoot(new['id'])))
    proof=dict(scope_check=scope_proof(old['id'],new['id']))
    records={old['id']:old,new['id']:new}
    assert _scope_proof(b,a,proof,records)[:2]==(True,True)
    mutate(new,'swap_sources')
    assert _scope_proof(b,a,proof,records)[:2]==(True,False)


@pytest.mark.parametrize('field',['affected','blocking'])
def test_target_comparison_checks_part_context_independently(field):
    old=helpers.model('Context','Snapshot','Run');new=deepcopy(old);new['id']='M2'
    before=dict(model_id=old['id'],affected=make_scope(old['id']),blocking=make_scope(old['id']))
    after=dict(model_id=new['id'],affected=make_scope(new['id']),blocking=make_scope(new['id']))
    before[field]=make_scope(old['id'],parts=['P2']);after[field]=make_scope(new['id'],parts=['P2'])
    records={old['id']:old,new['id']:new}
    assert _target_footprint_unchanged(before,after,records)
    new['body']['mappings'][0]['source_ref']['input_pointer']='/functional_requirements/1'
    assert not _target_footprint_unchanged(before,after,records)
