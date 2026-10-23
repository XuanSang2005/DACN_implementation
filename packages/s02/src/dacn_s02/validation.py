"""Draft.3 structural checks. No rationale, permissions or review are inferred."""
from datetime import datetime
from decimal import Decimal
from importlib.resources import files
import json
import re

from jsonschema import Draft202012Validator, FormatChecker, validators
from .codec_boundary import encode
from .errors import S02Error, require
from .profiles import L1, E1, get_profile, owner_profiles, blocking_statuses

COLLECTIONS = ("actors","actions","workflows","data","rules","components","responsibilities","interfaces","dependencies")
W = frozenset(chr(n) for n in (*range(9,14),*range(28,33),133,160,5760,*range(8192,8203),8232,8233,8239,8287,12288))
FORMATS = FormatChecker()

@FORMATS.checks("s02-id")
def valid_id(value): return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value) is not None

@FORMATS.checks("s02-text")
def text(value): return type(value) is str and any(c not in W for c in value)

@FORMATS.checks("s02-time")
def time(value):
    if type(value) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z",value) is None: return False
    try: datetime.fromisoformat(value); return True
    except ValueError: return False

@FORMATS.checks("s02-pointer")
def pointer(value):
    return type(value) is str and (value == "" or value.startswith("/")) and re.search(r"~(?![01])",value) is None

def number(_, value): return type(value) is int or type(value) is Decimal and value.is_finite()
def integer(_, value): return type(value) is int or type(value) is Decimal and value.is_finite() and value==value.to_integral_value()
TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({"number":number,"integer":integer})
Validator = validators.extend(Draft202012Validator,type_checker=TYPES)
SCHEMA = json.loads(files("dacn_s02").joinpath("schemas/contract.json").read_bytes())
Draft202012Validator.check_schema(SCHEMA)

def escape(value): return str(value).replace("~","~0").replace("/","~1")

def shape(value, name="Record", *, profile=L1):
    schema = get_profile(profile).schema
    encode(value)  # Reject unsupported floats/Unicode before diagnostics retain values.
    definition = schema["$defs"][name]
    require(definition is not False,"profile_export_unavailable")
    if name == "Record" and type(value) is dict and type(value.get("type")) is str and value["type"]+"Record" in schema["$defs"]:
        definition = schema["$defs"][value["type"]+"Record"]
    if name == "OperationEvent" and type(value) is dict and type(value.get("kind")) is str and value["kind"]+"Event" in schema["$defs"]:
        definition = schema["$defs"][value["kind"]+"Event"]
    errors = list(Validator({**definition,"$defs":schema["$defs"]},format_checker=FORMATS).iter_errors(value))
    if errors:
        e=errors[0]; path="".join("/"+escape(v) for v in e.absolute_path)
        raise S02Error("SCHEMA_INVALID","schema","Value violates the S02 schema",pointer=path,
                       details={"keyword":str(e.validator),"expected":ascii(e.validator_value)})

def resolve_pointer(value, path):
    if not pointer(path): raise ValueError("Invalid JSON Pointer")
    for token in ([] if path == "" else path[1:].split("/")):
        token=token.replace("~1","/").replace("~0","~")
        if type(value) is list:
            if re.fullmatch(r"0|[1-9][0-9]*",token) is None: raise ValueError("Invalid array index")
            value=value[int(token)]
        elif type(value) is dict: value=value[token]
        else: raise ValueError("Pointer traverses a scalar")
    return value

def walk_schema(value, spec, path="", *, profile=L1, _schema=None):
    """Yield value + resolved field schema; local refs only, never network refs."""
    schema = get_profile(profile).schema if _schema is None else _schema
    name=None
    if "$ref" in spec:
        name=spec["$ref"].split("/")[-1];spec={**schema["$defs"][name], **{k:v for k,v in spec.items() if k!="$ref"}}
    yield value,spec,path,name
    if "anyOf" in spec:
        if value is not None: yield from walk_schema(value,spec["anyOf"][0],path,profile=profile,_schema=schema)
    elif "oneOf" in spec:
        for variant in spec["oneOf"]:
            v=schema["$defs"][variant["$ref"].split("/")[-1]] if "$ref" in variant else variant
            if not list(Validator({**v,"$defs":schema["$defs"]},format_checker=FORMATS).iter_errors(value)):
                yield from walk_schema(value,variant,path,profile=profile,_schema=schema);break
    elif spec.get("type")=="object":
        for k,s in spec.get("properties",{}).items():
            if k in value: yield from walk_schema(value[k],s,path+"/"+escape(k),profile=profile,_schema=schema)
    elif spec.get("type")=="array":
        for i,v in enumerate(value): yield from walk_schema(v,spec["items"],path+"/"+str(i),profile=profile,_schema=schema)

def fields(record, *, profile=L1):
    schema=get_profile(profile).schema
    return walk_schema(record,schema["$defs"][record["type"]+"Record"],profile=profile,_schema=schema)

def typed_links(record, *, profile=L1):
    out=[]
    for v,s,p,n in fields(record,profile=profile):
        if "x-record" in s: out.append((p,v,s["x-record"]))
    return out

def index_model(record):
    b=record["body"]; elements={x["id"]:x for k in COLLECTIONS for x in b[k]}
    parts={p["id"]:p for m in b["mappings"] for p in m["parts"]}
    return elements,parts

def scope_sets(scope): return set(scope["element_ids"]),set(scope["mapping_part_ids"])
def subset(a,b): return a["model_id"]==b["model_id"] and all(x<=y for x,y in zip(scope_sets(a),scope_sets(b)))
def inventory(snapshot):
    return {f"/{k}/{i}"+suffix for k in ("functional_requirements","non_functional_requirements","constraints")
            for i,r in enumerate(snapshot["input"][k]) for suffix in ["",*[f"/acceptance_criteria/{j}" for j in range(len(r["acceptance_criteria"]))]]}

def validate_record(record, records, snapshots, *, events=None, stages=None, commands=None, owner_profile=L1, profile_map=None, reviews=None):
    """Validate one immutable record against a complete same-session graph."""
    profile=get_profile(owner_profile).profile_id
    profiles=owner_profiles(records,profile,profile_map)
    require(profiles.get(record["id"])==profile,"record_owner_profile")
    shape(record,profile=profile); rid=record["id"];b=record["body"];kind=record["type"]
    def check(ok,inv): require(ok,inv,record_id=rid)
    def get(i,t=None):
        v=records.get(i);check(v is not None and (t is None or v["type"]==t),"typed_record_reference");return v["body"]
    context_id=b.get("source_context_id")
    if kind=="source_context": context_id=rid
    elif context_id is None and b.get("model_id"): context_id=get(b["model_id"],"model")["source_context_id"]
    snapshot_id=get(context_id,"source_context")["snapshot_id"] if context_id else None
    for value,spec,path,name in fields(record,profile=profile):
        history = profile==E1 and spec.get("x-history",False)
        if "x-record" in spec:
            target=records.get(value);expected=spec["x-record"]
            check(target is not None and (expected=="*" or target["type"] in ([expected] if type(expected) is str else expected)),"typed_record_reference")
        if spec.get("x-command"):
            check(commands is not None and value in commands,"command_reference")
        if name=="SourceRef":
            snap=snapshots.get(value["snapshot_id"])
            try:
                if snap is None: raise ValueError()
                resolve_pointer(snap["input"],value["input_pointer"])
                if snapshot_id is not None and kind not in ("change","answer") and value["snapshot_id"]!=snapshot_id and not history: raise ValueError()
            except (KeyError,IndexError,ValueError):
                raise S02Error("SOURCE_REF_INVALID","references","Source reference does not resolve in the pinned snapshot",record_id=rid,pointer=path,details={**value,"expected_kind":"pinned source value"})
        if name=="AnswerRef":
            try: resolve_pointer(get(value["answer_id"],"answer"),value["pointer"])
            except (KeyError,IndexError,ValueError): check(False,"answer_pointer")
        if name in ("Scope","ElementRef"):
            model=records.get(value["model_id"]);check(model is not None and model["type"]=="model","scope_model")
            es,ps=index_model(model)
            if b.get('model_id') is not None and not history: check(value['model_id']==b['model_id'],'nested_reference_model')
            if name=="Scope": check(set(value["element_ids"])<=es.keys() and set(value["mapping_part_ids"])<=ps.keys(),"scope_members")
            else: check(value["element_id"] in es or value["element_id"] in ps,"element_reference")
        if name=="Trace": check(bool(value["source_refs"] or value["answer_refs"]),"trace_has_source")
        if name=="EventRef":
            check(commands is not None and value["command_id"] in commands,"event_session")
            check(events is not None and (value["command_id"],value["event_id"]) in events,"event_reference")
        if name=="StageRef": check(stages is not None and (value["command_id"],value["blob_id"]) in stages,"stage_reference")
    if kind=="artifact": check(b["producer_run_id"] is not None or b["purpose"] in ("s01_envelope","s01_run_source","s01_origin_source","schema"),"artifact_producer")
    if kind=="source_context":
        for field,purpose in (("envelope_artifact_id",("s01_envelope",)),("schema_artifact_id",("schema",)),("run_source_artifact_id",("s01_run_source","s01_origin_source")),("origin_source_artifact_id",("s01_run_source","s01_origin_source"))):
            a=get(b[field],"artifact");check(a["purpose"] in purpose and a["producer_run_id"] is None,"source_archive_kind")
    if kind=="run":
        check((b["base_model_id"] is None)==(b["base_analysis_set_id"] is None),"run_base_pair")
        check(b["completed_at"]>=b["started_at"],"run_time_order")
        check(b["status"] not in ("failed","rejected","stale") or bool(b["errors"]),"run_error_required")
        check(len({a["id"] for a in b["attempts"]})==len(b["attempts"]),"attempt_ids_unique")
        if b["base_analysis_set_id"]: check(get(b["base_analysis_set_id"])["model_id"]==b["base_model_id"],"run_base_set")
        check(get(b["config_artifact_id"])["purpose"]=="config","run_config")
        for a in b["attempts"]:
            check(a["base_model_id"]==b["base_model_id"] and a["base_analysis_set_id"]==b["base_analysis_set_id"],"attempt_base")
            for field,p in (("prompt_artifact_id","prompt"),("request_artifact_id","llm_request"),("response_artifact_id","llm_response")):
                if a[field]: check(get(a[field])["purpose"]==p,"attempt_artifact_kind")
            if a["status"] in ("completed","invalid_output","refused","incomplete"): check(a["response_artifact_id"] is not None,"attempt_response_required")
    for value,spec,path,name in fields(record,profile=profile):
        if name=="Error":
            check(value['stage']!='parse' or value['pointer'] is None,'parse_error_pointer_null')
        if name in ('Actor','Action','Data','Rule','Workflow','Component','Responsibility','Interface','Dependency'):
            if value['state']=='needs_clarification':
                check(any(get(i,'issue')['status'] in blocking_statuses(profile) for i in value['trace']['issue_ids']),'clarification_state_issue')
            if value['state']=='needs_reanalysis':
                check(kind=='model' and b['change_id'] is not None,'reanalysis_state_change')
    if kind=="model": validate_model(record,records,snapshots[snapshot_id],owner_profile=profile)
    if kind=="issue":
        if profile==E1 and (b['resolution_carry'] is not None or b['resolution_replacement'] is not None):
            from .resolution import validate_resolution
            validate_resolution(record,records,snapshots,events=events,stages=stages,commands=commands,profiles=profiles,reviews=reviews)
        else:
            validate_direct(record,records,events)
    if kind=="answer":
        if b["interpretation"]=="points_to_existing_source": check(bool(b["existing_source_refs"]),"answer_existing_source")
        if b["supersedes_answer_id"]: check(get(get(b["supersedes_answer_id"])["issue_id"])["issue_key"]==get(b["issue_id"])["issue_key"],"answer_lineage")
    if kind in ("scenario","characteristic"):
        check(b["scope"]["model_id"]==b["model_id"],"analysis_scope_model")
        if b["supersedes_id"]: check(get(b["supersedes_id"],kind)["analysis_key"]==b["analysis_key"],"analysis_lineage")
    if kind=="scenario":
        check([w["order"] for w in b["walkthrough"]]==list(range(1,len(b["walkthrough"])+1)),"walk_order")
        check(all(r["input_pointer"] in inventory(snapshots[snapshot_id]) for r in b["expected_obligations"]),"scenario_obligation_kind")
    if kind=="characteristic":
        opts={o["id"]:o for o in b["options"]};check(len(opts)==len(b["options"]),"option_ids")
        option=opts.get(b["recommended_option_id"])
        check((b["recommendation"]=="undecided" and option is None and b["recommended_option_id"] is None) or
              (b["recommendation"]!="undecided" and option is not None and (option["action"]=="keep")== (b["recommendation"]=="keep")),"recommended_option")
        for option in b['options']:
            check(all(s['input_pointer'].startswith('/constraints/') and s['input_pointer'] in inventory(snapshots[snapshot_id]) for s in option['constraint_refs']),'option_constraint_source_kind')
    if kind=="analysis_set": validate_set(record,records,owner_profile=profile,profile_map=profiles)
    if kind=="change": validate_change(record,records)
    if kind=="view":
        m=get(b["model_id"]);cs={x["id"] for x in m["components"]}; ins={x["id"]:x for x in m["interfaces"]};deps={x["id"]:x for x in m["dependencies"]}
        check(set(b["component_ids"])<=cs and set(b["interface_ids"])<=ins.keys() and set(b["dependency_ids"])<=deps.keys(),"view_members")
        needed={ins[i]["provider_component_id"] for i in b["interface_ids"]}
        for i in b["dependency_ids"]:
            d=deps[i];needed.update((d["consumer_component_id"],d["provider_component_id"]))
            check(d["interface_id"] is None or d["interface_id"] in b["interface_ids"],"view_interface_closed")
        check(needed<=set(b["component_ids"]),"view_endpoints_closed")
        check(set(b["omitted_element_ids"])==(cs|ins.keys()|deps.keys())-set(b["component_ids"]+b["interface_ids"]+b["dependency_ids"]),"view_omitted_inventory")
    if kind in ("validation","bundle","handoff"):
        a=get(b["analysis_set_id"]);check(a["model_id"]==b["model_id"],"analysis_model_binding")
    if kind=="bundle":
        for k in ("scenario_ids","characteristic_ids","issue_ids"): check(set(b[k])==set(a[k]),"bundle_current_selection")
        check(get(b["model_id"])["source_context_id"]==b["source_context_id"],"bundle_source")
        v=get(b["validation_id"]);check(v["analysis_set_id"]==b["analysis_set_id"] and v["model_id"]==b["model_id"],"bundle_validation")
        check(get(b['view_id'])['model_id']==b['model_id'] and get(b['diagram_id'])['model_id']==b['model_id'] and get(b['diagram_id'])['view_id']==b['view_id'],'bundle_view_diagram')
        check(v['view_id']==b['view_id'] and v['diagram_id']==b['diagram_id'],'bundle_validation_artifacts')
        if b["status"]=="awaiting_review": check(all(x=="passed" for x in v["checks"].values()) and v["readability"]["status"]=="acceptable" and get(b["diagram_id"])["status"]=="ready","bundle_ready_gate")
    if kind=="validation" and b["readability"]["status"]=="acceptable": check(b["readability"]["reviewer"] is not None and b["readability"]["note"] is not None,"readability_human")
    if kind=="diagram":
        if b["status"]=="not_run": check(b["svg_artifact_id"] is None,"diagram_not_run")
        if b["status"]=="ready": check(b["puml_artifact_id"] is not None and b["svg_artifact_id"] is not None and b["validation_id"] is not None and all(get(b["validation_id"])["checks"][k]=="passed" for k in ("conversion","render","fidelity")),"diagram_ready")
    if kind=="review":
        bundle=get(b['bundle_id'],'bundle')
        check(b['model_id']==bundle['model_id'] and b['source_context_id']==bundle['source_context_id'],'review_bundle_binding')
        check(b['accepted_scope']['model_id']==b['model_id'] and b['blocked_scope']['model_id']==b['model_id'],'review_scope_model')
        if b['decision'] in ('accepted','conditionally_accepted'): check(bundle['status']=='awaiting_review','review_bundle_ready')
        check(not any(x&y for x,y in zip(scope_sets(b["accepted_scope"]),scope_sets(b["blocked_scope"]))),"review_scopes_disjoint")
        check(b["decision"] not in ("request_changes","revoked") or not any(scope_sets(b["accepted_scope"])),"review_no_acceptance")
        if b["decision"]=="conditionally_accepted": check(bool(b["conditions"]),"review_conditions")
        # E1 contract correction only: retain the pinned L1 validation behavior.
        if profile==E1:
            previous=b['supersedes_review_id']
            check(b['decision']!='revoked' or previous is not None,'review_revocation_predecessor')
            if previous is not None:
                check(previous!=rid and get(previous,'review')['bundle_id']==b['bundle_id'],'review_predecessor_binding')
    if kind=="handoff":
        bundle=get(b['bundle_id'],'bundle')
        check(bundle['model_id']==b['model_id'] and bundle['analysis_set_id']==b['analysis_set_id'],'handoff_bundle_binding')
        check(b['allowed_scope']['model_id']==b['model_id'] and b['blocked_scope']['model_id']==b['model_id'],'handoff_scope_model')
        check(b["eligible"] or not any(scope_sets(b["allowed_scope"])),"false_handoff_empty")
        if b['eligible']:
            check(b['review_id'] is not None,'eligible_review_required');review=get(b['review_id'],'review')
            check(review['bundle_id']==b['bundle_id'] and review['decision'] in ('accepted','conditionally_accepted'),'eligible_review_binding')
            check(b['workflow_choices']==review['workflow_choices'],'handoff_review_choices')
            check(set(b['condition_ids'])=={c['id'] for c in review['conditions']},'handoff_conditions')
            from .scope import permitted_scope
            tasks=[]
            for changeid in bundle['change_ids']: tasks.extend(get(changeid,'change')['reevaluate'])
            result=permitted_scope(records[b['model_id']],review['accepted_scope'],review['accepted_scope'],current_analysis_set_id=b['analysis_set_id'],reviewed_analysis_set_id=bundle['analysis_set_id'],issues=[records[i] for i in a['issue_ids']],pending_tasks=tasks,conditions=review['conditions'],choices=review['workflow_choices'],profile=profile)
            check(bool(result['allowed_scope']['mapping_part_ids']) and result['allowed_scope']==b['allowed_scope'] and result['blocked_scope']==b['blocked_scope'],'handoff_closed_allowed_scope')

def validate_direct(record,records,events):
    """Unchanged a3 root-resolution rules. Operations verify atomic selection."""
    rid=record['id'];b=record['body']
    def check(ok,inv): require(ok,inv,record_id=rid)
    def get(i,t=None):
        v=records.get(i);check(v is not None and (t is None or v['type']==t),'typed_record_reference');return v['body']
    check(b["affected"]["model_id"]==b["model_id"] and subset(b["blocking"],b["affected"]),"issue_blocking_subset")
    check(b["status"] not in ("open","answered_pending_application") or not b["resolution_event_refs"],"pending_issue_not_applied")
    if b["status"]=="resolved":
        check(b["resolution"] is not None and bool(b["resolution_event_refs"] or b["trace"]["source_refs"]),"issue_resolution_evidence")
        if b["answer_ids"]:
            check(bool(b["resolution_event_refs"]),"answer_resolution_event")
            applied_answers=set()
            for reference in b["resolution_event_refs"]:
                event=events[reference["command_id"],reference["event_id"]]
                check(event['kind']=='application_applied','issue_resolution_application_event')
                payload=event['payload']
                check(payload['resolved_issue_id']==rid,'issue_resolution_target')
                answer=get(payload['answer_id'],'answer')
                check(get(answer['issue_id'],'issue')['issue_key']==b['issue_key'],'issue_resolution_answer_lineage')
                change=get(payload['change_id'],'change')
                check(reference in change['application_event_refs'] and change['new_model_id']==b['model_id'],'issue_resolution_change')
                applied_answers.add(payload['answer_id'])
            check(applied_answers<=set(b['answer_ids']),'issue_resolution_answers_applied')
            check(all(get(get(a,'answer')['issue_id'],'issue')['issue_key']==b['issue_key'] for a in b['answer_ids']),'issue_answer_lineage')
        else:
            check(not b['resolution_event_refs'] and bool(b['trace']['source_refs']),'source_only_resolution')
    if b["supersedes_id"]: check(get(b["supersedes_id"])["issue_key"]==b["issue_key"],"issue_lineage")

def validate_model(record, records, snapshot, *, owner_profile=L1):
    profile=get_profile(owner_profile).profile_id
    b=record["body"];rid=record["id"]
    def check(ok,inv): require(ok,inv,record_id=rid)
    creator=records.get(b['created_by_run_id'])
    check(creator is not None and creator['type']=='run' and creator['body']['result_model_id']==rid,'model_creator_result')
    maps={k:{x["id"]:x for x in b[k]} for k in COLLECTIONS}
    all_ids=[x["id"] for k in COLLECTIONS for x in b[k]]+[m["id"] for m in b["mappings"]]+[p["id"] for m in b["mappings"] for p in m["parts"]]+[x["id"] for w in b["workflows"] for k in ("nodes","edges") for x in w[k]]
    check(len(all_ids)==len(set(all_ids)),"model_ids_unique")
    def local(values,kind): check(set(values)<=maps[kind].keys(),"typed_local_reference_"+kind)
    def local_fields(v, fields):
        for field,target in fields.items(): local(v[field],target)
    check({a["name"] for a in b["actors"] if a["kind"]=="supplied"}==set(snapshot["input"]["actors"]),"supplied_actors_preserved")
    for a in b["actors"]:
        if a["kind"]=="supplied": check(any(re.fullmatch(r'/actors/(0|[1-9][0-9]*)',s['input_pointer']) is not None and resolve_pointer(snapshot["input"],s["input_pointer"])==a["name"] for s in a["trace"]["source_refs"]),"supplied_actor_source")
    for a in b["actions"]:
        check(bool(a["actor_ids"])==(a["initiator"]=="external"),"action_initiator_actors")
        local_fields(a,{"actor_ids":"actors","permission_rule_ids":"rules","rule_ids":"rules","read_data_ids":"data","write_data_ids":"data","workflow_ids":"workflows"})
        check(all(maps["rules"][i]["kind"]=="permission" for i in a["permission_rule_ids"]),"permission_rule_type")
    for r in b["rules"]: local(r["action_ids"],"actions")
    for w in b["workflows"]:
        nodes={n["id"]:n for n in w["nodes"]};check(w["entry_node_id"] in nodes,"workflow_entry")
        for n in w["nodes"]:
            check((n["action_id"] is not None)==(n["kind"]=="action"),"workflow_node_kind")
            if n["action_id"]: local([n["action_id"]],"actions")
        for e in w["edges"]:
            check(e["from"] in nodes and e["to"] in nodes,"workflow_edge_endpoint")
            check(nodes[e["from"]]["kind"]!="decision" or e["guard"] is not None,"decision_guard")
        check(len({p["node_id"] for p in w["branch_points"]})==len(w["branch_points"]),"branch_unique")
        for p in w["branch_points"]: check(p["node_id"] in nodes and sum(e["from"]==p["node_id"] for e in w["edges"])>=2,"branch_outgoing")
    for r in b["responsibilities"]:
        local([r["component_id"]],"components");local(r["action_ids"],"actions");local(r["rule_ids"],"rules")
    for i in b["interfaces"]:
        local([i["provider_component_id"]],"components");local(i["responsibility_ids"],"responsibilities")
        check(all(maps["responsibilities"][r]["component_id"]==i["provider_component_id"] for r in i["responsibility_ids"]),"interface_provider")
    for d in b["dependencies"]:
        local([d["consumer_component_id"],d["provider_component_id"]],"components")
        check(d["consumer_component_id"]!=d["provider_component_id"],"dependency_distinct_endpoints")
        local(d["action_ids"],"actions");local(d["workflow_ids"],"workflows");check(bool(d["action_ids"] or d["workflow_ids"]),"dependency_trigger")
        check((d["interface_id"] is not None)==(d["kind"]=="requires_interface"),"dependency_interface_kind")
        if d["interface_id"]:
            local([d["interface_id"]],"interfaces");check(maps["interfaces"][d["interface_id"]]["provider_component_id"]==d["provider_component_id"],"dependency_provider")
        expected=set(d["action_ids"]) or {n["action_id"] for w in d["workflow_ids"] for n in maps["workflows"][w]["nodes"] if n["action_id"]}
        check(len(d["support"])==len(expected) and {s["action_id"] for s in d["support"]}==expected,"dependency_support_inventory")
        for s in d["support"]:
            local(s["provider_responsibility_ids"],"responsibilities")
            if s["required_action_ids"] is not None: local(s["required_action_ids"],"actions")
            check(all(maps["responsibilities"][r]["component_id"]==d["provider_component_id"] for r in s["provider_responsibility_ids"]),"support_provider")
            if d["interface_id"]: check(set(s["provider_responsibility_ids"])<=set(maps["interfaces"][d["interface_id"]]["responsibility_ids"]),"support_interface")
    expected=inventory(snapshot);seen=[]
    for m in b["mappings"]:
        check(m["source_ref"]["snapshot_id"]==snapshot["snapshot_id"] and m["source_ref"]["input_pointer"] in expected,"mapping_source_kind")
        seen.append(m["source_ref"]["input_pointer"])
        check(bool(m["parts"]) or m["assessment"]=="not_assessed" and bool(m["issue_ids"]),"mapping_empty_not_assessed")
        for p in m["parts"]:
            local(p["action_ids"],"actions");local(p["primary_responsibility_ids"]+p["supporting_responsibility_ids"],"responsibilities")
            check(not set(p["primary_responsibility_ids"])&set(p["supporting_responsibility_ids"]),"part_responsibilities_disjoint")
            if p["target"]=="system": check(not p["action_ids"],"system_part_actions")
            elif p["assignment"]=="proposed": check(bool(p["action_ids"] and p["primary_responsibility_ids"]),"component_part_actions_responsibility")
            if p["assignment"] in ("unassigned","blocked"): check(p["remaining_gap"] is not None,"part_gap")
            if p["assignment"]=="blocked": check(any(records[i]["body"]["status"] in blocking_statuses(profile) for i in p["issue_ids"]),"part_blocking_issue")
    missing=expected-set(seen)
    if missing: raise S02Error("MAPPING_INVENTORY_INCOMPLETE","references","Requirement/criterion mappings missing",record_id=rid,details={"missing_refs":[{"snapshot_id":snapshot["snapshot_id"],"input_pointer":p} for p in sorted(missing)]})
    check(len(seen)==len(set(seen)),"mapping_row_unique")
    parent=b["parent_model_id"]
    if parent is None: check(b["revision"]==1 and b["change_id"] is None,"initial_model")
    else:
        old=records[parent]["body"];check(b["revision"]==old["revision"]+1 and b["change_id"] is not None,"model_revision")
        c=records[b["change_id"]]["body"];check(c["base_model_id"]==parent and c["new_model_id"]==rid,"model_change_binding")

def validate_set(record,records, *, owner_profile=L1, profile_map=None):
    profiles=owner_profiles(records,owner_profile,profile_map)
    b=record["body"];rid=record["id"]
    def check(ok,inv): require(ok,inv,record_id=rid)
    old=records[b["parent_set_id"]]["body"] if b["parent_set_id"] else None
    check((old is None and b["revision"]==1) or old is not None and old["model_id"]==b["model_id"] and b["revision"]==old["revision"]+1,"analysis_set_revision")
    selected=set();previous=set();affected_e=set();affected_p=set()
    for field,typ,key in (("scenario_ids","scenario","analysis_key"),("characteristic_ids","characteristic","analysis_key"),("issue_ids","issue","issue_key")):
        curr={records[i]["body"][key]:i for i in b[field]};check(len(curr)==len(b[field]),"analysis_key_unique")
        prev={records[i]["body"][key]:i for i in old[field]} if old else {}
        check(prev.keys()<=curr.keys(),"analysis_keys_not_dropped")
        selected.update(curr.values());previous.update(prev.values())
        for k,i in curr.items():
            item=records[i]["body"];check(item["model_id"]==b["model_id"],"analysis_current_model")
            if k in prev and prev[k]!=i: check(item["supersedes_id"]==prev[k],"analysis_current_successor")
            if k not in prev and old: check(item["supersedes_id"] is None,"analysis_new_key")
            if i not in previous:
                for body in ([item,records[prev[k]]["body"]] if k in prev else [item]):
                    scope=body["affected" if typ=="issue" else "scope"];affected_e.update(scope["element_ids"]);affected_p.update(scope["mapping_part_ids"])
            for path,target,t in typed_links(records[i],profile=profiles[i]):
                if profiles[i]==E1 and path in ("/body/resolution_carry/origin_issue_id","/body/resolution_carry/from_issue_id","/body/resolution_replacement/origin_issue_id","/body/resolution_replacement/from_issue_id","/body/resolution_replacement/obsolete_issue_id"): continue
                if t=="issue" and not (target==item.get("supersedes_id") and (profiles[i]==L1 or path=="/body/supersedes_id")): check(target in b["issue_ids"],"analysis_issue_ref_current")
                if t=="scenario" and not (target==item.get("supersedes_id") and (profiles[i]==L1 or path=="/body/supersedes_id")): check(target in b["scenario_ids"],"analysis_scenario_ref_current")
    check(set(b["changed_record_ids"])==selected-previous,"analysis_changed_inventory")
    es,ps=index_model(records[b["model_id"]]);scope=b["affected"]
    check(scope["model_id"]==b["model_id"],"analysis_affected_model")
    if old is None: check(set(scope["element_ids"])==es.keys() and set(scope["mapping_part_ids"])==ps.keys(),"initial_analysis_affected_all")
    else:
        from .scope import reverse_impact
        impact=reverse_impact(records[b["model_id"]],affected_e,affected_p)
        check(set(impact["element_ids"])<=set(scope["element_ids"]) and set(impact["mapping_part_ids"])<=set(scope["mapping_part_ids"]),"analysis_affected_closure")

def validate_change(record,records):
    b=record["body"];check=lambda ok,inv:require(ok,inv,record_id=record["id"])
    old=records[b["base_model_id"]]["body"];new=records[b["new_model_id"]]["body"]
    check(new["parent_model_id"]==b["base_model_id"] and new["change_id"]==record["id"],"change_model_binding")
    check(old["source_context_id"]==b["old_source_context_id"] and new["source_context_id"]==b["new_source_context_id"],"change_source_binding")
    check(b["affected"]["model_id"]==b["new_model_id"],"change_affected_model")
    if b["kind"]=="analysis_edit": check(b["old_source_context_id"]==b["new_source_context_id"],"analysis_edit_source")
    else: check(records[b["old_source_context_id"]]["body"]["snapshot_id"]!=records[b["new_source_context_id"]]["body"]["snapshot_id"],"requirements_switch_snapshot")
    oe,op=index_model(records[b["base_model_id"]]);ne,np=index_model(records[b["new_model_id"]]);oldids=oe.keys()|op.keys();newids=ne.keys()|np.keys()
    for o in b["operations"]:
        check(o["element_id"] in (oldids-newids if o["kind"]=="remove" else newids-oldids if o["kind"]=="add" else oldids&newids),"change_operation_membership")
    for t in b["reevaluate"]:
        check(t["scope"]["model_id"]==b["new_model_id"],"change_task_model")
        if t["status"]=="completed": check(bool(t["evidence_record_ids"]) and all(i in records and records[i]["body"].get("model_id")==b["new_model_id"] for i in t["evidence_record_ids"]),"change_task_evidence")
