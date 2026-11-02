"""Fresh synthetic DB copies and external B controls, never production inputs."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
import json,shutil
from dacn_s02.codec_boundary import encode,decode
from dacn_s02.repository import Repository
from dacn_s02.local_io import settings
from dacn_s02.h3_limits import Budget,digest
from dacn_s02.h3_history import ReviewTrustContext
from dacn_s02.h3_contracts import REGISTRY
from dacn_s02.h3_policy import SemanticTrustContext
from dacn_s02.h3_checkpoint_contracts import AUTHORITY,ANALYSIS
from dacn_s02.h3_review_io import LocalSyntheticHistoricalReviews,LocalSyntheticCheckpointAuthority
from dacn_s02.h3_service import HistoryService
from h2_checkpoint_fixtures import ScopedCase
from h3_b_fixtures import state_of,history,anchor_for


def baseline(path,guard=False,workflow=False):
    c=ScopedCase(path);c.bootstrap();c.advance(1)
    def add_workflow(candidate,analysis):
        candidate['proposals']['actions'][0]['workflow_ids']=[dict(local_handle='flow')]
        candidate['proposals']['workflows']=[dict(handle='flow',name='Synthetic retained workflow',entry_node_id=dict(local_handle='read-node'),
            nodes=[dict(handle='read-node',action_id=dict(local_handle='view'),kind='action',label='Read V'),dict(handle='end-node',action_id=None,kind='end',label='End')],
            edges=[dict(handle='to-end',**{'from':dict(local_handle='read-node'),'to':dict(local_handle='end-node')},guard=None,trace=c.tr())],branch_points=[],state='draft',trace=c.tr())]
    c.advance(2,change=add_workflow if workflow else None)
    if guard:c.advance(3,proof=False)
    return c


class BCase:
    def __init__(self,path,source):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True);(self.path/'s02').mkdir()
        db=self.path/'s02/s02.sqlite3';shutil.copyfile(source.repo.path,db)
        assert sha256(db.read_bytes()).digest()==sha256(source.repo.path.read_bytes()).digest()
        self.h2=object.__new__(ScopedCase);self.h2.__dict__=deepcopy(source.__dict__);self.h2.path=self.path;self.h2.repo=Repository(db)
        self.db=db;self.store_id=source.store_id;self.parent=source.parent;self.pair=list(source.pair)
        self.config=self.path/'s02.toml';self.config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic='+json.dumps(str(source.s01.path))+'\n')
        self.settings=settings(self.config);self.registry_path=self.path/'historical-reviews.json'
        entries=deepcopy(getattr(source,'historical_entries',[]))
        raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='BReviews',store_id=self.store_id,required_issue_ids=[x['issue_id'] for x in entries],reviews=entries));self.registry_path.write_bytes(raw)
        self.trust=ReviewTrustContext(str(self.registry_path),sha256(raw).hexdigest(),'BReviews',self.store_id);self.registry_raw=raw;self.receipts={}
        with self.repo()._read() as con:
            self.applications_before=[list(x) for x in con.execute("SELECT command_id,event_id,payload_json FROM operation_events WHERE kind='application_applied' ORDER BY command_id,event_id")]

    def service(self,authority=None,**kw):return HistoryService(self.settings,historical_reviews=self.trust,authority=authority,**kw)

    def repo(self):
        b=Budget();f=LocalSyntheticHistoricalReviews.load(self.trust,b);return f.open_repository(self.db)

    def anchor(self):
        h=history(state_of(self.repo()),self.store_id);base=h.view(h._state['commands'][self.parent]['session_id'],self.pair,self.pair)
        self.h2.parent=self.parent;self.h2.pair=self.pair
        return anchor_for(self.h2,base)

    def work(self,*,mode='adopt',step=0,goal='admission',anchor=None,change=None,decision='allow',parent=None,pair=None,unit_ids=None):
        parent=parent or self.parent;pair=pair or self.pair
        args=dict(expected_pair=pair,mode=mode,step=step,goal=goal,anchor=anchor)
        if unit_ids is not None:args['unit_ids']=unit_ids
        preview=self.service().inspect(parent,**args)['result'];units=preview['unit_ids'];source=preview['snapshot_id'];refs=preview['obligations']
        raw=dict(version=ANALYSIS,source_context_id=preview['source_context_id'],snapshot_id=source,base_pair=pair,selectors_sha256=digest(sorted(preview['selectors'].values(),key=lambda r:r['issue_key'])),unit_ids=units,
            inspections=[dict(source_ref=r,read='inspected',verdict='held' if r['input_pointer'].startswith('/functional_requirements/0') else 'usable',basis_source_refs=[r],needed_facts=['Unknown U permission'] if r['input_pointer'].startswith('/functional_requirements/0') else [],reason='Synthetic independent source inspection') for r in refs],
            independence=[dict(issue_key=k,unit_id=row['unit_id'],verdict='held' if row['source_refs'][0]['input_pointer'].startswith('/functional_requirements/0') else 'independent',basis_source_refs=refs,reason='Explicit synthetic U held, other families independent') for k in preview['selectors'] for row in preview['inventory']])
        if change:change(raw)
        data=encode(raw);bb=self.service().inspect(parent,**args,analysis=data,provider_id='BTestController')['result']['authority_binding']
        control=encode(dict(format=AUTHORITY,provider_id='BTestController',provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=bb,decision=decision,reason='External synthetic B work control')]))
        path=self.path/('authority-'+str(uuid4())+'.json');path.write_bytes(control);authority=LocalSyntheticCheckpointAuthority(path,SemanticTrustContext('BTestController','local-synthetic/1',sha256(control).hexdigest()))
        return dict(**args,analysis=data),authority

    def prepare(self,command,work,authority,*,parent=None,**kw):
        receipt=self.path/(command+'.receipt.json');self.receipts[command]=receipt
        return self.service(authority,**kw).prepare(command,parent or self.parent,receipt=receipt,**work)

    def execute(self,work,authority,*,command=None,parent=None):
        command=command or str(uuid4());self.prepare(command,work,authority,parent=parent)
        result=self.service(authority).resume(command,receipt=self.receipts[command])
        if result['result'].get('result_pair'):self.parent=command;self.pair=result['result']['result_pair']
        return result


def readback(case,command):
    from dacn_s02.h3_checkpoint_store import HistoryStore
    budget=Budget();reg=LocalSyntheticHistoricalReviews.load(case.trust,budget);repo=reg.open_repository(case.db);store=HistoryStore(repo,reg,budget);view=store.load(command)
    plan,stage=store.checked_plan(view);cmd=view['command'];s=view['state'];cfg=view['config']
    assert sum(e['kind']=='finalized' for e in cmd['events'])==1
    assert cmd['run']['id']==cfg['reserved_run_id']==cmd['operation']['reserved_run_id']
    assert len(store.plans(cmd,view['history']))==1
    events=[e for e in cmd['events'] if e['kind']=='finalized'];assert events[0]['payload']['promotions']==plan['promotions']
    with repo._read() as c:
        rows=c.execute("SELECT command_id,event_id,payload_json FROM operation_events WHERE kind='application_applied' ORDER BY command_id,event_id").fetchall()
    identity=dict(command=command,run_id=cmd['run']['id'],config_sha256=view['primary']['sha256'],analysis_sha256=view['raw']['sha256'],analysis_bytes=view['raw']['byte_length'],plan_sha256=stage['sha256'],registry_pin=cfg['historical_reviews_pin'],plan=plan,run=cmd['run'],applications=[list(x) for x in rows],
        current_head=view['current_head'],planned_records=plan['batch']['records'],actual_records={r['id']:s['records'][r['id']] for r in plan['batch']['records'] if r['id'] in s['records']},
        task_origins=plan['admission']['tasks'],base_issues={q['body']['issue_key']:q for q in view['base'].issues},
        current_issues={s['records'][i]['body']['issue_key']:s['records'][i] for i in s['records'][view['current_head'][1]]['body']['issue_ids']},
        plan_artifact=s['records'][plan['allocation']['plan_artifact_id']],promotions=events[0]['payload']['promotions'])
    (case.path/('readback-'+command+'-'+str(uuid4())+'.json')).write_bytes(encode({k:v for k,v in identity.items() if k!='plan'}))
    return view,plan,identity


def human_baseline(path):
    """Controller creates historical reviews BEFORE B, through Repository APIs.

    The second session is a namespaced replay of this explicit synthetic history,
    including exact Answer/application semantics, not a DB dump import/SQL edit.
    """
    from types import SimpleNamespace
    from p2_helpers import Foundation
    from profile_fixtures import graph
    from h3_fixtures import e1
    from dacn_s02.resolution import HumanReviewEvidence,review_digest
    from dacn_s02.s01_adapter import verify_archive
    f=Foundation(path);g=e1(graph(f))
    for create in (lambda:g.carry('not_applicable',method='human_review'),lambda:g.replacement(complete=True,method='human_review')):
        before=set(g.records);create();new=set(g.records)-before
        op=list(g.commands.values())[-1]
        repo=Repository(f.repo.path,reviews=g.reviews);repo.prepare(op)
        repo.finalize(op['command_id'],[g.records[i] for i in g.records if i in new],head=(g.model_id,g.set_id))
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
    return SimpleNamespace(path=Path(path),repo=repo,s01=f.s01,store_id=repo.store_info()['metadata']['store_id'],parent=list(g.commands)[-1],pair=[g.model_id,g.set_id],
        historical_entries=[dict(issue_id=i,reviewer=d.reviewer,assessment=d.assessment,dependency_sha256=d.dependency_sha256) for i,d in sorted(controls.items())])
