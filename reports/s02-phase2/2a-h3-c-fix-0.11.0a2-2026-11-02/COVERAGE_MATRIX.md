# Coverage mới — từng case/backend

31 ca/backend: 8 oracle nguyên bản, 7 regression trực tiếp, 16 controls cũ bị ảnh hưởng. C hoàn tất trước Python. Tất cả fixtures synthetic; runtime oracle qua API/DB thật. Không chạy `test_audit_c_union.py` theo erratum.

| Case | Phase | C | Python |
|---|---|---|---|
| `tests.test_audit_c_raw_holds::test_candidate_negative_facts_gate_stage2[control]` | pure oracle | PASS | PASS |
| `tests.test_audit_c_raw_holds::test_candidate_negative_facts_gate_stage2[held]` | pure oracle | PASS | PASS |
| `tests.test_audit_c_raw_holds::test_candidate_negative_facts_gate_stage2[not_inspected]` | pure oracle | PASS | PASS |
| `tests.test_audit_c_raw_holds::test_candidate_negative_facts_gate_stage2[unrepresented]` | pure oracle | PASS | PASS |
| `tests.test_audit_c_runtime_holds::test_publication_cannot_lose_raw_candidate_hold[False]` | API/DB oracle | PASS | PASS |
| `tests.test_audit_c_runtime_holds::test_publication_cannot_lose_raw_candidate_hold[True]` | API/DB oracle | PASS | PASS |
| `tests.test_audit_c_mapping_gap::test_missing_mapping_coverage_is_not_current_stage4[False]` | pure oracle | PASS | PASS |
| `tests.test_audit_c_mapping_gap::test_missing_mapping_coverage_is_not_current_stage4[True]` | pure oracle | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C01_raw_negative_is_not_overridden_by_usable_analysis[1-held]` | new_regression | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C01_raw_negative_is_not_overridden_by_usable_analysis[2-held]` | new_regression | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C01_raw_negative_is_not_overridden_by_usable_analysis[2-not_inspected]` | new_regression | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C01_raw_negative_is_not_overridden_by_usable_analysis[2-unrepresented]` | new_regression | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C01_compatible_U_hold_keeps_independent_V_progress[held]` | new_regression | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C01_compatible_U_hold_keeps_independent_V_progress[unrepresented]` | new_regression | PASS | PASS |
| `tests.test_h3_c_findings_regression::test_C02_null_coverage_remains_raw_and_projected_gap_without_new_Model` | new_regression | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C4_step1_through4_retains_unassessed_U_without_overwrite` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C4_whole_candidate_guard_on_real_bridge_but_independent_mapping_progresses[False]` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C4_whole_candidate_guard_on_real_bridge_but_independent_mapping_progresses[True]` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C4_unknown_hold_rematerializes_and_does_not_release_new_V` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C4_shared_component_is_context_but_real_Part_bridge_blocks` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C3_guard_own_null_then_inherited_actual_SHA` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C2_G_C3_anchored_tasks_keep_pinned_predicates_through_detached_steps3_4` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C2_Model_A2_successors_keep_root_history_and_allow_independent_V[direct-applicable]` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C2_Model_A2_successors_keep_root_history_and_allow_independent_V[carry-applicable]` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C2_Model_A2_successors_keep_root_history_and_allow_independent_V[pending-undetermined]` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C2_Model_A2_successors_keep_root_history_and_allow_independent_V[replacement-complete]` | affected_control | PASS | PASS |
| `tests.test_h3_c_pure::test_G_C2_Model_A2_successors_keep_root_history_and_allow_independent_V[incomplete-incomplete]` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C1_G_C4_bad_raw_is_rejected_and_kept_exact_without_domain[scope_hash]` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C1_G_C4_bad_raw_is_rejected_and_kept_exact_without_domain[unknown_field]` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C3_G_C4_tampered_sealed_claims_do_not_replace_raw_reconstruction[projection]` | affected_control | PASS | PASS |
| `tests.test_h3_c_controls::test_G_C3_G_C4_tampered_sealed_claims_do_not_replace_raw_reconstruction[guard]` | affected_control | PASS | PASS |

Wall time: c: 222.215s; python: 249.172s. Encoder instrumentation, per-case times và JUnit nằm trong [CASE_MATRIX.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/CASE_MATRIX.json), [commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/checks/commands.json), logs từng backend.

E/S matrix và safety/full của a1 là evidence lịch sử, không phải lượt chạy a2. Lượt này không mở rộng sang toàn E01–E24/S1–S6; writer/CAS và các backend safety không đổi.
