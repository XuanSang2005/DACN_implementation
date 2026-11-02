"""H3-C API: explicit B/C publisher, immutable T0/seal and paired Repository CAS.

No CLI/provider/LLM or Answer/application/decision creation. Original external
historical registry is mandatory even for finalized read/replay.
"""
from contextlib import contextmanager
from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
import time
from .local_io import Settings,check_store,write_receipt,read_receipt
from .validation import valid_id
from .errors import S02Error
from .h1_store import profile_pins
from .h1_recovery import reconcile
from .h3_limits import Budget,DEFAULTS,VERSION,need,digest
from .h3_bindings import config_intent
from .h3_review_io import LocalSyntheticHistoricalReviews
from .h3_continuation_authority import LocalSyntheticContinuationAuthority
from .h3_continuation_contracts import CONFIG,HANDLER,POLICY
from .h3_continuation_checks import ContinuationVerifier
from .h3_continuation_inputs import binding,intent,refs
from .h3_continuation_plan import build
from .h3_continuation_store import ContinuationStore


def output(command,status,result=None):return dict(command_id=command,status=status,record_ids=[],errors=[],result=result or {})


class ContinuationService:
    def __init__(self,settings,*,historical_reviews,authority=None,_hook=None,_repository_options=None,_monotonic=time.monotonic):
        need(type(settings) is Settings,'c_typed_settings');check_store(settings)
        if authority is not None and type(authority) is not LocalSyntheticContinuationAuthority:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','C requires its versioned local/synthetic authority')
        self.settings=settings;self.trust=historical_reviews;self.authority=authority;self.hook=_hook or (lambda point:None);self.options=dict(_repository_options or {});self.clock=_monotonic
        need(not set(self.options)-{'_hook','_ids','_clock'},'c_repository_options')

    def invocation(self):
        budget=Budget(clock=self.clock);registry=LocalSyntheticHistoricalReviews.load(self.trust,budget)
        repo=registry.open_repository(self.settings.state/'s02.sqlite3',timeout=self.settings.timeout/1000,**self.options);reconcile(repo,self.trust.expected_store_id)
        return ContinuationStore(repo,registry,budget)

    def _request(self,store,parent,pair,command=None):
        need(valid_id(parent) and type(pair) in (list,tuple) and len(pair)==2 and all(valid_id(x) for x in pair),'c_request_pair')
        with store.repo._read() as c:
            h=store.checked(c);current=store.repo._command(c,command) if command is not None else None
            if current is not None:return store.context(c,h,current)
            cmd=store.repo._command(c,parent);need(cmd is not None and cmd['state']=='finalized' and cmd['run']['body']['status'] in ('completed','blocked'),'c_parent_finalized')
            session=cmd['operation']['session_id'];head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(session,)).fetchone());need(list(pair)==head,'c_expected_current_pair')
            base=h.view(session,pair,head);need(base.parent_command_id==parent,'c_unique_parent_publisher');return dict(history=h,base=base)

    def _selection(self,view,mode,step,units,goal):
        need(mode in ('step','revalidate') and type(step) is int and 1<=step<=4 and (mode=='step')==(goal=='build') and goal in ('build','admission','retained_output'),'c_mode_step_goal')
        base=view['base'];need(type(units) in (list,tuple) and bool(units) and all(valid_id(x) for x in units) and len(units)==len(set(units)),'c_unit_selection');units=sorted(units);base.context.source.selected(units)
        parent=ContinuationVerifier(view['history']).published(base.parent_command_id);meta=parent.plan()['admission'];aliases=parent.plan()['allocation']['aliases']
        if goal=='retained_output':
            for u in units:need(int(meta['progress_by_unit'][u]['work_completed_through'])>=step and any(int(o['step'])==step for o in meta['progress_by_unit'][u]['outputs']),'c_retained_stage_proof')
        return units,parent,meta,aliases

    def inspect(self,parent,*,expected_pair,step,unit_ids,mode='step',goal='build',candidate=None,analysis=None,provider_id=None):
        store=self.invocation();view=self._request(store,parent,expected_pair);units,parentcap,meta,aliases=self._selection(view,mode,step,unit_ids,goal);base=view['base'];bb=None
        i=intent(base,meta,mode=mode,step=step,units=units,goal=goal,aliases=aliases)
        if analysis is not None:
            need(type(analysis) is bytes and provider_id is not None and (type(candidate) is bytes if mode=='step' else candidate is None),'c_inspect_inputs')
            bb=binding(base,meta,provider_id=provider_id,mode=mode,step=step,units=units,goal=goal,aliases=aliases,candidate=candidate,analysis=analysis)
        return output(None,'completed',dict(store_id=base.history.store_id,session_id=base.session_id,base_pair=base.pair,source_context_id=base.context.source.context_id,snapshot_id=base.context.source.snapshot_id,
            unit_ids=units,inventory=[dict(unit_id=u,source_refs=refs(base.context.source,f.obligations)) for u,f in sorted(base.context.source.units.items())],obligations=refs(base.context.source,base.context.source.obligations),
            selectors=meta['selectors'],guards=meta['guards'],aliases=aliases,progress_by_unit=meta['progress_by_unit'],read_write_intent=i,scope_request_sha256=digest(i),authority_binding=bb,
            history_binding=base.history.binding(base),historical_reviews_pin=store.registry.registry.pin(),eligibility_authorized_in_process=False,semantic_status='synthetic_not_business_confirmation'))

    def _authorize(self,view,store):
        if self.authority is None:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','Pending C work requires original external semantic authority')
        store.registry.rehash(store.budget);return self.authority.authorize(view['config']['authority_binding'],store.budget)

    @contextmanager
    def publication_checks(self,store,cfg):
        original=store.repo._hook
        def guarded(point,c):
            original(point,c)
            if point in ('after_begin','before_finalize_insert','before_commit'):
                store.registry.rehash(store.budget)
                if self.authority is None:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','Pending C work requires external semantic authority')
                self.authority.authorize(cfg['authority_binding'],store.budget);store.budget.check()
        store.repo._hook=guarded
        try:yield
        finally:store.repo._hook=original

    def _receipt(self,path,command,storeid):
        p=Path(path)
        if p.exists():need(read_receipt(self.settings,p,store_id=storeid)['command_id']==command,'c_receipt_command');return
        try:write_receipt(self.settings,p,command,store_id=storeid)
        except (OSError,S02Error):
            if not p.exists():raise
            need(read_receipt(self.settings,p,store_id=storeid)['command_id']==command,'c_concurrent_receipt')

    def prepare(self,command,parent,*,receipt,expected_pair,step,unit_ids,analysis,candidate=None,mode='step',goal='build'):
        need(valid_id(command) and type(analysis) is bytes and (type(candidate) is bytes if mode=='step' else candidate is None),'c_prepare_inputs')
        store=self.invocation();view=self._request(store,parent,expected_pair,command);raw=dict(candidate=candidate,analysis=analysis)
        if 'config' in view:
            cfg=view['config'];need(cfg['parent_command_id']==parent and cfg['mode']==mode and cfg['step']==step and cfg['unit_ids']==sorted(unit_ids) and cfg['goal']==goal and [cfg['base_model_id'],cfg['base_analysis_set_id']]==list(expected_pair) and {k:s['bytes'] if s else None for k,s in view['raw'].items()}==raw,'c_existing_intent_conflict')
            self._receipt(receipt,command,cfg['store_id'])
            if view['command']['state']=='finalized':return self._report(view,store)
            self._authorize(view,store);return output(command,'prepared',dict(reserved_run_id=cfg['reserved_run_id']))
        if self.authority is None:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','C preparation requires external semantic authority')
        self.authority.read(store.budget);units,parentcap,meta,aliases=self._selection(view,mode,step,unit_ids,goal);base=view['base'];source=base.context.source
        bb=binding(base,meta,provider_id=self.authority.trust.provider_id,mode=mode,step=step,units=units,goal=goal,aliases=aliases,**raw)
        cfg=dict(**profile_pins(),marker=CONFIG,config_version=CONFIG,handler_version=HANDLER,policy_version=POLICY,limits_version=VERSION,limits=asdict(DEFAULTS),store_id=base.history.store_id,session_id=base.session_id,command_id=command,parent_command_id=parent,reserved_run_id='h3c.preT0.reserved',started_at='1970-01-01T00:00:00.000Z',
            mode=mode,step=step,unit_ids=units,goal=goal,source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],base_model_sha256=digest(base.context.model()),base_analysis_set_sha256=digest(base.analysis_set),anchor=None,parent_metadata=meta,aliases=aliases,
            inputs={k:dict(stage_ref=dict(command_id=command,blob_id='h3c.preT0.'+k),sha256=bb[k+'_sha256'],byte_length=len(data),media_type='application/json') if data is not None else None for k,data in raw.items()},historical_reviews_pin=store.registry.registry.pin(),history_binding=base.history.binding(base),authority_binding=bb,intent_sha256='0'*64)
        cfg['intent_sha256']=digest(config_intent(cfg));ContinuationVerifier(view['history']).config(cfg,base,raw,parentcap);self.authority.authorize(bb,store.budget)
        self.hook('before_receipt');self._receipt(receipt,command,cfg['store_id']);self.hook('after_receipt');self.hook('before_prepare')
        with self.publication_checks(store,cfg):prepared=store.prepare(cfg,raw)
        self.hook('after_prepare')
        if prepared['state']=='finalized':return self._report(store.load(command),store)
        return output(command,'prepared',dict(reserved_run_id=prepared['operation']['reserved_run_id']))

    def build(self,view,store):
        return build(view['config'],view['base'],view['primary'],{k:s['bytes'] if s else None for k,s in view['raw'].items()},max(view['config']['started_at'],store.repo._clock()))

    def resume(self,command,*,receipt=None):
        store=self.invocation()
        if receipt is not None:need(read_receipt(self.settings,receipt,store_id=self.trust.expected_store_id)['command_id']==command,'c_resume_receipt')
        view=store.load(command)
        if view is None:return output(command,'not_prepared',dict(phase='not_prepared'))
        if view['command']['state']=='finalized':return self._report(view,store)
        self._authorize(view,store);found=store.checked_plan(view)
        if found:plan,stage=found
        else:
            self.hook('before_build');plan=self.build(view,store);self._authorize(view,store);self.hook('before_seal')
            with self.publication_checks(store,view['config']):sealed=store.seal(command,plan)
            self.hook('after_seal')
            if sealed.get('finalized'):return self._report(store.load(command),store)
            plan,stage=sealed['plan'],sealed['stage']
        self.hook('before_finalize');view=store.load(command)
        if view['command']['state']=='finalized':return self._report(view,store)
        self._authorize(view,store);plan,stage=store.checked_plan(view);records,blobs=store.materialize(plan,stage['bytes'],view['state'])
        with self.publication_checks(store,view['config']):store.repo.finalize(command,records,blobs=blobs,promotions=plan['promotions'],head=plan['batch']['head'])
        self.hook('after_finalize');return self._report(store.load(command),store)

    def _report(self,view,store):
        cfg=view['config'];cmd=view['command'];found=store.checked_plan(view);cid=cfg['command_id']
        if cmd['state']!='finalized':return output(cid,'prepared',dict(phase='sealed' if found else 'prepared',reserved_run_id=cfg['reserved_run_id']))
        need(found is not None,'c_finalized_seal_required');plan,stage=found;run=cmd['run'];body=run['body'];published=body['status'] in ('completed','blocked');state=view['state']
        need(cmd['events'][-1]['payload']==dict(run_id=cfg['reserved_run_id'],promotions=plan['promotions']),'c_actual_finalized_promotions')
        if published or body['status']=='rejected':
            need(all(state['records'].get(r['id'])==r for r in plan['batch']['records']),'c_actual_published_records')
            need((plan['batch']['head'] is not None)==published,'c_actual_result_head')
        else:
            need(body['status']=='stale' and body['result_model_id'] is None and body['result_analysis_set_id'] is None and len(body['errors'])==1,'c_stale_run')
            error=body['errors'][0];need(error['code'] in ('MODEL_CONFLICT','ANALYSIS_CONFLICT'),'c_stale_error');model=error['code']=='MODEL_CONFLICT';key='model_id' if model else 'analysis_set_id';target=error.get('details',{}).get('expected_'+key);typ='model' if model else 'analysis_set'
            need(target in state['records'] and state['records'][target]['type']==typ and state['owners'][target]==cfg['session_id'] and target!=cfg['base_'+key],'c_stale_conflict_ref')
            expected_error=S02Error(error['code'],'revision','Model head changed' if model else 'AnalysisSet head changed',details={'expected_'+key:target,'provided_'+key:cfg['base_'+key]}).error;need(error==expected_error,'c_stale_error_binding')
            expected=deepcopy(next(r for r in plan['batch']['records'] if r['id']==cfg['reserved_run_id']));expected['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=[expected_error]);need(run==expected,'c_stale_reserved_identity')
            need(all(r['id'] not in state['records'] for r in plan['batch']['records'] if r['type'] in ('model','change','issue','analysis_set')),'c_stale_no_domain_records')
            need(all(state['records'].get(r['id'])==r for r in plan['batch']['records'] if r['type']=='artifact'),'c_stale_artifacts')
        a=plan['allocation'];need(state['blobs'][a['plan_artifact_id']]==stage['bytes'],'c_actual_plan_blob')
        result=output(cid,body['status'],dict(phase='finalized',run_id=run['id'],run_status=body['status'],result_pair=plan['batch']['head'] if published else None,current_head=view['current_head'],is_current=published and plan['batch']['head']==view['current_head'],candidate_outcome=plan['candidate_outcome'],
            last_checked_eligibility=plan['admission'] if published else None,progress_by_unit=plan['admission']['progress_by_unit'] if published else {},next_aliases=plan['allocation']['aliases'] if published else {},semantic_status='synthetic_not_business_confirmation',eligibility_authorized_in_process=False,plan_sha256=stage['sha256'],historical_reviews_pin=cfg['historical_reviews_pin']))
        result['errors']=body['errors'];result['record_ids']=[run['id'],*[p['artifact_id'] for p in plan['promotions']],*(plan['batch']['head'] if published else [])];return result

    def report(self,command):
        store=self.invocation();view=store.load(command);return self._report(view,store) if view is not None else output(command,'not_prepared',dict(phase='not_prepared'))
    def step(self,command,parent,**kw):
        self.prepare(command,parent,mode='step',**kw);return self.resume(command,receipt=kw['receipt'])
    def revalidate(self,command,parent,**kw):
        self.prepare(command,parent,mode='revalidate',**kw);return self.resume(command,receipt=kw['receipt'])
