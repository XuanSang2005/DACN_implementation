"""Real synthetic A2 DB histories, external reviews and C-only work controls."""
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
from dacn_s02.codec_boundary import encode
from dacn_s02.repository import Repository
from dacn_s02.h3_limits import Budget
from dacn_s02.h3_history import HistoryData
from dacn_s02.h3_review_io import LocalSyntheticHistoricalReviews
from dacn_s02.h3_policy import SemanticTrustContext
from dacn_s02.h3_continuation_authority import LocalSyntheticContinuationAuthority
from dacn_s02.h3_continuation_contracts import AUTHORITY
from dacn_s02.h3_continuation_service import ContinuationService
from dacn_s02.h3_continuation_store import ContinuationStore
from h3_c_fixtures import graph_case,request
from h3_b_fixtures import state_of
from h3_b_runtime_fixtures import BCase


def baseline(path,patch,branch='direct',other=False):
    Path(path).mkdir(parents=True,exist_ok=True)
    f,g=graph_case(path,patch,branch);repo=Repository(f.repo.path,reviews=g.reviews)
    # The controller's historical AS-only actions predate C. Persist through
    # Repository APIs; no importing a DB dump or deriving review trust from DB.
    for cid,op in g.commands.items():
        if repo.get_command(cid) is not None:continue
        repo.prepare(op);run=g.records[op['reserved_run_id']];aset=g.records[run['body']['result_analysis_set_id']]
        answers=[r for r in g.records.values() if r['type']=='answer' and r['body']['issue_id'] in aset['body']['changed_record_ids'] and repo.get_record(r['id']) is None]
        repo.finalize(cid,[run,aset,*[g.records[i] for i in aset['body']['changed_record_ids']],*answers],head=(g.model_id,aset['id']))
    repo.verify();controls=g.reviews
    if other:repo,controls=other_session(f,g)
    return SimpleNamespace(repo=repo,s01=f.s01,store_id=repo.store_info()['metadata']['store_id'],parent=list(g.commands)[-1],pair=[g.model_id,g.set_id],
        historical_entries=[dict(issue_id=i,reviewer=d.reviewer,assessment=d.assessment,dependency_sha256=d.dependency_sha256) for i,d in sorted(controls.items())])


class CCase:
    def __init__(self,path,source,*,advance=True):
        b=BCase(path,source);self.__dict__=b.__dict__;self.s01=source.s01;self.historical_entries=deepcopy(source.historical_entries)
        if not getattr(source,'c_ready',False):
            result=b.execute(*b.work());self.parent=b.parent;self.pair=b.pair
            assert result['status']=='blocked'
            if advance:
                result=self.execute(*self.work(step=1));assert result['result']['candidate_outcome']=='valid'

    repo=BCase.repo
    prepare=BCase.prepare
    execute=BCase.execute

    def descriptor(self):return SimpleNamespace(repo=self.repo(),s01=self.s01,store_id=self.store_id,parent=self.parent,pair=self.pair,historical_entries=self.historical_entries,c_ready=True)

    def service(self,authority=None,**kw):return ContinuationService(self.settings,historical_reviews=self.trust,authority=authority,**kw)

    def base(self):
        b=Budget();reg=LocalSyntheticHistoricalReviews.load(self.trust,b);state=state_of(reg.open_repository(self.db));h=HistoryData(**state,registry=reg.registry,store_id=self.store_id,budget=b)
        session=h._state['commands'][self.parent]['session_id'];return h.view(session,self.pair,self.pair)

    def work(self,*,step=2,mode='step',change=None,unknown=False,decision='allow',unit_ids=None,raw_suffix=b''):
        cfg,raw=request(self.base(),step=step,mode=mode,mutate=change,unknown=unknown,unit_ids=unit_ids)
        raw={k:v+raw_suffix if v is not None else None for k,v in raw.items()}
        args=dict(expected_pair=self.pair[:],mode=mode,step=step,goal=cfg['goal'],unit_ids=cfg['unit_ids'],**raw)
        bb=self.service().inspect(self.parent,**args,provider_id='CTestController')['result']['authority_binding']
        control=encode(dict(format=AUTHORITY,provider_id='CTestController',provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=bb,decision=decision,reason='External synthetic C work control')]))
        path=self.path/('authority-'+str(uuid4())+'.json');path.write_bytes(control)
        authority=LocalSyntheticContinuationAuthority(path,SemanticTrustContext('CTestController','local-synthetic/1',sha256(control).hexdigest()))
        return args,authority


def readback(case,command):
    b=Budget();reg=LocalSyntheticHistoricalReviews.load(case.trust,b);store=ContinuationStore(reg.open_repository(case.db),reg,b);v=store.load(command);plan,stage=store.checked_plan(v)
    cmd=v['command'];cfg=v['config'];state=v['state']
    assert len(store.plans(cmd,v['history']))==1 and sum(e['kind']=='finalized' for e in cmd['events'])==1
    assert cmd['run']['id']==cfg['reserved_run_id']==cmd['operation']['reserved_run_id']
    assert cmd['events'][-1]['payload']['promotions']==plan['promotions']
    with case.repo()._read() as c:applications=[list(x) for x in c.execute("SELECT command_id,event_id,payload_json FROM operation_events WHERE kind='application_applied' ORDER BY command_id,event_id")]
    identity=dict(command=command,run_id=cmd['run']['id'],config_sha256=v['primary']['sha256'],raw_sha256={k:s['sha256'] if s else None for k,s in v['raw'].items()},plan_sha256=stage['sha256'],registry_pin=cfg['historical_reviews_pin'],run=cmd['run'],applications=applications,
        planned_records=plan['batch']['records'],actual_records={r['id']:state['records'][r['id']] for r in plan['batch']['records'] if r['id'] in state['records']},base_issues={q['body']['issue_key']:q for q in v['base'].issues},
        current_issues={state['records'][i]['body']['issue_key']:state['records'][i] for i in state['records'][v['current_head'][1]]['body']['issue_ids']},plan_artifact=state['records'][plan['allocation']['plan_artifact_id']],promotions=plan['promotions'])
    (case.path/('readback-'+command+'-'+str(uuid4())+'.json')).write_bytes(encode(identity));return v,plan,identity


def other_session(f,g):
    """Explicit namespaced fixture controller history; R covers both sessions."""
    from dacn_s02.resolution import HumanReviewEvidence,review_digest
    from dacn_s02.s01_adapter import verify_archive
    # Explicit controller map, already held outside the DB. No B adapter exports
    # evaluator/assessment or expected SHA from stored Issue metadata.
    controls=deepcopy(g.reviews)
    identities=set(g.records)|set(g.commands)|{g.session}|{eid for _,eid in g.events}|{bid for _,bid in g.stages}
    names={i:'Other.'+i for i in identities}
    event_names={(c,e):'Other.Event.'+c+'.'+e for c,e in g.events}
    def walk(v):
        if type(v) is str:return names.get(v,v)
        if type(v) is list:return [walk(x) for x in v]
        if type(v) is dict:
            result={k:walk(x) for k,x in v.items()}
            if 'command_id' in v and 'event_id' in v:result['event_id']=event_names[v['command_id'],v['event_id']]
            return result
        return v
    records={names[i]:walk(r) for i,r in g.records.items()};profiles={names[i]:p for i,p in g.record_profiles.items()};blobs={names[i]:b for i,b in g.blobs.items()}
    snapshots={r['body']['snapshot_id']:verify_archive(r,records,blobs) for r in records.values() if r['type']=='source_context'}
    for i,decision in g.reviews.items():
        new=names[i];controls[new]=HumanReviewEvidence(decision.reviewer,review_digest(records[new],records,snapshots,profiles),decision.assessment)
    for original,op0 in g.commands.items():
        op=walk(op0);cid=op['command_id'];rid=op['reserved_run_id'];rr=records[rid]
        events=sorted((walk(e) for (c,_),e in g.events.items() if c==original),key=lambda e:e['ordinal'])
        ids=iter(e['event_id'] for e in events if e['kind']!='application_applied')
        repo=Repository(f.repo.path,reviews=controls,_ids=lambda:next(ids))
        prepared=events[0]['payload'];stageitems=[]
        original_prepared=sorted((e for (c,_),e in g.events.items() if c==original),key=lambda e:e['ordinal'])[0]['payload']
        for ref in original_prepared['stage_refs']:
            s=g.stages[original,ref['blob_id']];meta=walk({k:v for k,v in s.items() if k!='bytes'});stageitems.append((meta,s['bytes']))
        repo.prepare(op,session_spec=f.s01env['snapshot']['spec_id'] if op['request']['kind']=='start' else None,staged=stageitems,attempt_id=prepared['attempt_id'])
        for e in events[1:]:
            if e['kind'] in ('finalized','application_applied'):continue
            repo.append_event(cid,e['kind'],e['payload'])
        body=rr['body'];batchids=[rid]
        if body['result_model_id']:
            m=records[body['result_model_id']];batchids.append(m['id'])
            if m['body']['change_id']:batchids.append(m['body']['change_id'])
        if body['result_analysis_set_id']:
            a=records[body['result_analysis_set_id']];batchids.extend([a['id'],*a['body']['changed_record_ids']])
        if op['request']['kind']=='start':
            ctx=records[body['source_context_id']];batchids.append(ctx['id']);batchids.extend(ctx['body'][k] for k in ('envelope_artifact_id','run_source_artifact_id','origin_source_artifact_id','schema_artifact_id'))
        if op['request']['kind']=='work' and body['result_analysis_set_id'] is None:
            batchids.extend(i for i,r in records.items() if r['type']=='answer')
        final=events[-1]['payload'];batchids.extend(p['artifact_id'] for p in final['promotions']);batchids=list(dict.fromkeys(batchids))
        app=[('application_applied',e['payload'],e['event_id']) for e in events if e['kind']=='application_applied']
        repo.finalize(cid,[records[i] for i in batchids],blobs={i:blobs[i] for i in batchids if i in blobs},promotions=final['promotions'],
            head=(body['result_model_id'] or body['base_model_id'],body['result_analysis_set_id']) if body['result_analysis_set_id'] else None,application_events=app)
    repo=Repository(f.repo.path,reviews=controls);repo.verify()
    return repo,controls
