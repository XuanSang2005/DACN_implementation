"""Closed private H3-A data contracts. No loader, service, writer or authority I/O.

Schemas are detached copies; canonical E1 definitions/registry remain unchanged.
A validated shape is neither a checked store lookup nor a publication token.
"""
from copy import deepcopy
from dataclasses import dataclass
from .codec_boundary import encode, decode
from .profiles import E1, get_profile
from .validation import Validator, FORMATS
from .h3_limits import Budget, VERSION as LIMITS, DEFAULTS, need, digest

POLICY = 's02-h3-history-policy/0.1.0-draft.2'
HANDLER = 's02-2a-h3-a/0.9.0a2'
CONFIG = 's02-h3-config/0.1.0-draft.2'
PLAN = 's02-h3-plan/0.1.0-draft.2'
ADMISSION = 's02-h3-admission/0.1.0-draft.2'
REGISTRY = 's02-h3-historical-reviews/0.1.0-draft.1'
AUTHORITY = 's02-h3-local-authority/0.1.0-draft.2'
BINDING = 's02-h3-work/0.1.0-draft.2'
HISTORY = 's02-h3-history-binding/0.1.0-draft.2'
ANCHOR = 's02-h3-anchor/0.1.0-draft.2'


def obj(**properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
def arr(items, *, unique=True):
    return dict(type='array', items=items, **({'uniqueItems': True} if unique else {}))
def nullable(spec): return {'anyOf': [spec, {'type': 'null'}]}
def ref(name): return {'$ref': '#/$defs/' + name}
def const(value): return {'const': value}
def enum(*values): return {'enum': list(values)}
def mapping(spec): return dict(type='object', propertyNames=ref('ID'), additionalProperties=spec)

ID = dict(type='string', format='s02-id')
TEXT = dict(type='string', format='s02-text')
HASH = dict(type='string', pattern='^[a-f0-9]{64}$')
INT = dict(type='integer', minimum=0)
TIME = dict(type='string', format='s02-time')
BOOL = dict(type='boolean')
IDS = arr(ref('ID'))
PAIR = dict(type='array', prefixItems=[ref('ID'), ref('ID')], minItems=2, maxItems=2, items=False)


def _definitions():
    d = deepcopy(get_profile(E1).schema['$defs'])
    d.update(ID=ID, Text=TEXT, Hash=HASH, Pair=PAIR)
    d['ReviewEntry'] = obj(issue_id=ID, reviewer=TEXT,
        assessment=enum('applicable','undetermined','not_applicable','complete','incomplete'), dependency_sha256=HASH)
    d['Registry'] = obj(format=const(REGISTRY), purpose=const('synthetic_historical_evidence_only'),
        registry_id=ID, store_id=ID, required_issue_ids=IDS, reviews=arr(ref('ReviewEntry')))
    d['ReviewsPin'] = obj(format=const(REGISTRY), registry_id=ID, store_id=ID, raw_sha256=HASH,
        required_issue_ids_sha256=HASH, reviews_sha256=HASH)
    d['RecordPin'] = obj(record_id=ID, sha256=HASH)
    d['EventPin'] = obj(command_id=ID, event_id=ID, sha256=HASH)
    d['SnapshotPin'] = obj(snapshot_id=ID, sha256=HASH, archive_sha256=HASH)
    d['History'] = obj(version=const(HISTORY), owner_profiles_sha256=HASH,
        records=arr(ref('RecordPin')), events=arr(ref('EventPin')), snapshots=arr(ref('SnapshotPin')),
        current_issues=mapping(ID), historical_reviews_pin=ref('ReviewsPin'))
    d['Alias'] = obj(id=ID, kind=enum('Actor','Action','Workflow','WorkflowNode','WorkflowEdge','Data','Rule',
        'Component','Responsibility','Interface','Dependency','Part','Issue'))
    d['Output'] = obj(unit_id=ID, step=dict(type='integer', minimum=1, maximum=4),
        origin_command_id=ID, output_ids=IDS, raw_sha256=HASH, source_refs=arr(ref('SourceRef')),
        aliases=mapping(ref('Alias')))
    d['Correspondence'] = obj(from_id=ID, to_id=nullable(ID), kind=enum('element','part','issue','row'),
        relation=enum('unchanged','current_ref_rebind','removed','modified'), from_context_sha256=HASH,
        to_context_sha256=nullable(HASH), reason=TEXT)
    d['AnchorTransition'] = obj(command_id=ID, from_pair=PAIR, to_pair=PAIR,
        source_context_id=ID, snapshot_id=ID, parent_assessment_sha256=nullable(HASH),
        result_assessment_sha256=HASH, diff_sha256=HASH, closure_sha256=HASH,
        correspondence=arr(ref('Correspondence')))
    d['Anchor'] = obj(version=const(ANCHOR), command_id=ID, plan_artifact_id=ID, plan_sha256=HASH,
        published_pair=PAIR, source_context_id=ID, snapshot_id=ID,
        transitions=arr(ref('AnchorTransition')), transition_hashes=arr(HASH,unique=False),
        outputs=arr(ref('Output')))
    d['Selector'] = obj(issue_id=ID, issue_key=ID, target_step=dict(type='integer',minimum=1,maximum=4),
        kind=enum('obligation_families','explicit_uses','all_source_uses'), source_refs=arr(ref('SourceRef')),
        element_ids=IDS, mapping_part_ids=IDS, impact_known=BOOL,
        code_task_role=nullable(enum('await_builder','global_mapping','merge_guard')))
    d['TaskOrigin'] = obj(issue_id=ID, issue_key=ID, origin_command_id=ID, root_issue_id=ID,
        unit_ids=IDS, target_step=dict(type='integer',minimum=1,maximum=4),
        role=enum('await_builder','global_mapping','merge_guard'), predicate=TEXT, origin_plan_sha256=HASH)
    d['GuardOrigin'] = obj(issue_id=ID, issue_key=ID, origin_command_id=ID, root_issue_id=ID,
        source_context_id=ID, base_pair=PAIR, failed_candidate_sha256=nullable(HASH),
        failed_analysis_sha256=HASH, predicate=TEXT, origin_plan_sha256=HASH)
    d['Assessment'] = obj(from_pair=PAIR, result_pair=PAIR, parent_assessment_sha256=nullable(HASH),
        source_sha256=HASH, diff_sha256=HASH, context_sha256=HASH, closure_sha256=HASH, proof_sha256=HASH,
        result_model_sha256=HASH, result_analysis_set_sha256=HASH, output_refs=arr(ref('Output')),
        state=enum('pending','current','assessed_held','needs_revalidation','terminal_out_of_scope'))
    d['Progress'] = obj(work_completed_through=dict(type='integer',minimum=0,maximum=4),
        outputs=arr(ref('Output')), actual_output_ids=IDS,
        assessment_state=enum('pending','current','assessed_held','needs_revalidation','terminal_out_of_scope'),
        unresolved_keys=IDS, next_tasks=arr(dict(type='integer',minimum=1,maximum=4)),
        latest_checked_pair=nullable(PAIR), assessment=nullable(ref('Assessment')))
    d['Obligation'] = obj(source_ref=ref('SourceRef'), mapping_row_id=ID,
        assessment=enum('not_assessed','proposed'), mapping_part_ids=IDS, issue_ids=IDS)
    d['IssueRoles'] = obj(issue_key=ID, predecessor_issue_id=nullable(ID), current_issue_id=ID,
        origin_issue_id=nullable(ID), obsolete_issue_id=nullable(ID), replacement_issue_id=nullable(ID))
    d['Transition'] = obj(issue_key=ID, branch=enum('DIRECT','CARRY','REPLACEMENT'),
        assessment=nullable(enum('applicable','undetermined','not_applicable','complete','incomplete')),
        proof_record_id=ID, proof_sha256=HASH, reason_codes=arr(TEXT))
    d['Admission'] = obj(marker=const(ADMISSION), policy_version=const(POLICY), from_pair=PAIR, result_pair=PAIR,
        obligations=arr(ref('Obligation')), selectors=mapping(ref('Selector')), tasks=mapping(ref('TaskOrigin')),
        guards=mapping(ref('GuardOrigin')), progress_by_unit=mapping(ref('Progress')),
        retained_assessments=arr(ref('Assessment')), issue_roles=arr(ref('IssueRoles')),
        transitions=arr(ref('Transition')), full_hold_reasons=arr(TEXT))
    d['InputPin'] = obj(stage_ref=ref('StageRef'), sha256=HASH, byte_length=INT, media_type=const('application/json'))
    d['Binding'] = obj(version=const(BINDING), purpose=const('synthetic_test_only'),
        provider_id=ID, provider_version=const('local-synthetic/1'), policy_version=const(POLICY),
        store_id=ID, session_id=ID, parent_command_id=ID, source_context_id=ID, snapshot_id=ID,
        archive_sha256=HASH, base_pair=PAIR, base_model_sha256=HASH, base_analysis_set_sha256=HASH,
        operation=enum('adopt','step','revalidate'), goal=enum('build','admission','retained_output'),
        step=dict(type='integer',minimum=0,maximum=4), unit_ids=IDS, aliases_sha256=HASH,
        current_selectors_sha256=HASH, progress_before_sha256=nullable(HASH),
        retained_assessment_hashes=arr(HASH), read_write_intent_sha256=HASH,
        candidate_sha256=nullable(HASH), candidate_length=INT, analysis_sha256=HASH, analysis_length=INT,
        history_sha256=HASH, anchor_sha256=nullable(HASH), historical_reviews_pin=ref('ReviewsPin'))
    d['Analysis'] = obj(version=const('s02-h3-analysis/0.1.0-draft.2'), source_context_id=ID,
        snapshot_id=ID, base_pair=PAIR, selectors_sha256=HASH, unit_ids=IDS,
        inspections=arr(obj(source_ref=ref('SourceRef'),read=enum('inspected','not_inspected'),
            verdict=enum('usable','held','not_relevant_with_reason'),basis_source_refs=arr(ref('SourceRef')),
            needed_facts=arr(TEXT),reason=TEXT)),
        independence=arr(obj(issue_key=ID,unit_id=ID,verdict=enum('independent','held','unknown'),
            basis_source_refs=arr(ref('SourceRef')),reason=TEXT)))
    d['Approval'] = obj(binding=ref('Binding'), decision=enum('allow','deny'), reason=TEXT)
    d['Authority'] = obj(format=const(AUTHORITY), provider_id=ID, provider_version=const('local-synthetic/1'),
        purpose=const('synthetic_test_only'), approvals=arr(ref('Approval')))
    pins=dict(profile_id=const(E1),contract_version=const(get_profile(E1).descriptor['contract_version']),
              rules_id=const(get_profile(E1).descriptor['rules_id']))
    d['Config'] = obj(**pins,marker=const(CONFIG),config_version=const(CONFIG),handler_version=const(HANDLER),
        policy_version=const(POLICY),limits_version=const(LIMITS),limits=obj(**{k:const(v) for k,v in vars(DEFAULTS).items()}),
        store_id=ID,session_id=ID,command_id=ID,parent_command_id=ID,reserved_run_id=ID,started_at=TIME,
        mode=enum('adopt','step','revalidate'),step=dict(type='integer',minimum=0,maximum=4),unit_ids=IDS,
        goal=enum('build','admission','retained_output'),source_context_id=ID,snapshot_id=ID,archive_sha256=HASH,
        base_model_id=ID,base_analysis_set_id=ID,base_model_sha256=HASH,base_analysis_set_sha256=HASH,
        anchor=nullable(ref('Anchor')),parent_metadata=nullable(ref('Admission')),aliases=mapping(ref('Alias')),
        inputs=obj(candidate=nullable(ref('InputPin')),analysis=ref('InputPin')),
        historical_reviews_pin=ref('ReviewsPin'),history_binding=ref('History'),
        authority_binding=ref('Binding'),intent_sha256=HASH)
    d['PlanBindings'] = obj(command_id=ID,session_id=ID,parent_command_id=ID,reserved_run_id=ID,
        primary_config_sha256=HASH,primary_config_stage_ref=ref('StageRef'),intent_sha256=HASH,
        base_pair=PAIR,history_sha256=HASH,anchor_sha256=nullable(HASH),authority_binding_sha256=HASH,
        historical_reviews_pin=ref('ReviewsPin'),handler_version=const(HANDLER))
    d['Promotion'] = obj(artifact_id=ID,stage_ref=ref('StageRef'))
    d['Plan'] = obj(**pins,marker=const(PLAN),plan_version=const(PLAN),bindings=ref('PlanBindings'),
        allocation=obj(plan_blob_id=ID,plan_artifact_id=ID,created_at=TIME,aliases=mapping(ref('Alias'))),
        batch=obj(records=arr(ref('Record')),artifact_sources=arr(ref('Promotion')),head=nullable(PAIR)),
        promotions=arr(ref('Promotion')),admission=nullable(ref('Admission')),
        candidate_outcome=enum('valid','blocked','rejected','guard_only','revalidated','adopted'),
        diagnostics=arr(ref('Error')))
    return d

_DEFS = _definitions()
KINDS = ('Config','Plan','Admission','History','Anchor','Registry','ReviewsPin','Binding','Authority','Selector','Progress','Analysis')


def schema(kind):
    need(kind in KINDS, 'contract_kind')
    return {'$schema':'https://json-schema.org/draft/2020-12/schema', '$ref':'#/$defs/'+kind,'$defs':deepcopy(_DEFS)}


def validate(kind, value, budget, *, input_lane=False, slot=None):
    need(type(budget) is Budget, 'shared_h3_budget')
    budget.inspect(value,input_lane=input_lane,slot=slot)
    errors=Validator(schema(kind),format_checker=FORMATS).iter_errors(value)
    error=next(errors,None)
    need(error is None, kind+'_shape'+(':'+ '/'.join(map(str,error.absolute_path)) if error else ''))
    budget.check()
    if kind in ('Binding','Config'):
        v=value
        mode=v['operation'] if kind=='Binding' else v['mode']
        need(bool(v['unit_ids']), 'work_units_nonempty')
        need((mode=='adopt')==(v['step']==0), 'mode_step')
        need((mode=='step')==(v['goal']=='build'), 'mode_goal')
        if kind=='Binding':
            need((v['candidate_sha256'] is None)==(mode!='step'),'candidate_mode')
            need((v['candidate_length']==0)==(v['candidate_sha256'] is None),'candidate_pin_length')
        else:
            need((v['inputs']['candidate'] is None)==(mode!='step'),'candidate_mode')
            need((v['parent_metadata'] is None)==(mode=='adopt'),'adopt_parent_metadata')
    if kind=='Anchor':
        need(value['transition_hashes']==[digest(x) for x in value['transitions']],'anchor_transition_hashes')
    if kind=='Progress':
        steps=[int(x['step']) for x in value['outputs']]
        need(sorted(steps)==list(range(1,int(value['work_completed_through'])+1)),'progress_proven_stages')
        need({i for x in value['outputs'] for i in x['output_ids']}<=set(value['actual_output_ids']),'progress_actual_inventory')
        need((value['assessment'] is None)==(value['latest_checked_pair'] is None),'progress_assessment_pin')
        if value['assessment'] is not None:
            need(value['assessment']['result_pair']==value['latest_checked_pair'] and
                 value['assessment']['state']==value['assessment_state'] and
                 value['assessment']['output_refs']==value['outputs'],'progress_assessment_correspondence')
    if kind=='Authority':
        keys=[digest(x['binding']) for x in value['approvals']]
        need(len(keys)==len(set(keys)),'authority_duplicate_binding')
        for x in value['approvals']:
            validate('Binding',x['binding'],budget)
            need(x['binding']['provider_id']==value['provider_id'],'authority_provider')
    return deepcopy(value)


@dataclass(frozen=True)
class Contract:
    """Exact immutable bytes, a shape capability only; never a grant of trust."""
    kind: str
    raw: bytes

    @classmethod
    def parse(cls,kind,raw,budget):
        lane={'Registry':'registry','Authority':'authority','Config':'config','Plan':'plan'}.get(kind,'raw')
        value=budget.parse(raw,slot='h3.'+kind,kind=lane)
        validate(kind,value,budget)
        return cls(kind,raw)

    def payload(self): return decode(self.raw)
