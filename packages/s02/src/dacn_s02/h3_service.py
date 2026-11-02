"""H3-B local/synthetic API. External review trust is mandatory per invocation.

No CLI, Model/Change builder, human decision or Answer/application orchestration.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import time
from .codec_boundary import encode
from .errors import S02Error
from .profiles import E1
from .repository import record
from .service import artifact
from .local_io import Settings,check_store,write_receipt,read_receipt
from .validation import valid_id
from .h1_store import profile_pins
from .h1_recovery import reconcile
from .h3_limits import Budget,DEFAULTS,VERSION,need,digest
from .h3_history import HistoryData
from .h3_bindings import config_intent
from .h3_checkpoint_contracts import CONFIG,PLAN,HANDLER,POLICY
from .h3_checkpoint_checks import CheckpointVerifier,binding,issue_changes,admission,aliases_for
from .h3_review_io import LocalSyntheticHistoricalReviews,LocalSyntheticCheckpointAuthority
from .h3_checkpoint_store import HistoryStore,frozen_state


def output(cid,status,result=None):return dict(command_id=cid,status=status,record_ids=[],errors=[],result=result or {})


class HistoryService:
    def __init__(self,settings,*,historical_reviews,authority=None,_hook=None,_repository_options=None,_monotonic=time.monotonic):
        need(type(settings) is Settings,'b_typed_settings');check_store(settings)
        if authority is not None and type(authority) is not LocalSyntheticCheckpointAuthority:
            raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','B requires its versioned local/synthetic authority adapter')
        self.settings=settings;self.trust=historical_reviews;self.authority=authority
        self.hook=_hook or (lambda point:None);self.options=dict(_repository_options or {});self.clock=_monotonic
        need(not set(self.options)-{'_hook','_ids','_clock'},'b_repository_options')

    def invocation(self):
        budget=Budget(clock=self.clock)
        frozen=LocalSyntheticHistoricalReviews.load(self.trust,budget)
        repo=frozen.open_repository(self.settings.state/'s02.sqlite3',timeout=self.settings.timeout/1000,**self.options)
        # Frozen external map exists before reconciliation performs any graph read.
        reconcile(repo,self.trust.expected_store_id)
        return HistoryStore(repo,frozen,budget)

    def _request(self,store,parent,pair,command=None):
        need(valid_id(parent) and type(pair) in (list,tuple) and len(pair)==2 and all(valid_id(x) for x in pair),'b_request_pair_types')
        with store.repo._read() as c:
            h=store.checked(c)
            current=store.repo._command(c,command) if command is not None else None
            if current is not None:return store.context(c,h,current)
            cmd=store.repo._command(c,parent)
            need(cmd is not None and cmd['state']=='finalized' and cmd['run']['body']['status'] in ('completed','blocked'),'b_entry_parent')
            session=cmd['operation']['session_id'];head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(session,)).fetchone())
            need(type(pair) in (list,tuple) and list(pair)==head,'b_expected_current_pair')
            base=h.view(session,pair,head);need(base.parent_command_id==parent,'b_parent_publisher')
            return dict(history=h,base=base,existing=False)

    def _selection(self,view,*,mode,step,unit_ids,goal,anchor):
        need(mode in ('adopt','revalidate'),'b_as_only_mode');base=view['base'];v=CheckpointVerifier(view['history']);parent=None
        need(unit_ids is None or type(unit_ids) in (list,tuple) and all(valid_id(x) for x in unit_ids),'b_request_unit_types')
        units=sorted(unit_ids) if unit_ids is not None else sorted(base.context.source.units)
        need(type(step) is int and len(units)==len(set(units)),'b_step_units')
        if mode=='adopt':
            need(step==0 and goal=='admission' and set(units)==set(base.context.source.units),'b_adopt_request')
            if anchor is not None:v.anchor(anchor,base)
            rows,guards=v.selector_seed(base);meta=None;aliases={}
            if anchor is not None:aliases=aliases_for(anchor,base)
        else:
            need(1<=step<=4 and goal in ('admission','retained_output') and anchor is None,'b_revalidate_request')
            parent=v.published(base.parent_command_id);meta=parent.plan()['admission'];rows=deepcopy(meta['selectors']);guards=deepcopy(meta['guards']);aliases=parent.plan()['allocation']['aliases']
            if goal=='retained_output':
                for u in units:need(int(meta['progress_by_unit'][u]['work_completed_through'])>=step and any(int(o['step'])==step for o in meta['progress_by_unit'][u]['outputs']),'b_retained_stage_proof_required')
        base.context.source.selected(units)
        return units,parent,meta,rows,guards,aliases

    def inspect(self,parent,*,expected_pair,mode='adopt',step=0,unit_ids=None,goal='admission',anchor=None,analysis=None,provider_id=None):
        store=self.invocation();view=self._request(store,parent,expected_pair);units,parentcap,meta,rows,guards,aliases=self._selection(view,mode=mode,step=step,unit_ids=unit_ids,goal=goal,anchor=anchor)
        base=view['base'];bb=None
        if analysis is not None:
            need(type(analysis) is bytes and provider_id is not None,'b_inspect_raw_provider')
            bb=binding(base,provider_id=provider_id,mode=mode,step=step,units=units,goal=goal,aliases=aliases,rows=rows,progress=meta['progress_by_unit'] if meta else None,anchor=anchor,raw=analysis)
        stages=meta['progress_by_unit'] if meta else CheckpointVerifier(view['history']).anchor(anchor,base).payload() if anchor is not None else __import__('dacn_s02.h3_policy',fromlist=['unassessed_progress']).unassessed_progress(base)
        return output(None,'completed',dict(store_id=view['history'].store_id,session_id=base.session_id,base_pair=base.pair,source_context_id=base.context.source.context_id,snapshot_id=base.context.source.snapshot_id,
            unit_ids=units,obligations=[dict(snapshot_id=base.context.source.snapshot_id,input_pointer=p) for p in sorted(base.context.source.obligations)],selectors=rows,guards=guards,aliases=aliases,progress_by_unit=stages,
            inventory=[dict(unit_id=u,source_refs=[dict(snapshot_id=base.context.source.snapshot_id,input_pointer=p) for p in sorted(f.obligations)]) for u,f in sorted(base.context.source.units.items())],
            history_binding=base.history.binding(base),historical_reviews_pin=store.registry.registry.pin(),authority_binding=bb,eligibility_authorized_in_process=False,semantic_status='synthetic_not_business_confirmation'))

    def _authorize(self,view,store):
        if self.authority is None:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','Pending B work requires external semantic authority')
        store.registry.rehash(store.budget)
        return self.authority.authorize(view['config']['authority_binding'],store.budget)

    @contextmanager
    def publication_checks(self,store,cfg):
        original=store.repo._hook
        def guarded(point,c):
            original(point,c)
            if point in ('after_begin','before_finalize_insert','before_commit'):
                store.registry.rehash(store.budget)
                if self.authority is None:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','Pending B work requires external semantic authority')
                self.authority.authorize(cfg['authority_binding'],store.budget);store.budget.check()
        store.repo._hook=guarded
        try:yield
        finally:store.repo._hook=original

    def _receipt(self,path,command,storeid):
        p=Path(path)
        if p.exists():
            got=read_receipt(self.settings,p,store_id=storeid);need(got['command_id']==command,'b_receipt_command');return
        try:write_receipt(self.settings,p,command,store_id=storeid)
        except (OSError,S02Error):
            if not p.exists():raise
            got=read_receipt(self.settings,p,store_id=storeid);need(got['command_id']==command,'b_concurrent_receipt_command')

    def prepare(self,command,parent,*,receipt,expected_pair,analysis,mode='adopt',step=0,unit_ids=None,goal='admission',anchor=None):
        need(valid_id(command) and type(analysis) is bytes,'b_prepare_inputs')
        store=self.invocation();view=self._request(store,parent,expected_pair,command);budget=store.budget
        if 'config' in view:
            cfg=view['config'];units=sorted(unit_ids) if unit_ids is not None else sorted(view['base'].context.source.units)
            need(cfg['parent_command_id']==parent and cfg['mode']==mode and cfg['step']==step and cfg['unit_ids']==units and cfg['goal']==goal and cfg['anchor']==anchor and
                 [cfg['base_model_id'],cfg['base_analysis_set_id']]==list(expected_pair) and view['raw']['bytes']==analysis,'b_existing_intent_conflict')
            self._receipt(receipt,command,cfg['store_id'])
            if view['command']['state']=='finalized':return self._report(view,store)
            self._authorize(view,store);return output(command,'prepared',dict(reserved_run_id=cfg['reserved_run_id']))
        if self.authority is None:raise S02Error('H3_AUTHORITY_UNAVAILABLE','persistence','B preparation requires external semantic authority')
        self.authority.read(budget)
        base=view['base'];source=base.context.source;units,parentcap,meta,rows,guards,aliases=self._selection(view,mode=mode,step=step,unit_ids=unit_ids,goal=goal,anchor=anchor)
        bb=binding(base,provider_id=self.authority.trust.provider_id,mode=mode,step=step,units=units,goal=goal,aliases=aliases,rows=rows,progress=meta['progress_by_unit'] if meta else None,anchor=anchor,raw=analysis)
        cfg=dict(**profile_pins(),marker=CONFIG,config_version=CONFIG,handler_version=HANDLER,policy_version=POLICY,limits_version=VERSION,limits=asdict(DEFAULTS),
            store_id=view['history'].store_id,session_id=base.session_id,command_id=command,parent_command_id=parent,reserved_run_id='h3.preT0.reserved',started_at='1970-01-01T00:00:00.000Z',
            mode=mode,step=step,unit_ids=units,goal=goal,source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,
            base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],base_model_sha256=digest(base.context.model()),base_analysis_set_sha256=digest(base.analysis_set),
            anchor=anchor,parent_metadata=meta,aliases=aliases,inputs=dict(candidate=None,analysis=dict(stage_ref=dict(command_id=command,blob_id='h3.preT0.analysis'),sha256=bb['analysis_sha256'],byte_length=len(analysis),media_type='application/json')),
            historical_reviews_pin=store.registry.registry.pin(),history_binding=base.history.binding(base),authority_binding=bb,intent_sha256='0'*64)
        cfg['intent_sha256']=digest(config_intent(cfg));CheckpointVerifier(view['history']).config(cfg,base,analysis,parentcap)
        self.authority.authorize(bb,budget)
        self.hook('before_receipt');self._receipt(receipt,command,cfg['store_id']);self.hook('after_receipt')
        self.hook('before_prepare')
        with self.publication_checks(store,cfg):prepared=store.prepare(cfg,analysis)
        self.hook('after_prepare')
        if prepared['state']=='finalized':return self._report(store.load(command),store)
        return output(command,'prepared',dict(reserved_run_id=prepared['operation']['reserved_run_id']))

    def build(self,view,store):
        cfg=view['config'];fresh=store.fresh(view['state']);now=max(cfg['started_at'],store.repo._clock());base=view['base'];cid=cfg['command_id'];rid=cfg['reserved_run_id']
        stages,rows,guards=view['inputs'];changes=issue_changes(cfg,base,rows,guards,view['raw']['bytes']);records=[];selected=[]
        for q in base.issues:
            key=q['body']['issue_key']
            if key in changes:q=record('issue',fresh(),changes[key],now);records.append(q)
            selected.append(q['id'])
        aset=record('analysis_set',fresh(),{**deepcopy(base.analysis_set['body']),'revision':int(base.analysis_set['body']['revision'])+1,'parent_set_id':base.pair[1],'issue_ids':selected,'changed_record_ids':[r['id'] for r in records]},now);records.append(aset);head=[base.pair[0],aset['id']]
        sources=[];blobs={}
        for stage in (view['primary'],view['raw']):
            aid=fresh();records.append(artifact(aid,stage['purpose'],stage['bytes'],rid,now));blobs[aid]=stage['bytes'];sources.append(dict(artifact_id=aid,stage_ref=dict(command_id=cid,blob_id=stage['blob_id'])))
        run=record('run',rid,dict(mode='replay',source_context_id=cfg['source_context_id'],config_artifact_id=sources[0]['artifact_id'],base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],command_id=cid,
            result_model_id=None,result_analysis_set_id=aset['id'],steps=[] if cfg['mode']=='adopt' else [cfg['step']],status='blocked',started_at=cfg['started_at'],completed_at=now,attempts=[],errors=[]),cfg['started_at']);records.append(run)
        s=frozen_state(cfg,view['history'])
        for r in records:s['records'][r['id']]=r;s['record_profiles'][r['id']]=E1;s['owners'][r['id']]=cfg['session_id']
        s['blobs'].update(blobs)
        for ordinal,kind,payload in [(2,'log',dict(message='H3-B immutable work plan sealed')),(3,'finalized',dict(run_id=rid,promotions=sources))]:
            eid='h3.projection.'+kind+'.'+cid;s['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=ordinal,kind=kind,payload=payload)
        h=HistoryData(**s,registry=store.registry.registry,store_id=cfg['store_id'],budget=store.budget)
        bv=h.view(cfg['session_id'],base.pair,base.pair);rv=h.view(cfg['session_id'],head,head);verifier=CheckpointVerifier(h)
        parent=verifier.published(cfg['parent_command_id']) if cfg['mode']=='revalidate' else None
        stages,rows,guards=verifier.config(cfg,bv,view['raw']['bytes'],parent)
        meta=admission(cfg,bv,rv,stages,rows,guards,view['raw']['bytes'])
        blocked=bool(meta['full_hold_reasons'] or any(p['unresolved_keys'] or p['assessment_state']!='current' for p in meta['progress_by_unit'].values()));run['body']['status']='blocked' if blocked else 'completed'
        pbid=fresh();paid=fresh()
        return dict(**profile_pins(),marker=PLAN,plan_version=PLAN,bindings=store.bindings(cfg,view['primary']),allocation=dict(plan_blob_id=pbid,plan_artifact_id=paid,created_at=now,aliases=cfg['aliases']),
            batch=dict(records=records,artifact_sources=sources,head=head),promotions=sources+[dict(artifact_id=paid,stage_ref=dict(command_id=cid,blob_id=pbid))],admission=meta,candidate_outcome='adopted' if cfg['mode']=='adopt' else 'revalidated',diagnostics=[])

    def resume(self,command,*,receipt=None):
        store=self.invocation()
        if receipt is not None:
            value=read_receipt(self.settings,receipt,store_id=self.trust.expected_store_id);need(value['command_id']==command,'b_resume_receipt_command')
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
        self._authorize(view,store)
        # Re-read winning seal; never rebuild/rebase allocations or proofs.
        plan,stage=store.checked_plan(view);records,blobs=store.materialize(plan,stage['bytes'],view['state'])
        with self.publication_checks(store,view['config']):store.repo.finalize(command,records,blobs=blobs,promotions=plan['promotions'],head=plan['batch']['head'])
        self.hook('after_finalize');return self._report(store.load(command),store)

    def _report(self,view,store):
        cmd=view['command'];cfg=view['config'];cid=cfg['command_id'];found=store.checked_plan(view)
        if cmd['state']!='finalized':return output(cid,'prepared',dict(phase='sealed' if found else 'prepared',reserved_run_id=cfg['reserved_run_id']))
        need(found is not None,'b_finalized_plan_required');plan,stage=found;run=cmd['run'];rb=run['body'];published=rb['status'] in ('completed','blocked')
        if published:CheckpointVerifier(view['history']).published(cid)
        else:
            need(rb['status']=='stale' and rb['result_model_id'] is None and rb['result_analysis_set_id'] is None,'b_finalized_nonpublication')
            need(len(rb['errors'])==1 and rb['errors'][0]['code'] in ('MODEL_CONFLICT','ANALYSIS_CONFLICT'),'b_stale_cas_error')
            expected_run=deepcopy(next(r for r in plan['batch']['records'] if r['id']==cfg['reserved_run_id']))
            error=rb['errors'][0];model=error['code']=='MODEL_CONFLICT';kind='model' if model else 'analysis_set'
            key='model_id' if model else 'analysis_set_id';details=error.get('details',{})
            target=details.get('expected_'+key);records=view['state']['records']
            need(target in records and records[target]['type']==kind and view['state']['owners'][target]==cfg['session_id'] and target!=cfg['base_'+key],'b_stale_conflict_ref')
            expected_error=S02Error(error['code'],'revision','Model head changed' if model else 'AnalysisSet head changed',details={'expected_'+key:target,'provided_'+key:cfg['base_'+key]}).error
            need(error==expected_error,'b_stale_conflict_binding')
            expected_run['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=[expected_error])
            need(run==expected_run,'b_stale_exact_reserved_run')
            need(all(view['state']['records'].get(r['id'])==r for r in plan['batch']['records'] if r['type']=='artifact'),'b_stale_exact_artifacts')
            need(all(r['id'] not in view['state']['records'] for r in plan['batch']['records'] if r['type'] in ('issue','analysis_set')),'b_stale_no_planned_domain_records')
            CheckpointVerifier(view['history']).envelope(cfg,plan)
        result=output(cid,rb['status'],dict(phase='finalized',run_id=run['id'],run_status=rb['status'],result_pair=plan['batch']['head'] if published else None,current_head=view['current_head'],is_current=published and plan['batch']['head']==view['current_head'],
            candidate_outcome=plan['candidate_outcome'],last_checked_eligibility=plan['admission'] if published else None,progress_by_unit=plan['admission']['progress_by_unit'] if published else {},next_aliases=plan['allocation']['aliases'] if published else {},
            semantic_status='synthetic_not_business_confirmation',eligibility_authorized_in_process=False,plan_sha256=stage['sha256'],historical_reviews_pin=cfg['historical_reviews_pin']))
        result['errors']=rb['errors'];result['record_ids']=[run['id'],*[p['artifact_id'] for p in plan['promotions']],*(plan['batch']['head'] if published else [])]
        return result

    def report(self,command):
        store=self.invocation();view=store.load(command)
        return self._report(view,store) if view is not None else output(command,'not_prepared',dict(phase='not_prepared'))

    def adopt(self,command,parent,**kwargs):
        self.prepare(command,parent,mode='adopt',**kwargs);return self.resume(command,receipt=kwargs['receipt'])

    def revalidate(self,command,parent,**kwargs):
        self.prepare(command,parent,mode='revalidate',**kwargs);return self.resume(command,receipt=kwargs['receipt'])
