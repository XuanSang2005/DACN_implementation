from copy import deepcopy
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.codec_boundary import encode
from dacn_s02.h2_candidates import parse_candidate,scope_request_hash,VERSION
from h2_fixtures import context,work,unit,R1,CR,HASH


def candidate(w,step=4):
    refs=lambda p:dict(snapshot_id='SNAP',input_pointer=p)
    proposals=dict(findings=[])
    if step==4:
        p=dict(handle='part',obligation='Synthetic scoped proposal',assignment='proposed',target='components',action_ids=[dict(base_handle='action')],primary_responsibility_ids=[dict(base_handle='responsibility')],supporting_responsibility_ids=[],covered_portion='Synthetic only',remaining_gap=None,finding_handles=[])
        proposals['mappings']=[dict(source_ref=refs(R1),assessment='proposed',parts=[p],finding_handles=[])]
    return dict(candidate_version=VERSION,step=step,unit_ids=list(w.binding.payload()['unit_ids']),scope_request_sha256=scope_request_hash(w.binding),proposals=proposals,questions=[],inspection=[dict(source_ref=refs(p),read='inspected',verdict='usable',needed_facts=[],evidence_source_refs=[refs(p)],finding_handles=[],reason='Synthetic') for p in sorted(w.ctx.source.obligations)],unrepresented_source_refs=[])


def parse(w,c,**kw):
    return parse_candidate(encode(c),w.ctx,step=4,unit_ids=w.binding.payload()['unit_ids'],expected_scope_hash=scope_request_hash(w.binding),base_aliases=kw.get('aliases',{'action':dict(id='A2',kind='Action'),'responsibility':dict(id='RS2',kind='Responsibility')}),read_context_ids=kw.get('read',frozenset(['A2','RS2'])))


def test_closed_candidate_valid_typed_scoped_mapping_without_allocation():
    w=work(context(),step=4);c=candidate(w);original=deepcopy(c);result=parse(w,c)
    assert result.declared_handles==( ('part','Part'), )
    assert result.base_reference_ids=={'A2','RS2'}
    assert result.payload()['proposals']['mappings'][0]['parts'][0]['handle']=='part'
    assert c==original


@pytest.mark.parametrize('change',[
 lambda c:c.update(trusted=True),lambda c:c.update(candidate_version='old'),
 lambda c:c.update(scope_request_sha256='2'*64),lambda c:c.update(unit_ids=['foreign']),
 lambda c:c['proposals']['mappings'][0]['parts'][0].update(action_ids=[dict(local_handle='missing')]),
 lambda c:c['proposals']['mappings'][0]['parts'][0].update(action_ids=[dict(base_handle='responsibility')]),
 lambda c:c['proposals']['mappings'].append(deepcopy(c['proposals']['mappings'][0])),
 lambda c:c['inspection'].pop(),
 lambda c:c['proposals']['mappings'][0]['source_ref'].update(snapshot_id='Other'),
])
def test_candidate_negatives_do_not_change_scope_or_oracle(change):
    w=work(context(),step=4);c=candidate(w);change(c)
    with pytest.raises(S02Error):parse(w,c)


def test_base_context_read_right_is_explicit_and_typed():
    w=work(context(),step=4);c=candidate(w)
    with pytest.raises(S02Error):parse(w,c,read=frozenset(['RS2']))
    with pytest.raises(S02Error):parse(w,c,aliases={'action':dict(id='A2',kind='Responsibility')})


def test_criterion_family_cannot_be_truncated_or_extra_row_added():
    from h2_fixtures import R0
    w=work(context(),selected=(R0,),step=4);c=candidate(w)
    c['proposals']['mappings'][0]['source_ref']['input_pointer']=R0
    with pytest.raises(S02Error):parse(w,c)


def test_scoped_candidate_and_pre_post_policy_share_exact_raw_pins():
    from dataclasses import replace
    from dacn_s02.h2_graph import ModelContext
    from dacn_s02.h2_policy import admit,assess_union
    from h2_fixtures import graph,part
    m=graph();m['body']['mappings'][2].update(parts=[],assessment='not_assessed',issue_ids=['Q'])
    ctx=context(m)
    def build_raw(req,e):
        proposals=dict(findings=[],mappings=[dict(source_ref=dict(snapshot_id='SNAP',input_pointer=R1),assessment='proposed',parts=[dict(handle='new-part',obligation='Synthetic scoped proposal',assignment='proposed',target='components',action_ids=[dict(base_handle='action')],primary_responsibility_ids=[dict(base_handle='responsibility')],supporting_responsibility_ids=[],covered_portion='Synthetic',remaining_gap=None,finding_handles=[])],finding_handles=[])])
        return encode(dict(candidate_version=VERSION,step=4,unit_ids=req['unit_ids'],scope_request_sha256=scope_request_hash(req),proposals=proposals,questions=[],inspection=[dict(source_ref=r['source_ref'],read=r['read'],verdict=r['verdict'],needed_facts=r['needed_facts'],evidence_source_refs=r['basis_source_refs'],finding_handles=[],reason=r['reason']) for r in e['inspections']],unrepresented_source_refs=[]))
    w=work(ctx,step=4,candidate_builder=build_raw)
    parsed=parse_candidate(w.candidate,ctx,step=w.binding.payload()['step'],unit_ids=w.binding.payload()['unit_ids'],expected_scope_hash=scope_request_hash(w.binding),base_aliases={'action':dict(id='A2',kind='Action'),'responsibility':dict(id='RS2',kind='Responsibility')},read_context_ids=frozenset(['A2','RS2']))
    assert parsed.sha256==w.binding.payload()['candidate_sha256']
    before=admit(ctx,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    # Independent prototype fixture, not a builder/handler or allocated Run.
    after_model=deepcopy(m);after_model.update(id='M2');after_model['body'].update(parent_model_id=ctx.id,revision=2,change_id='Change2')
    after_model['body']['mappings'][2].update(parts=[part('NewPart',['A2'],['RS2'])],assessment='proposed')
    after=ModelContext(after_model,ctx.source,ctx.budget)
    result=assess_union(ctx,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    assert before.allowed_units==(unit(ctx,R1),) and result.allowed_units==(unit(ctx,R1),)
    assert result.footprint.actions=={'A2'} and result.global_blocked
    assert w.issues[0]['body']['status']=='open'
