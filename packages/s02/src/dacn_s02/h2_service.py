"""Fresh E1 scoped checkpoints. All authority is supplied by the process caller."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import time
from .codec_boundary import encode, decode
from .errors import S02Error, storage_error
from .repository import record
from .service import artifact
from .profiles import E1
from .h1_store import profile_pins
from .h2_store import ScopeStore
from .h2_checkpoint import (CONFIG,PLAN,HANDLER,ADMISSION,source_inventory,selectors,permits,check_stage,pack,normalized_model,
                            blocking_keys,hold_footprint)
from .h2_contracts import (BindingRequest,AuthorityContext,AnalysisEvidence,POLICY,WORK,selectors_hash,HoldSelector)
from .h2_candidates import parse_candidate,scope_request_hash
from .h2_graph import ModelContext,impact,semantic
from .h2_policy import admit,assess_union,_evaluate
from .h2_limits import Budget,DEFAULTS,VERSION,digest,need
from .h2_builders import ScopedBuilder
from .h2_authority import unavailable
from .scope import make_scope


def output(command,status,result=None,errors=()):
    return dict(command_id=command,status=status,record_ids=[],errors=list(errors),result=result or {})


class H2Service:
    def __init__(self,repository,*,authority=None,_monotonic=time.monotonic,_hook=None):
        self.repo=repository;self.authority=authority;self.clock=_monotonic;self.hook=_hook or (lambda point:None)

    def budget(self):return Budget(clock=self.clock)

    def intent(self,parent,*,mode,step=0,unit_ids=(),expected_pair=None,goal='build',guard_keys=(),provider_id=None,candidate=None,analysis=None,budget=None):
        """Read-only code-owned binding skeleton; never grants eligibility."""
        budget=budget or self.budget();store=ScopeStore(self.repo,budget)
        need(mode in ('bootstrap','step','revalidate'),'h2_mode')
        need(len(unit_ids)==len(set(unit_ids)) and len(guard_keys)==len(set(guard_keys)),'h2_unique_request')
        view=store.preflight(parent,mode,expected_pair if expected_pair is not None else [None,None])
        source=source_inventory(view,budget);cfg=view['config'];units=sorted(unit_ids)
        if mode=='bootstrap':
            need(step==0 and not units and candidate is None and analysis is None and not guard_keys,'h2_bootstrap_intent')
            return view,source,None
        need(type(step) is int and 1<=step<=4,'h2_step');source.selected(units)
        need((mode=='step' and goal=='build' and not guard_keys) or (mode=='revalidate' and goal in ('admission','retained_output') and guard_keys and candidate is None),'h2_mode_inputs')
        meta=cfg['parent_metadata'];check_stage(meta,units,step,mode,goal)
        sels=selectors(meta,view['issues'],source,budget)
        guards={q['body']['issue_key']:q['id'] for q in view['issues'] if q['body']['issue_key'] in guard_keys}
        need(set(guards)==set(guard_keys) and set(guards)<=meta['guards'].keys(),'h2_guard_targets')
        retained=sorted({digest(p['assessment']) for p in meta['progress_by_unit'].values() if p['assessment'] is not None})
        read_ids=sorted({a['id'] for a in cfg['aliases'].values()}|{q['id'] for q in view['issues']})
        intent=dict(mode=mode,goal=goal,step=step,unit_ids=units,source_refs=[dict(snapshot_id=source.snapshot_id,input_pointer=p) for p in sorted(source.selected(units))],read_context_ids=read_ids,aliases_sha256=digest(cfg['aliases']),guard_keys=sorted(guard_keys))
        binding=dict(version=WORK,purpose='synthetic_test_only',provider_id=provider_id,provider_version='local-synthetic/1',policy_version=POLICY,
            store_id=view['store_id'],session_id=cfg['session_id'],source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,
            base_model_id=cfg['base_model_id'],base_model_sha256=digest(view['base_model']),base_analysis_set_id=cfg['base_analysis_set_id'],base_analysis_set_sha256=digest(view['base_set']),
            operation=mode,goal=goal,step=step,unit_ids=units,current_selectors_sha256=selectors_hash(sels,source),progress_before_sha256=digest(meta['progress_by_unit']),retained_assessment_hashes=retained,
            read_write_intent_sha256=digest(intent),candidate_sha256=sha256(candidate).hexdigest() if candidate is not None else None,candidate_length=len(candidate or b''),
            analysis_sha256=sha256(analysis or b'').hexdigest(),analysis_length=len(analysis or b''),guard_keys=sorted(guards),current_guard_ids=sorted(guards.values()),assessment_policy_version=POLICY)
        view['intent']=intent
        return view,source,binding

    def preflight(self,parent,*,mode,step=0,unit_ids=(),expected_pair=None,goal='build',guard_keys=(),candidate=None,analysis=None,budget=None):
        budget=budget or self.budget()
        if mode!='bootstrap':
            if self.authority is None:unavailable('Semantic H2 work requires external process authority')
            need(type(analysis) is bytes and (type(candidate) is bytes if mode=='step' else candidate is None),'h2_raw_inputs')
            budget.raw_work(candidate,analysis)
            context,_=self.authority.read(budget)
        else:context=None
        view,source,b=self.intent(parent,mode=mode,step=step,unit_ids=unit_ids,expected_pair=expected_pair,goal=goal,guard_keys=guard_keys,
                                  provider_id=context.provider_id if context else None,candidate=candidate,analysis=analysis,budget=budget)
        if b is not None:
            binding=BindingRequest.parse(b,budget);context,grant=self.authority.authorize(binding,budget,expected_context=context)
        else:binding=None
        return view,source,binding,context

    def prepare(self,command,parent,*,mode,store_id,step=0,unit_ids=(),expected_pair=None,goal='build',guard_keys=(),candidate=None,analysis=None,_budget=None,_preflight=None):
        budget=_budget or self.budget();store=ScopeStore(self.repo,budget)
        from .h1_recovery import reconcile
        reconcile(self.repo,store_id)
        # Existing prepared intent is compared to original inputs even after a
        # different writer advanced the head. No implicit rebase/preflight.
        existing=store.load(command)
        if existing:
            old=existing['config']
            need(all(old[k]==v for k,v in dict(parent_command_id=parent,mode=mode,step=step,unit_ids=sorted(unit_ids),goal=goal,guard_keys=sorted(guard_keys),store_id=store_id).items()),'h2_prepare_intent_conflict')
            need([old['base_model_id'],old['base_analysis_set_id']]==(expected_pair or [None,None]),'h2_prepare_pair_conflict')
            need(all((existing['raw'][k]['bytes'] if existing['raw'][k] else None)==v for k,v in dict(candidate=candidate,analysis=analysis).items()),'h2_prepare_raw_conflict')
            if existing['command']['state']=='finalized':return self.report(command,_budget=budget)
            self.authorize(existing,budget)
            return output(command,'prepared',dict(reserved_run_id=old['reserved_run_id']))
        view,source,binding,context=_preflight or self.preflight(parent,mode=mode,step=step,unit_ids=unit_ids,expected_pair=expected_pair,goal=goal,guard_keys=guard_keys,candidate=candidate,analysis=analysis,budget=budget)
        need(view['store_id']==store_id,'h2_store_identity')
        cfg=dict(**profile_pins(),**view['config'],marker=CONFIG,config_version=CONFIG,handler_version=HANDLER,limits_version=VERSION,limits=asdict(DEFAULTS),
            command_id=command,parent_command_id=parent,mode=mode,step=step,unit_ids=sorted(unit_ids),goal=goal,guard_keys=sorted(guard_keys),store_id=store_id,
            execution_origin='synthetic_not_business_confirmation',binding=binding.payload() if binding else None,authority=asdict(context) if context else None,
            intent=view.get('intent'),inputs={})
        self.hook('before_prepare');prepared=store.prepare(cfg,dict(candidate=candidate,analysis=analysis));self.hook('after_prepare')
        if prepared['state']=='finalized':return self.report(command,_budget=budget)
        return output(command,'prepared',dict(reserved_run_id=prepared['operation']['reserved_run_id']))

    def authorize(self,view,budget):
        cfg=view['config']
        if cfg['mode']=='bootstrap':budget.check();return None,None
        if self.authority is None:unavailable('Pending H2 work requires original external process authority')
        binding=BindingRequest.parse(cfg['binding'],budget)
        context=AuthorityContext(**cfg['authority'])
        source=source_inventory(view,budget);meta=cfg['parent_metadata'];b=binding.payload()
        current_selectors=selectors(meta,view['issues'],source,budget)
        if cfg['intent']['aliases_sha256']!=digest(cfg['aliases']):raise storage_error('H2 alias interpretation differs from pinned intent')
        expected=dict(store_id=cfg['store_id'],session_id=cfg['session_id'],source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,
            base_model_id=cfg['base_model_id'],base_model_sha256=digest(view['base_model']),base_analysis_set_id=cfg['base_analysis_set_id'],base_analysis_set_sha256=digest(view['base_set']),
            operation=cfg['mode'],goal=cfg['goal'],step=cfg['step'],unit_ids=cfg['unit_ids'],guard_keys=cfg['guard_keys'],
            current_selectors_sha256=selectors_hash(current_selectors,source),progress_before_sha256=digest(meta['progress_by_unit']),read_write_intent_sha256=digest(cfg['intent']),
            retained_assessment_hashes=sorted({digest(p['assessment']) for p in meta['progress_by_unit'].values() if p['assessment'] is not None}),
            current_guard_ids=sorted(q['id'] for q in view['issues'] if q['body']['issue_key'] in cfg['guard_keys']))
        for lane in ('candidate','analysis'):
            raw=view['raw'][lane]
            expected[lane+'_sha256']=raw['sha256'] if raw else None
            expected[lane+'_length']=raw['byte_length'] if raw else 0
        if any(b[k]!=v for k,v in expected.items()):raise storage_error('H2 persisted intent differs from authority binding')
        return self.authority.authorize(binding,budget,expected_context=context)

    def origin(self,store,view,command):
        if command in store.origin_cache:return store.origin_cache[command]
        with self.repo._read() as c:
            state=store.state(c);cmd=self.repo._command(c,command)
            need(cmd is not None,'h2_origin_missing')
            plan=store.published_plan(cmd,state);store.origin_cache[command]=plan
            return plan

    def guard(self,builder,reason,candidate_model=None):
        cfg=builder.cfg;key='h2.guard.'+sha256(cfg['command_id'].encode('ascii')).hexdigest()
        need(key not in builder.meta['guards'],'h2_guard_collision')
        source=builder.source
        # Full source coverage retains the failed context without referring to
        # any discarded candidate allocation in canonical Issues/Model.
        q=builder.issue(builder.refs(source.obligations),'Revalidate discarded scoped candidate impact',kind='analysis_omission',key=key,role='merge_guard',unknown=True)
        builder.meta['guards'][key]=dict(origin_command_id=cfg['command_id'],origin_run_id=cfg['reserved_run_id'],root_issue_id=q['id'],predicate='h2.merge_assessment/1',
            base_pair=[cfg['base_model_id'],cfg['base_analysis_set_id']],candidate_sha256=cfg['binding']['candidate_sha256'],analysis_sha256=cfg['binding']['analysis_sha256'],
            failure_context_sha256=digest(candidate_model) if candidate_model else None,failed_candidate_model=deepcopy(candidate_model),source_refs=builder.refs(source.obligations),reason_codes=list(reason),impacted_unit_ids=sorted(source.units),policy_version=POLICY)
        for unit,p in builder.meta['progress_by_unit'].items():
            p['guard_keys']=sorted(set(p['guard_keys'])|{key})
            p['assessment_state']='needs_revalidation'
        builder.materialize_selectors()
        return key

    def verify_guard(self,store,view,key):
        meta=view['config']['parent_metadata'];g=meta['guards'][key]
        origin=self.origin(store,view,g['origin_command_id'])
        need(origin['candidate_outcome']=='guard_only' and origin['admission']['guards'].get(key)==g and g['predicate']=='h2.merge_assessment/1','h2_guard_origin')
        need(key=='h2.guard.'+sha256(g['origin_command_id'].encode('ascii')).hexdigest(),'h2_guard_key')
        current=next(q for q in view['issues'] if q['body']['issue_key']==key)
        seen=set();q=current
        while q['id']!=g['root_issue_id']:
            need(q['id'] not in seen and q['body']['issue_key']==key and q['body']['supersedes_id'] is not None,'h2_guard_lineage');seen.add(q['id'])
            q=view['state']['records'][q['body']['supersedes_id']]
        need(any(r==q for r in origin['batch']['records']),'h2_guard_root')
        need(q['body']['kind']=='analysis_omission' and q['body']['status']=='open' and q['body']['supersedes_id'] is None and q['body']['model_id']==g['base_pair'][0] and q['body']['trace']['source_refs'],'h2_guard_root_predicate')
        need(current['body']['kind']=='analysis_omission' and not current['body']['answer_ids'] and current['body']['resolution_carry'] is None and current['body']['resolution_replacement'] is None,'h2_guard_direct_only')
        # No guard may appear in domain aliases or Model issue links.
        def refs(v):
            if isinstance(v,list):return set().union(*(refs(x) for x in v)) if v else set()
            if isinstance(v,dict):return set(v.get('issue_ids',[]))|set().union(*(refs(x) for x in v.values()))
            return set()
        need(current['id'] not in refs(view['base_model']),'h2_guard_domain_reference')
        if g['failed_candidate_model'] is not None:
            need(digest(g['failed_candidate_model'])==g['failure_context_sha256'],'h2_failed_context_hash')
            source=source_inventory(view,store.budget)
            base=ModelContext(view['state']['records'][g['base_pair'][0]],source,store.budget)
            failed=ModelContext(g['failed_candidate_model'],source,store.budget)
            impact(base,failed)  # revisit the exact discarded context, never publish it
        return g,current

    def revalidate(self,store,view,builder,ctx,sels,binding,evidence,grant,authority,ps):
        cfg=view['config'];meta=builder.meta;keys=set(cfg['guard_keys']);source=builder.source
        all_guards={k for p in meta['progress_by_unit'].values() if p['assessment_state']=='needs_revalidation' for k in p['guard_keys']}
        need(all_guards<=keys,'h2_all_required_guards')
        guards=[self.verify_guard(store,view,k) for k in sorted(keys)]
        # Evidence must account for every use of every guard, not just selected
        # units. Explicit held obligations require a separate surviving hold.
        represented=set()
        for q,s in zip(view['issues'],sels):
            if q['body']['issue_key'] not in keys and q['body']['issue_key'] not in meta['tasks'] and q['body']['status']=='open':
                represented.update(source.obligations if s.kind=='all_source_uses' else {p for f in source.families if f.obligations&s.sources for p in f.obligations})
        proof=True
        for ptr,row in evidence.inspections.items():
            proof &= row['read']=='inspected' and (row['verdict']!='held' or ptr in represented)
        for key in keys:
            for unit in source.units:
                pair=evidence.pairs.get((key,unit));unitrefs=source.units[unit].obligations
                held=bool(unitrefs&represented)
                proof &= bool(pair and pair['verdict']==('held' if held else 'independent') and source.obligations<=pair['basis'])
        # The current graph is authoritative. The failed delta is discarded;
        # its exact hash/provenance remains in each technical assessment.
        for _,q in guards:
            s=next(s for s in sels if s.issue_id==q['id'])
            fp=ctx.closure(*ctx.source_seed(s.sources))
            if any(r!='ACTION_WITHOUT_PART' for r in fp.reasons):proof=False
        domain_edit=any('requires_domain_edit_outside_h2' in row['reason'] for row in evidence.payload()['inspections'])
        if cfg['goal']=='retained_output':
            selected=source.selected(cfg['unit_ids']);es,pset=ctx.source_seed(selected);fp=ctx.closure(es,pset)
            assigned={a for r in ctx.maps['responsibilities'].values() for a in r['action_ids']}
            if int(cfg['step'])>=3 and not fp.actions<=assigned:domain_edit=True
            if int(cfg['step'])==4 and any(r['assessment']!='proposed' or not r['parts'] for r in ctx.rows.values() if r['source_ref']['input_pointer'] in selected):domain_edit=True
        proof &= not domain_edit
        for q in builder.issues:
            if q['body']['issue_key'] not in keys:continue
            builder.successor(q)
            q['body'].update(status='resolved' if proof else 'open',resolution='Code checked P_guard; discarded candidate remains discarded; synthetic only' if proof else None)
            if proof:q['body']['blocking']=make_scope(ctx.id)
        builder.materialize_selectors()
        # _evaluate accepts revalidation bindings; public admit correctly only
        # accepts build bindings. Keep original exact tuple/raw evidence.
        # Policy pins bind the base AS. Evaluate against base and provisionally
        # resolved guards without falsifying their IDs/pins in input evidence.
        eval_issues=deepcopy(view['issues'])
        for q in eval_issues:
            if q['body']['issue_key'] in keys and proof:q['body']['status']='resolved';q['body']['blocking']=make_scope(ctx.id)
        admission=_evaluate(ctx,ctx,view['base_set'],eval_issues,sels,binding,evidence,grant,None,'before',ps,authority)
        for unit,p in meta['progress_by_unit'].items():
            if proof:
                p['guard_keys']=[k for k in p['guard_keys'] if k not in keys]
                p['assessment_state']='current' if unit in admission.allowed_units else 'assessed_held' if any(x in represented for x in source.units[unit].obligations) else ('needs_revalidation' if p['guard_keys'] else 'pending')
            else:p['assessment_state']='terminal_out_of_scope' if domain_edit and unit in cfg['unit_ids'] else 'needs_revalidation'
        return dict(predicate_passed=bool(proof),requires_domain_edit_outside_h2=domain_edit,checked_guard_origins=[g for g,_ in guards],policy=pack(admission))

    def build(self,store,view,budget,context,grant):
        cfg=view['config'];source=source_inventory(view,budget);fresh=store.fresh(view['state']);now=max(cfg['started_at'],self.repo._clock())
        builder=ScopedBuilder(view,source,fresh,now,budget);policy={};outcome='valid';delta=None
        if cfg['mode']=='bootstrap':builder.bootstrap()
        else:
            binding=BindingRequest.parse(cfg['binding'],budget);sels=selectors(builder.meta,view['issues'],source,budget)
            evidence=AnalysisEvidence(view['raw']['analysis']['bytes'],source,budget)
            need(evidence.matches(binding),'h2_evidence_binding')
            ctx=ModelContext(view['base_model'],source,budget)
            ps=permits(builder.meta,view['issues'],cfg['unit_ids'],int(cfg['step']),lambda cmd:self.origin(store,view,cmd))
            if cfg['mode']=='revalidate':
                policy=self.revalidate(store,view,builder,ctx,sels,binding,evidence,grant,context,ps);outcome='revalidated'
            else:
                candidate=parse_candidate(view['raw']['candidate']['bytes'],ctx,step=int(cfg['step']),unit_ids=cfg['unit_ids'],expected_scope_hash=scope_request_hash(binding),
                    base_aliases=cfg['aliases'],read_context_ids=frozenset(cfg['intent']['read_context_ids']),current_issue_ids=frozenset(q['id'] for q in view['issues']))
                admission=admit(ctx,view['base_set'],view['issues'],sels,binding,evidence,grant,candidate_raw=candidate.raw,permits=ps,authority_context=context)
                # Clarification is AS-only: it may record a source hold instead
                # of demanding the missing business fact to record that hold.
                if cfg['step']!=1 and set(admission.allowed_units)!=set(cfg['unit_ids']):
                    self.guard(builder,admission.reason_codes);outcome='guard_only';policy=pack(admission)
                else:
                    built=builder.build(candidate);candidate_ctx=ModelContext(built,source,budget)
                    union=assess_union(ctx,candidate_ctx,view['base_set'],view['issues'],sels,binding,evidence,grant,candidate_raw=candidate.raw,permits=ps,authority_context=context)
                    delta=impact(ctx,candidate_ctx);policy=pack(union)
                    if union.outcome=='rejected':raise S02Error('H2_CANDIDATE_REJECTED','schema','Candidate exceeds scoped append rights',details={'reasons':list(union.reason_codes)})
                    failed=cfg['step']!=1 and (union.outcome=='guard_required' or set(union.allowed_units)!=set(cfg['unit_ids']))
                    new_hold_reasons=[]
                    if cfg['step']!=1:
                        # Authority binds the original selectors and raw work.
                        # Derived Issues are not old input selectors: rematerialize
                        # all of them on the full candidate AND base before seal.
                        from .validation import shape
                        new_issues=[q for q in builder.issues if q['id'] not in view['state']['records']]
                        new_holds=tuple(builder.new_selectors[q['body']['issue_key']] for q in new_issues)
                        budget.cap('issues',len(builder.issues))
                        budget.inspect(dict(model=built,current_issues=builder.issues))
                        for q,s in zip(new_issues,new_holds):
                            shape(q,profile=E1)
                            need(q['body']['model_id']==candidate_ctx.id and all(q['body'][k]['model_id']==candidate_ctx.id for k in ('affected','blocking')),'h2_new_hold_model')
                            need(s.elements<=candidate_ctx.elements.keys() and s.parts<=candidate_ctx.parts.keys(),'h2_new_hold_members')
                            need(set(q['body']['blocking']['element_ids'])<=s.elements and set(q['body']['blocking']['mapping_part_ids'])<=s.parts,'h2_new_hold_cannot_shrink')
                        after_keys=blocking_keys(candidate_ctx,new_issues,new_holds,source.units)
                        before_keys=blocking_keys(ctx,new_issues,new_holds,source.units)
                        # Stage 1 is source inspection, not retained domain
                        # output: a new U hold must not blanket-block V.
                        protected=set(cfg['unit_ids'])|{u for u,p in builder.meta['progress_by_unit'].items() if int(p['work_completed_through'])>=2}
                        if any(after_keys[u] or before_keys[u] for u in protected):new_hold_reasons.append('NEW_OUTPUT_HOLD')
                        for q,s in zip(new_issues,new_holds):
                            if q['body']['status']!='open' or int(cfg['step'])<s.target_step:continue
                            for side,foot in ((ctx,delta.before),(candidate_ctx,delta.after)):
                                held=hold_footprint(side,q,s)
                                if ('SCOPE_UNDETERMINED' in held.reasons or
                                    foot.elements&s.elements or foot.parts&s.parts or
                                    foot.uses&held.uses or foot.active_parts&held.active_parts):
                                    new_hold_reasons.append('NEW_HOLD_IMPACT')
                        policy['new_issue_blockers']={side:[dict(unit_id=u,blockers=[dict(issue_key=k) for k in keys]) for u,keys in sorted(rows.items())]
                                                     for side,rows in (('before',before_keys),('after',after_keys))}
                        new_hold_reasons=sorted(set(new_hold_reasons))
                        policy['new_hold_reason_codes']=new_hold_reasons
                        if new_hold_reasons:failed=True

                    # Retained units need full evidence and unchanged causal
                    # context, or the entire candidate remains unpublished.
                    for unit,p in builder.meta['progress_by_unit'].items():
                        if not p['outputs'] or unit in cfg['unit_ids']:continue
                        es,parts=ctx.source_seed(source.units[unit].obligations);foot=ctx.closure(es,parts)
                        if (delta.before.uses|delta.after.uses)&foot.uses or (delta.before.active_parts|delta.after.active_parts)&foot.active_parts:failed=True
                    if failed:
                        builder=ScopedBuilder(view,source,fresh,now,budget);self.guard(builder,tuple(new_hold_reasons) or union.reason_codes or ('RETAINED_CONTEXT_CHANGED',),built);outcome='guard_only'
                    else:
                        builder.resolve_tasks()
                        pre_rebind=deepcopy(builder.model);pre_issues=deepcopy(builder.issues)
                        builder.rebind()
                        need(normalized_model(pre_rebind,pre_issues)==normalized_model(builder.model,builder.issues),'h2_rebind_only_correspondence')
                        for unit in cfg['unit_ids']:
                            p=builder.meta['progress_by_unit'][unit];p['work_completed_through']=cfg['step'];p['outputs'][str(cfg['step'])]=builder.new_output[unit]
                            held=any(evidence.inspections[r]['verdict']=='held' for r in source.units[unit].obligations)
                            p['assessment_state']='assessed_held' if held else 'current'
        records,aset=builder.records();head=[builder.model['id'],aset['id']]
        meta=builder.meta;meta['projection']=meta.get('projection') if cfg['mode']=='step' and outcome!='guard_only' else None
        meta.update(version=ADMISSION,result_pair=head,base_pair=[cfg['base_model_id'],cfg['base_analysis_set_id']],source_context_id=source.context_id,snapshot_id=source.snapshot_id,
            inventory=[dict(unit_id=u,source_refs=builder.refs(source.units[u].obligations)) for u in sorted(source.units)],policy=policy,
            unchanged_issue_keys=[q['body']['issue_key'] for q in builder.issues if q['id'] in view['state']['records']],parent_progress_sha256=digest(cfg['parent_metadata']['progress_by_unit']) if cfg['parent_metadata'] else None)
        meta['obligations']=[dict(source_ref=row['source_ref'],mapping_row_id=row['id'],assessment=row['assessment'],mapping_part_ids=[p['id'] for p in row['parts']],issue_ids=row['issue_ids']) for row in builder.model['body']['mappings']]
        result_ctx=ModelContext(builder.model,source,budget)
        current_holds=selectors(meta,builder.issues,source,budget,derived=True)
        unresolved=blocking_keys(result_ctx,builder.issues,current_holds,source.units)
        for unit,p in meta['progress_by_unit'].items():
            parent=cfg['parent_metadata']['progress_by_unit'][unit]['assessment'] if cfg['parent_metadata'] else None
            p['latest_checked_pair']=head
            p['unresolved_keys']=unresolved[unit]
            if p['assessment_state']=='current' and any(k not in meta['tasks'] for k in p['unresolved_keys']):p['assessment_state']='assessed_held'
            p['next_tasks']=[] if int(p['work_completed_through'])==4 else [int(p['work_completed_through'])+1]
            p['assessment']=dict(input_binding_key=digest(cfg['binding']) if cfg['binding'] else None,base_pair=meta['base_pair'],result_pair=head,
                result_model_sha256=digest(builder.model),result_analysis_set_sha256=digest(aset),parent_assessment_sha256=digest(parent) if parent else None,
                policy_version=POLICY,diff_sha256=digest(pack(delta)) if delta else digest([]),context_sha256=digest(normalized_model(builder.model,builder.issues)),
                output_refs=p['outputs'],state=p['assessment_state'],synthetic_not_business_confirmation=True)
        status='blocked' if any(q['body']['status']=='open' for q in builder.issues) else 'completed'
        if cfg['mode']=='bootstrap':status='completed'
        return self.plan(store,view,fresh,now,dict(records=records,head=head,status=status,aliases=builder.aliases,admission=meta,outcome=outcome))

    def plan(self,store,view,fresh,now,result,errors=()):
        cfg=view['config'];records=list(result.get('records',[]));sources=[]
        for stage in [view['primary'],*[s for s in view['raw'].values() if s is not None]]:
            aid=fresh();ref=dict(command_id=cfg['command_id'],blob_id=stage['blob_id']);records.append(artifact(aid,stage['purpose'],stage['bytes'],cfg['reserved_run_id'],now));sources.append(dict(artifact_id=aid,stage_ref=ref))
        pbid=fresh();paid=fresh();head=result.get('head')
        run=record('run',cfg['reserved_run_id'],dict(mode='live' if cfg['mode']=='bootstrap' else 'replay',source_context_id=cfg['source_context_id'],config_artifact_id=sources[0]['artifact_id'],
            base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],command_id=cfg['command_id'],result_model_id=head[0] if head and head[0]!=cfg['base_model_id'] else None,
            result_analysis_set_id=head[1] if head else None,steps=[] if cfg['mode']=='bootstrap' else [cfg['step']],status=result['status'],started_at=cfg['started_at'],completed_at=now,attempts=[],errors=list(errors)),cfg['started_at']);records.append(run)
        return dict(marker=PLAN,plan_version=PLAN,**profile_pins(),bindings=store.bindings(cfg,view['primary'],view['raw']),allocation=dict(plan_blob_id=pbid,plan_artifact_id=paid,created_at=now,aliases=result.get('aliases',cfg['aliases'])),
            batch=dict(records=records,artifact_sources=sources,head=head),promotions=sources+[dict(artifact_id=paid,stage_ref=dict(command_id=cfg['command_id'],blob_id=pbid))],
            admission=result.get('admission',{}),candidate_outcome=result.get('outcome','rejected'),diagnostics=list(errors))

    def resume(self,command,*,store_id=None,_budget=None):
        budget=_budget or self.budget();store=ScopeStore(self.repo,budget)
        if store_id is not None:
            from .h1_recovery import reconcile
            reconcile(self.repo,store_id)
        view=store.load(command)
        if view is None:return output(command,'not_prepared',dict(phase='not_prepared'))
        if view['command']['state']=='finalized':return self.report(command,_budget=budget)
        context,grant=self.authorize(view,budget)
        found=store.checked_plan(view['command'],view['state'],view['config'],view['primary'],view['raw'])
        if found:plan,stage=found
        else:
            self.hook('before_build')
            try:plan=self.build(store,view,budget,context,grant)
            except S02Error as exc:
                if exc.error['stage']=='persistence':raise
                fresh=store.fresh(view['state']);plan=self.plan(store,view,fresh,max(view['config']['started_at'],self.repo._clock()),dict(status='rejected'),[exc.error])
            self.authorize(view,budget);self.hook('before_seal')
            with self.publication_checks(view,budget):
                sealed=store.seal(command,plan)
            self.hook('after_seal')
            if 'finalized' in sealed:return self.report(command,_budget=budget)
            plan,stage=sealed['plan'],sealed['stage']
        self.hook('before_finalize')
        current=store.load(command)
        if current['command']['state']=='finalized':return self.report(command,_budget=budget)
        self.authorize(current,budget);budget.check()
        records,blobs=store.materialize(plan,stage['bytes'],current['state'])
        with self.publication_checks(current,budget):
            self.repo.finalize(command,records,blobs=blobs,promotions=plan['promotions'],head=plan['batch']['head'])
        self.hook('after_finalize')
        return self.report(command,_budget=budget)

    def publication_checks(self,view,budget):
        """Reauthorize under the repository transaction; restore its caller hook.

        Uses existing fault-injection boundaries, without altering DB2/H1 code.
        Each service owns its Repository for one synchronous invocation.
        """
        from contextlib import contextmanager
        @contextmanager
        def guarded():
            original=self.repo._hook
            def hook(point,connection):
                original(point,connection)
                if point in ('after_begin','before_finalize_insert','before_commit'):
                    self.authorize(view,budget);budget.check()
            self.repo._hook=hook
            try:yield
            finally:self.repo._hook=original
        return guarded()

    def report(self,command,*,progress=False,_budget=None):
        budget=_budget or self.budget();store=ScopeStore(self.repo,budget);view=store.load(command)
        if view is None:return output(command,'not_prepared',dict(phase='not_prepared'))
        cmd=view['command'];cfg=view['config']
        if cmd['state']!='finalized':return output(command,'completed' if progress else 'prepared',dict(phase=cmd['state'],reserved_run_id=cfg['reserved_run_id']))
        plan=store.published_plan(cmd,view['state']);run=cmd['run'];b=run['body']
        published=b['status'] in ('completed','blocked');pair=plan['batch']['head'] if published else None
        model=view['state']['records'][pair[0]] if pair else None
        aset=view['state']['records'][pair[1]] if pair else None
        result=output(command,'completed' if progress else b['status'],dict(phase='finalized',run_id=run['id'],run_status=b['status'],result_pair=pair,current_head=view['current_head'],is_current=pair==view['current_head'],
            semantic_status='synthetic_not_business_confirmation',eligibility_authorized_in_process=False,last_checked_eligibility=plan['admission'] if published else None,
            progress_by_unit=plan['admission'].get('progress_by_unit',{}) if published else {},next_aliases=plan['allocation']['aliases'] if published else {},model=model,
            issues=[view['state']['records'][i] for i in aset['body']['issue_ids']] if aset else [],candidate_outcome=plan['candidate_outcome']),b['errors'] if not progress else ())
        result['record_ids']=list(dict.fromkeys([run['id'],*[p['artifact_id'] for p in plan['promotions']],*(pair or [])]))
        return result
