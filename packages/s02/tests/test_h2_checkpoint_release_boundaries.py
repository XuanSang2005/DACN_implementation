"""Additional release gates on the same frozen production wheel."""
from pathlib import Path
from uuid import uuid4
import pytest
from h2_checkpoint_fixtures import ScopedCase
from h1_fixtures import Case,input_data
from test_h2_checkpoint_processes import spec,launch,final
from dacn_s02.h2_service import H2Service
from dacn_s02.repository import Repository,digest
from dacn_s02.errors import S02Error


@pytest.mark.parametrize('mode',['model','revalidation'])
def test_two_processes_model_or_revalidation_cas(tmp_path,mode):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1)
    if mode=='revalidation':
        case.advance(2,proof=False)
        work,authority=case.work(2,mode='revalidate',goal='admission',guards=list(case.meta['guards']))
    else:work,authority=case.work(2)
    base=case.pair[:];commands=[str(uuid4()),str(uuid4())];service=H2Service(case.repo,authority=authority)
    for cmd in commands:service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    barrier=dict(barrier_point='before_finalize',barrier=str(tmp_path/'barrier'))
    a=launch(case,spec(case,commands[0],work,authority,**barrier));b=launch(case,spec(case,commands[1],work,authority,**barrier))
    ra,rb=a(),b();assert ra[0]==rb[0]==2,(ra,rb)
    views=[final(case,cmd) for cmd in commands]
    assert sorted(v['command']['run']['body']['status'] for v,_ in views)==['blocked','stale']
    loser,plan=next((v,p) for v,p in views if v['command']['run']['body']['status']=='stale')
    assert plan['batch']['head'][1] not in loser['state']['records']
    if mode=='model':assert plan['batch']['head'][0] not in loser['state']['records']
    else:assert plan['batch']['head'][0]==base[0]
    planned_issues=[r['id'] for r in plan['batch']['records'] if r['type']=='issue']
    assert all(i not in loser['state']['records'] for i in planned_issues)


def test_h2_hot_journal_checked_recovery_and_readonly_progress(tmp_path):
    source=input_data();source['actors']=['Synthetic actor '+str(i)+' '+('漢'*12000) for i in range(40)]
    case=Case(tmp_path,source);cmd=str(uuid4());work=dict(mode='bootstrap',step=0,unit_ids=[],expected_pair=[None,None],goal='build',guard_keys=[],candidate=None,analysis=None)
    H2Service(case.repo).prepare(cmd,case.parent,store_id=case.store_id,**work)
    killed=launch(case,spec(case,cmd,work,None,phase='seal',repo_point='before_commit',action='kill'))()
    assert killed[0]==71,killed
    journal=Path(str(case.repo.path)+'-journal')
    assert journal.is_file() and journal.read_bytes()[:8]==bytes.fromhex('d9d505f920a163d7')
    before=digest(case.repo.path.read_bytes()),digest(journal.read_bytes())
    with pytest.raises(S02Error):H2Service(Repository(case.repo.path)).report(cmd,progress=True)
    with pytest.raises(S02Error):H2Service(Repository(case.repo.path)).resume(cmd,store_id=str(uuid4()))
    assert before==(digest(case.repo.path.read_bytes()),digest(journal.read_bytes()))
    result=H2Service(Repository(case.repo.path)).resume(cmd,store_id=case.store_id)
    assert result['status']=='completed',result
    final(case,cmd)
