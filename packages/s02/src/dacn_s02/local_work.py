"""LP-01 fresh draft handler and immutable plans over unchanged E1/DB2."""
from copy import deepcopy
from uuid import UUID, uuid5

from .codec_boundary import encode, decode
from .errors import require, S02Error
from .repository import record, digest
from .service import staged, artifact
from .h1_store import WorkStore, profile_pins
from .h1_builders import Builder
from .h1_candidates import parse
from .h1_limits import Budget, bounded_decode, cap
from .validation import integer, validate_record, time as valid_time
from .profiles import E1
from .profile_graph import validate_graph
from .s01_adapter import verify_archive

HANDLER = 's02-local-draft/0.13.0a1'
CONFIG = 's02-local-config/1'
PLAN = 's02-local-plan/1'


def identity(command, label):
    return str(uuid5(UUID(command), label))


def ref(command, name):
    return dict(command_id=command, blob_id=identity(command, 'stage:' + name))


class DraftBuilder(Builder):
    """Only code-owned provenance changes; candidate content is untouched."""
    def issue(self, *args, **kwargs):
        value = super().issue(*args, **kwargs)
        value['body']['reason'] = 'Local draft: source facts and unrepresented work remain visible'
        value['body']['trace']['rationale'] = 'Code draft bookkeeping; not business confirmation'
        return value

    def finish(self, *args, **kwargs):
        value = super().finish(*args, **kwargs)
        for item in value['records']:
            if item['type'] == 'change':
                item['body']['reason'] = 'Local provider draft; no source change or business confirmation'
                for op in item['body']['operations']:
                    if op['reason'] == 'H1 candidate proposal': op['reason'] = 'Local draft candidate proposal'
                    elif op['reason'] == 'H1 current trace/context': op['reason'] = 'Local draft current trace/context'
        return value


def outer(cfg, meta, raw):
    """Only after durable capture. No string stripping or silent output repair."""
    returned = None
    usage = None
    candidate = None
    error = None
    try:
        require(meta['complete_body'] and meta['error'] is None and meta['status'] == 200, 'local_complete_http_200')
        headers = dict(meta['headers'])
        require(headers.get('content-encoding', 'identity').lower() == 'identity', 'local_compression_not_supported')
        value = bounded_decode(raw, Budget())
        require(type(value) is dict, 'local_outer_object')
        returned = value.get('model') if type(value.get('model')) is str and value['model'].strip() else None
        require(returned == cfg['provider']['model'], 'local_returned_model')
        require(value.get('done') is True and value.get('done_reason') == 'stop', 'local_generation_complete')
        msg = value.get('message')
        require(type(msg) is dict and msg.get('role') == 'assistant' and type(msg.get('content')) is str, 'local_assistant_content')
        require(not msg.get('tool_calls') and not msg.get('thinking') and not value.get('thinking'), 'local_no_tools_thinking')
        require(meta['model_pin_after'] == cfg['provider'], 'local_model_pin_changed')
        counts = [value.get(k) for k in ('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count')]
        if all(integer(None,x) and x >= 0 for x in counts):
            usage = dict(input_tokens=counts[0], cached_input_tokens=counts[1], output_tokens=counts[2], cost_usd=None, price_source=None)
        if integer(None,value.get('prompt_eval_count')):
            require(value['prompt_eval_count'] <= cfg['context_bound']['input_upper_bound'], 'local_token_bound_violated')
        require(value.get('eval_count') is None or integer(None,value['eval_count']) and 0 <= value['eval_count'] <= cfg['limits']['num_predict'], 'local_output_cap')
        candidate = msg['content'].encode('utf-8')
    except (S02Error, UnicodeError) as exc:
        error = exc.error if isinstance(exc, S02Error) else S02Error('INVALID_JSON','parse','Invalid response Unicode').error
    return candidate, returned, usage, error


class LocalWork:
    def __init__(self, repo):
        self.repo = repo
        self.helpers = WorkStore(repo)

    def state(self, c):
        return self.helpers.state(c)

    def view(self, c, command):
        state = self.state(c)
        cmd = self.repo._command(c, command)
        require(cmd is not None, 'local_command_exists')
        stages = {name: state['stages'].get((command, ref(command, name)['blob_id']))
                  for name in ('config', 'prompt', 'request', 'capture', 'response', 'plan')}
        require(stages['config'] is not None, 'local_config_exists')
        cfg = decode(stages['config']['bytes'])
        require(cfg['marker'] == CONFIG and cfg['handler'] == HANDLER and cfg['command_id'] == command, 'local_handler_config')
        require(cfg['reserved_run_id'] == cmd['operation']['reserved_run_id'] and cfg['session_id'] == cmd['operation']['session_id'], 'local_config_operation')
        request = cmd['operation']['request']
        require(all(cfg[k] == request[k] for k in ('source_context_id','base_model_id','base_analysis_set_id')), 'local_base_config')
        helper_cfg = dict(cfg, step='bootstrap' if cfg['step'] == 0 else cfg['step'])
        view = self.helpers.context(cmd, state, helper_cfg)
        context = state['records'][cfg['source_context_id']]
        require(digest(state['blobs'][context['body']['envelope_artifact_id']]) == cfg['source_sha256'], 'local_source_pin')
        require(view['snapshot']['snapshot_id'] == cfg['snapshot_id'], 'local_snapshot_pin')
        for key in ('base_model', 'base_set'):
            require((digest(encode(view[key])) if view[key] else None) == cfg[key + '_sha256'], 'local_base_hash')
        if cfg['step']:
            for name in ('prompt','request'):
                require(stages[name] is not None and digest(stages[name]['bytes']) == cfg[name + '_sha256'], 'local_prepared_input_hash')
        view.update(cfg=cfg, stages=stages)
        view['current_head'] = list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone())
        return view

    def prepare(self, cfg, prompt, request):
        command = cfg['command_id']
        items = [staged(command, ref(command,'config')['blob_id'], 'config', encode(cfg))]
        if cfg['step']:
            items += [staged(command, ref(command,'prompt')['blob_id'], 'prompt', prompt), staged(command, ref(command,'request')['blob_id'], 'llm_request', request)]
        def write(c):
            current = self.repo._command(c, command)
            if current:
                view = self.view(c, command)
                require(encode(view['cfg']) == encode(cfg), 'local_prepare_conflict')
                return command
            parent = self.repo._command(c, cfg['parent_command_id'])
            require(parent is not None and parent['state']=='finalized' and parent['run']['body']['status']=='completed', 'local_parent_completed')
            require(parent['operation']['session_id'] == cfg['session_id'], 'local_parent_session')
            if cfg['step']:
                prior = self.view(c, cfg['parent_command_id'])
                p = self.checked_plan(prior)
                require(prior['cfg']['step'] == cfg['step']-1 and p['result']['status']=='completed', 'local_step_order')
                require(cfg['aliases'] == p['result']['aliases'] and cfg['mapping_task_key'] == p['result']['admission']['mapping_task_key'], 'local_parent_metadata')
            else:
                require(parent['operation']['request']['kind']=='start', 'local_fresh_intake')
            head = list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone())
            require(head == [cfg['base_model_id'],cfg['base_analysis_set_id']], 'local_prepare_stale')
            op = dict(kind='work', source_context_id=cfg['source_context_id'],base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],scope=None,config_artifact_id=None)
            c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?)',(command,cfg['session_id'],cfg['parent_command_id'],cfg['reserved_run_id'],encode(op).decode('ascii'),digest(encode(op)),E1))
            self.repo._put_stages(c,command,items)
            self.repo._put_event(c,self.repo._event(c,command,'prepared',dict(stage_refs=[dict(command_id=command,blob_id=s['blob_id']) for s,_ in items],attempt_id=cfg['attempt_id'] if cfg['step'] else None)))
            self.view(c,command)
            return command
        return self.repo._write(write,lambda: command if self.repo.get_command(command) else None)

    def dispatch(self, command):
        def write(c):
            view=self.view(c,command);cmd=view['command']
            require(cmd['state']=='prepared','local_dispatch_once')
            event=cmd['events'][0]
            self.repo._put_event(c,self.repo._event(c,command,'dispatch_intent',dict(prepared_event=dict(command_id=command,event_id=event['event_id']),transport_attempt=1)))
            return True
        return self.repo._write(write,lambda: any(e['kind']=='dispatch_intent' for e in self.repo.get_command(command)['events']))

    def capture(self, command, meta, raw):
        def write(c):
            view=self.view(c,command);cfg=view['cfg'];existing=view['stages']['capture']
            if existing:
                require(existing['bytes']==encode(meta) and view['stages']['response']['bytes']==raw,'local_capture_db_immutable')
                return
            require(view['command']['state']=='dispatch_unknown','local_capture_dispatched')
            require(meta['command_id']==command and meta['request_sha256']==cfg['request_sha256'] and meta['body_sha256']==digest(raw),'local_capture_inputs')
            self.repo._put_stages(c,command,[staged(command,ref(command,'capture')['blob_id'],'config',encode(meta)),staged(command,ref(command,'response')['blob_id'],'llm_response',raw,'application/octet-stream')])
            if meta['complete_body'] and meta['error'] is None:
                _,returned,usage,_=outer(cfg,meta,raw)
                payload=dict(response=ref(command,'response'),http_status=meta['status'],safe_headers={k:v for k,v in meta['headers'] if k in ('content-type','retry-after')},requested_model=cfg['provider']['model'],returned_model=returned,provider_response_id=None,usage=usage,elapsed_ms=meta['elapsed_ms'])
                self.repo._put_event(c,self.repo._event(c,command,'response_received',payload))
            else:
                self.repo._put_event(c,self.repo._event(c,command,'log',dict(message='LP-01 incomplete capture preserved; no response_received')))
        def probe():
            found=self.repo.get_stage(command,ref(command,'capture')['blob_id'])
            return True if found else None
        return self.repo._write(write,probe)

    def build(self, view):
        cfg=view['cfg'];command=cfg['command_id'];count=0
        now=decode(view['stages']['plan']['bytes'])['sealed_at'] if view['stages']['plan'] else max(cfg['started_at'],self.repo._clock())
        require(valid_time(now) and now>=cfg['started_at'],'local_plan_time')
        def fresh():
            nonlocal count
            count+=1
            return identity(command,'allocation:'+str(count))
        candidate=None;error=None;returned=None;usage=None
        meta=decode(view['stages']['capture']['bytes']) if view['stages']['capture'] else None
        received=next((e['payload'] for e in view['command']['events'] if e['kind']=='response_received'),None)
        dispatched=any(e['kind']=='dispatch_intent' for e in view['command']['events'])
        result=dict(records=[],head=None,status='interrupted',aliases=cfg['aliases'],admission={})
        if not cfg['step']:
            result=DraftBuilder(view,fresh,now,Budget()).bootstrap()
        elif not cfg['context_bound']['eligible']:
            error=S02Error('LOCAL_CONTEXT_BLOCKED','schema','Tokenizer proof or context capacity unavailable; no dispatch or truncation').error
        elif received:
            candidate,returned,usage,error=outer(cfg,meta,view['stages']['response']['bytes'])
            if error is None:
                try:
                    value,linker=parse(candidate,cfg['step'],view['snapshot'],cfg['aliases'],fresh,Budget())
                    result=DraftBuilder(view,fresh,now,Budget()).analyze(value,linker)
                except S02Error as exc:
                    error=exc.error
                    result=dict(records=[],head=None,status='rejected',aliases=cfg['aliases'],admission={})
            if error is not None: result.update(status='rejected')
        else:
            error=S02Error('LOCAL_DISPATCH_UNKNOWN','persistence','Dispatch outcome unknown; never resend').error
        def compose(result,error):
            records=list(result['records']);blobs={};promotions=[];artifact_ids={}
            for name in ('config','prompt','request','capture','response'):
                stage=view['stages'][name]
                if stage is None: continue
                aid=identity(command,'artifact:'+name);artifact_ids[name]=aid
                records.append(artifact(aid,stage['purpose'],stage['bytes'],cfg['reserved_run_id'],now,stage['media_type']))
                promotions.append(dict(artifact_id=aid,stage_ref=ref(command,name)))
            attempts=[]
            if dispatched:
                attempts=[dict(id=cfg['attempt_id'],step=cfg['step'],base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],prompt_artifact_id=artifact_ids['prompt'],request_artifact_id=artifact_ids['request'],response_artifact_id=artifact_ids.get('response') if received else None,provider='ollama-local',requested_model=cfg['provider']['model'],returned_model=received['returned_model'] if received else None,provider_response_id=None,transport_attempt=1,repair_round=0,status='unknown_outcome' if not received else 'invalid_output' if error else 'completed',usage=received['usage'] if received else None,elapsed_ms=meta['elapsed_ms'] if meta else 0)]
            run=record('run',cfg['reserved_run_id'],dict(mode='live',source_context_id=cfg['source_context_id'],config_artifact_id=artifact_ids['config'],base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],command_id=command,result_model_id=result.get('result_model_id'),result_analysis_set_id=result.get('result_analysis_set_id'),steps=[cfg['step']] if cfg['step'] else [],status=result['status'],started_at=now,completed_at=now,attempts=attempts,errors=[error] if error else []),now)
            records.append(run)
            promotions.append(dict(artifact_id=identity(command,'artifact:plan'),stage_ref=ref(command,'plan')))
            return dict(**profile_pins(),marker=PLAN,handler=HANDLER,sealed_at=now,config_sha256=digest(encode(cfg)),result=result,records=records,promotions=promotions,head=result['head'],allocation_count=count)
        plan=compose(result,error)
        if error is None:
            merged=dict(view['state']['records']);profiles=dict(view['state']['record_profiles'])
            for item in plan['records']:merged[item['id']]=item;profiles[item['id']]=E1
            try:
                for item in result['records']:
                    validate_record(item,merged,{view['snapshot']['snapshot_id']:view['snapshot']},events=view['state']['events'],stages=view['state']['stages'],commands=view['state']['commands'],owner_profile=E1,profile_map=profiles)
            except S02Error as exc:
                result=dict(records=[],head=None,status='rejected',aliases=cfg['aliases'],admission={})
                plan=compose(result,exc.error)
        return plan

    def checked_plan(self, view):
        stage=view['stages']['plan']
        require(stage is not None,'local_sealed_plan_required')
        plan=decode(stage['bytes'])
        require(encode(plan)==encode(self.build(view)),'local_sealed_reconstruction')
        return plan

    def materialize(self, view, plan):
        cfg=view['cfg'];command=cfg['command_id'];raw=encode(plan)
        records=deepcopy(plan['records']);blobs={}
        for name,stage in view['stages'].items():
            if name!='plan' and stage is not None:blobs[identity(command,'artifact:'+name)]=stage['bytes']
        aid=identity(command,'artifact:plan');blobs[aid]=raw
        records.append(artifact(aid,'config',raw,cfg['reserved_run_id'],plan['sealed_at']))
        return records,blobs

    def seal(self, command):
        def write(c):
            view=self.view(c,command)
            if view['stages']['plan']:
                return self.checked_plan(view)
            plan=self.build(view);raw=encode(plan);cap('plan_bytes',len(raw))
            self.repo._put_stages(c,command,[staged(command,ref(command,'plan')['blob_id'],'config',raw)])
            self.repo._put_event(c,self.repo._event(c,command,'log',dict(message='LP-01 immutable plan sealed')))
            # Validate detached actual batch including canonical Attempt/event boundary.
            state=self.state(c);records,blobs=self.materialize(view,plan)
            run=next(r for r in records if r['id']==view['cfg']['reserved_run_id'])
            conflict=self.repo._base_error(c,view['command']['operation'])
            if conflict:
                records=[r for r in records if r['type'] in ('run','artifact')]
                run['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=[conflict.error])
            for r in records:
                require(r['id'] not in state['records'],'local_fresh_record')
                state['records'][r['id']]=r;state['owners'][r['id']]=view['cfg']['session_id'];state['record_profiles'][r['id']]=E1
            state['blobs'].update(blobs)
            e=self.repo._event(c,command,'finalized',dict(run_id=run['id'],promotions=plan['promotions']))
            state['events'][command,e['event_id']]=e
            validate_graph(**state,reviews=self.repo._reviews)
            return plan
        return self.repo._write(write,lambda: self.load_plan(command))

    def load_plan(self, command):
        with self.repo._read() as c:
            view=self.view(c,command)
            return self.checked_plan(view) if view['stages']['plan'] else None

    def publish(self, command):
        with self.repo._read() as c:
            view=self.view(c,command);plan=self.checked_plan(view);records,blobs=self.materialize(view,plan)
        self.repo.finalize(command,records,blobs=blobs,promotions=plan['promotions'],head=plan['head'])
        return self.report(command)

    def report(self, command):
        with self.repo._read() as c:
            view=self.view(c,command);cmd=view['command'];cfg=view['cfg']
            if cmd['state']!='finalized':return dict(command_id=command,status='prepared',record_ids=[],errors=[],result=dict(phase=cmd['state'],semantic_status='unreviewed_draft'))
            plan=self.checked_plan(view);run=cmd['run'];body=run['body'];state=view['state']
            expected,blobs=self.materialize(view,plan)
            require(all(state['blobs'][aid]==raw for aid,raw in blobs.items()),'local_published_blobs')
            published=body['status'] in ('completed','blocked')
            for record_ in expected:
                if record_['type'] in ('model','change','issue','analysis_set') and body['status']=='stale':
                    require(record_['id'] not in state['records'],'local_stale_no_records');continue
                if record_['type']=='run' and body['status']=='stale':
                    other=deepcopy(record_);other['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=body['errors'])
                    require(other==run and len(body['errors'])==1 and body['errors'][0]['code'] in ('MODEL_CONFLICT','ANALYSIS_CONFLICT'),'local_stale_run')
                    continue
                require(state['records'][record_['id']]==record_,'local_published_records')
            pair=plan['head'] if published else None
            model=state['records'][pair[0]] if pair else None
            aset=state['records'][pair[1]] if pair else None
            issues=[state['records'][i] for i in aset['body']['issue_ids']] if aset else []
            return dict(command_id=command,status='blocked' if any(e['code']=='LOCAL_CONTEXT_BLOCKED' for e in body['errors']) else body['status'],record_ids=[r['id'] for r in expected if r['id'] in state['records']],errors=body['errors'],result=dict(phase='finalized',run_status=body['status'],context_bound=cfg['context_bound'],handler=HANDLER,execution_origin=cfg['execution_origin'],semantic_status='unreviewed_draft',run_id=run['id'],step=cfg['step'],completed_through=cfg['step'] if body['status']=='completed' else max(0,cfg['step']-1),result_pair=pair,current_head=view['current_head'],is_current=pair==view['current_head'],model=model,mappings=model['body']['mappings'] if model else [],issues=issues,aliases=plan['result']['aliases'],admission=plan['result']['admission'],attempts=body['attempts']))
