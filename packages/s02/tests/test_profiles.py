from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from importlib.resources import files
import pytest
from jsonschema import Draft202012Validator
from dacn_s02.profiles import L1,E1,REGISTRY,get_profile,check_descriptor
from dacn_s02.validation import shape,fields,typed_links,SCHEMA
from dacn_s02.errors import S02Error
from profile_fixtures import graph


def test_profile_resources_bytes_local_refs_and_independent_trees():
    assert sha256(files('dacn_s02').joinpath('schemas/contract.json').read_bytes()).hexdigest()=='dd32824ab03c5e4d5faae3eb3888bdea3cacd5ba4735a4a5df19416b024f70b7'
    for p in REGISTRY.values():
        Draft202012Validator.check_schema(p.schema)
        assert check_descriptor(p.descriptor,schema_bytes=p.schema_bytes,descriptor_bytes=p.descriptor_bytes)==p
        def walk(v):
            if type(v) is dict:
                if '$ref' in v:assert v['$ref'].startswith('#/$defs/')
                for x in v.values():walk(x)
            elif type(v) is list:
                for x in v:walk(x)
        walk(p.schema)
    s=get_profile(E1).schema;s['$defs'].clear();assert get_profile(E1).schema['$defs']
    assert SCHEMA['$id']=='urn:dacn:s02:0.1.0-draft.3'

@pytest.mark.parametrize('field,value',[('profile_id','unknown'),('rules_id','unknown'),('schema_sha256','0'*64),('required_capabilities',[]),('required_capabilities',['foundation-draft3','unknown']),('contract_version','s02/other')])
def test_unknown_descriptor_rejected(field,value):
    d=get_profile(E1).descriptor;d[field]=value
    with pytest.raises(S02Error):check_descriptor(d)

@pytest.mark.parametrize('mutation',['missing_carry','missing_replacement','both','new_status_direct','old_method','extra'])
def test_e1_branch_shapes_negative(foundation,mutation):
    g=graph(foundation);q=g.carry();b=q['body']
    if mutation=='missing_carry':del b['resolution_carry']
    if mutation=='missing_replacement':del b['resolution_replacement']
    if mutation=='both':b['resolution_replacement']={}
    if mutation=='new_status_direct':b['resolution_carry']=None;b['status']='resolution_pending_revalidation'
    if mutation=='old_method':b['resolution_carry']['evaluation']['method']='structural_reuse'
    if mutation=='extra':b['arbitrary']=True
    with pytest.raises(S02Error):shape(q,profile=E1)


def test_explicit_dispatch_concurrent_and_typed_history(foundation):
    g=graph(foundation);legacy=deepcopy(g.records[g.current_issue]);q=g.carry()
    def work(i):
        p,r=(L1,legacy) if i%2 else (E1,q)
        shape(r,profile=p);return len(list(fields(r,profile=p)))
    with ThreadPoolExecutor(max_workers=4) as pool:assert all(pool.map(work,range(40)))
    assert ('/body/resolution_carry/origin_issue_id',legacy['id'],'issue') in typed_links(q,profile=E1)
    with pytest.raises(S02Error):shape(q,profile=L1)
    with pytest.raises(S02Error):shape(legacy,profile=E1)
    with pytest.raises(S02Error):shape({},'Export',profile=E1)
    g.record_profiles.pop(q['id'])
    with pytest.raises(S02Error):g.check()


def test_event_stage_inherit_operation_no_override(foundation):
    g=graph(foundation);g.carry();cmd=list(g.commands)[-1]
    event=g.events[cmd,'prep'];event['profile_id']=L1
    with pytest.raises(S02Error):g.check()


def test_e1_never_uses_mutable_global_schema_alias(foundation,monkeypatch):
    import dacn_s02.validation as validation
    import dacn_s02.events as operational
    g=graph(foundation);g.carry()
    # Repository remains L1; this pure E1 graph must dispatch from owner maps.
    monkeypatch.setattr(validation,'SCHEMA',{})
    monkeypatch.setattr(operational,'SCHEMA',{})
    g.check()


def test_repository_cannot_write_e1_issue(foundation):
    from helpers import run,aset
    f=foundation;m,a=f.initial(True);op=f.operation();f.repo.prepare(op)
    q=deepcopy(f.repo.get_record('Q2'));q['id']='Q-E1';q['body'].update(supersedes_id='Q2',resolution_carry=None,resolution_replacement=None)
    s=aset(m,'AS-E1',a,issues=[q['id']])
    with pytest.raises(S02Error):f.repo.finalize(op['command_id'],[q,s,run(op,f.context,f.config,set_id=s['id'])],head=(m['id'],s['id']))
    assert f.repo.heads(f.session)==(m['id'],a['id'])
    assert f.repo.get_record(q['id']) is None


def test_publication_profile_cannot_disagree_with_operation(foundation):
    g=graph(foundation);q=g.carry();cmd=list(g.commands)[-1]
    g.operation_profiles[cmd]=L1
    with pytest.raises(S02Error,match='graph_publication_profile'):g.check()
