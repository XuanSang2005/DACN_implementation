from copy import deepcopy
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.observed_source import check_base_pair
from dacn_s02.profiles import E1,L1
from profile_fixtures import observed_graph,graph

@pytest.mark.parametrize('switch',[False,True])
def test_a1_observed_unchanged_uses_snapshot_branch(foundation,switch):
    g,app,observed=observed_graph(foundation,switch=switch);g.check()
    assert observed['result_kind']=='unchanged'
    assert g.records['CH1']['body']['kind']==('requirements_switch' if switch else 'analysis_edit')
    assert app['payload']['new_source_context_id']==('ObservedContext' if switch else g.context)
    assert app['payload']['observed_source_context_id']=='ObservedContext'
    assert g.blobs['ObsRaw']!=g.blobs['ObsOrigin']
    before=deepcopy(g.kwargs());g.check();assert g.kwargs()==before

@pytest.mark.parametrize('mutation',['missing_field','no_archive','old_context','wrong_run','wrong_snapshot','wrong_store','wrong_request','wrong_consent','wrong_input','origin_hash','wrong_branch','wrong_base','raw_mismatch','event_profile_override'])
def test_a1_rejects_mismatched_evidence(foundation,mutation):
    g,app,_=observed_graph(foundation);p=app['payload'];cmd=app['command_id'];obs=g.records['ObservedContext']['body']
    if mutation=='missing_field':del p['observed_source_context_id']
    if mutation=='no_archive':p['observed_source_context_id']=None
    if mutation=='old_context':p['observed_source_context_id']=g.context
    if mutation=='wrong_run':obs['s01_run_id']='wrong'
    if mutation=='wrong_snapshot':obs['snapshot_id']='wrong'
    if mutation=='wrong_store':obs['store_key']='wrong'
    if mutation=='wrong_request':g.events[cmd,'s01_dispatch_intent']['payload']['s01_request']={**g.events[cmd,'s01_dispatch_intent']['payload']['s01_request'],'base_revision':99}
    if mutation=='wrong_consent':p['consent_event']=p['interpretation_event']
    if mutation=='wrong_input':g.stages[cmd,'FullInput']['bytes']=g.blobs['ObsOrigin']
    if mutation=='origin_hash':g.events[cmd,'consent_recorded']['payload']['approved_input_sha256']=g.records['ObsOrigin']['body']['sha256']
    if mutation=='wrong_branch':g.records['CH1']['body']['kind']='requirements_switch'
    if mutation=='wrong_base':g.commands[cmd]['request']['base_analysis_set_id']='AS-M2'
    if mutation=='raw_mismatch':g.blobs['ObsRaw']+=b' '
    if mutation=='event_profile_override':g.operation_profiles[cmd]=L1
    with pytest.raises(S02Error):g.check()


def test_a1_pair_check_requires_both_heads():
    req=dict(base_model_id='M1',base_analysis_set_id='AS1')
    check_base_pair(req,('M1','AS1'))
    for pair in [('M2','AS1'),('M1','AS2'),(None,None)]:
        with pytest.raises(S02Error):check_base_pair(req,pair)


def test_existing_source_e1_direct(foundation):
    g=graph(foundation);q=g.records[g.current_issue];q['body'].update(resolution_carry=None,resolution_replacement=None);g.record_profiles[q['id']]=E1
    app=next(e for e in g.events.values() if e['kind']=='application_applied');app['payload']['observed_source_context_id']=None;g.operation_profiles[app['command_id']]=E1
    from profile_fixtures import application_profiles
    application_profiles(g,app['command_id'])
    g.check()
    app['payload']['observed_source_context_id']=g.context
    with pytest.raises(S02Error):g.check()


def test_recovery_does_not_allow_s01_resend(foundation):
    from helpers import operation
    g,app,_=observed_graph(foundation);parent=app['command_id']
    op=operation(g.session,g.context,(g.model_id,g.set_id),kind='apply_answer',answer_id='Answer1',issue_key='Question2',parent=parent)
    cmd=op['command_id'];g.commands[cmd]=op;g.operation_profiles[cmd]=E1
    g.events[cmd,'prep']=dict(event_id='prep',command_id=cmd,ordinal=1,kind='prepared',payload=dict(stage_refs=[],attempt_id=None))
    dispatch=deepcopy(g.events[parent,'s01_dispatch_intent']);dispatch.update(command_id=cmd,event_id='again',ordinal=2);g.events[cmd,'again']=dispatch
    with pytest.raises(S02Error,match='a1_no_resend'):g.check()
