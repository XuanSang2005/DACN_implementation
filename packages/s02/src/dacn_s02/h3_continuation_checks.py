"""Pure C result/publisher checks, exact B->C/C->C dispatch and raw reconstruction."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from .codec_boundary import encode,decode
from .h3_limits import need,digest
from .h3_policy import _view as checked_history_view
from .h3_bindings import config_intent,verify_guard_origin,verify_task_origin
from .h3_checkpoint_checks import CheckpointVerifier,dependencies,PublishedCheckpoint
from . import h3_checkpoint_contracts as B
from .h3_continuation_contracts import validate,CONFIG,PLAN,GUARD,PREDICATE
from .h3_continuation_inputs import binding,inspections,intent
from .h3_continuation_builders import guard_key
from .h3_continuation_plan import build,bindings,MESSAGE


@dataclass(frozen=True)
class PublishedContinuation:
    command_id: str
    config_raw: bytes
    plan_raw: bytes
    def config(self):return decode(self.config_raw)
    def plan(self):return decode(self.plan_raw)


class ContinuationVerifier(CheckpointVerifier):
    def checked_view(self,view):
        checked_history_view(view);need(view.history is self.history,'c_view_history')
        actual=self.view(view.pair,view.session_id);need(view.parent_command_id==actual.parent_command_id,'c_view_publisher')
        need(type(view.context) is type(actual.context) and view.context.budget is self.history.budget,'c_view_context_type_budget')
        need(view.context.source.__dict__==actual.context.source.__dict__,'c_view_source_inventory')
        memo=view.context._cache;need(type(memo) is dict,'c_context_cache_type')
        for key,value in list(memo.items()):
            need(type(key) is tuple and len(key)==2 and all(type(x) is frozenset for x in key),'c_context_cache_key')
            need(actual.context.closure(*key)==value,'c_context_cache_fixed_point')
        for key,value in actual.context.__dict__.items():
            if key in ('source','budget','_cache'):continue
            provided=view.context.__dict__.get(key)
            if key in ('source_elements','source_parts','action_parts','action_rules','action_support'):
                need(type(provided) is type(value) and {k:v for k,v in provided.items() if v}=={k:v for k,v in value.items() if v},'c_context_indexes')
            else:need(provided==value,'c_context_indexes')
        return actual

    def config(self,cfg,base,raw,parent=None):
        base=self.checked_view(base);b=self.history.budget;validate('Config',cfg,b);source=base.context.source
        actual=self.published(base.parent_command_id)
        need(parent is None or type(parent) in (PublishedCheckpoint,PublishedContinuation) and parent==actual,'c_checked_parent_capability')
        meta=actual.plan()['admission'];need(cfg['parent_metadata']==meta,'c_exact_promoted_parent')
        need(cfg['store_id']==self.history.store_id and cfg['session_id']==base.session_id and cfg['parent_command_id']==base.parent_command_id,'c_config_identity')
        need([cfg['base_model_id'],cfg['base_analysis_set_id']]==base.pair and cfg['base_model_sha256']==digest(base.context.model()) and cfg['base_analysis_set_sha256']==digest(base.analysis_set),'c_config_pair')
        need(cfg['source_context_id']==source.context_id and cfg['snapshot_id']==source.snapshot_id and cfg['archive_sha256']==source.archive_sha256,'c_config_source')
        need(cfg['historical_reviews_pin']==self.history.registry.pin(),'c_registry_fixed');dependencies(cfg['history_binding'],base)
        need(cfg['aliases']==actual.plan()['allocation']['aliases'],'c_parent_aliases');source.selected(cfg['unit_ids'])
        need(set(meta['progress_by_unit'])==set(source.units),'c_parent_unit_inventory')
        if cfg['goal']=='retained_output':
            for uid in cfg['unit_ids']:
                p=meta['progress_by_unit'][uid];need(int(p['work_completed_through'])>=int(cfg['step']) and any(int(o['step'])==int(cfg['step']) for o in p['outputs']),'c_retained_stage_proof')
        need(type(raw) is dict and set(raw)=={'candidate','analysis'},'c_raw_slots');b.raw_work(raw['candidate'],raw['analysis'])
        for lane in ('candidate','analysis'):
            pin=cfg['inputs'][lane];data=raw[lane]
            if pin is None:need(data is None,'c_raw_absent')
            else:need(type(data) is bytes and pin['sha256']==sha256(data).hexdigest() and pin['byte_length']==len(data) and pin['stage_ref']['command_id']==cfg['command_id'],'c_raw_exact_pin')
        expected=binding(base,meta,provider_id=cfg['authority_binding']['provider_id'],mode=cfg['mode'],step=int(cfg['step']),units=cfg['unit_ids'],goal=cfg['goal'],aliases=cfg['aliases'],candidate=raw['candidate'],analysis=raw['analysis'])
        expected['history_sha256']=digest(cfg['history_binding'])
        need(cfg['authority_binding']==expected,'c_binding_exact');need(cfg['intent_sha256']==digest(config_intent(cfg)),'c_intent')
        inspections(raw['analysis'],cfg,base);return actual

    def primary(self,cfg):
        s=self.history._state;cid=cfg['command_id'];events=sorted((e for (c,_),e in s['events'].items() if c==cid),key=lambda e:e['ordinal'])
        need(events and events[0]['kind']=='prepared','c_prepared')
        refs=events[0]['payload']['stage_refs'];need(bool(refs),'c_prepared_refs')
        p=s['stages'].get((cid,refs[0]['blob_id']));need(p is not None and p['purpose']=='config' and p['bytes']==encode(cfg),'c_primary_exact')
        expected=[dict(command_id=cid,blob_id=p['blob_id'])]+[cfg['inputs'][lane]['stage_ref'] for lane in ('candidate','analysis') if cfg['inputs'][lane] is not None]
        need(refs==expected,'c_prepared_input_inventory')
        raw={lane:s['stages'][cid,cfg['inputs'][lane]['stage_ref']['blob_id']]['bytes'] if cfg['inputs'][lane] is not None else None for lane in ('candidate','analysis')}
        for lane in ('candidate','analysis'):
            if cfg['inputs'][lane] is not None:need(s['stages'][cid,cfg['inputs'][lane]['stage_ref']['blob_id']]['purpose']=='llm_response','c_raw_stage_purpose')
        return p,raw

    def result(self,cfg,plan,base,result=None,parent=None):
        base=self.checked_view(base);validate('Plan',plan,self.history.budget)
        primary,raw=self.primary(cfg);self.config(cfg,base,raw,parent);s=self.history._state;op=s['commands'].get(cfg['command_id'])
        need(op is not None and all(op[k]==cfg[k] for k in ('command_id','session_id','parent_command_id','reserved_run_id')),'c_operation_identity')
        need(op['request']==dict(kind='work',source_context_id=cfg['source_context_id'],base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],scope=None,config_artifact_id=None),'c_operation_request')
        expected=build(cfg,base,primary,raw,plan['allocation']['created_at'])
        need(plan==expected,'c_raw_to_result_exact')
        records=plan['batch']['records'];need(all(s['records'].get(r['id'])==r for r in records),'c_planned_actual_records')
        if plan['batch']['head'] is not None:
            actual=self.view(plan['batch']['head'],cfg['session_id'])
            if result is not None:need(self.checked_view(result).pair==actual.pair,'c_result_view')
            self.origins(cfg,plan,actual)
        else:need(result is None and plan['admission'] is None and plan['candidate_outcome']=='rejected','c_rejected_head')
        self.envelope(cfg,plan);return deepcopy(plan)

    def origins(self,cfg,plan,result):
        meta=plan['admission'];s=self.history._state
        for k,origin in meta['tasks'].items():
            need(k==origin['issue_key'],'c_task_key');verify_task_origin(origin,result)
        for key,g in meta['guards'].items():
            need(key==g['issue_key'],'c_guard_key')
            if g.get('version')!=GUARD:verify_guard_origin(g,result);continue
            validate('CGuardOrigin',g,self.history.budget);q=result.issue(key)
            need(g['issue_id']==q['id'] and q['body']['resolution_carry'] is None and q['body']['resolution_replacement'] is None and not q['body']['answer_ids'],'c_guard_current_direct')
            command=g['origin_command_id'];need(key==guard_key(command) and g['predicate']==PREDICATE,'c_guard_predicate')
            if command==cfg['command_id']:
                need(g['origin_plan_sha256'] is None and g['origin_plan_artifact_id']==plan['allocation']['plan_artifact_id'] and plan['candidate_outcome']=='guard_only','c_guard_introducing_pin');originplan=plan;origincfg=cfg
            else:
                need(command in self.cache and type(self.cache[command]) is PublishedContinuation,'c_guard_checked_ancestor')
                cap=self.cache[command];originplan=cap.plan();origincfg=cap.config();aid=originplan['allocation']['plan_artifact_id']
                need(g['origin_plan_artifact_id']==aid and g['origin_plan_sha256']==s['records'][aid]['body']['sha256']==digest(originplan),'c_guard_inherited_actual_sha')
            need(g['base_pair']==[origincfg['base_model_id'],origincfg['base_analysis_set_id']] and g['source_context_id']==origincfg['source_context_id']==cfg['source_context_id'],'c_guard_origin_base')
            need(g['failed_candidate_sha256']==origincfg['inputs']['candidate']['sha256'] and g['failed_analysis_sha256']==origincfg['inputs']['analysis']['sha256'],'c_guard_failed_raw_pins')
            root=s['records'].get(g['root_issue_id']);need(root is not None and root in originplan['batch']['records'] and root['type']=='issue' and root['body']['model_id']==g['base_pair'][0] and root['body']['status']=='open' and root['body']['supersedes_id'] is None,'c_guard_root')
            cursor=q['id'];visited=set()
            while cursor!=root['id']:
                self.history.budget.check();need(cursor is not None and cursor not in visited,'c_guard_lineage');visited.add(cursor);cursor=s['records'][cursor]['body']['supersedes_id']

    def envelope(self,cfg,plan):
        s=self.history._state;cid=cfg['command_id'];primary,raw=self.primary(cfg);need(plan['bindings']==bindings(cfg,primary),'c_plan_bindings')
        refs=[dict(command_id=cid,blob_id=primary['blob_id'])]+[cfg['inputs'][k]['stage_ref'] for k in ('candidate','analysis') if cfg['inputs'][k] is not None]
        sources=plan['batch']['artifact_sources'];need([p['stage_ref'] for p in sources]==refs,'c_raw_promotions')
        for p in sources:
            stage=s['stages'][cid,p['stage_ref']['blob_id']];a=s['records'][p['artifact_id']]
            need(a['type']=='artifact' and a['body']['purpose']==stage['purpose'] and a['body']['producer_run_id']==cfg['reserved_run_id'] and a['body']['sha256']==stage['sha256'] and s['blobs'][a['id']]==stage['bytes'],'c_artifact_exact_raw')
        a=plan['allocation'];need(plan['promotions']==sources+[dict(artifact_id=a['plan_artifact_id'],stage_ref=dict(command_id=cid,blob_id=a['plan_blob_id']))],'c_plan_promotion')
        need(len({p['artifact_id'] for p in plan['promotions']})==len(plan['promotions']),'c_promotion_unique')
        stage=s['stages'][cid,a['plan_blob_id']];artifact=s['records'][a['plan_artifact_id']]
        need(stage['bytes']==encode(plan) and s['blobs'][artifact['id']]==stage['bytes'] and artifact['body']['sha256']==digest(plan),'c_sealed_promoted_bytes')
        need(artifact['body']['producer_run_id']==cfg['reserved_run_id'] and artifact['created_at']==a['created_at'],'c_plan_artifact_allocation')
        events=sorted((e for (c,_),e in s['events'].items() if c==cid),key=lambda e:e['ordinal'])
        need([e['kind'] for e in events]==['prepared','log','finalized'] and [e['ordinal'] for e in events]==[1,2,3],'c_own_phase_protocol')
        need(events[1]['payload']==dict(message=MESSAGE) and events[2]['payload']==dict(run_id=cfg['reserved_run_id'],promotions=plan['promotions']),'c_own_finalized_payload')
        need({bid for c,bid in s['stages'] if c==cid}=={x['blob_id'] for x in refs}|{a['plan_blob_id']},'c_own_stage_inventory')

    def _published(self,command):
        if command in self.cache:return self.cache[command]
        s=self.history._state;todo=[];seen=set();cursor=command
        while cursor not in self.cache:
            self.history.budget.check();self.history.budget.cap('depth',len(todo)+1);need(cursor not in seen,'c_parent_cycle');seen.add(cursor)
            op=s['commands'].get(cursor);need(op is not None,'c_publisher_command')
            finals=[e for (c,_),e in s['events'].items() if c==cursor and e['kind']=='finalized']
            need(len(finals)==1 and finals[0]['payload']['run_id']==op['reserved_run_id'],'c_publisher_finalized')
            rr=s['records'].get(op['reserved_run_id']);need(rr is not None and rr['type']=='run' and rr['body']['status'] in ('completed','blocked'),'c_publisher_run')
            rb=rr['body'];cfgraw=s['blobs'][rb['config_artifact_id']];value=self.history.budget.parse(cfgraw,kind='config',slot='c.publisher.config.'+cursor)
            marker=value.get('marker') if type(value) is dict else None
            if marker==B.CONFIG:
                self.cache[cursor]=CheckpointVerifier(self.history).published(cursor);break
            need(marker==CONFIG,'c_publisher_version');cfg=validate('Config',value,self.history.budget)
            aids=[p['artifact_id'] for p in finals[0]['payload']['promotions'] if p['artifact_id']!=rb['config_artifact_id'] and s['records'][p['artifact_id']]['body']['purpose']=='config']
            need(len(aids)==1,'c_publisher_plan_inventory');raw=s['blobs'][aids[0]];plan=validate('Plan',self.history.budget.parse(raw,kind='plan',slot='c.publisher.plan.'+cursor),self.history.budget)
            need(plan['allocation']['plan_artifact_id']==aids[0],'c_actual_publisher_plan');todo.append((cursor,cfgraw,raw,cfg,plan));cursor=cfg['parent_command_id']
        for cid,cfgraw,raw,cfg,plan in reversed(todo):
            base=self.view([cfg['base_model_id'],cfg['base_analysis_set_id']],cfg['session_id'])
            self.result(cfg,plan,base,parent=self.cache[cfg['parent_command_id']]);self.cache[cid]=PublishedContinuation(cid,cfgraw,raw)
        return self.cache[command]


def check_continuation_result(config,plan,base_view,result_view=None,*,checked_parent_plan=None):
    return ContinuationVerifier(base_view.history).result(config,plan,base_view,result_view,checked_parent_plan)
