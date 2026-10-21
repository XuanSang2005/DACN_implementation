from copy import deepcopy
from decimal import Decimal
import pytest
from dacn_s02.codec_boundary import decode,encode
from dacn_s02.validation import shape,W,resolve_pointer,validate_record
from dacn_s02.errors import S02Error
from dacn_s02.repository import record
from helpers import model,trace

def test_exact_codec():
    raw=b'{"large":123456789012345678901234567890,"d":0.1234567890123456789012345,"unknown":null,"flag":true,"text":"  e\\u0301  "}'
    v=decode(raw);assert v['large']==Decimal('123456789012345678901234567890');assert v['d']==Decimal('0.1234567890123456789012345')
    assert encode(decode(encode(v)))==encode(v);assert v['text']=='  e\u0301  ';assert 'absent' not in v and v['unknown'] is None

@pytest.mark.parametrize('raw,code',[(b'{"a":1,"\\u0061":2}','DUPLICATE_KEY'),(b'{','INVALID_JSON'),(b'NaN','INVALID_JSON')])
def test_decode_errors(raw,code):
    with pytest.raises(S02Error) as e: decode(raw)
    assert e.value.error['code']==code and e.value.error['pointer'] is None

@pytest.mark.parametrize('value',[0.1,'\ud800\udc00',{'\ud800\udc00':'bad'}])
def test_unrepresentable_controlled(value):
    with pytest.raises(S02Error) as e: encode(value)
    assert e.value.error['code']=='PROCESSING_FAILED';encode(e.value.error)

@pytest.mark.parametrize('char',sorted(W))
def test_whitespace_nonblank(char):
    a=record('artifact','A',dict(media_type=char,sha256='a'*64,byte_length=0,purpose='schema',producer_run_id=None))
    with pytest.raises(S02Error): shape(a)
    a['body']['media_type']=char+'x'+char;shape(a)

@pytest.mark.parametrize('char',['\u200b','\ufeff'])
def test_outside_w_nonblank(char):
    shape(record('artifact','A',dict(media_type=char,sha256='a'*64,byte_length=0,purpose='schema',producer_run_id=None)))

@pytest.mark.parametrize('bad',[' bad','bad ','x\n','é','',True,2,None])
def test_ids_no_regex_newline_veto(bad):
    with pytest.raises(S02Error): shape(record('artifact',bad,dict(media_type='x',sha256='a'*64,byte_length=0,purpose='schema',producer_run_id=None)))

@pytest.mark.parametrize('bad',[True,Decimal('1.5'),-1,1.0,None])
def test_integer_no_bool_or_float(bad):
    with pytest.raises(S02Error): shape(record('artifact','A',dict(media_type='x',sha256='a'*64,byte_length=bad,purpose='schema',producer_run_id=None)))

def test_fields_missing_unknown_null():
    a=record('answer','A',dict(issue_id='Q',supersedes_answer_id=None,respondent='User',recorded_by='Operator',text='  Preserve  ',interpretation='needs_interpretation',existing_source_refs=[]))
    shape(a)
    for field in a['body']:
        bad=deepcopy(a);del bad['body'][field]
        with pytest.raises(S02Error): shape(bad)
    bad=deepcopy(a);bad['body']['s01_update_run_id']=None
    with pytest.raises(S02Error): shape(bad)
    bad=deepcopy(a);bad['body']['existing_source_refs']=None
    with pytest.raises(S02Error): shape(bad)

def test_pointer_escapes_and_array_index():
    assert resolve_pointer({'a/b':{'~':['x','x']}},'/a~1b/~0/1')=='x'
    for p in ['/a~2b','/a~1b/~0/01','/a~1b/~0/-','/a~1b/~0/2']:
        with pytest.raises((ValueError,IndexError)): resolve_pointer({'a/b':{'~':['x','x']}},p)

@pytest.mark.parametrize('initiator,actors,ok',[('unknown',['Actor'],False),('internal',['Actor'],False),('external',[],False),('external',['Actor'],True),('unknown',[],True),('internal',[],True)])
def test_f05_actor_invariant(foundation,initiator,actors,ok):
    f=foundation;op=f.operation();f.repo.prepare(op);m=model(f.context,f.snapshot,op['reserved_run_id']);m['body']['actions'][0].update(initiator=initiator,actor_ids=actors)
    from helpers import aset,run
    a=aset(m);batch=[m,a,run(op,f.context,f.config,model_id=m['id'],set_id=a['id'])]
    if not ok:
        with pytest.raises(S02Error) as e: f.repo.finalize(op['command_id'],batch,head=(m['id'],a['id']))
        assert e.value.error['details']=={'invariant':'action_initiator_actors'}
    else:
        f.repo.finalize(op['command_id'],batch,head=(m['id'],a['id']))
        assert f.repo.get_record(m['id'])['body']['actions'][0]['permission_rule_ids']==[]

def test_wrapper_not_export():
    with pytest.raises(S02Error): shape(dict(illustration='minh họa chưa thực thi',contract_version='s02/0.1.0-draft.3',session_id='S',records=[],external_bindings=[],scenarios=[]),'Export')
