# Coverage H3-C — executed local/synthetic

Các controls C bên dưới đã pass trên cả C/Python trong final regression; chi tiết từng ca nằm ở C_CASES.json và C_WORKERS.json của handoff; không dùng pass B-AS thay C. Các ca là synthetic/mock, không là đánh giá LLM/nghiệp vụ.

| Gate | Case C chính | Oracle |
| --- | --- | --- |
| G-C1 | schema_parent_bridge_and_exact_C_authority; closed_shapes_and_mode_inputs; modified_raw_binding; API_authority_is_separate_and_exact_raw_bytes | Closed draft.4 bằng snapshot đã audit; actual B→C; authority C riêng; exact raw/hash domain/read allowlist; không borrow B |
| G-C2 | Model_A2_successors; source_only; not_applicable; complete_replacement_falls_back; historical_switch; anchored_tasks | Canonical full graph; root/from/obsolete/Answer/event roles; current target khác key; pending giữ hold; technical predicate đúng origin |
| G-C3 | stage1_B_to_C_and_C_to_C; guard_own_null_then_inherited_actual_SHA; tampered_sealed_claims; anchored_tasks_pure | Detached result→promoted reader→next Config; own Artifact+null SHA→inherited actual SHA; metadata/claim không thay capability |
| G-C4 | step1_through4; bad_raw; unknown_hold; shared_component; whole_candidate_guard_on_real_bridge | No-anchor giữ output cũ; retained outputs/full keys/Part–row–source/fixed-point/reverse impact/whole union; raw reconstruction |

Mốc pure đầu gồm41 distinct controls/backend trước khi có file writer C, có snapshot riêng. Sau đó controls mới phát hiện lỗi identity và retained technical task; delta task được kiểm detached pure cả hai backend trước API delta. Mốc41 không được trình bày như toàn coverage cuối.

| H3 matrix | C controls mới và supporting regression |
| --- | --- |
| E01 | DIRECT applied→CARRY actual Model+A2; completed/blocked; full H2-anchor B→C; unchanged Answer/application/claims |
| E02 | CARRY applicable, các checkpoints steps2–4; origin cố định, from/supersedes đúng base current |
| E03 | Historical human REPLACEMENT complete, target current khác key, structural continuation và S1/S5 effects |
| E04 | Historical switch: typed old/current SourceRefs, old human proof bất biến; thiếu structural identity giữ undetermined, V vẫn tiến |
| E05 | Source-only clone; pending Answer mixed-current giữ global hold khi chưa đủ proof; không tự apply Answer |
| E06 | No-anchor U actual outputs stage0/needs_revalidation, V mới chỉ tiến với proof; full-anchor controls riêng |
| E07 | Raw canonical proof claim rejected; task evidence thiếu→incomplete/hold; malformed khác missing coverage |
| E08 | Corrupt root/from/origin/source/scope/false release reject; tampered sealed projection/model/assessment reject |
| E09 | Current predecessor/history lineage; stale CAS AS-only/Model+AS; planned domain records loser không có |
| E10 | CARRY undetermined/pending Model successor và S5 crash-reopen; không auto applicable |
| E11 | not_applicable target/no-target; chỉ incomplete với target existing/current/khác key, hoặc guard base |
| E12 | Existing incomplete không first complete; complete→incomplete khi không có current task attestation; no new Validation |
| E13 | Target role/current key checked bởi canonical A2 + raw→result reconstruction; supporting negative target controls trong full regression |
| E14 | Raw snapshot/unit/base-handle false rejected; historical from refs theo đúng source; canonical validators không nới |
| E15 | Projection/model tamper rejected; retained row/source/assessment/Issue context và Part membership qua append-only checker; full canonical row-swap/set-order regression |
| E16 | Shared-component control khác real Part bridge; candidate union bị bỏ toàn bộ khi blocker kéo sang V/W; independent mapping tiến |
| E17 | Unknown/global rematerialize sau graph growth; held inspection phải có hold; labels không tự thu hẹp unknown pending Answer |
| E18 | C authority exact + registry loader trước checked read; HR-P ancestors/other session all-store R missing/tamper/subset/restore; finalized vẫn cần registry |
| E19 | Actual B/C publisher, full anchor và no-anchor; progress/raw/parent/projection/hash tamper reject; không tăng từ status/appearance |
| E20 | Hai OS preparers/resumers DIRECT/REPLACEMENT; two Model+A2 publishers; sealed loser gặp AS-only và Model+AS opponents |
| E21 | T0/seal/T3 rollback/kill/lost ACK/unknown; each effects class; exact IDs/times/config/raw/seal; providerless replay |
| E22 | Revalidate AS-only không tăng stage; C→C nhiều checkpoint; inherited guard actual SHA; giữ retained outputs/task origin |
| E23 | C schema/mode/step gates và actual B/C parent dispatch; unchanged fresh/E1/L1/migrated/H1/source gates được kiểm trong regression trên wheel C. Không mở scope5–9/repair/source switch |
| E24 | Whole current-key selection; source-only + Answer pending + replacement mixed set giữ đúng blocker accounting; two-key Model successors/targets; mỗi Answer application/claims trước=sau |
| E25 | Ngoài H3-C: không CLI/four-worker/large-history stress H3-D. Full legacy regression vẫn chứa stress lịch sử H2, không gọi đó là coverage D |

| Safety | Ca/phase/backend và path |
| --- | --- |
| S1 | two_OS_preparers_same_command: same/different raw × DIRECT/REPLACEMENT; different_registry_pin; two_OS_resumers rendezvous before_seal/before_finalize × DIRECT/REPLACEMENT |
| S2 | two_Model_A2_publishers_paired_CAS; sealed_loser_both_head_change_opponents[AS_only,Model_AS]. One winner/stale; không planned Model/Change/Issues/AS của loser |
| S3 | prepare/seal/finalize × before_commit rollback/kill, after_commit kill/lost_ack/unknown. 15 combinations/backend; fresh process checked reopen |
| S4 | after T0/after seal × missing/tampered/ancestor_missing/other_session_missing. 8 combinations/backend, original restore giữ identity, finalized providerless cần original registry |
| S5 | DIRECT→CARRY, pending, RP complete, complete→incomplete fallback, guard-only, rejected; mỗi class seal before/after commit, T3 before/after commit và T3 lost ACK. Thêm completed Run path cùng5 controls; blocked không bị ép completed |
| S6 | exact oracle dùng cho tất cả safety cases: command/reserved Run/T0 times/raw/config/registry/plan bytes/allocations/promotions; one finalized; exact planned→actual Model/Change/A2/AS; history/root/from/obsolete/current refs; old records/applications/claims |

Mỗi worker có PID/argv/backend/test_case/input spec/hook/phase/action/exit/stdout/stderr. DB/stages/sidecars trước-sau và JSON readbacks giữ trong final-regression/s02; C_WORKERS.json và READBACK_INDEX.json trỏ tới chúng. Không tăng caps/timeouts hoặc giảm assertions. Không claim exhaustive mọi topology × fault; phạm vi là core C tại §7.1, không liveness stress D.
