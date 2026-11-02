"""C independent OS worker plumbing and exact A2 identity/readback oracles."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4
import json,os,subprocess,sys,shutil
from dacn_s02.codec_boundary import encode,decode
from dacn_s02.h3_limits import Budget
from dacn_s02.h3_review_io import LocalSyntheticHistoricalReviews
from dacn_s02.h3_continuation_store import ContinuationStore
from h3_c_runtime_fixtures import readback


def evidence(case):
    out=Path(os.environ.get('S02_TEST_EVIDENCE_DIR',str(case.path/'evidence')))/case.path.name;out.mkdir(parents=True,exist_ok=True);return out


def spec(case,command,work,a,**changes):
    token=str(uuid4());path=evidence(case)/(token+'.work.json');data=dict(work)
    for lane in ('candidate','analysis'):
        if data[lane] is not None:
            raw=path.with_suffix('.'+lane+'.json');raw.write_bytes(data[lane]);data[lane]=str(raw)
    path.write_bytes(encode(data));value=dict(db=str(case.db),config=str(case.config),command=command,parent=case.parent,receipt=str(case.path/(command+'.receipt.json')),work=str(path),mode='resume',review_trust=asdict(case.trust),authority=str(a.path) if a else None,authority_trust=asdict(a.trust) if a else None)
    value.update(changes);return value


def launch(case,value):
    out=evidence(case);token=str(uuid4());path=out/(token+'.input.json');path.write_text(json.dumps(value))
    argv=[sys.executable,'-B',str(Path(__file__).with_name('h3_c_worker.py')),str(path)];env=os.environ.copy();env.pop('PYTHONPATH',None)
    p=subprocess.Popen(argv,cwd=case.path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def finish():
        timed_out=False
        try:stdout,stderr=p.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            p.kill();stdout,stderr=p.communicate();timed_out=True
        (out/(token+'.stdout.log')).write_bytes(stdout);(out/(token+'.stderr.log')).write_bytes(stderr)
        (out/(token+'.command.json')).write_text(json.dumps(dict(pid=p.pid,argv=argv,cwd=str(case.path),exit_code=p.returncode,timed_out=timed_out,test_case=os.environ.get('PYTEST_CURRENT_TEST'),backend=os.environ.get('S02_TEST_CODEC_BACKEND','c'))))
        assert not timed_out,('C worker exceeded unchanged 45s harness timeout',p.pid,stdout,stderr)
        if p.returncode!=71:
            row=next((x.removeprefix('H3_ENCODERS ') for x in stdout.decode().splitlines() if x.startswith('H3_ENCODERS ')),None);assert row is not None,(stdout,stderr)
            row=json.loads(row);backend=os.environ.get('S02_TEST_CODEC_BACKEND','c');assert row['backend']==backend and row['calls'][backend]>0 and row['calls']['c' if backend=='python' else 'python']==0
        return p.returncode,stdout.decode(),stderr.decode()
    return finish


def result(value):return decode(next(x.removeprefix('H3_RESULT ') for x in value[1].splitlines() if x.startswith('H3_RESULT ')).encode())


def save_snapshot(case,label):
    root=evidence(case)/label;root.mkdir(exist_ok=False)
    for p in case.db.parent.iterdir():
        if p.is_file():shutil.copy2(p,root/p.name)
    return root


def claims(case):
    with case.repo()._read() as c:return [list(r) for r in c.execute('SELECT * FROM application_heads ORDER BY answer_id')]


def pending(case,command):
    b=Budget();reg=LocalSyntheticHistoricalReviews.load(case.trust,b);store=ContinuationStore(reg.open_repository(case.db),reg,b);v=store.load(command)
    if v is None:return None
    found=store.checked_plan(v)
    return dict(command=command,reserved_run_id=v['config']['reserved_run_id'],started_at=v['config']['started_at'],config_bytes=v['primary']['bytes'],raw_bytes={k:s['bytes'] if s else None for k,s in v['raw'].items()},plan_bytes=found[1]['bytes'] if found else None,plan=found[0] if found else None,old_records={r['record_id']:v['state']['records'][r['record_id']] for r in v['config']['history_binding']['records']},claims=claims(case))


def exact(case,command,previous=None):
    v,p,i=readback(case,command);cfg=v['config'];cmd=v['command'];published=cmd['run']['body']['status'] in ('completed','blocked');rejected=cmd['run']['body']['status']=='rejected'
    assert cfg['historical_reviews_pin']==p['bindings']['historical_reviews_pin']
    assert len(cmd['staged_blobs'])==(4 if cfg['mode']=='step' else 3) and len(cmd['events'])==3
    assert i['applications']==case.applications_before
    if previous:
        assert cfg['reserved_run_id']==previous['reserved_run_id'] and cfg['started_at']==previous['started_at']
        assert v['primary']['bytes']==previous['config_bytes'] and {k:s['bytes'] if s else None for k,s in v['raw'].items()}==previous['raw_bytes']
        if previous['plan_bytes'] is not None:assert encode(p)==previous['plan_bytes']
        assert all(v['state']['records'][k]==r for k,r in previous['old_records'].items())
        assert claims(case)==previous['claims']
    for r in p['batch']['records']:
        if published or rejected:assert v['state']['records'][r['id']]==r
        elif r['type'] in ('model','change','analysis_set','issue'):assert r['id'] not in v['state']['records']
        elif r['type']=='artifact':assert v['state']['records'][r['id']]==r
        else:
            expected=deepcopy(r);expected['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=cmd['run']['body']['errors']);assert cmd['run']==expected
    if published:
        current={v['state']['records'][qid]['body']['issue_key']:v['state']['records'][qid] for qid in v['state']['records'][p['batch']['head'][1]]['body']['issue_ids']}
        assert set(q['body']['issue_key'] for q in v['base'].issues)<=set(current)
        for q in v['base'].issues:
            now=current[q['body']['issue_key']];b=now['body'];old=q['body']
            if now['id']!=q['id']:
                assert b['supersedes_id']==q['id'] and b['model_id']==p['batch']['head'][0] and b['answer_ids']==old['answer_ids']
                for lane in ('resolution_carry','resolution_replacement'):
                    proof=b[lane]
                    if proof:
                        assert proof['from_issue_id']==q['id'] and proof['base_analysis_set_id']==v['base'].pair[1]
                        if old[lane]:
                            assert proof['origin_issue_id']==old[lane]['origin_issue_id']
                            if lane=='resolution_replacement':assert proof['obsolete_issue_id']==old[lane]['obsolete_issue_id']
                        if lane=='resolution_replacement':assert proof['replacement_issue_id'] in {x['id'] for k,x in current.items() if k!=b['issue_key']}
        for r in p['batch']['records']:
            if r['type']=='change':assert r['body']['application_event_refs']==[] and r['body']['kind']=='analysis_edit' and r['body']['old_source_context_id']==r['body']['new_source_context_id']
    else:assert not any(r['type'] in ('model','change','issue','analysis_set') for r in p['batch']['records']) or not rejected
    for ref in p['promotions']:
        stage=v['state']['stages'][ref['stage_ref']['command_id'],ref['stage_ref']['blob_id']];assert v['state']['blobs'][ref['artifact_id']]==stage['bytes']
    (evidence(case)/(command+'.readback.json')).write_bytes(encode(i));save_snapshot(case,'final-'+command);return v,p
