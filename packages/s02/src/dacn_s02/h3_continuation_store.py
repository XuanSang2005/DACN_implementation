"""C transaction adapter. DB2/Repository paired CAS and B store remain unchanged."""
from copy import deepcopy
from .codec_boundary import encode
from .profiles import E1
from .service import staged
from .h3_history import HistoryData
from .h3_limits import need,digest
from .h3_bindings import config_intent
from .h3_checkpoint_store import HistoryStore
from .h3_continuation_contracts import validate
from .h3_continuation_checks import ContinuationVerifier
from .h3_continuation_plan import frozen_state,MESSAGE


class ContinuationStore(HistoryStore):
    """Reuse only checked registry/load/materialize/fresh primitives from B."""
    def primary(self,cmd,h):
        s=h._state;cid=cmd['operation']['command_id'];refs=cmd['events'][0]['payload']['stage_refs'];need(len(refs) in (2,3),'c_prepared_input_count')
        stages=[s['stages'][r['command_id'],r['blob_id']] for r in refs];need(stages[0]['purpose']=='config','c_primary_purpose')
        cfg=validate('Config',self.budget.parse(stages[0]['bytes'],kind='config',slot='c.config.'+cid),self.budget)
        need(cmd['operation']['request']['kind']=='work' and all(cfg[k]==cmd['operation'][k] for k in ('command_id','session_id','parent_command_id','reserved_run_id')),'c_primary_operation')
        need(cfg['historical_reviews_pin']==self.registry.registry.pin() and cfg['store_id']==h.store_id,'c_primary_registry_store')
        expected=[refs[0]]+[cfg['inputs'][k]['stage_ref'] for k in ('candidate','analysis') if cfg['inputs'][k] is not None];need(refs==expected,'c_prepared_raw_order')
        raw={k:s['stages'][cid,cfg['inputs'][k]['stage_ref']['blob_id']] if cfg['inputs'][k] is not None else None for k in ('candidate','analysis')}
        for lane,stage in raw.items():
            if stage is not None:
                pin=cfg['inputs'][lane];need(stage['purpose']=='llm_response' and all(pin[k]==stage[k] for k in ('sha256','byte_length','media_type')),'c_staged_raw_pin')
        need(cfg['intent_sha256']==digest(config_intent(cfg)),'c_primary_intent')
        kinds=[e['kind'] for e in cmd['events']];need(kinds in (['prepared'],['prepared','log'],['prepared','log','finalized']),'c_phase_protocol')
        logs=[e for e in cmd['events'] if e['kind']=='log'];need(not logs or logs[0]['payload']==dict(message=MESSAGE),'c_seal_log')
        own=[v for (c,b),v in s['stages'].items() if c==cid];need(len(own)==len(refs)+len(logs),'c_pending_stage_inventory')
        return cfg,stages[0],raw

    def context(self,c,h,cmd):
        cfg,primary,raw=self.primary(cmd,h);v=ContinuationVerifier(h);base=v.view([cfg['base_model_id'],cfg['base_analysis_set_id']],cfg['session_id']);parent=v.config(cfg,base,{k:x['bytes'] if x else None for k,x in raw.items()})
        head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone())
        return dict(history=h,state=h._state,command=cmd,config=cfg,primary=primary,raw=raw,base=base,parent=parent,current_head=head)

    def plans(self,cmd,h):
        cid=cmd['operation']['command_id'];primary=cmd['events'][0]['payload']['stage_refs'][0]['blob_id'];found=[]
        for (c,bid),stage in h._state['stages'].items():
            if c!=cid or bid==primary or stage['purpose']!='config':continue
            plan=validate('Plan',self.budget.parse(stage['bytes'],kind='plan',slot='c.plan.'+cid),self.budget);need(plan['allocation']['plan_blob_id']==bid,'c_sealed_plan_identity');found.append((plan,stage))
        need(len(found)<=1,'c_one_plan');return found

    def witness(self,view,plan,raw):
        cfg=view['config'];cid=cfg['command_id'];s=frozen_state(cfg,view['history']);records,blobs=self.materialize(plan,raw,view['state'])
        for r in records:
            need(r['id'] not in s['records'],'c_plan_fresh_T0_ids');s['records'][r['id']]=r;s['record_profiles'][r['id']]=E1;s['owners'][r['id']]=cfg['session_id']
        s['blobs'].update(blobs);a=plan['allocation'];meta,data=staged(cid,a['plan_blob_id'],'config',raw);s['stages'][cid,meta['blob_id']]={**meta,'bytes':data}
        if not any(c==cid and e['kind']=='log' for (c,i),e in s['events'].items()):
            eid='h3c.witness.'+digest([cid,'seal']);s['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=2,kind='log',payload=dict(message=MESSAGE))
        eid='h3c.witness.'+digest([cid,'final']);s['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=3,kind='finalized',payload=dict(run_id=cfg['reserved_run_id'],promotions=plan['promotions']))
        h=HistoryData(**s,registry=self.registry.registry,store_id=cfg['store_id'],budget=self.budget);v=ContinuationVerifier(h);base=v.view([cfg['base_model_id'],cfg['base_analysis_set_id']],cfg['session_id'])
        if plan['batch']['head'] is not None:return v.published(cid)
        return v.result(cfg,plan,base)

    def prepare(self,cfg,raw):
        expected=deepcopy(cfg);cid=cfg['command_id']
        def work(c):
            h=self.checked(c);current=self.repo._command(c,cid)
            if current is not None:
                old,primary,oldraw=self.primary(current,h)
                need(config_intent(old)==config_intent(expected) and {k:s['bytes'] if s else None for k,s in oldraw.items()}==raw,'c_concurrent_intent_conflict');return current
            base=h.view(cfg['session_id'],[cfg['base_model_id'],cfg['base_analysis_set_id']],[cfg['base_model_id'],cfg['base_analysis_set_id']])
            need(cfg['history_binding']==h.binding(base),'c_T0_history_changed')
            head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone());need(head==base.pair,'c_prepare_pair_stale')
            ContinuationVerifier(h).config(cfg,base,raw);fresh=self.fresh(h._state);actual=deepcopy(cfg);actual.update(reserved_run_id=fresh(),started_at=self.repo._clock());items=[]
            for lane in ('candidate','analysis'):
                if raw[lane] is None:continue
                item=staged(cid,fresh(),'llm_response',raw[lane]);items.append(item);actual['inputs'][lane]['stage_ref']=dict(command_id=cid,blob_id=item[0]['blob_id'])
            actual['intent_sha256']=digest(config_intent(actual));primary=staged(cid,fresh(),'config',self.budget.serialized(actual,'config'));items.insert(0,primary)
            request=dict(kind='work',source_context_id=actual['source_context_id'],base_model_id=actual['base_model_id'],base_analysis_set_id=actual['base_analysis_set_id'],scope=None,config_artifact_id=None)
            c.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?)',(cid,actual['session_id'],actual['parent_command_id'],actual['reserved_run_id'],encode(request).decode('ascii'),digest(request),E1))
            self.repo._put_stages(c,cid,items);self.repo._put_event(c,self.repo._event(c,cid,'prepared',dict(stage_refs=[dict(command_id=cid,blob_id=m['blob_id']) for m,b in items],attempt_id=None)));return self.repo._command(c,cid)
        def probe():
            view=self.load(cid)
            if view is None:return None
            need(config_intent(view['config'])==config_intent(expected) and {k:s['bytes'] if s else None for k,s in view['raw'].items()}==raw,'c_prepare_probe_intent');return view['command']
        return self.repo._write(work,probe)

    def seal(self,cid,plan):
        raw=self.budget.serialized(plan,'plan')
        def work(c):
            h=self.checked(c);cmd=self.repo._command(c,cid);need(cmd is not None,'c_seal_prepared');view=self.context(c,h,cmd)
            if cmd['state']=='finalized':return dict(finalized=True)
            existing=self.checked_plan(view)
            if existing:return dict(plan=existing[0],stage=existing[1])
            self.witness(view,plan,raw);stage=staged(cid,plan['allocation']['plan_blob_id'],'config',raw)
            self.repo._put_stages(c,cid,[stage]);self.repo._put_event(c,self.repo._event(c,cid,'log',dict(message=MESSAGE)));return dict(plan=plan,stage={**stage[0],'bytes':raw})
        def probe():
            view=self.load(cid)
            if view is None:return None
            if view['command']['state']=='finalized':return dict(finalized=True)
            found=self.checked_plan(view);return dict(plan=found[0],stage=found[1]) if found else None
        return self.repo._write(work,probe)
