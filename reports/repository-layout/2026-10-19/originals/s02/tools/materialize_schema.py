"""Build the checked-in Draft 2020-12 schema from the draft.3 field tables.

No input examples are used to infer fields. x-* annotations drive typed links;
they do not assert semantic truth. Run only when maintaining this artifact.
"""
import json
from pathlib import Path

DEFS = {}
def ref(name): return {"$ref": "#/$defs/" + name}
def obj(**fields): return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}
def arr(items, minimum=0, unique=False): return {"type": "array", "items": items, "minItems": minimum, "uniqueItems": unique}
def enum(*values): return {"enum": list(values)}
def nullable(value): return {"anyOf": [value, {"type": "null"}]}
def integer(minimum=0, maximum=None): return {"type": "integer", "minimum": minimum, **({"maximum": maximum} if maximum is not None else {})}
ID = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", "format": "s02-id"}
TEXT = {"type": "string", "format": "s02-text"}
TIME = {"type": "string", "format": "s02-time"}
POINTER = {"type": "string", "format": "s02-pointer"}
DIGEST = {"type": "string", "pattern": "^[a-f0-9]{64}$", "minLength": 64, "maxLength": 64}
BOOL = {"type": "boolean"}
def rid(kind): return {**ID, "x-record": kind}
def ids(kind=None): return arr(rid(kind) if kind else ID, unique=True)
def texts(): return arr(TEXT)
def d(name, value): DEFS[name] = value; return ref(name)

source = d("SourceRef", obj(snapshot_id=ID, input_pointer=POINTER))
answer = d("AnswerRef", obj(answer_id=rid("answer"), pointer=POINTER))
element = d("ElementRef", obj(model_id=rid("model"), element_id=ID))
scope = d("Scope", obj(model_id=rid("model"), element_ids=ids(), mapping_part_ids=ids()))
event = d("EventRef", obj(command_id=ID, event_id=ID))
stage = d("StageRef", obj(command_id=ID, blob_id=ID))
trace = d("Trace", obj(origin=enum("explicit", "inferred"), source_refs=arr(source), answer_refs=arr(answer), rationale=TEXT, issue_ids=ids("issue")))
state = enum("draft", "ready", "needs_clarification", "needs_reanalysis")
def entity(**fields): return obj(id=ID, trace=trace, state=state, **fields)
usage = d("Usage", obj(input_tokens=integer(), cached_input_tokens=integer(), output_tokens=integer(), cost_usd=nullable({"type":"string", "pattern":"^[0-9]+(\\.[0-9]+)?$"}), price_source=nullable(TEXT)))
error = d("Error", obj(code=TEXT, stage=enum("intake", "parse", "schema", "references", "revision", "llm", "render", "review", "persistence"), record_id=nullable(ID), pointer=nullable(POINTER), related_ids=ids(), message=TEXT, details={"type":"object"}))
attempt = d("Attempt", obj(id=ID, step=integer(1,9), base_model_id=nullable(rid("model")), base_analysis_set_id=nullable(rid("analysis_set")), prompt_artifact_id=rid("artifact"), request_artifact_id=rid("artifact"), response_artifact_id=nullable(rid("artifact")), provider=TEXT, requested_model=TEXT, returned_model=nullable(TEXT), provider_response_id=nullable(TEXT), transport_attempt=integer(1), repair_round=integer(), status=enum("completed","refused","incomplete","transport_failed","unknown_outcome","invalid_output","stale"), usage=nullable(usage), elapsed_ms=integer()))
purposes = ["s01_envelope","s01_run_source","s01_origin_source","schema","llm_request","llm_response","config","prompt","puml","svg"]
B = {}
B["artifact"] = obj(media_type=TEXT, sha256=DIGEST, byte_length=integer(), purpose=enum(*purposes), producer_run_id=nullable(rid("run")))
B["source_context"] = obj(store_key=ID, s01_run_id=ID, snapshot_id=ID, envelope_artifact_id=rid("artifact"), run_source_artifact_id=rid("artifact"), origin_source_artifact_id=rid("artifact"), schema_artifact_id=rid("artifact"))
B["run"] = obj(mode=enum("live","replay"), source_context_id=rid("source_context"), config_artifact_id=rid("artifact"), base_model_id=nullable(rid("model")), base_analysis_set_id=nullable(rid("analysis_set")), command_id={**ID,"x-command":True}, result_analysis_set_id=nullable(rid("analysis_set")), steps=arr(integer(1,9),unique=True), status=enum("completed","blocked","rejected","failed","stale","interrupted"), result_model_id=nullable(rid("model")), started_at=TIME, completed_at=TIME, attempts=arr(attempt), errors=arr(error))
B["issue"] = obj(issue_key=ID, supersedes_id=nullable(rid("issue")), model_id=rid("model"), detected_step=integer(1,9), kind=enum("business","quality_target","analysis_omission","design_choice","verification"), question=TEXT, reason=TEXT, trace=trace, affected=scope, blocking=scope, status=enum("open","answered_pending_application","resolved","withdrawn"), answer_ids=ids("answer"), resolution_event_refs=arr(event), resolution=nullable(TEXT))
B["answer"] = obj(issue_id=rid("issue"), supersedes_answer_id=nullable(rid("answer")), respondent=TEXT, recorded_by=TEXT, text=TEXT, interpretation=enum("points_to_existing_source","changes_requirements","needs_interpretation"), existing_source_refs=arr(source))
actor = d("Actor", entity(name=TEXT,kind=enum("supplied","candidate")))
action = d("Action", entity(name=TEXT,initiator=enum("external","internal","unknown"),actor_ids=ids(),permission_rule_ids=ids(),read_data_ids=ids(),write_data_ids=ids(),rule_ids=ids(),workflow_ids=ids()))
node = d("Node", obj(id=ID,action_id=nullable(ID),kind=enum("action","decision","end"),label=TEXT))
edge = d("Edge", obj(id=ID,**{"from":ID,"to":ID},guard=nullable(TEXT),trace=trace))
branch = d("BranchPoint", obj(node_id=ID,mode=enum("exclusive","unknown"),trace=trace))
workflow = d("Workflow", entity(name=TEXT,entry_node_id=ID,nodes=arr(node),edges=arr(edge),branch_points=arr(branch)))
data = d("Data", entity(name=TEXT,description=TEXT))
rule = d("Rule", entity(statement=TEXT,kind=enum("business","permission","consistency"),action_ids=ids()))
component = d("Component", entity(name=TEXT,purpose=TEXT,grouping_reason=TEXT,alternatives=texts(),uncertainties=texts()))
responsibility = d("Responsibility", entity(component_id=ID,statement=TEXT,action_ids=ids(),rule_ids=ids()))
interface = d("Interface", entity(name=TEXT,capability=TEXT,provider_component_id=ID,responsibility_ids=ids()))
support = d("Support", obj(action_id=ID,provider_responsibility_ids=arr(ID,1,True),required_action_ids=nullable(ids())))
dependency = d("Dependency", entity(kind=enum("uses_component","requires_interface"),consumer_component_id=ID,provider_component_id=ID,interface_id=nullable(ID),capability=TEXT,action_ids=ids(),workflow_ids=ids(),reason=TEXT,support=arr(support)))
part = d("Part", obj(id=ID,obligation=TEXT,assignment=enum("proposed","unassigned","blocked"),target=enum("components","system"),action_ids=ids(),primary_responsibility_ids=ids(),supporting_responsibility_ids=ids(),covered_portion=nullable(TEXT),remaining_gap=nullable(TEXT),issue_ids=ids("issue")))
mapping = d("Mapping", obj(id=ID,source_ref=source,parts=arr(part),assessment=enum("not_assessed","proposed"),issue_ids=ids("issue")))
B["model"] = obj(revision=integer(1),parent_model_id=nullable(rid("model")),source_context_id=rid("source_context"),created_by_run_id=rid("run"),change_id=nullable(rid("change")),actors=arr(actor),actions=arr(action),workflows=arr(workflow),data=arr(data),rules=arr(rule),components=arr(component),responsibilities=arr(responsibility),interfaces=arr(interface),dependencies=arr(dependency),mappings=arr(mapping))
walk = d("Walk", obj(order=integer(1),element_refs=arr(element),observation=TEXT))
B["scenario"] = obj(analysis_key=ID,supersedes_id=nullable(rid("scenario")),model_id=rid("model"),name=TEXT,trace=trace,scope=scope,trigger=TEXT,conditions=texts(),expected_obligations=arr(source),walkthrough=arr(walk),assessment=enum("not_assessed","supports_at_model_level","gap","needs_clarification"),issue_ids=ids("issue"),verification_obligations=texts())
option = d("Option", obj(id=ID,action=enum("keep","split","merge","move_responsibility","change_dependency"),description=TEXT,benefits=texts(),costs=texts(),other_characteristic_impacts=texts(),constraint_refs=arr(source),precondition_issue_ids=ids("issue")))
effect = obj(element_refs=arr(element),observation=TEXT,evidence_refs=arr(source),assumptions=texts())
B["characteristic"] = obj(analysis_key=ID,supersedes_id=nullable(rid("characteristic")),model_id=rid("model"),name=TEXT,trace=trace,scope=scope,goal=nullable(TEXT),conditions=texts(),priority=enum("must","should","could",None),scenario_ids=ids("scenario"),boundary_effects=arr(effect),options=arr(option,1),recommendation=enum("keep","change","undecided"),recommended_option_id=nullable(ID),issue_ids=ids("issue"),risks=texts(),verification_obligations=texts())
B["analysis_set"] = obj(model_id=rid("model"),revision=integer(1),parent_set_id=nullable(rid("analysis_set")),scenario_ids=ids("scenario"),characteristic_ids=ids("characteristic"),issue_ids=ids("issue"),changed_record_ids=ids(["scenario","characteristic","issue"]),affected=scope)
changeop = obj(kind=enum("add","replace","remove"),element_id=ID,reason=TEXT)
reuse = obj(**{"from":element,"to":element},reason=TEXT,checked_source_refs=arr(source),checked_by=TEXT)
task = d("Task", obj(step=integer(1,9),scope=scope,reason=TEXT,status=enum("pending","completed"),evidence_record_ids=ids()))
B["change"] = obj(base_model_id=rid("model"),new_model_id=rid("model"),kind=enum("analysis_edit","requirements_switch"),old_source_context_id=rid("source_context"),new_source_context_id=rid("source_context"),reason=TEXT,source_record_ids=arr({**ID,"x-record":"*"},unique=True),application_event_refs=arr(event),operations=arr(changeop),affected=scope,reused=arr(reuse),reevaluate=arr(task),invalidated_bundle_ids=ids("bundle"))
B["view"] = obj(model_id=rid("model"),name=TEXT,component_ids=ids(),interface_ids=ids(),dependency_ids=ids(),omitted_element_ids=ids(),scope_note=TEXT,config_artifact_id=rid("artifact"))
B["diagram"] = obj(model_id=rid("model"),view_id=rid("view"),converter_version=TEXT,toolchain_artifact_id=rid("artifact"),status=enum("not_run","render_failed","fidelity_failed","ready"),puml_artifact_id=nullable(rid("artifact")),svg_artifact_id=nullable(rid("artifact")),aliases=arr(obj(element_id=ID,alias=TEXT)),validation_id=nullable(rid("validation")))
checks = obj(**{k:enum("passed","failed","not_run") for k in ("schema","references","mapping_inventory","freshness","view","conversion","render","fidelity")})
B["validation"] = obj(model_id=rid("model"),analysis_set_id=rid("analysis_set"),view_id=nullable(rid("view")),diagram_id=nullable(rid("diagram")),validator_version=TEXT,checks=checks,errors=arr(error),reported_issue_ids=ids("issue"),completed_change_tasks=arr(obj(change_id=rid("change"),task_index=integer(),evidence_record_ids=arr(rid("*"),1,True))),readability=obj(status=enum("not_reviewed","acceptable","needs_layout_fix"),reviewer=nullable(TEXT),note=nullable(TEXT)))
B["bundle"] = obj(model_id=rid("model"),analysis_set_id=rid("analysis_set"),source_context_id=rid("source_context"),scenario_ids=ids("scenario"),characteristic_ids=ids("characteristic"),issue_ids=ids("issue"),answer_ids=ids("answer"),change_ids=ids("change"),view_id=rid("view"),diagram_id=rid("diagram"),validation_id=rid("validation"),status=enum("preparing_review","awaiting_review"),disclosures=texts())
choice = d("WorkflowChoice", obj(workflow_id=ID,node_id=ID,edge_id=ID,independence_evidence=TEXT))
condition = obj(id=ID,text=TEXT,scope=scope,blocking=BOOL,verification=TEXT)
B["review"] = obj(bundle_id=rid("bundle"),model_id=rid("model"),source_context_id=rid("source_context"),reviewer=TEXT,decision=enum("request_changes","accepted","conditionally_accepted","revoked"),supersedes_review_id=nullable(rid("review")),accepted_scope=scope,blocked_scope=scope,workflow_choices=arr(choice),conditions=arr(condition),acknowledged_issue_ids=ids("issue"),feedback=TEXT)
B["handoff"] = obj(bundle_id=rid("bundle"),review_id=nullable(rid("review")),model_id=rid("model"),analysis_set_id=rid("analysis_set"),eligible=BOOL,allowed_scope=scope,blocked_scope=scope,workflow_choices=arr(choice),condition_ids=ids(),reason_codes=texts())
records = []
for kind, body in B.items():
    d(kind + "Body", body)
    records.append(d(kind + "Record", obj(type={"const":kind},id=ID,created_at=TIME,body=ref(kind+"Body"))))
d("Record", {"oneOf":records})
d("Export", obj(contract_version={"const":"s02/0.1.0-draft.3"},session_id=ID,records=arr(ref("Record"))))
# Exact operation requests are an internal phase-1 interface, not candidate imports.
context_fields = dict(base_model_id=nullable(rid("model")),base_analysis_set_id=nullable(rid("analysis_set")),source_context_id=rid("source_context"))
requests = [obj(kind=enum("start"),store_key=ID,s01_run_id=ID,expected_snapshot_id=nullable(ID)),
            obj(kind=enum("work"),**context_fields,scope=nullable(scope),config_artifact_id=nullable(rid("artifact"))),
            obj(kind=enum("apply_answer"),answer_id=rid("answer"),issue_key=ID,**context_fields),
            obj(kind=enum("recovery"),reason=TEXT)]
d("Operation", obj(command_id=ID,session_id=nullable(ID),parent_command_id=nullable(ID),reserved_run_id=ID,request={"oneOf":requests}))
d("StagedBlob", obj(command_id=ID,blob_id=ID,media_type=TEXT,purpose=enum(*purposes,"requirement_update_input"),sha256=DIGEST,byte_length=integer()))
E = {}
E["prepared"] = obj(stage_refs=arr(stage),attempt_id=nullable(ID))
# Internal T0 pin for reuse already allowed by §4.3; optional for a1 histories.
E["prepared"]["properties"]["reused_artifact_ids"] = ids("artifact")
E["dispatch_intent"] = obj(prepared_event=event,transport_attempt=integer(1))
E["response_received"] = obj(response=stage,http_status=integer(100,599),safe_headers={"type":"object","propertyNames":{"enum":["content-type","request-id","retry-after"]},"additionalProperties":{"type":"string"}},requested_model=TEXT,returned_model=nullable(TEXT),provider_response_id=nullable(TEXT),usage=nullable(usage),elapsed_ms=integer())
E["finalized"] = obj(run_id=rid("run"),promotions=arr(obj(stage_ref=stage,artifact_id=rid("artifact"))))
E["log"] = obj(message=TEXT)
E["interrupted"] = obj(reason=TEXT)
s01request = obj(mode={"const":"update"},spec_id=ID,base_revision=integer(1))
E["interpretation_selected"] = obj(answer_id=rid("answer"),interpretation=enum("points_to_existing_source","changes_requirements"),explanation=TEXT,existing_source_refs=arr(source),proposed_input=nullable(stage),s01_request=nullable(s01request))
E["consent_recorded"] = obj(answer_id=rid("answer"),interpretation_event=event,respondent=TEXT,text=TEXT,approved_input_sha256=nullable(DIGEST))
E["s01_dispatch_intent"] = obj(answer_id=rid("answer"),consent_event=event,s01_store_key=ID,s01_run_id=ID,s01_request=s01request,input_stage_ref=stage)
E["s01_result_observed"] = obj(answer_id=rid("answer"),dispatch_event=event,s01_run_id=ID,lookup_status=enum("validated","rejected","failed","unknown"),snapshot_id=nullable(ID))
E["application_applied"] = obj(answer_id=rid("answer"),interpretation_event=event,consent_event=nullable(event),s01_observation_event=nullable(event),change_id=rid("change"),new_source_context_id=rid("source_context"),resolved_issue_id=rid("issue"))
E["recovery_observed"] = obj(answer_id=rid("answer"),related_event=event,reason=TEXT)
events=[]
for kind, payload in E.items():
    events.append(d(kind+"Event",obj(event_id=ID,command_id=ID,ordinal=integer(1),kind={"const":kind},payload=payload)))
d("OperationEvent", {"oneOf":events})
schema={"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:dacn:s02:0.1.0-draft.3", "$defs":DEFS,"$ref":"#/$defs/Export"}
if __name__ == "__main__":
    path=Path(__file__).resolve().parents[1]/"src/dacn_s02/schemas/contract.json"
    path.write_text(json.dumps(schema,ensure_ascii=True,indent=2)+"\n")
