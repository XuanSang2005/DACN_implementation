from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_history import ReviewRegistry,ReviewTrustContext
from dacn_s02.h3_limits import Budget
from h3_fixtures import setup,control,data,view


def test_empty_registry_is_explicit_external_lane(foundation):
    g=setup(foundation);raw,trust=control(g);b=Budget();r=ReviewRegistry.parse(raw,trust,b)
    assert r.payload()['required_issue_ids']==[] and dict(r.reviews())=={}
    assert r.pin()['raw_sha256']==sha256(raw).hexdigest()
    with pytest.raises(S02Error):ReviewRegistry.parse(raw,None,b)


def test_registry_ancestor_inventory_decisions_and_immutability(foundation):
    g=setup(foundation);q=g.carry('not_applicable','human_review');g.replacement(True)
    raw,trust=control(g);before=deepcopy(g.kwargs());b=Budget();registry=ReviewRegistry.parse(raw,trust,b)
    h=data(g,b,registry);v=h.view(g.session,[g.model_id,g.set_id],[g.model_id,g.set_id])
    assert set(registry.payload()['required_issue_ids'])=={q['id'],g.current_issue}
    assert h.registry.pin()['reviews_sha256']!=h.registry.pin()['raw_sha256']
    assert v.projection('Question2')['obsolete_issue_id']==q['id']
    assert g.kwargs()==before
    detached=registry.payload();detached['reviews'].clear();assert len(registry.reviews())==2
    with pytest.raises(TypeError):registry.reviews()['fake']=None


@pytest.mark.parametrize('field,value',[('expected_sha256','0'*64),('expected_registry_id','Other'),('expected_store_id','Other')])
def test_external_pins_never_taken_from_payload(foundation,field,value):
    g=setup(foundation);raw,trust=control(g)
    with pytest.raises(S02Error):ReviewRegistry.parse(raw,replace(trust,**{field:value}),Budget())


@pytest.mark.parametrize('mutation',['missing','extra','duplicate','unsorted','wrong_reviewer','wrong_assessment','wrong_digest','unknown_field','format'])
def test_registry_invalid_or_missing_evidence_fails_closed(foundation,mutation):
    g=setup(foundation);g.carry('not_applicable','human_review');g.replacement(True)
    raw,trust=control(g);v=ReviewRegistry.parse(raw,trust,Budget()).payload()
    if mutation=='missing':v['reviews'].pop();v['required_issue_ids'].pop()
    if mutation=='extra':v['required_issue_ids'].append('ZUnused');v['reviews'].append(dict(issue_id='ZUnused',reviewer='SYNTHETIC',assessment='complete',dependency_sha256='0'*64))
    if mutation=='duplicate':v['reviews'].append(deepcopy(v['reviews'][0]))
    if mutation=='unsorted':v['reviews'].reverse();v['required_issue_ids'].reverse()
    if mutation=='wrong_reviewer':v['reviews'][0]['reviewer']='OTHER CONTROL'
    if mutation=='wrong_assessment':v['reviews'][0]['assessment']='undetermined'
    if mutation=='wrong_digest':v['reviews'][0]['dependency_sha256']='0'*64
    if mutation=='unknown_field':v['trusted']=True
    if mutation=='format':v['format']='unknown'
    raw=encode(v);trust=replace(trust,expected_sha256=sha256(raw).hexdigest())
    with pytest.raises(S02Error):
        b=Budget();r=ReviewRegistry.parse(raw,trust,b);data(g,b,r)


def test_registry_duplicate_json_and_non_utf8_are_rejected(foundation):
    g=setup(foundation);raw,t=control(g)
    for broken in (raw[:-1]+b',"format":"duplicate"}',raw.decode().encode('utf-16'),raw.decode().encode('utf-16-le')):
        with pytest.raises(S02Error):ReviewRegistry.parse(broken,replace(t,expected_sha256=sha256(broken).hexdigest()),Budget())


def test_semantic_approval_cannot_replace_historical_registry(foundation):
    g=setup(foundation);g.carry('applicable','human_review');raw,t=control(g)
    with pytest.raises(S02Error):data(g,Budget(),registry={'trusted':True,'reviewer':'SYNTHETIC REVIEWER'})
    # Self-derived DB fields have no supported parser entry without external pins.
    with pytest.raises(S02Error):ReviewRegistry.parse(raw,{'expected_sha256':sha256(raw).hexdigest()},Budget())


def test_registry_pin_is_fixed_across_structural_history_growth(foundation):
    g=setup(foundation);g.carry('applicable','human_review');b=Budget();raw,t=control(g);r=ReviewRegistry.parse(raw,t,b)
    old=data(g,b,r);g.carry(new_model=True);new=data(g,b,r)
    assert old.registry.pin()==new.registry.pin()
    assert len(new.registry.reviews())==1


def test_new_human_history_requires_new_external_inventory_not_auto_upgrade(foundation):
    g=setup(foundation);raw,t=control(g);b=Budget();r=ReviewRegistry.parse(raw,t,b)
    g.carry('applicable','human_review')
    with pytest.raises(S02Error,match='registry_whole_store_required_ids'):data(g,b,r)


def test_graph_guard_runs_before_recursive_copy_or_hash(foundation):
    g=setup(foundation);raw,t=control(g);b=Budget();r=ReviewRegistry.parse(raw,t,b)
    g.records['M2']['body']['extra']=[];g.records['M2']['body']['extra'].append(g.records['M2']['body']['extra'])
    with pytest.raises(S02Error,match='cyclic_input'):data(g,b,r)


def test_referenced_history_depth_uses_shared_existing_cap(foundation):
    from dacn_s02.repository import record
    g=setup(foundation);root=deepcopy(g.records[g.current_issue]);previous=None
    # Valid shapes and IDs, intentionally no publication. Bound the referential
    # traversal before recursive canonical validation can consume stack depth.
    for n in range(66):
        q=deepcopy(root);q['id']='LongLineage'+str(n);q['body'].update(supersedes_id=previous,answer_ids=[],resolution_event_refs=[],resolution_carry=None,resolution_replacement=None)
        g.add(q);previous=q['id']
    with pytest.raises(S02Error,match='depth'):data(g)
