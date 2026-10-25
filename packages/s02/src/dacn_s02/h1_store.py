"""H1 checked transaction adapters over unchanged DB2 tables and Record rules."""
from copy import deepcopy

from .codec_boundary import decode, encode
from .errors import S02Error, require, storage_error
from .repository import digest, record
from .service import staged, artifact
from .profiles import E1, get_profile
from . import store_profiles
from .profile_graph import validate_graph
from .validation import COLLECTIONS, inventory, valid_id, shape, time as valid_time
from .h1_candidates import HANDLER_VERSION, VERSION as CANDIDATE_VERSION
from .h1_limits import VERSION as LIMITS_VERSION, DEFAULTS, cap

CONFIG_MARKER='s02_2a_work_config'
CONFIG_VERSION='s02-2a-work-config/0.1.0-draft.1'
PLAN_MARKER='s02_2a_work_plan'
PLAN_VERSION='s02-2a-work-plan/0.1.0-draft.1'
PLAN_KEYS={'marker','plan_version','profile_id','contract_version','rules_id','bindings','allocation','batch','promotions','admission','candidate_outcome','diagnostics'}


def profile_pins():
    p=get_profile(E1).descriptor
    return dict(profile_id=E1,contract_version=p['contract_version'],rules_id=p['rules_id'])


def unsupported():
    raise storage_error('Unsupported H1 command/config/plan/handler version; no rebuild performed')


def logical(config):
    return {k:v for k,v in config.items() if k not in ('started_at','reserved_run_id','intent_sha256')}


class WorkStore:
    def __init__(self, repo): self.repo=repo

    def state(self,c):
        records,blobs,commands,events,stages=self.repo._check(c)
        return dict(records=records,blobs=blobs,commands=commands,events=events,stages=stages,
            owners={r['id']:r['session_id'] for r in c.execute('SELECT id,session_id FROM records')},
            record_profiles={r['id']:r['profile_id'] for r in c.execute('SELECT id,profile_id FROM records')},
            operation_profiles={r['command_id']:r['profile_id'] for r in c.execute('SELECT command_id,profile_id FROM operations')})

    def fresh(self,state):
        used=set(state['records'])|set(state['commands'])|{o['reserved_run_id'] for o in state['commands'].values()}
        used.update(eid for _,eid in state['events']);used.update(bid for _,bid in state['stages'])
        for r in state['records'].values():
            if r['type']=='model':
                for k in COLLECTIONS:
                    for e in r['body'][k]:used.add(e['id'])
                for m in r['body']['mappings']:
                    used.add(m['id']);used.update(p['id'] for p in m['parts'])
                for w in r['body']['workflows']:
                    for k in ('nodes','edges'):used.update(x['id'] for x in w[k])
        def new():
            for _ in range(8):
                value=self.repo._ids();require(valid_id(value),'generated_id')
                if value not in used:used.add(value);return value
            raise storage_error('H1 ID generator collided eight times')
        return new

    def primary(self,cmd,state,*,execute=True):
        require(cmd['operation']['request']['kind']=='work','h1_work_only')
        refs=cmd['events'][0]['payload']['stage_refs']
        configs=[state['stages'][r['command_id'],r['blob_id']] for r in refs if state['stages'][r['command_id'],r['blob_id']]['purpose']=='config']
        require(len(configs)==1,'h1_primary_pin_unique');primary=configs[0]
        cap('config_bytes',len(primary['bytes']));config=decode(primary['bytes'])
        if type(config) is not dict or config.get('marker')!=CONFIG_MARKER or config.get('config_version')!=CONFIG_VERSION:unsupported()
        require(all(config.get(k)==v for k,v in profile_pins().items()),'h1_config_profile')
        require(config.get('intent_sha256')==digest(encode(logical(config))),'h1_intent_hash')
        op=cmd['operation'];req=op['request']
        require(all(config.get(k)==op[k] for k in ('command_id','session_id','parent_command_id','reserved_run_id')),'h1_config_operation')
        require(all(config.get(k)==req[k] for k in ('source_context_id','base_model_id','base_analysis_set_id')),'h1_config_base')
        if execute:
            if (config.get('handler_version')!=HANDLER_VERSION or config.get('candidate_version')!=(None if config.get('step')=='bootstrap' else CANDIDATE_VERSION)
                or config.get('limits_version')!=LIMITS_VERSION):unsupported()
            require(encode(config['limits'])==encode(DEFAULTS) and config['limits_sha256']==digest(encode(DEFAULTS)),'h1_limits_pin')
        raws=[state['stages'][r['command_id'],r['blob_id']] for r in refs if state['stages'][r['command_id'],r['blob_id']]['purpose']=='llm_response']
        require(len(raws)==(0 if config['step']=='bootstrap' else 1),'h1_raw_pin_inventory')
        raw=raws[0] if raws else None
        require(config['input']==(dict(sha256=raw['sha256'],byte_length=raw['byte_length'],media_type=raw['media_type']) if raw else None),'h1_raw_pin')
        return config,primary,raw

    def plans(self,cmd,state):
        found=[]
        primary_ids={r['blob_id'] for r in cmd['events'][0]['payload']['stage_refs']}
        for (owner,_),stage in state['stages'].items():
            if owner!=cmd['operation']['command_id'] or stage['purpose']!='config':continue
            cap('plan_bytes',len(stage['bytes']));value=decode(stage['bytes'])
            if type(value) is dict and value.get('marker')==PLAN_MARKER:found.append((value,stage))
            elif stage['blob_id'] not in primary_ids:raise storage_error('Unexpected H1 config stage; no rebuild performed')
        if len(found)>1:raise storage_error('h1_multiple_plans; no plan selected or repaired')
        return found

    def bindings(self,config,primary,raw):
        return dict(command_id=config['command_id'],session_id=config['session_id'],parent_command_id=config['parent_command_id'],
            reserved_run_id=config['reserved_run_id'],source_context_id=config['source_context_id'],
            base_pair=[config['base_model_id'],config['base_analysis_set_id']],step=config['step'],
            primary_config_stage_ref=dict(command_id=primary['command_id'],blob_id=primary['blob_id']),primary_config_sha256=primary['sha256'],
            raw_stage_ref=dict(command_id=raw['command_id'],blob_id=raw['blob_id']) if raw else None,
            input=config['input'],intent_sha256=config['intent_sha256'],handler_version=config['handler_version'],candidate_version=config['candidate_version'],
            execution_origin=config['execution_origin'],limits_version=config['limits_version'],limits_sha256=config['limits_sha256'],aliases_sha256=digest(encode(config['aliases'])))

    def checked_plan(self,cmd,state,config,primary,raw):
        found=self.plans(cmd,state)
        if not found:return None
        plan,stage=found[0]
        self.validate_plan(plan,cmd,config,primary,raw)
        if plan.get('plan_version')!=PLAN_VERSION:unsupported()
        if set(plan)!=PLAN_KEYS or not all(plan.get(k)==v for k,v in profile_pins().items()):raise storage_error('h1_plan_envelope')
        if encode(plan['bindings'])!=encode(self.bindings(config,primary,raw)):raise storage_error('h1_plan_bindings')
        if plan['allocation']['plan_blob_id']!=stage['blob_id']:raise storage_error('h1_plan_stage_identity')
        return plan,stage

    def validate_plan(self,plan,cmd,config,primary,raw):
        """Treat damaged private blobs as integrity failures, never instructions."""
        try:
            require(type(plan) is dict and set(plan)==PLAN_KEYS,'h1_plan_keys')
            if plan['plan_version']!=PLAN_VERSION:unsupported()
            require(plan['marker']==PLAN_MARKER and all(plan[k]==v for k,v in profile_pins().items()),'h1_plan_profile')
            require(encode(plan['bindings'])==encode(self.bindings(config,primary,raw)),'h1_plan_bindings')
            a=plan['allocation'];batch=plan['batch']
            require(type(a) is dict and set(a)=={'plan_blob_id','plan_artifact_id','created_at','aliases'},'h1_allocation_keys')
            require(valid_id(a['plan_blob_id']) and valid_id(a['plan_artifact_id']) and valid_time(a['created_at']),'h1_allocation_types')
            require(type(a['aliases']) is dict,'h1_aliases')
            for h,value in a['aliases'].items():
                require(valid_id(h) and type(value) is dict and set(value)=={'id','kind'} and valid_id(value['id'])
                        and value['kind'] in ('Actor','Action','Workflow','Data','Rule','Component','Responsibility','Node','Edge','Part','Issue'),'h1_alias_type')
            require(type(batch) is dict and set(batch)=={'records','artifact_sources','head'} and type(batch['records']) is list,'h1_batch')
            ids=[];runs=[]
            for r in batch['records']:
                shape(r,profile=E1);require(r['type'] in ('run','artifact','issue','model','change','analysis_set'),'h1_record_kind')
                ids.append(r['id'])
                if r['type']=='run':runs.append(r)
                if r['type']=='issue':require(not r['body']['answer_ids'] and r['body']['resolution_carry'] is None and r['body']['resolution_replacement'] is None,'h1_issue_scope')
            require(len(ids)==len(set(ids)) and a['plan_artifact_id'] not in ids,'h1_batch_identity')
            require(len(runs)==1 and runs[0]['id']==config['reserved_run_id'] and runs[0]['body']['command_id']==config['command_id'] and not runs[0]['body']['attempts'],'h1_run')
            require(batch['head'] is None or type(batch['head']) is list and len(batch['head'])==2 and all(valid_id(i) for i in batch['head']),'h1_head')
            prepared={(r['command_id'],r['blob_id']) for r in cmd['events'][0]['payload']['stage_refs']}
            refs=[]
            for source in batch['artifact_sources']:
                require(type(source) is dict and set(source)=={'artifact_id','stage_ref'} and valid_id(source['artifact_id']),'h1_artifact_source')
                shape(source['stage_ref'],'StageRef',profile=E1)
                refs.append((source['stage_ref']['command_id'],source['stage_ref']['blob_id']))
            require(len(refs)==len(set(refs)) and set(refs)==prepared,'h1_artifact_source_inventory')
            expected=[dict(artifact_id=s['artifact_id'],stage_ref=s['stage_ref']) for s in batch['artifact_sources']]
            expected.append(dict(artifact_id=a['plan_artifact_id'],stage_ref=dict(command_id=config['command_id'],blob_id=a['plan_blob_id'])))
            require(encode(plan['promotions'])==encode(expected),'h1_plan_promotions')
            require(plan['candidate_outcome'] in ('valid','blocked','rejected') and type(plan['admission']) is dict and type(plan['diagnostics']) is list,'h1_plan_result')
            for error in plan['diagnostics']:shape(error,'Error',profile=E1)
        except S02Error as exc:
            if exc.error['stage']=='persistence':raise
            raise storage_error('Invalid H1 sealed plan: '+exc.error['message']) from exc
        except (KeyError,TypeError,ValueError) as exc:raise storage_error('Malformed H1 sealed plan; no rebuild performed') from exc

    def context(self,cmd,state,config):
        context=state['records'][config['source_context_id']]
        from .s01_adapter import verify_archive
        snapshot=verify_archive(context,state['records'],state['blobs'])
        base=state['records'].get(config['base_model_id']);aset=state['records'].get(config['base_analysis_set_id'])
        issues=[state['records'][i] for i in aset['body']['issue_ids']] if aset else []
        session=cmd['operation']['session_id']
        allowed={'source_context','artifact','run','model','analysis_set','issue','change'}
        require(all(r['type'] in allowed and (r['type']!='issue' or (not r['body']['answer_ids'] and r['body']['resolution_carry'] is None and r['body']['resolution_replacement'] is None))
                    for i,r in state['records'].items() if state['owners'][i]==session),'h1_history_out_of_scope')
        return dict(state=state,command=cmd,config=config,snapshot=snapshot,base_model=base,base_set=aset,issues=issues)

    def parent_context(self,c,state,parent,step):
        cmd=self.repo._command(c,parent)
        require(cmd is not None and cmd['state']=='finalized' and cmd['run']['body']['status']=='completed','h1_parent_completed')
        require(state['operation_profiles'][parent]==E1,'h1_parent_profile')
        run=cmd['run']['body'];model=run['result_model_id'] or run['base_model_id'];aset=run['result_analysis_set_id']
        if step=='bootstrap':
            require(cmd['operation']['request']['kind']=='start' and model is None and aset is None,'h1_bootstrap_parent')
            aliases={};task=None;completed=[]
        else:
            config,primary,raw=self.primary(cmd,state)
            require(config['step']==('bootstrap' if step==1 else step-1),'h1_step_order')
            found=self.checked_plan(cmd,state,config,primary,raw);require(found is not None,'h1_parent_plan')
            plan,_=found;aliases=deepcopy(plan['allocation']['aliases']);task=plan['admission']['mapping_task_key'];completed=plan['admission']['completed_steps']
            require(completed==list(range(1,step)),'h1_completed_step_pins')
            require(plan['batch']['head']==[model,aset],'h1_parent_published_plan')
        require(model is None or aset is not None,'h1_parent_pair')
        return cmd,dict(source_context_id=run['source_context_id'],base_model_id=model,base_analysis_set_id=aset,
            aliases=aliases,mapping_task_key=task,completed_steps=completed)

    def prepare(self,command_id,parent,step,raw,store_id):
        require(step=='bootstrap' or type(step) is int and 1<=step<=4,'h1_step')
        require((raw is None)==(step=='bootstrap'),'h1_mock_input')
        require(raw is None or type(raw) is bytes,'h1_raw_bytes')
        if raw is not None:cap('raw_bytes',len(raw))
        from .h1_recovery import reconcile
        reconcile(self.repo,store_id)
        expected_logical=[]
        def work(c):
            state=self.state(c);info=store_profiles.check(c,path=self.repo.path,writable=True)
            require(info['metadata']['store_id']==store_id and info['metadata']['origin_kind']=='fresh','h1_store_binding')
            parentcmd,pins=self.parent_context(c,state,parent,step)
            current=self.repo._command(c,command_id)
            config=dict(**profile_pins(),marker=CONFIG_MARKER,config_version=CONFIG_VERSION,
                command_id=command_id,session_id=parentcmd['operation']['session_id'],parent_command_id=parent,
                step=step,handler_version=HANDLER_VERSION,candidate_version=None if step=='bootstrap' else CANDIDATE_VERSION,
                execution_origin='local_code' if step=='bootstrap' else 'synthetic_mock',store_id=store_id,
                limits_version=LIMITS_VERSION,limits=DEFAULTS,limits_sha256=digest(encode(DEFAULTS)),
                input=None if raw is None else dict(sha256=digest(raw),byte_length=len(raw),media_type='application/json'),**pins)
            expected_logical[:]=[deepcopy(config)]
            if current:
                old,_,oldraw=self.primary(current,state)
                require(encode(logical(old))==encode(config) and (raw is None or raw==oldraw['bytes']),'h1_prepare_intent_conflict')
                return current
            heads=c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(config['session_id'],)).fetchone()
            require(tuple(heads)==(config['base_model_id'],config['base_analysis_set_id']),'h1_parent_head_stale')
            fresh=self.fresh(state);config.update(reserved_run_id=fresh(),started_at=self.repo._clock())
            config['intent_sha256']=digest(encode(logical(config)))
            operation=dict(command_id=command_id,session_id=config['session_id'],parent_command_id=parent,reserved_run_id=config['reserved_run_id'],
                request=dict(kind='work',source_context_id=config['source_context_id'],base_model_id=config['base_model_id'],base_analysis_set_id=config['base_analysis_set_id'],scope=None,config_artifact_id=None))
            temporary=dict(operation=operation)
            self.context(temporary,state,config)
            from .s01_adapter import verify_archive
            context=state['records'][config['source_context_id']];snapshot=verify_archive(context,state['records'],state['blobs'])
            cap('obligations',len(inventory(snapshot)));cap('config_bytes',len(encode(config)))
            c.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?)',(command_id,operation['session_id'],parent,operation['reserved_run_id'],encode(operation['request']).decode('ascii'),digest(encode(operation['request'])),E1))
            stages=[staged(command_id,fresh(),'config',encode(config))]
            if raw is not None:stages.append(staged(command_id,fresh(),'llm_response',raw))
            self.repo._put_stages(c,command_id,stages)
            self.repo._put_event(c,self.repo._event(c,command_id,'prepared',dict(stage_refs=[dict(command_id=command_id,blob_id=s['blob_id']) for s,_ in stages],attempt_id=None)))
            return self.repo._command(c,command_id)
        def probe():
            loaded=self.load(command_id)
            if loaded is None:return None
            # Re-enter the guarded comparison; never accept mere ID existence.
            cfg=loaded['config']
            require(expected_logical and encode(logical(cfg))==encode(expected_logical[0]) and cfg['parent_command_id']==parent and cfg['step']==step and cfg['store_id']==store_id and
                    (raw is None if cfg['input'] is None else raw==loaded['raw']['bytes']),'h1_prepare_probe_intent')
            return loaded['command']
        return self.repo._write(work,probe)

    def load(self,command_id):
        with self.repo._read() as c:
            state=self.state(c);cmd=self.repo._command(c,command_id)
            if cmd is None:return None
            config,primary,raw=self.primary(cmd,state,execute=cmd['state']!='finalized')
            view=self.context(cmd,state,config);view.update(primary=primary,raw=raw)
            row=c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(config['session_id'],)).fetchone()
            view['current_head']=list(row)
            return view

    def materialize(self,plan,planraw,state):
        records=deepcopy(plan['batch']['records']);blobs={}
        for source in plan['batch']['artifact_sources']:
            ref=source['stage_ref'];blobs[source['artifact_id']]=state['stages'][ref['command_id'],ref['blob_id']]['bytes']
        allocation=plan['allocation'];aid=allocation['plan_artifact_id'];rid=plan['bindings']['reserved_run_id']
        records.append(artifact(aid,'config',planraw,rid,allocation['created_at']));blobs[aid]=planraw
        return records,blobs

    def seal(self,command_id,plan):
        planraw=encode(plan);cap('plan_bytes',len(planraw))
        def work(c):
            state=self.state(c);cmd=self.repo._command(c,command_id);require(cmd is not None,'h1_prepared_command')
            if cmd['state']=='finalized':return dict(finalized=cmd['run'])
            config,primary,raw=self.primary(cmd,state)
            existing=self.checked_plan(cmd,state,config,primary,raw)
            if existing:return dict(plan=existing[0],stage=existing[1])
            self.validate_plan(plan,cmd,config,primary,raw)
            require(set(plan)==PLAN_KEYS and plan['marker']==PLAN_MARKER and plan['plan_version']==PLAN_VERSION,'h1_plan_envelope')
            require(all(plan[k]==v for k,v in profile_pins().items()),'h1_plan_profile')
            require(encode(plan['bindings'])==encode(self.bindings(config,primary,raw)),'h1_plan_bindings')
            bid=plan['allocation']['plan_blob_id'];stage=staged(command_id,bid,'config',planraw)
            self.repo._put_stages(c,command_id,[stage])
            self.repo._put_event(c,self.repo._event(c,command_id,'log',dict(message='H1 immutable work plan sealed')))
            # Detached whole-graph preflight includes the exact promoted plan.
            state=self.state(c);records,blobs=self.materialize(plan,planraw,state)
            run=next(r for r in records if r['id']==cmd['operation']['reserved_run_id'])
            conflict=self.repo._base_error(c,cmd['operation'])
            if conflict:
                records=[r for r in records if r['type'] in ('run','artifact')]
                run['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=[conflict.error])
            require(not (set(r['id'] for r in records)&state['records'].keys()),'h1_plan_fresh_records')
            for r in records:
                state['records'][r['id']]=r;state['owners'][r['id']]=config['session_id'];state['record_profiles'][r['id']]=E1
            state['blobs'].update(blobs)
            projection=self.repo._event(c,command_id,'finalized',dict(run_id=run['id'],promotions=plan['promotions']))
            state['events'][command_id,projection['event_id']]=projection
            validate_graph(**state,reviews=self.repo._reviews)
            return dict(plan=plan,stage={**stage[0],'bytes':planraw})
        def probe():
            view=self.load(command_id)
            if view['command']['state']=='finalized':return dict(finalized=view['command']['run'])
            found=self.checked_plan(view['command'],view['state'],view['config'],view['primary'],view['raw'])
            return dict(plan=found[0],stage=found[1]) if found else None
        return self.repo._write(work,probe)
