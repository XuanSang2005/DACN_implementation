# H3-A coverage — controls synthetic, implementation để audit

Các test names dưới là controls mới của H3-A trên installed wheel. Expected scopes/sets/counts được viết từ topology/source fixtures và contract; không gọi function đang kiểm để sinh oracle. Canonical validators được dùng làm gate của input graph, không lấy verdict ấy thay independent expected result. Test fixtures có thể dựng lịch sử qua **existing** S01/S02/H2 infrastructure; đó không phải H3 writer/restart runtime mới.

| Matrix proposal | Tests mới / nội dung trong scope A | Phần chưa nghiệm thu |
| --- | --- | --- |
| E01/E02 | `test_direct_to_carry_projection_preserves_root_and_current_refs`, `test_carry_multihop_and_pending_resolution_holds`, typed projection tests: exact root/from/current, all-key lineage, immutable application count | Builder/ID allocation/Model publication C |
| E03 | `test_replacement_current_target_and_old_key_preserved`, `test_replacement_structural_continuation_and_rehold`: historical complete/incomplete và structural continuation | Human complete lần đầu ngoài H3; runtime C |
| E04 | `test_existing_cross_snapshot_human_proof_is_history_not_new_decision`: checked archive/history refs, current human proof từ trước và không rewrite source_checks | Không source switch hoặc suy structural applicable từ equal text/criteria index; validator giữ nguyên điều kiện |
| E05 | Mixed source-only/pending Answer controls; `test_direct_answer_history_and_independent_output_with_u_hold`: hai families có criteria, shared component, V tiến/U held, application count=1 | Không nhận/trả lời/apply Answer mới, không semantic acceptance |
| E06 | `test_no_anchor_never_infers_stage_or_deletes_existing_outputs`, fabricated progress negative | Runtime adopt B; pure projection không là AS publication |
| E07 | `test_missing_coverage_pending_is_legal_but_false_release_is_invalid`: undetermined thiếu source/pairs giữ hold; claimed applicable sai bị reject | Conservative successor builder C, không sửa raw/canonical proof giả |
| E08/E09 | `test_invalid_proof_never_becomes_undetermined`, external/registry negatives, stale pair: root/event/from/source/scope/cycle/current ref sai không được chữa bằng label | Store head/receipt CAS/recovery B/C |
| E10/E11 | `test_all_pending_revalidation_states_block`, `test_pending_predecessor_cannot_be_structurally_released`, not_applicable controls, existing/new target-key controls | Không tạo target hoặc quyết định review; source/Model transition bị chặn khi chưa đủ |
| E12/E13 | `test_replacement_complete_needs_existing_task_evidence`, current/historical target negative, incomplete/complete controls | Không tạo Validation/TaskAttestation mới; runtime current-task completion C hoặc scope riêng |
| E14 | Wrong source snapshot/pointer controls trong canonical graph và full inspection; history vs current typed projection | Không trusted operational lookup chỉ từ pure data |
| E15 | `test_retention_checks_part_row_source_context_not_only_part_payload`: same Part payload/source-set nhưng row/source đổi giữ needs_revalidation và reject edit | No completed output repair/reparent publication |
| E16/E17 | Independent shared-component control; `test_unknown_source_hold_survives_empty_graph_and_growth`: fixed expected Actor/actions/Parts, all-source holds; scope/pending/no-shrink checks | Không dependencies bước5; bridge/concurrent writer tests H2-C giữ historical, không tính như H3 safety |
| E18 | Registry tests: exact bytes/UTF-8/pins, all-store R kể cả ancestor/session khác, historical vs semantic lane, missing/tampered/self-derived/unknown/version/duplicates; R fixed across structural growth | Filesystem loader/factory/restart/report HR-P B chưa có, không gọi pure tests là proof runtime D01 |
| E19 | Closed Anchor/Config/Plan/Admission crosspins; `test_real_existing_h2_anchor_is_purely_checked_without_new_h3_io`, task/guard provenance và fabricated progress negative | No H1/general bridge; B phải thực thi loader/actual reads; plan checks thuần không seal/CAS |
| E24 | `test_application_count_and_source_only_pending_answer_mixed_history`: current DIRECT source-only + pending Answer + REPLACEMENT incomplete, cùng history CARRY applicable/undetermined/not_applicable; giữ keys và old application count | Pure graph/data, không tạo các trạng thái ấy bằng H3 pipeline |

**E20/E21/E25:** chưa có H3 writer/process runtime để kiểm. Gates B-AS/C-Model+A2 của §7.1 vẫn bắt buộc ngay các đợt đó; D chỉ mở rộng CLI/four-worker/stress. Native H2 process/anchor fixtures trong suite này chỉ cấp provenance cho pure controls, không chứng minh H3 restart/CAS/lost ACK đã chạy. E23 chỉ có shape/scope/entry restrictions phù hợp A, không CLI usage/runtime.

Các contracts tests bổ sung type/shape/closed nesting/versions/mode/nullability, immutable schema copies, exact config intent/pins, required whole rows/current Issue roles, StageRef/promotions/reserved Run/projected Record equality; registry/ref/Budget caps, cyclic inputs trước copy/hash, history-chain depth trước canonical recursion và AST không loader/factory/network/writer.

[START_HERE](START_HERE.md) pin wheel/SHA và kết quả JUnit **thực chạy** từng backend; bảng này không tự là số tests pass. Failures/provisional runs được giữ trong bằng chứng external và không đổi thành pass của delivery.
