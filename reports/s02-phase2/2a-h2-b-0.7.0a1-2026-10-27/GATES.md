# Gates và phạm vi bằng chứng

Tất cả là kiểm phần mềm local/synthetic. Expected scopes/progress trong tests là assertions theo source fixture; không dùng kết quả production policy làm expected. H2-A pure oracles và H2-B writer traces được ghi riêng.

| Gate | Kiểm H2-B / đối chiếu |
| --- | --- |
| I1, I11 — inventory/criteria và progress riêng | `test_scoped_u_held_v_to_four`; demo CLI source S01 + bốn mock; U vẫn hold, V tới 4, đủ 8 rows, global mapping task open |
| I2, I7 — current keys/refs, immutable output | Whole E1 verifier; `check_result`/`check_projection`; guard/revalidation giữ business Issue nguyên ID/bytes trên AS-only; output/local IDs không tăng khi revalidate |
| I3 — selectors sống qua graph rỗng/lớn, unknown | `test_unknown_global_finding_holds_future_graph`; pure H2 context/selectors oracles trong full S02 |
| I4–I6 — fixed point/meaningful impact/union | `test_builder_real_bridge_outside_write_and_disjoint_control`, `test_new_hold_in_union_never_publishes_partial_candidate`, `test_shared_component_context_does_not_expand_write_scope`; Part/workflow/Support/context oracle H2-A nguyên byte chạy lại trên wheel mới |
| I7 — ngoài quyền ghi / source | `test_foreign_source_and_outside_write_rejected_after_raw_capture`; closed projection toàn selected family; old row/source/membership không được sửa |
| I8 — task không miễn business/gap | `test_revalidate_never_resolves_business_or_global_task`; construction origin/root/predicate checked; H1-01/02/V4 và genuine-gap regression giữ nguyên |
| I9, I15 — retained output / result assessment | `test_retained_output_guard_revalidation_and_domain_edit_limit`; `test_revalidation_explicit_domain_edit_terminal`; hashes Model+AS, parent progress/assessment, explicit terminal giữ guard |
| I10 — receipt/T0/seal/T3/identity | `test_h2_process_crash_lost_ack` cho prepare/seal/finalize, trước/sau COMMIT, kill/lost ACK/unknown; `test_h2_two_preparers`, `test_h2_two_resumers` |
| I10 — CAS đầy đủ | AS-only stale trong core suite; `test_two_processes_model_or_revalidation_cas` bổ sung Model và AS-only revalidation bằng hai OS processes; planned domain/Issue/AS IDs phía stale không công bố |
| I12–I13 — authority/limits/integrity | Provider deny/hash/unavailable/restart/finalized history; `test_authority_change_inside_publication_transaction_rolls_back`; pending duplicate plan fail; finalized unpromoted future plan không đổi lịch sử; H2 limits corrected/original oracles |
| I14 — guard/P_guard | `test_guard_missing_proof_then_resolution_new_command`; thiếu proof open successor, đủ proof resolved guard, U giữ hold, command mới cho V; không replay candidate bị chặn |
| Durability trên từng publication kind | `test_h2_model_guard_revalidate_crash_paths`: Model, guard-only, revalidation, trước/sau seal/T3 |
| Receipt/usage/progress | `test_scoped_cli_authority_receipts_exit_codes`: 0/2/3/4/5/64, no provider trước effects, receipt-only explicit prepare, finalized replay/progress, không raw mới trên resume |
| Recovery | H1 recovery nguyên byte; `test_h2_hot_journal_checked_recovery_and_readonly_progress` bổ sung H2 cache spill, readonly/wrong-store không sửa DB/journal, recovery đúng identity |
| Prepare/finalize overlap | `test_finalize_between_prepare_preflight_and_transaction_returns_history` giữ outcome lịch sử khi worker khác finalize trước T0 comparison |

Fresh H2 bước 1–4 không sinh Dependency/Support hoặc sửa proposed mapping đã công bố. Các graph Support/Part-chain/context permutations ngoài capability builder được kiểm ở pure-policy layer đã tích hợp, không trình bày chúng thành output step 5 hoặc pipeline fixture được import vào DB. E1 whole-graph verifier không thay bằng những kiểm này.

Full S02 dùng snapshot test inputs của E1 adapter, gồm 47 core H2-B cases. Ba release-boundary cases được thêm như supplement trên cùng frozen production wheel và chạy C/Python riêng; không báo chúng như đã nằm trong snapshot full ban đầu. [TEST_RESULTS](TEST_RESULTS.md) ghi số thực tế và đường dẫn JUnit từng nhóm.
