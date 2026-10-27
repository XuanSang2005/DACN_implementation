"""Handwritten H2-A graphs/claims only. No store, builder or scope oracle calls."""
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from helpers import model as old_model, source as old_source, part, trace, aset, issue
from dacn_s02.codec_boundary import encode
from dacn_s02.h2_limits import Budget, digest
from dacn_s02.h2_contracts import (SourceInventory, HoldSelector, BindingRequest, AnalysisEvidence,
    AuthorityGrant, AuthorityContext, POLICY, WORK, HOLD, ANALYSIS, selectors_hash)
from dacn_s02.h2_graph import ModelContext
from dacn_s02.h2_policy import admit

R0='/functional_requirements/0'
R1='/functional_requirements/1'
CR=R0+'/acceptance_criteria/0'
N='/non_functional_requirements/0'
C='/constraints/0'
HASH='1'*64


def snapshot():
    raw=old_source()
    raw['functional_requirements']=[dict(id='R1',text='Synthetic cancel request; permission unknown',priority=None,acceptance_criteria=['Synthetic cancel outcome']),dict(id='R2',text='Synthetic read independent status',priority='could',acceptance_criteria=[])]
    raw['non_functional_requirements']=[dict(id='N1',text='Keep logical review possible',priority=None,acceptance_criteria=[])]
    raw['constraints']=[dict(id='C1',text='Synthetic local only',priority='must',acceptance_criteria=[])]
    return dict(snapshot_id='SNAP',input=raw)


def graph(*, skeleton=False):
    m=old_model('SRC','SNAP','RUN');b=m['body']
    for group in ('actions','workflows','components','responsibilities'):
        for i,e in enumerate(b[group]):
            e['trace']=trace('SNAP',R0 if i==0 else R1)
            if group=='actions':e['initiator']='internal'
            if group=='workflows':
                for edge in e['edges']:edge['trace']=deepcopy(e['trace'])
    system=lambda i:dict(id=i,obligation='Synthetic system proposal',assignment='proposed',target='system',action_ids=[],primary_responsibility_ids=[],supporting_responsibility_ids=[],covered_portion='Synthetic',remaining_gap=None,issue_ids=[])
    b['mappings']=[dict(id='Map'+str(i),source_ref=dict(snapshot_id='SNAP',input_pointer=p),assessment='not_assessed' if skeleton else 'proposed',issue_ids=['Q'] if skeleton else [],parts=[] if skeleton else ps) for i,(p,ps) in enumerate([(R0,[part('P1',['A1'],['RS1'])]),(CR,[part('PCriterion',['A1'],['RS1'])]),(R1,[part('P2',['A2'],['RS2'])]),(N,[system('PN')]),(C,[system('PC')])])]
    if skeleton:
        for k in ('actions','workflows','components','responsibilities'):b[k]=[]
    return m


def current_issue(m, *, elements=('A1',), parts=('P1',), key='Question2', identity='Q', kind='business'):
    q=issue(m,identity=identity,key=key,blocked=elements,parts=parts)
    q['body'].update(kind=kind,resolution_carry=None,resolution_replacement=None)
    q['body']['trace']=trace('SNAP',R0)
    return q


def context(m=None, *, budget=None, snap=None):
    budget=budget or Budget(clock=lambda:0)
    source=SourceInventory(snap or snapshot(),'SRC',HASH,budget)
    return ModelContext(m or graph(),source,budget)


def unit(ctx, pointer):
    return next(f.unit_id for f in ctx.source.families if f.pointer==pointer)


def work(ctx, *, selected=(R1,), step=2, issues=None, all_source=False, evidence_change=None, binding_change=None, selector_change=None, candidate=b'{}', candidate_builder=None):
    if issues is None:issues=[current_issue(ctx.model(),elements=() if not ctx.elements.get('A1') else ('A1',),parts=() if 'P1' not in ctx.parts else ('P1',))]
    current=aset(ctx.model(),identity='AS1',issues=[q['id'] for q in issues])
    selectors=[]
    for q in issues:
        b=q['body']
        v=dict(version=HOLD,issue_id=q['id'],issue_key=b['issue_key'],target_step=1,kind='all_source_uses' if all_source else 'obligation_families',source_refs=[dict(snapshot_id='SNAP',input_pointer=R0)],element_ids=list(b['blocking']['element_ids']),mapping_part_ids=list(b['blocking']['mapping_part_ids']),impact_known=not all_source,code_task_role=None)
        if selector_change:selector_change(v)
        selectors.append(HoldSelector.parse(v,ctx.source,ctx.budget))
    refs=lambda p:dict(snapshot_id='SNAP',input_pointer=p)
    ids=[unit(ctx,p) for p in selected]
    e=dict(version=ANALYSIS,id='Evidence',source_context_id='SRC',snapshot_id='SNAP',base_model_id=ctx.id,base_analysis_set_id=current['id'],step=step,unit_ids=ids,selectors_sha256=selectors_hash(selectors,ctx.source),policy_version=POLICY,
        inspections=[dict(source_ref=refs(p),read='inspected',verdict='held' if issues and p in (R0,CR) else 'usable',basis_source_refs=[refs(p)],needed_facts=['Permission missing'] if issues and p in (R0,CR) else [],reason='Handwritten synthetic expected disposition') for p in sorted(ctx.source.obligations)],
        independence=[dict(issue_key=q['body']['issue_key'],unit_id=u,verdict='independent',basis_source_refs=[refs(p) for p in sorted(ctx.source.obligations)],reason='Synthetic expected independence; not business approval') for q in issues for u in ids])
    if evidence_change:evidence_change(e)
    raw=encode(e)
    if candidate_builder is not None:candidate=None
    ctx.budget.raw_work(candidate,raw)
    evidence=AnalysisEvidence(raw,ctx.source,ctx.budget)
    req=dict(version=WORK,purpose='synthetic_test_only',provider_id='test-provider',provider_version='local-synthetic/1',policy_version=POLICY,store_id='Store',session_id='Session',source_context_id='SRC',snapshot_id='SNAP',archive_sha256=HASH,base_model_id=ctx.id,base_model_sha256=ctx.hash,base_analysis_set_id=current['id'],base_analysis_set_sha256=digest(current),operation='step',goal='build',step=step,unit_ids=ids,current_selectors_sha256=selectors_hash(selectors,ctx.source),progress_before_sha256=HASH,retained_assessment_hashes=[],read_write_intent_sha256=HASH,candidate_sha256=None if candidate is None else sha256(candidate).hexdigest(),candidate_length=len(candidate or b''),analysis_sha256=sha256(raw).hexdigest(),analysis_length=len(raw),guard_keys=[],current_guard_ids=[],assessment_policy_version=POLICY)
    if candidate_builder is not None:
        candidate=candidate_builder(req,e)
        ctx.budget.raw_work(candidate,raw)
        req.update(candidate_sha256=sha256(candidate).hexdigest(),candidate_length=len(candidate))
    if binding_change:binding_change(req)
    binding=BindingRequest.parse(req,ctx.budget)
    authority_context=AuthorityContext('test-provider','local-synthetic/1',HASH)
    grant=AuthorityGrant(binding.key,'test-provider','local-synthetic/1',HASH,'allow','Trusted test caller, never work JSON')
    return SimpleNamespace(ctx=ctx,aset=current,issues=issues,selectors=selectors,binding=binding,evidence=evidence,grant=grant,authority_context=authority_context,candidate=candidate)


def decide(w, *, phase='before', grant=None, authority_context=None, permits=()):
    return admit(w.ctx,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant if grant is None else grant,candidate_raw=w.candidate,phase=phase,permits=permits,authority_context=w.authority_context if authority_context is None else authority_context)


def dependency(*, required, action='A2'):
    return dict(id='D21',trace=trace('SNAP',R1),state='ready',kind='uses_component',consumer_component_id='C2',provider_component_id='C1',interface_id=None,capability='Synthetic support',action_ids=[action],workflow_ids=[],reason='Explicit test relation',support=[dict(action_id=action,provider_responsibility_ids=['RS1'],required_action_ids=required)])
