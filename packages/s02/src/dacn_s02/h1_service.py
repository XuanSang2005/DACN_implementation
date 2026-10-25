"""Sequential fresh-session H1 mock checkpoints. No arbitrary Record import."""
from copy import deepcopy
import time

from .codec_boundary import encode,decode
from .errors import S02Error
from .repository import record, digest
from .service import artifact
from .h1_store import WorkStore, PLAN_MARKER, PLAN_VERSION, profile_pins
from .h1_candidates import parse
from .h1_builders import Builder
from .h1_limits import Budget, cap
from .profiles import E1
from .validation import validate_record


class H1Service:
    def __init__(self, repository, *, _monotonic=time.monotonic, _hook=None):
        self.repo=repository;self.store=WorkStore(repository);self.clock=_monotonic
        self.hook=_hook or (lambda point:None)

    def prepare(self,command_id,parent_command_id,step,raw,store_id):
        self.hook('before_prepare')
        result=self.store.prepare(command_id,parent_command_id,step,raw,store_id)
        self.hook('after_prepare')
        if result['state']=='finalized':return self.report(command_id)
        return dict(command_id=command_id,status='prepared',record_ids=[],errors=[],
                    result=dict(phase='prepared',reserved_run_id=result['operation']['reserved_run_id']))

    def plan(self,view, fresh, result, now, errors=()):
        cfg=view['config'];cmd=cfg['command_id'];rid=cfg['reserved_run_id']
        sources=[];promotions=[];records=list(result.get('records',[]))
        for stage in [view['primary'],*([view['raw']] if view['raw'] else [])]:
            aid=fresh();ref=dict(command_id=cmd,blob_id=stage['blob_id'])
            records.append(artifact(aid,stage['purpose'],stage['bytes'],rid,now))
            sources.append(dict(artifact_id=aid,stage_ref=ref));promotions.append(dict(artifact_id=aid,stage_ref=ref))
        config_id=sources[0]['artifact_id'];pbid=fresh();paid=fresh()
        promotions.append(dict(artifact_id=paid,stage_ref=dict(command_id=cmd,blob_id=pbid)))
        status=result['status']
        run=record('run',rid,dict(mode='live' if cfg['step']=='bootstrap' else 'replay',source_context_id=cfg['source_context_id'],
            config_artifact_id=config_id,base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],
            command_id=cmd,result_model_id=result.get('result_model_id'),result_analysis_set_id=result.get('result_analysis_set_id'),
            steps=[] if cfg['step']=='bootstrap' else [cfg['step']],status=status,started_at=cfg['started_at'],completed_at=now,
            attempts=[],errors=list(errors)),cfg['started_at'])
        records.append(run)
        return dict(marker=PLAN_MARKER,plan_version=PLAN_VERSION,**profile_pins(),
            bindings=self.store.bindings(cfg,view['primary'],view['raw']),
            allocation=dict(plan_blob_id=pbid,plan_artifact_id=paid,created_at=now,aliases=result.get('aliases',cfg['aliases'])),
            batch=dict(records=records,artifact_sources=sources,head=result.get('head')),promotions=promotions,
            admission=result.get('admission',{}),candidate_outcome='valid' if status=='completed' else 'blocked' if status=='blocked' else 'rejected',diagnostics=list(errors))

    def resume(self,command_id,*,store_id=None):
        if store_id is not None:
            from .h1_recovery import reconcile
            reconcile(self.repo,store_id)
        view=self.store.load(command_id)
        if view is None:
            return dict(command_id=command_id,status='not_prepared',record_ids=[],errors=[],
                result=dict(phase='not_prepared',required_action='explicit prepare-work with parent/step/input/hash'))
        if view['command']['state']=='finalized':return self.report(command_id)
        found=self.store.checked_plan(view['command'],view['state'],view['config'],view['primary'],view['raw'])
        if found:plan,stage=found
        else:
            self.hook('before_build');fresh=self.store.fresh(view['state']);now=max(view['config']['started_at'],self.repo._clock())
            budget=Budget(self.clock);builder=Builder(view,fresh,now,budget)
            try:
                if view['config']['step']=='bootstrap':result=builder.bootstrap()
                else:
                    candidate,linker=parse(view['raw']['bytes'],view['config']['step'],view['snapshot'],view['config']['aliases'],fresh,budget)
                    result=builder.analyze(candidate,linker)
                plan=self.plan(view,fresh,result,now)
                merged={i:r for i,r in view['state']['records'].items() if view['state']['owners'][i]==view['config']['session_id']}
                profiles={i:view['state']['record_profiles'][i] for i in merged}
                for item in plan['batch']['records']:merged[item['id']]=item;profiles[item['id']]=E1
                for item in plan['batch']['records']:
                    budget.check()
                    validate_record(item,merged,{view['snapshot']['snapshot_id']:view['snapshot']},events=view['state']['events'],
                        stages=view['state']['stages'],commands=view['state']['commands'],owner_profile=E1,profile_map=profiles)
                budget.check();cap('plan_bytes',len(encode(plan)))
            except S02Error as exc:
                plan=self.plan(view,fresh,dict(status='rejected'),now,[exc.error])
            self.hook('before_seal')
            try:sealed=self.store.seal(command_id,plan)
            except S02Error as exc:
                if exc.error['stage']=='persistence':raise
                # A graph/build failure may be reported, never repaired into a
                # successful candidate. The failed seal transaction rolled back.
                failure=S02Error('H1_BUILD_FAILED','schema','Canonical H1 batch failed whole-graph validation',details={'cause':exc.error['code']})
                plan=self.plan(view,fresh,dict(status='failed'),now,[failure.error])
                sealed=self.store.seal(command_id,plan)
            self.hook('after_seal')
            if 'finalized' in sealed:return self.report(command_id)
            plan,stage=sealed['plan'],sealed['stage']
        self.hook('before_finalize')
        # Refresh checked bytes, not candidate/file/clock. The pair CAS remains
        # authoritative if a writer advanced either head since this plan.
        current=self.store.load(command_id)
        if current['command']['state']=='finalized':return self.report(command_id)
        records,blobs=self.store.materialize(plan,stage['bytes'],current['state'])
        self.repo.finalize(command_id,records,blobs=blobs,promotions=plan['promotions'],head=plan['batch']['head'])
        self.hook('after_finalize')
        return self.report(command_id)

    def report(self,command_id,*,progress=False):
        view=self.store.load(command_id)
        if view is None:
            return dict(command_id=command_id,status='not_prepared',record_ids=[],errors=[],result=dict(phase='not_prepared'))
        cmd=view['command'];cfg=view['config']
        if cmd['state']!='finalized':
            return dict(command_id=command_id,status='completed' if progress else 'prepared',record_ids=[],errors=[],
                result=dict(phase=cmd['state'],reserved_run_id=cmd['operation']['reserved_run_id'],execution_origin=cfg['execution_origin']))
        run=cmd['run'];b=run['body'];records=view['state']['records']
        pair=[b['result_model_id'] or b['base_model_id'],b['result_analysis_set_id']] if b['result_analysis_set_id'] else None
        model=records[pair[0]] if pair else None;aset=records[pair[1]] if pair else None
        issues=[records[i] for i in aset['body']['issue_ids']] if aset else []
        final=next(e for e in cmd['events'] if e['kind']=='finalized')
        artifact_ids=[p['artifact_id'] for p in final['payload']['promotions']]
        actual=[run['id'],*artifact_ids,*([pair[1]] if pair else []),*([b['result_model_id']] if b['result_model_id'] else [])]
        k=cfg['step'];steps=[*cfg['completed_steps'],k] if k!='bootstrap' and b['status'] in ('completed','blocked') else cfg['completed_steps']
        result=dict(phase='finalized',execution_origin=cfg['execution_origin'],semantic_status='synthetic_draft_not_reviewed',
            source_context_id=b['source_context_id'],snapshot_id=view['snapshot']['snapshot_id'],run_id=run['id'],run_status=b['status'],
            result_pair=pair,current_head=view['current_head'],is_current=pair==view['current_head'],completed_steps=steps,
            next_step=(1 if k=='bootstrap' else k+1 if k<4 else None) if b['status']=='completed' else None,
            model=model,mappings=model['body']['mappings'] if model else [],issues=issues,
            questions=[q for q in issues if q['body']['status']=='open' and q['body']['kind'] in ('business','quality_target')],
            holds=[q['id'] for q in issues if q['body']['status']=='open' and (q['body']['blocking']['element_ids'] or q['body']['blocking']['mapping_part_ids'])],
            artifacts=[dict(id=i,**records[i]['body']) for i in artifact_ids])
        # Only promoted metadata can describe the next input allowlist. Extra
        # logs/stages after finalization cannot change the authoritative outcome.
        result['next_aliases']={};result['plan_metadata']='not_used'
        if pair:
            for aid in artifact_ids:
                if aid==b['config_artifact_id'] or records[aid]['body']['purpose']!='config':continue
                try:
                    plan=decode(view['state']['blobs'][aid])
                    self.store.validate_plan(plan,cmd,cfg,view['primary'],view['raw'])
                    if plan['batch']['head']==pair:
                        result['next_aliases']=deepcopy(plan['allocation']['aliases']);result['plan_metadata']='checked_promoted'
                except S02Error:
                    result['plan_metadata']='unavailable_no_rebuild'
        return dict(command_id=command_id,status='completed' if progress else b['status'],record_ids=list(dict.fromkeys(actual)),
                    errors=[] if progress else b['errors'],result=result)


def exit_code(output):
    return {'completed':0,'prepared':0,'blocked':2,'rejected':2,'stale':2,'failed':3,'interrupted':3,'not_found':4,'not_prepared':5}.get(output['status'],3)
