"""Fresh full-source draft orchestration. No synthetic authority or human review."""
from base64 import b64encode, b64decode
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
import fcntl
import os
import time
from uuid import uuid4

from dacn_s01.repository import Repository as S01Repository
from dacn_s01.service import Service as S01Service
from .codec_boundary import encode, decode
from .errors import require, storage_error, S02Error
from .repository import Repository, record, digest, timestamp
from .service import staged, artifact
from .local_io import check_store, writable, read_receipt, write_receipt
from .local_journal import Journal, LIMITS, _regular
from .local_work import LocalWork, identity, ref, CONFIG, HANDLER
from .local_prompts import render_compact
from .h1_store import profile_pins
from . import __version__
from .local_transport import Exchange, VERSION as TRANSPORT_VERSION
from .s01_adapter import intake, verify_archive


class LocalService:
    def __init__(self, settings, provider=None, *, _hook=None, _repository_options=None):
        check_store(settings)
        self.settings=settings
        self.repo=Repository(settings.state/'s02.sqlite3',timeout=settings.timeout/1000,**(_repository_options or {}))
        self.provider=provider
        self.hook=_hook or (lambda point:None)
        self.store=LocalWork(self.repo)

    @contextmanager
    def lock(self):
        path=writable(self.settings,self.settings.state/'local-execution.lock')
        _regular(path)
        fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise storage_error('Local execution in progress; no second sender')
            yield
        finally:os.close(fd)

    def journal(self):
        info=self.repo.store_info()['metadata']
        require(info['origin_kind']=='fresh','local_fresh_store_required')
        return Journal(writable(self.settings,self.settings.state/'local-journal.sqlite3'),info['store_id'])

    def analyze(self, *, receipt, store_key, input_path=None, s01_run_id=None, expected_snapshot=None):
        require(store_key in self.settings.stores,'local_s01_store_key')
        require((input_path is None)!=(s01_run_id is None),'local_one_source')
        require(s01_run_id is None or expected_snapshot is not None,'local_selected_snapshot_required')
        require(self.provider is not None,'local_provider_required')
        self.repo.assert_writable()
        with self.lock():
            journal=self.journal()
            if not journal.path.exists():
                # Only explicit analyze may initialize, and never if local work already exists.
                with self.repo._read() as c:
                    require(not c.execute("SELECT 1 FROM staged_blobs WHERE purpose='config' AND CAST(bytes AS TEXT) LIKE '%s02-local-%' LIMIT 1").fetchone(),'local_missing_journal_not_recreated')
                journal.initialize()
            prior=journal.flow()
            store_id=journal.store_id
            if Path(receipt).exists():root=read_receipt(self.settings,receipt,store_id=store_id)['command_id']
            else:
                require(prior is None,'local_campaign_already_bound_use_original_receipt')
                root=str(uuid4());write_receipt(self.settings,receipt,root,store_id=store_id)
            raw=Path(input_path).read_bytes() if input_path is not None else None
            source=dict(store_key=store_key,s01_path=str(self.settings.stores[store_key]),input_b64=b64encode(raw).decode() if raw is not None else None,input_sha256=digest(raw) if raw is not None else None,selected_run_id=s01_run_id,expected_snapshot=expected_snapshot)
            if prior:
                require(prior['root']==root and prior['source']==source,'local_flow_intent_conflict')
            else:
                prior=dict(marker='s02-local-flow/1',root=root,store_id=store_id,source=source,s01_run_id=s01_run_id or str(uuid4()),created_at=timestamp(),provider_config=self.provider.configuration())
                journal.flow(prior)
            return self._resume(prior,journal)

    def resume(self, *, receipt):
        with self.lock():
            journal=self.journal();flow=journal.flow()
            root=read_receipt(self.settings,receipt,store_id=journal.store_id)['command_id']
            require(flow is not None and flow['root']==root,'local_resume_flow_receipt')
            return self._resume(flow,journal)

    def _intake(self, flow, journal):
        root=flow['root'];source=flow['source']
        existing=self.repo.get_command(root)
        if existing is not None and existing['state']=='finalized':
            frozen=decode(self.repo.get_stage(root,ref(root,'config')['blob_id'])['bytes'])
            require(frozen['marker']=='s02-local-intake/1' and frozen['flow']==flow,'local_finalized_intake_binding')
            return None
        s01=S01Repository(source['s01_path'])
        require(self.settings.stores.get(source['store_key'])==Path(source['s01_path']),'local_s01_path_changed')
        s01.verify();env=s01.get_run(flow['s01_run_id'])
        if env is None and source['input_b64'] is not None:
            if not journal.claim_s01():
                return self.blocked(root,'S01 outcome unknown; lookup original run only, never resubmit',status='interrupted')
            self.hook('after_s01_claim')
            raw=b64decode(source['input_b64']);require(digest(raw)==source['input_sha256'],'local_s01_input_hash')
            env=S01Service(s01).submit(raw,dict(mode='create',spec_id=None,base_revision=None),run_id=flow['s01_run_id'])
            self.hook('after_s01_submit')
        if env is None:return self.blocked(root,'Selected S01 run not found',status='not_found')
        if env['status']!='validated':return self.blocked(root,'S01 rejected/failed; no LLM call',status='rejected',extra=dict(s01_envelope=env))
        selected=intake(source['s01_path'],flow['s01_run_id'],source['expected_snapshot'])
        snap=selected.envelope['snapshot'];session=identity(root,'session');rid=identity(root,'intake-run');ctxid=identity(root,'source-context');now=flow['created_at']
        config=encode(dict(**profile_pins(),marker='s02-local-intake/1',flow=flow))
        op=dict(command_id=root,session_id=session,parent_command_id=None,reserved_run_id=rid,request=dict(kind='start',store_key=source['store_key'],s01_run_id=flow['s01_run_id'],expected_snapshot_id=source['expected_snapshot']))
        cmd=self.repo.get_command(root)
        if cmd is None:self.repo.prepare(op,session_spec=snap['spec_id'],staged=[staged(root,ref(root,'config')['blob_id'],'config',config)])
        else:
            require(cmd['operation']==op and self.repo.get_stage(root,ref(root,'config')['blob_id'])['bytes']==config,'local_intake_recovery_pin')
            if cmd['state']=='finalized':return None
        self.hook('after_intake_prepare')
        records=[];blobs={}
        def archive(label,purpose,raw,producer=None):
            aid=identity(root,label);records.append(artifact(aid,purpose,raw,producer,now));blobs[aid]=raw;return aid
        env_id=archive('envelope','s01_envelope',selected.envelope_bytes)
        source_id=archive('source','s01_run_source',selected.run_source)
        origin_id=source_id if env['run']['source']['source_id']==snap['origin_source_id'] else archive('origin','s01_origin_source',selected.origin_source)
        schema_id=archive('schema','schema',selected.schema);config_id=archive('config','config',config,rid)
        records.append(record('source_context',ctxid,dict(store_key=source['store_key'],s01_run_id=flow['s01_run_id'],snapshot_id=snap['snapshot_id'],envelope_artifact_id=env_id,run_source_artifact_id=source_id,origin_source_artifact_id=origin_id,schema_artifact_id=schema_id),now))
        records.append(record('run',rid,dict(mode='live',source_context_id=ctxid,config_artifact_id=config_id,base_model_id=None,base_analysis_set_id=None,command_id=root,result_model_id=None,result_analysis_set_id=None,steps=[],status='completed',started_at=now,completed_at=now,attempts=[],errors=[]),now))
        self.repo.finalize(root,records,blobs=blobs,promotions=[dict(artifact_id=config_id,stage_ref=ref(root,'config'))])
        self.hook('after_intake_finalize')
        return None

    @staticmethod
    def blocked(command,reason,status='blocked',extra=None):
        return dict(command_id=command,status=status,record_ids=[],errors=[],result=dict(semantic_status='unreviewed_draft',reason=reason,**(extra or {})))

    def config(self, flow, step, provider_pin=None):
        root=flow['root'];command=identity(root,'step:'+str(step));parent=root if step==0 else identity(root,'step:'+str(step-1))
        with self.repo._read() as c:
            state=self.store.state(c);parentcmd=self.repo._command(c,parent);run=parentcmd['run']['body']
            require(run['status']=='completed','local_parent_eligible')
            source_id=run['source_context_id'];source=state['records'][source_id];snapshot=verify_archive(source,state['records'],state['blobs'])
            mid=run['result_model_id'] or run['base_model_id'];asid=run['result_analysis_set_id']
            model=state['records'].get(mid);aset=state['records'].get(asid)
            aliases={};task=None;completed=[]
            if step:
                view=self.store.view(c,parent);plan=self.store.checked_plan(view)
                aliases=plan['result']['aliases'];task=plan['result']['admission']['mapping_task_key'];completed=plan['result']['admission']['completed_steps']
            cfg=dict(**profile_pins(),marker=CONFIG,handler=HANDLER,package_version=__version__,transport_version=TRANSPORT_VERSION,adapter_version='ollama-local/1',store_id=flow['store_id'],campaign_id=root,command_id=command,session_id=parentcmd['operation']['session_id'],parent_command_id=parent,reserved_run_id=identity(command,'run'),attempt_id=identity(command,'attempt') if step else None,started_at=timestamp(),step=step,source_context_id=source_id,snapshot_id=snapshot['snapshot_id'],source_sha256=digest(state['blobs'][source['body']['envelope_artifact_id']]),base_model_id=mid,base_analysis_set_id=asid,base_model_sha256=digest(encode(model)) if model else None,base_set_sha256=digest(encode(aset)) if aset else None,aliases=aliases,mapping_task_key=task,completed_steps=completed,limits=LIMITS,provider=provider_pin,execution_origin=self.provider.origin if step else 'local_code',context_bound=None,template_pin=None,grant=None)
            prompt=b'';request=b''
            if step:
                # Entire source/model/Issues/allowlist; no truncation to fit context.
                context=dict(snapshot=snapshot,model=model,issues=[state['records'][q] for q in aset['body']['issue_ids']],aliases=aliases)
                rendered=render_compact(step,context);prompt=rendered['messages_bytes']
                cfg['template_pin']=dict(version=rendered['version'],template_version=rendered['template_version'],hashes=rendered['template_sha256'])
                bound=self.provider.bound(rendered['messages']);cfg['context_bound']=bound
                request=encode(dict(model=provider_pin['model'],messages=rendered['messages'],stream=False,format='json',options=dict(num_ctx=LIMITS['num_ctx'],num_predict=LIMITS['num_predict'],temperature=0,seed=0)))
                require(len(request)<=LIMITS['body_bytes'],'local_request_cap')
                cfg['grant']=dict(version='local-draft-grant/1',store_id=flow['store_id'],campaign_id=root,source_context_id=source_id,snapshot_id=snapshot['snapshot_id'],source_sha256=cfg['source_sha256'],endpoint=provider_pin['endpoint'],model=provider_pin['model'],model_digest=provider_pin['model_digest'],steps=[1,2,3,4],limits_sha256=digest(encode(LIMITS)),purpose='draft_analysis')
            cfg.update(request_sha256=digest(request),prompt_sha256=digest(prompt))
            return cfg,prompt,request

    def _resume(self, flow, journal):
        failure=self._intake(flow,journal)
        if failure:return failure
        for step in range(5):
            command=identity(flow['root'],'step:'+str(step))
            cmd=self.repo.get_command(command)
            if cmd and cmd['state']=='finalized':
                result=self.store.report(command)
                if result['status']!='completed':return result
                continue
            work=journal.get(command)
            if work is None:
                if step:
                    require(self.provider is not None,'local_pending_provider_required')
                    require(self.provider.configuration()==flow['provider_config'],'local_provider_config_changed')
                    pin=self.provider.pin()
                else:pin=None
                cfg,prompt,request=self.config(flow,step,pin)
                journal.reserve(cfg,request,prompt);work=journal.get(command)
                self.hook('after_reserve')
            cfg=decode(work['config'])
            self.store.prepare(cfg,work['prompt'],work['request']);self.hook('after_prepare')
            if step and cfg['context_bound']['eligible']:
                if work['capture'] is not None:
                    self.store.capture(command,decode(work['capture']),work['body'])
                elif work['claimed_ns'] is not None:
                    # Lock excludes an active sender. After process death outcome is unknown.
                    pass
                else:
                    require(self.provider is not None and self.provider.configuration()==flow['provider_config'],'local_dispatch_provider')
                    require(self.provider.pin()==cfg['provider'],'local_dispatch_model_pin')
                    require(self.repo.heads(cfg['session_id'])==(cfg['base_model_id'],cfg['base_analysis_set_id']), 'local_dispatch_base_current')
                    claim_clock=time.monotonic();require(journal.claim(command),'local_dispatch_claim_lost');self.hook('after_claim')
                    self.store.dispatch(command);self.hook('after_intent')
                    remaining=LIMITS['timeout_seconds']-(time.monotonic()-claim_clock)
                    if remaining<=0:return self.blocked(command,'Claim deadline exhausted; outcome unknown, no resend',status='interrupted')
                    try:exchange=self.provider.send(work['request'],remaining)
                    except (OSError,S02Error,ValueError):
                        exchange=Exchange(None,(),b'',False,False,'provider_failed_after_claim',max(0,int((time.monotonic()-claim_clock)*1000)))
                    self.hook('after_http')
                    # No parsing here. Raw and metadata commit before outer/candidate decode.
                    meta=asdict(exchange);body=meta.pop('body');meta['headers']=[list(pair) for pair in meta['headers']]
                    meta.update(**profile_pins(),command_id=command,request_sha256=cfg['request_sha256'],body_sha256=digest(body),model_pin_after=None)
                    try:meta['model_pin_after']=self.provider.pin()
                    except (OSError,S02Error,ValueError):pass
                    journal.capture(command,meta,body);self.hook('after_capture')
                    self.store.capture(command,meta,body);self.hook('after_response_event')
            expected=journal.get(command)
            require(expected['config']==encode(cfg),'local_pending_journal_config')
            original=self.repo._hook
            def guard(point,connection):
                original(point,connection)
                if point in ('after_begin','before_finalize_insert','before_commit'):
                    require(journal.get(command)==expected,'local_publication_journal_changed')
            self.repo._hook=guard
            try:
                self.store.seal(command);self.hook('after_seal')
                self.hook('before_publish');result=self.store.publish(command);self.hook('after_publish')
            finally:self.repo._hook=original
            if result['status']!='completed':return result
        return result

    def report(self, *, receipt):
        info=self.repo.store_info()['metadata'];root=read_receipt(self.settings,receipt,store_id=info['store_id'])['command_id']
        # Finalized report needs only checked DB2 artifacts, never journal/provider.
        for step in reversed(range(5)):
            cmd=identity(root,'step:'+str(step));found=self.repo.get_command(cmd)
            if found:return self.store.report(cmd)
        found=self.repo.get_command(root)
        return self.blocked(root,'No local step prepared',status='not_prepared',extra=dict(intake=found))
