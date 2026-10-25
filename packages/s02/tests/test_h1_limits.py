"""H1 resource boundaries are input/work bounds, never semantic quality scores."""
from copy import deepcopy
import pytest

from dacn_s02.errors import S02Error
from dacn_s02.codec_boundary import encode
from dacn_s02.h1_limits import DEFAULTS,Budget,bounded_decode,cap,model_limits
from dacn_s02.h1_service import H1Service
from dacn_s02.h1_store import WorkStore
from dacn_s02.h1_candidates import parse
from h1_fixtures import Case,input_data
from uuid import uuid4


@pytest.mark.parametrize('name',list(DEFAULTS))
def test_each_pinned_boundary_inclusive_and_one_over(name):
    cap(name,DEFAULTS[name])
    with pytest.raises(S02Error) as caught:cap(name,DEFAULTS[name]+1)
    assert caught.value.error['code']=='LOCAL_LIMIT_EXCEEDED' and caught.value.error['details']['limit']==name


@pytest.mark.parametrize('raw,limit',[(b'['*64+b'0'+b']'*64,'depth'),(b'['+b'0,'*100000+b'0]','values'),(b'"'+b'x'*65537+b'"','string_bytes')])
def test_lexical_bounds_before_tree_materialization(raw,limit):
    with pytest.raises(S02Error) as caught:bounded_decode(raw,Budget())
    assert caught.value.error['details']['limit']==limit


def test_lexical_exact_boundary_and_utf_encodings():
    assert bounded_decode(b'['*63+b'0'+b']'*63,Budget()) is not None
    assert len(bounded_decode(b'"'+b'x'*65536+b'"',Budget()))==65536
    for encoding in ('utf-8-sig','utf-16','utf-32'):
        assert bounded_decode('{"a":[true,null,1.2]}'.encode(encoding),Budget())['a'][0] is True
    assert len(bounded_decode(b'['+b'0,'*99998+b'0]',Budget()))==99999


def test_findings_cap_on_real_candidate_projection(tmp_path):
    case=Case(tmp_path);candidate=deepcopy(case.responses[0]);source=candidate['inspection'][0]['source_ref']
    def finding(i):return dict(handle='finding'+str(i),kind='verification',question='Check the proposed draft',reason='Synthetic bounded projection',
        trace=dict(origin='inferred',source_refs=[source],rationale='Test only',finding_handles=[]),affected_refs=[],blocking_refs=[],impact_known=True)
    candidate['proposals']['findings']=[finding(i) for i in range(500)]
    parsed,_=parse(encode(candidate),1,case.snapshot,{},lambda:str(uuid4()),Budget())
    assert len(parsed['proposals']['findings'])==500
    candidate['proposals']['findings'].append(finding(500))
    with pytest.raises(S02Error) as caught:parse(encode(candidate),1,case.snapshot,{},lambda:str(uuid4()),Budget())
    assert caught.value.error['details']['limit']=='findings'


@pytest.mark.parametrize('count',[1000,1001])
def test_source_inventory_boundary_before_bootstrap_prepare(tmp_path,count):
    source=input_data();source['functional_requirements']=source['functional_requirements'][:1]
    source['functional_requirements'][0]['acceptance_criteria']=['Synthetic criterion '+str(i) for i in range(count-1)]
    source['non_functional_requirements']=[];source['constraints']=[]
    case=Case(tmp_path,source);cmd=str(uuid4())
    if count==1000:
        result=H1Service(case.repo).prepare(cmd,case.parent,'bootstrap',None,case.store_id)
        assert result['status']=='prepared'
    else:
        with pytest.raises(S02Error) as caught:H1Service(case.repo).prepare(cmd,case.parent,'bootstrap',None,case.store_id)
        assert caught.value.error['details']['limit']=='obligations' and case.repo.get_command(cmd) is None


def test_raw_limit_before_prepare_and_clock_after_prepare(tmp_path):
    case=Case(tmp_path);case.advance('bootstrap');cmd='test-raw-limit'
    with pytest.raises(S02Error) as caught:H1Service(case.repo).prepare(cmd,case.parent,1,b' '*1048577,case.store_id)
    assert caught.value.error['code']=='LOCAL_LIMIT_EXCEEDED' and case.repo.get_command(cmd) is None
    cmd=case.prepare(1,encode(case.responses[0]));head=case.repo.heads(case.intake['session_id']);ticks=iter((0,31))
    result=H1Service(case.repo,_monotonic=lambda:next(ticks)).resume(cmd)
    assert result['status']=='rejected' and result['errors'][0]['details']['limit']=='compute_seconds'
    assert case.repo.heads(case.intake['session_id'])==head and WorkStore(case.repo).load(cmd)['raw']['bytes']==encode(case.responses[0])


@pytest.mark.parametrize('field,limit',[('actors','entities'),('nodes','nodes'),('edges','edges'),('parts','parts'),('issues','issues'),('refs','refs')])
def test_result_graph_caps_measure_total_not_only_new_entities(tmp_path,field,limit):
    case=Case(tmp_path);result=case.advance('bootstrap');body=deepcopy(result['result']['model']['body']);issues=[]
    if field=='actors':body['actors']=[{}]*DEFAULTS[limit]
    if field in ('nodes','edges'):body['workflows']=[dict(nodes=[] if field!='nodes' else [{}]*DEFAULTS[limit],edges=[] if field!='edges' else [{}]*DEFAULTS[limit])]
    if field=='parts':body['mappings']=[dict(parts=[{}]*DEFAULTS[limit])]
    if field=='issues':issues=[{}]*DEFAULTS[limit]
    if field=='refs':body['actors']=[dict(action_ids=['a']*(DEFAULTS[limit]-2))]  # source_context_id + created_by_run_id
    # This targets the total-graph guard, independently of entity schema checks.
    if field=='actors':body.update(actions=[],workflows=[],data=[],rules=[],components=[],responsibilities=[],interfaces=[],dependencies=[])
    if field=='refs':body['mappings']=[]
    model_limits(body,issues)
    if field=='actors':body['actors'].append({})
    elif field in ('nodes','edges'):body['workflows'][0][field].append({})
    elif field=='parts':body['mappings'][0]['parts'].append({})
    elif field=='issues':issues.append({})
    else:body['actors'][0]['action_ids'].append('a')
    with pytest.raises(S02Error) as caught:model_limits(body,issues)
    assert caught.value.error['details']['limit']==limit
