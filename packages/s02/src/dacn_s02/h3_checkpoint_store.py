"""H3-B transaction adapter, using unchanged DB2/Repository CAS primitives."""
from copy import deepcopy
from .codec_boundary import encode,decode
from .profiles import E1
from . import store_profiles
from .service import staged,artifact
from .h1_store import WorkStore
from .h3_history import HistoryData
from .h3_limits import need,digest
from .h3_bindings import config_intent
from .h3_checkpoint_contracts import validate
from .h3_checkpoint_checks import CheckpointVerifier


def frozen_state(cfg,history):
    """Full pinned T0 facts plus this command, for a detached CAS witness.

    Whole current graph/registry and every pinned fact are verified separately.
    This witness removes only post-T0 additions, never any pinned Record/event.
    It allows validating a sealed losing plan without rebasing it onto a rival.
    """
    s=history._state;pin=cfg['history_binding'];cid=cfg['command_id']
    ids={p['record_id'] for p in pin['records']};keys={(p['command_id'],p['event_id']) for p in pin['events']}
    commands={c for c,e in keys}|{cid}
    events={k:deepcopy(e) for k,e in s['events'].items() if k in keys or k[0]==cid and e['kind']!='finalized'}
    refs=set()
    def walk(v):
        if type(v) is list:
            for x in v:walk(x)
        elif type(v) is dict:
            if set(v)=={'command_id','blob_id'}:refs.add((v['command_id'],v['blob_id']))
            else:
                for x in v.values():walk(x)
    for e in events.values():walk(e['payload'])
    # Own sealed plan is not referenced by the log payload until T3 promotion.
    refs.update(k for k in s['stages'] if k[0]==cid)
    result=dict(records={i:deepcopy(v) for i,v in s['records'].items() if i in ids},
        record_profiles={i:v for i,v in s['record_profiles'].items() if i in ids},owners={i:v for i,v in s['owners'].items() if i in ids},
        commands={c:deepcopy(v) for c,v in s['commands'].items() if c in commands},operation_profiles={c:v for c,v in s['operation_profiles'].items() if c in commands},
        events=events,stages={k:deepcopy(v) for k,v in s['stages'].items() if k in refs},blobs={i:v for i,v in s['blobs'].items() if i in ids})
    need(ids<=result['records'].keys() and keys<=result['events'].keys(),'b_full_T0_witness_inventory')
    return result


class HistoryStore(WorkStore):
    def __init__(self,repo,registry,budget):
        super().__init__(repo);self.registry=registry;self.budget=budget

    def checked(self,c):return self.registry.checked(self.repo,c,self.budget)[0]

    def primary(self,cmd,h):
        s=h._state;cid=cmd['operation']['command_id'];refs=cmd['events'][0]['payload']['stage_refs']
        need(cmd['operation']['request']['kind']=='work' and len(refs)==2,'b_prepared_inputs')
        stages=[s['stages'][p['command_id'],p['blob_id']] for p in refs]
        need(stages[0]['purpose']=='config' and stages[1]['purpose']=='llm_response','b_input_purposes')
        cfg=validate('Config',self.budget.parse(stages[0]['bytes'],kind='config',slot='b.config.'+cid),self.budget)
        need(all(cfg[k]==cmd['operation'][k] for k in ('command_id','session_id','parent_command_id','reserved_run_id')),'b_primary_operation')
        need(cfg['historical_reviews_pin']==self.registry.registry.pin() and cfg['store_id']==h.store_id,'b_primary_registry_store')
        pin=cfg['inputs']['analysis'];need(pin['stage_ref']==refs[1] and all(pin[k]==stages[1][k] for k in ('sha256','byte_length','media_type')),'b_primary_raw_pin')
        need(cfg['intent_sha256']==digest(config_intent(cfg)),'b_primary_intent')
        events=cmd['events'];need(sum(e['kind']=='prepared' for e in events)==1,'b_single_prepared_event')
        need(all(e['kind'] in ('prepared','log','finalized') and (e['kind']!='log' or e['payload']==dict(message='H3-B immutable work plan sealed')) for e in events),'b_pending_event_protocol')
        logs=sum(e['kind']=='log' for e in events);need(logs<=1 and sum(e['kind']=='finalized' for e in events)<=1,'b_pending_phase_counts')
        own=[v for (c,_),v in s['stages'].items() if c==cid]
        need(len(own)==2+logs and sum(v['purpose']=='config' for v in own)==1+logs and sum(v['purpose']=='llm_response' for v in own)==1,'b_pending_stage_protocol')
        return cfg,stages[0],stages[1]

    def context(self,c,h,cmd):
        cfg,primary,raw=self.primary(cmd,h);v=CheckpointVerifier(h)
        base=v.view([cfg['base_model_id'],cfg['base_analysis_set_id']],cfg['session_id'])
        parent=v.published(cfg['parent_command_id']) if cfg['mode']=='revalidate' else None
        inputs=v.config(cfg,base,raw['bytes'],parent)
        head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone())
        return dict(history=h,state=h._state,command=cmd,config=cfg,primary=primary,raw=raw,base=base,parent=parent,inputs=inputs,current_head=head)

    def load(self,command):
        with self.repo._read() as c:
            h=self.checked(c);cmd=self.repo._command(c,command)
            return self.context(c,h,cmd) if cmd is not None else None

    def entry(self,parent,pair):
        with self.repo._read() as c:
            h=self.checked(c);cmd=self.repo._command(c,parent)
            need(cmd is not None and cmd['state']=='finalized' and cmd['run']['body']['status'] in ('completed','blocked'),'b_entry_finalized_parent')
            session=cmd['operation']['session_id'];head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(session,)).fetchone())
            need(list(pair)==head,'b_entry_pair_stale')
            v=h.view(session,pair,head);need(v.parent_command_id==parent,'b_entry_unique_publisher')
            return h,v

    def plans(self,cmd,h):
        cid=cmd['operation']['command_id'];primary=cmd['events'][0]['payload']['stage_refs'][0]['blob_id'];found=[]
        for (c,bid),stage in h._state['stages'].items():
            if c!=cid or bid==primary or stage['purpose']!='config':continue
            value=validate('Plan',self.budget.parse(stage['bytes'],kind='plan',slot='b.plan.'+cid),self.budget)
            need(value['allocation']['plan_blob_id']==bid,'b_sealed_plan_stage_identity');found.append((value,stage))
        need(len(found)<=1,'b_one_sealed_plan')
        return found

    def bindings(self,cfg,primary):
        return dict(command_id=cfg['command_id'],session_id=cfg['session_id'],parent_command_id=cfg['parent_command_id'],reserved_run_id=cfg['reserved_run_id'],
            primary_config_sha256=primary['sha256'],primary_config_stage_ref=dict(command_id=cfg['command_id'],blob_id=primary['blob_id']),intent_sha256=cfg['intent_sha256'],base_pair=[cfg['base_model_id'],cfg['base_analysis_set_id']],
            history_sha256=digest(cfg['history_binding']),anchor_sha256=digest(cfg['anchor']) if cfg['anchor'] is not None else None,authority_binding_sha256=digest(cfg['authority_binding']),historical_reviews_pin=cfg['historical_reviews_pin'],handler_version=cfg['handler_version'])

    def materialize(self,plan,raw,state):
        # The H1 primitive only copies planned bytes and adds the plan Artifact;
        # it has no H1 context checks or hidden allocation/provider call.
        return super().materialize(plan,raw,state)

    def witness(self,view,plan,raw):
        cfg=view['config'];s=frozen_state(cfg,view['history']);cid=cfg['command_id']
        records,blobs=self.materialize(plan,raw,view['state'])
        for r in records:
            need(r['id'] not in s['records'],'b_plan_fresh_T0_ids');s['records'][r['id']]=r;s['record_profiles'][r['id']]=E1;s['owners'][r['id']]=cfg['session_id']
        s['blobs'].update(blobs)
        alloc=plan['allocation'];meta,data=staged(cid,alloc['plan_blob_id'],'config',raw);s['stages'][cid,meta['blob_id']]={**meta,'bytes':data}
        logs=[e for (c,_),e in s['events'].items() if c==cid and e['kind']=='log']
        if not logs:
            eid='h3.projection.seal.'+cid;s['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=2,kind='log',payload=dict(message='H3-B immutable work plan sealed'))
        eid='h3.projection.final.'+cid;s['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=3,kind='finalized',payload=dict(run_id=cfg['reserved_run_id'],promotions=plan['promotions']))
        h=HistoryData(**s,registry=self.registry.registry,store_id=cfg['store_id'],budget=self.budget)
        verifier=CheckpointVerifier(h);return verifier.published(cid)

    def checked_plan(self,view):
        found=self.plans(view['command'],view['history'])
        if not found:return None
        plan,stage=found[0];self.witness(view,plan,stage['bytes'])
        return plan,stage

    def prepare(self,cfg,raw):
        expected=deepcopy(cfg);cid=cfg['command_id']
        def work(c):
            h=self.checked(c);current=self.repo._command(c,cid)
            if current:
                old,_,oldraw=self.primary(current,h)
                need(config_intent(old)==config_intent(expected) and oldraw['bytes']==raw,'b_prepare_concurrent_intent_conflict')
                return current
            # Recheck full T0 inventory under the write lock, never silently pin
            # a different history after an unrelated concurrent append.
            base=h.view(cfg['session_id'],[cfg['base_model_id'],cfg['base_analysis_set_id']],[cfg['base_model_id'],cfg['base_analysis_set_id']])
            need(cfg['history_binding']==h.binding(base),'b_prepare_T0_history_changed')
            head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone());need(head==base.pair,'b_prepare_pair_stale')
            v=CheckpointVerifier(h);parent=v.published(cfg['parent_command_id']) if cfg['mode']=='revalidate' else None;v.config(cfg,base,raw,parent)
            fresh=self.fresh(h._state);actual=deepcopy(cfg);actual.update(reserved_run_id=fresh(),started_at=self.repo._clock())
            ar=staged(cid,fresh(),'llm_response',raw);actual['inputs']['analysis']['stage_ref']=dict(command_id=cid,blob_id=ar[0]['blob_id'])
            actual['intent_sha256']=digest(config_intent(actual));primary=staged(cid,fresh(),'config',self.budget.serialized(actual,'config'))
            request=dict(kind='work',source_context_id=actual['source_context_id'],base_model_id=actual['base_model_id'],base_analysis_set_id=actual['base_analysis_set_id'],scope=None,config_artifact_id=None)
            c.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?)',(cid,actual['session_id'],actual['parent_command_id'],actual['reserved_run_id'],encode(request).decode('ascii'),digest(request),E1))
            self.repo._put_stages(c,cid,[primary,ar]);self.repo._put_event(c,self.repo._event(c,cid,'prepared',dict(stage_refs=[dict(command_id=cid,blob_id=x[0]['blob_id']) for x in (primary,ar)],attempt_id=None)))
            return self.repo._command(c,cid)
        def probe():
            view=self.load(cid)
            if view is None:return None
            need(config_intent(view['config'])==config_intent(expected) and view['raw']['bytes']==raw,'b_prepare_probe_intent')
            return view['command']
        return self.repo._write(work,probe)

    def seal(self,cid,plan):
        raw=self.budget.serialized(plan,'plan')
        def work(c):
            h=self.checked(c);cmd=self.repo._command(c,cid);need(cmd is not None,'b_seal_prepared')
            view=self.context(c,h,cmd)
            if cmd['state']=='finalized':return dict(finalized=True)
            existing=self.checked_plan(view)
            if existing:return dict(plan=existing[0],stage=existing[1])
            self.witness(view,plan,raw)
            # Allocate no IDs/clocks here. The winning sealed bytes select all
            # allocations; concurrent losers adopt this exact plan on readback.
            stage=staged(cid,plan['allocation']['plan_blob_id'],'config',raw)
            self.repo._put_stages(c,cid,[stage]);self.repo._put_event(c,self.repo._event(c,cid,'log',dict(message='H3-B immutable work plan sealed')))
            return dict(plan=plan,stage={**stage[0],'bytes':raw})
        def probe():
            view=self.load(cid)
            if view is None:return None
            if view['command']['state']=='finalized':return dict(finalized=True)
            found=self.checked_plan(view)
            return dict(plan=found[0],stage=found[1]) if found else None
        return self.repo._write(work,probe)
