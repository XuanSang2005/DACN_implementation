from copy import deepcopy
from dataclasses import replace
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h2_limits import Budget,Limits,references
from dacn_s02.h2_contracts import AnalysisEvidence,BindingRequest,SourceInventory,HoldSelector,AuthorityContext
from h2_fixtures import graph,context,work,snapshot,R0,R1,CR,N,C,HASH


def test_inventory_includes_criteria_nfr_constraints_and_preserves_unknowns():
    s=snapshot();original=deepcopy(s);src=SourceInventory(s,'SRC',HASH,Budget(clock=lambda:0))
    assert src.obligations=={R0,R1,CR,N,C}
    assert len(src.units)==4
    assert src.units[next(f.unit_id for f in src.families if f.pointer==R0)].obligations=={R0,CR}
    assert s==original and s['input']['functional_requirements'][0]['priority'] is None
    assert all(v is None for v in s['input']['operating_conditions'].values())


@pytest.mark.parametrize('field',['trusted','extra','reviewer_name'])
def test_closed_analysis_never_accepts_authority_flags(field):
    ctx=context();w=work(ctx);v=w.evidence.payload();v[field]=True
    with pytest.raises(S02Error):AnalysisEvidence(encode(v),ctx.source,ctx.budget)


@pytest.mark.parametrize('change',[
 lambda e:e.update(version='unsupported'),
 lambda e:e.update(snapshot_id='Other'),
 lambda e:e['inspections'][0]['source_ref'].update(input_pointer='/functional_requirements/00'),
 lambda e:e['inspections'].append(deepcopy(e['inspections'][0])),
 lambda e:e['independence'].append(deepcopy(e['independence'][0])),
 lambda e:e['inspections'][0].update(read='not_inspected',verdict='usable'),
])
def test_analysis_invalid_contracts(change):
    with pytest.raises(S02Error):work(context(),evidence_change=change)


@pytest.mark.parametrize('change',[
 lambda b:b.update(version='old'),lambda b:b.update(step=True),
 lambda b:b.update(candidate_length=True),lambda b:b.update(provider_version='unknown'),
 lambda b:b.update(unit_ids=b['unit_ids']*2),lambda b:b.update(analysis_sha256='INVALID'),
 lambda b:b.update(trusted=True),
])
def test_binding_closed_types_and_version(change):
    with pytest.raises(S02Error):work(context(),binding_change=change)


def test_revalidation_contract_has_no_candidate_but_no_writer_is_created():
    w=work(context());v=w.binding.payload();v.update(operation='revalidate',goal='retained_output',candidate_sha256=None,candidate_length=0)
    parsed=BindingRequest.parse(v,Budget(clock=lambda:0))
    assert parsed.payload()['operation']=='revalidate'
    v['candidate_sha256']=HASH
    with pytest.raises(S02Error):BindingRequest.parse(v,Budget(clock=lambda:0))


def test_unknown_scope_requires_future_all_source_selector():
    with pytest.raises(S02Error):work(context(),selector_change=lambda s:s.update(impact_known=False))
    w=work(context(),all_source=True)
    assert not w.selectors[0].impact_known and w.selectors[0].kind=='all_source_uses'


def test_reference_occurrences_and_atomic_refs():
    src=dict(snapshot_id='S',input_pointer='/functional_requirements/0')
    v=dict(finding_handles=['same','same'],questions=['same'],finding_handle='same',source_refs=[src,src],unit_ids=['u','u'],guard_keys=['g','g'],progress_by_unit={'u':dict(issue_key='q')},independence=[dict(unit_id='u',held_unit_id='v')],id='declaration',handle='declaration')
    assert references(v)==14


def test_50000_ref_boundary_and_repeated_handles():
    Budget(clock=lambda:0).inspect(dict(finding_handles=['same']*50000))
    with pytest.raises(S02Error) as e:Budget(clock=lambda:0).inspect(dict(finding_handles=['same']*50001))
    assert e.value.error['details']['reason']=='refs'


def test_aggregate_input_refs_not_reset_by_file_or_unit():
    b=Budget(clock=lambda:0);b.inspect(dict(unit_ids=['u']*25000),input_lane=True)
    b.inspect(dict(guard_keys=['g']*25000),input_lane=True)
    with pytest.raises(S02Error):b.inspect(dict(issue_key='one_more'),input_lane=True)


def test_aggregate_lexical_values_before_decoding_next_input():
    b=Budget(clock=lambda:0,limits=replace(Limits(),values=8))
    b.parse(b'[0,1,2]')  #4 values
    b.parse(b'[3,4,5]')  #4 more
    with pytest.raises(S02Error):b.parse(b'null')


def test_work_byte_sum_not_per_blob():
    b=Budget(clock=lambda:0);b.raw_work(b'x'*524288,b'y'*524288)
    with pytest.raises(S02Error):b.raw_work(b'x'*524288,b'y'*524289)


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'NaN',b'Infinity',b'"\\ud800"'])
def test_exact_codec_not_replaced_by_lexical_guard(raw):
    with pytest.raises(S02Error):Budget(clock=lambda:0).parse(raw)


def test_depth_strings_cycles_and_no_limit_increase():
    with pytest.raises(S02Error):Budget(limits=replace(Limits(),refs=50001))
    with pytest.raises(S02Error):Budget(clock=lambda:0).parse(('['*65+'0'+']'*65).encode())
    with pytest.raises(S02Error):Budget(clock=lambda:0).inspect('é'*32769)
    cycle=[];cycle.append(cycle)
    with pytest.raises(S02Error):Budget(clock=lambda:0).inspect(cycle)


def test_serialized_caps_measure_encoded_bytes_not_character_count():
    b=Budget(clock=lambda:0,limits=replace(Limits(),config_bytes=32))
    assert b.serialized(dict(x='é'), 'config')==encode(dict(x='é'))
    with pytest.raises(S02Error):b.serialized(dict(x='é'*20),'config')


def test_one_cooperative_budget_shared_through_graph_and_policy():
    now=[0];b=Budget(clock=lambda:now[0]);ctx=context(budget=b)
    ctx.closure(parts=['P1']);now[0]=31
    with pytest.raises(S02Error) as e:ctx.closure(parts=['P1'])  # even cache hits check
    assert e.value.error['details']['reason']=='compute_seconds'


def test_graph_caps_do_not_truncate_results():
    b=Budget(clock=lambda:0,limits=replace(Limits(),entities=2))
    with pytest.raises(S02Error):context(graph(),budget=b)


def test_authority_context_is_external_and_versioned():
    with pytest.raises(S02Error):AuthorityContext('test-provider','other',HASH)
    with pytest.raises(S02Error):AuthorityContext('test-provider','local-synthetic/1','bad')


def test_exact_codec_metadata_round_trip_and_immutable_evidence():
    from dacn_s02.codec_boundary import decode
    from h2_fixtures import decide
    ctx=context();w=work(ctx)
    parsed=BindingRequest.parse(decode(w.binding.raw),Budget(clock=lambda:0))
    assert parsed.key==w.binding.key
    copy=w.evidence.payload();copy['inspections'].clear()
    assert len(w.evidence.inspections)==5
    with pytest.raises((S02Error,TypeError)):w.evidence.inspections[R1]['verdict']='held'
    with pytest.raises(S02Error):w.evidence.units=frozenset()
    assert decide(w).allowed_units


def test_unicode_key_and_malformed_progress_fail_controlled():
    with pytest.raises(S02Error):Budget(clock=lambda:0).inspect({'\ud800':'value'})
    with pytest.raises(S02Error):Budget(clock=lambda:0).inspect(dict(progress_by_unit=[]))


def test_forged_binding_object_does_not_reuse_old_grant_hash():
    from h2_fixtures import decide
    w=work(context());w.binding=BindingRequest(b'{}',w.binding.key)
    with pytest.raises(S02Error):decide(w)


def test_named_input_slot_is_counted_once_without_resetting_other_inputs():
    b=Budget(clock=lambda:0);raw=encode(dict(finding_handles=['same']*24000))
    b.parse(raw,slot='candidate');b.parse(raw,slot='candidate')
    assert b.input_refs==24000
    b.inspect(dict(guard_keys=['other']*26000),input_lane=True,slot='authority')
    assert b.input_refs==50000
    with pytest.raises(S02Error):b.inspect(dict(issue_key='excess'),input_lane=True)
    with pytest.raises(S02Error):b.parse(b'{}',slot='candidate')
