"""Independent synthetic H3-A controls, no H3 writer/loader or real decisions.

Existing fixture infrastructure creates a checked local S01/application graph;
E1 allocation here is explicit in memory, never an operational migration.
"""
from copy import deepcopy
from hashlib import sha256
from dacn_s02.codec_boundary import encode
from dacn_s02.profiles import E1
from dacn_s02.h3_history import ReviewRegistry,ReviewTrustContext,HistoryData
from dacn_s02.h3_limits import Budget
from dacn_s02.h3_contracts import REGISTRY
from profile_fixtures import graph


def e1(g):
    for i,r in g.records.items():
        g.record_profiles[i]=E1
        if r['type']=='issue':r['body'].setdefault('resolution_carry',None);r['body'].setdefault('resolution_replacement',None)
    for c in g.commands:g.operation_profiles[c]=E1
    for e in g.events.values():
        if e['kind']=='application_applied':e['payload'].setdefault('observed_source_context_id',None)
    return g


def setup(foundation):
    g=e1(graph(foundation))
    # The positive fixture deliberately represents internal actions with known
    # initiators. Original legacy helpers retain their unknown-initiator controls.
    for r in g.records.values():
        if r['type']=='model':
            for a in r['body']['actions']:a['initiator']='internal'
    return g


def control(g,*,registry_id='ReviewControl',store_id='Store'):
    # Decisions are from the fixture controller's explicit reviews map, not a
    # production reader exporting evaluator/assessment from Issue metadata.
    entries=[dict(issue_id=i,reviewer=v.reviewer,assessment=v.assessment,dependency_sha256=v.dependency_sha256)
        for i,v in sorted(g.reviews.items())]
    value=dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id=registry_id,
        store_id=store_id,required_issue_ids=[x['issue_id'] for x in entries],reviews=entries)
    raw=encode(value);trust=ReviewTrustContext('external-synthetic-registry.json',sha256(raw).hexdigest(),registry_id,store_id)
    return raw,trust


def data(g,budget=None,registry=None):
    budget=budget or Budget()
    if registry is None:
        raw,trust=control(g);registry=ReviewRegistry.parse(raw,trust,budget)
    kw={k:v for k,v in g.kwargs().items() if k!='reviews'}
    return HistoryData(**kw,registry=registry,store_id='Store',budget=budget)


def view(g,budget=None):
    h=data(g,budget);return h.view(g.session,[g.model_id,g.set_id],[g.model_id,g.set_id])


def selector_rows(v,*,unknown=False):
    return [dict(issue_id=q['id'],issue_key=q['body']['issue_key'],target_step=1,
        kind='all_source_uses' if unknown else 'obligation_families',source_refs=deepcopy(q['body']['trace']['source_refs']),
        element_ids=deepcopy(q['body']['blocking']['element_ids']),mapping_part_ids=deepcopy(q['body']['blocking']['mapping_part_ids']),
        impact_known=not unknown,code_task_role=None) for q in v.issues]


def bind_work(v,rows,*,candidate=b'{}',step=1,selected=None,binding_change=None,analysis_change=None,mode='step'):
    from dacn_s02.h3_contracts import Contract,BINDING,POLICY
    from dacn_s02.h3_limits import digest
    from dacn_s02.h3_policy import authorize_bytes,SemanticTrustContext
    if mode!='step':candidate=None
    source=v.context.source;uids=sorted(selected if selected is not None else source.units)
    analysis=dict(version='s02-h3-analysis/0.1.0-draft.2',source_context_id=source.context_id,snapshot_id=source.snapshot_id,
        base_pair=v.pair,selectors_sha256=digest(sorted(rows,key=lambda x:x['issue_key'])),unit_ids=uids,
        inspections=[dict(source_ref=dict(snapshot_id=source.snapshot_id,input_pointer=p),read='inspected',verdict='usable',
            basis_source_refs=[dict(snapshot_id=source.snapshot_id,input_pointer=p)],needed_facts=[],reason='Synthetic full inventory') for p in sorted(source.obligations)],
        independence=[dict(issue_key=q['body']['issue_key'],unit_id=u,verdict='independent',
            basis_source_refs=[dict(snapshot_id=source.snapshot_id,input_pointer=p) for p in sorted(source.obligations)],reason='Independent handwritten test control') for q in v.issues for u in uids])
    if analysis_change:analysis_change(analysis)
    raw=encode(analysis);e=Contract.parse('Analysis',raw,v.history.budget)
    binding=dict(version=BINDING,purpose='synthetic_test_only',provider_id='TestControl',provider_version='local-synthetic/1',policy_version=POLICY,
        store_id='Store',session_id=v.session_id,parent_command_id=v.parent_command_id,source_context_id=source.context_id,snapshot_id=source.snapshot_id,
        archive_sha256=source.archive_sha256,base_pair=v.pair,base_model_sha256=digest(v.context.model()),base_analysis_set_sha256=digest(v.analysis_set),
        operation=mode,goal='build' if mode=='step' else 'admission',step=step,unit_ids=uids,aliases_sha256=digest({}),current_selectors_sha256=analysis['selectors_sha256'],
        progress_before_sha256=None,retained_assessment_hashes=[],read_write_intent_sha256='1'*64,candidate_sha256=sha256(candidate).hexdigest() if candidate is not None else None,
        candidate_length=len(candidate or b''),analysis_sha256=sha256(raw).hexdigest(),analysis_length=len(raw),history_sha256=digest(v.history.binding(v)),
        anchor_sha256=None,historical_reviews_pin=v.history.registry.pin())
    if binding_change:binding_change(binding)
    b=Contract.parse('Binding',encode(binding),v.history.budget)
    from dacn_s02.h3_contracts import AUTHORITY
    authority=encode(dict(format=AUTHORITY,provider_id='TestControl',provider_version='local-synthetic/1',purpose='synthetic_test_only',
        approvals=[dict(binding=binding,decision='allow',reason='External synthetic control')]))
    trust=SemanticTrustContext('TestControl','local-synthetic/1',sha256(authority).hexdigest())
    grant=authorize_bytes(authority,trust,b,v.history.budget)
    return b,e,grant,trust,candidate


def multi_setup(tmp_path,monkeypatch,*,held=False):
    """Two explicitly independent families; per-criterion rows, shared component.

    All topology/source expectations below are handwritten. No closure/reverse
    function constructs the expected independent sets.
    """
    import helpers
    from helpers import Foundation,trace,part,issue
    original_source=helpers.source;original_model=helpers.model
    def source():
        v=original_source();v['functional_requirements'][0]['acceptance_criteria']=['First criterion']
        v['functional_requirements'].append(dict(id='R2',text='Independent second obligation',priority='could',acceptance_criteria=['Second criterion']))
        return v
    def model(*args,**kw):
        m=original_model(*args,**kw);sid=m['body']['actors'][0]['trace']['source_refs'][0]['snapshot_id'];body=m['body']
        for group in ('actions','workflows','components','responsibilities'):
            for n,e in enumerate(body[group]):
                p='/functional_requirements/'+str(n);e['trace']=trace(sid,p)
                if group=='actions':e['initiator']='internal'
                if group=='workflows':
                    for edge in e['edges']:edge['trace']=trace(sid,p)
        body['responsibilities'][1]['component_id']='C1'  # shared context alone is not a dependency
        pairs=[('/functional_requirements/0','P1','A1','RS1'),('/functional_requirements/0/acceptance_criteria/0','PC0','A1','RS1'),
               ('/functional_requirements/1','P2','A2','RS2'),('/functional_requirements/1/acceptance_criteria/0','PC1','A2','RS2')]
        body['mappings']=[dict(id='Row'+str(n),source_ref=dict(snapshot_id=sid,input_pointer=p),parts=[part(i,[a],[resp])],assessment='proposed',issue_ids=[]) for n,(p,i,a,resp) in enumerate(pairs)]
        return m
    with monkeypatch.context() as patch:
        patch.setattr(helpers,'source',source);patch.setattr(helpers,'model',model)
        g=setup(Foundation(tmp_path))
    if held:
        q=issue(g.records[g.model_id],'HoldU',key='HoldU',blocked=['A1'],parts=['P1','PC0']);q['body'].update(resolution_carry=None,resolution_replacement=None)
        g.publish([q],[g.current_issue,q['id']])
    return g


def add_other_session_human_history(g):
    """Copy a synthetic reviewed graph into another session with explicit IDs.

    This is fixture construction only. External decisions are copied from the
    controller and re-bound to fixture IDs, never a production trust derivation.
    """
    from dacn_s02.resolution import HumanReviewEvidence,review_digest
    other=deepcopy(g)
    identities=set(other.records)|set(other.commands)|{other.session}
    remap={i:'Other.'+i for i in identities}
    def walk(x):
        if type(x) is str:return remap.get(x,x)
        if type(x) is list:return [walk(v) for v in x]
        if type(x) is dict:return {k:walk(v) for k,v in x.items()}
        return x
    for i,r in other.records.items():
        ni=remap[i];g.records[ni]=walk(r);g.record_profiles[ni]=other.record_profiles[i];g.owners[ni]=remap[other.owners[i]]
    for c,op in other.commands.items():g.commands[remap[c]]=walk(op);g.operation_profiles[remap[c]]=other.operation_profiles[c]
    for (c,e),event in other.events.items():g.events[remap[c],e]=walk(event)
    for (c,b),stage in other.stages.items():g.stages[remap[c],b]=walk(stage)
    for i,blob in other.blobs.items():g.blobs[remap[i]]=blob
    for i,decision in other.reviews.items():
        ni=remap[i];g.reviews[ni]=HumanReviewEvidence(decision.reviewer,review_digest(g.records[ni],g.records,g.snapshots(),g.record_profiles),decision.assessment)
    return remap
