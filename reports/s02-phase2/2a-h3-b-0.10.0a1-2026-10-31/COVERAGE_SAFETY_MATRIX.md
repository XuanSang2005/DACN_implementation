# H3-B — gates, paths và independent expectations

Trạng thái chạy thực tế/paths/counts lấy từ START_HERE và evidence JUnit/commands; bảng này định nghĩa oracle, không thay kết quả. Tests dùng installed wheel, C rồi Python tuần tự, concurrency OS-process chỉ bên trong race cases. Synthetic controller/fixtures không là human/business confirmation. H2 baseline chỉ tạo lịch sử/đối thủ hợp lệ; safety pass đòi chính API/writer B.

| Gate | Tests | Expected độc lập / DB readback |
| --- | --- | --- |
| G1, E06/E19/E22 | test_h3_b_pure: no-anchor/full-anchor, B anchor transitions, result metadata mutations, mutable view/clock; runtime no-anchor/full-anchor/workflow | No-anchor stage0/output hold; actual Actor/Action/nested workflow IDs đủ; full stage2 origin refs nguyên; exact result Model/AS hashes/latest pair/parent chain. False/null hash/current/branch/prefix/omitted stage không cấp progress |
| G2/E18 | Pure old/mixed Config/Plan/Binding/Authority/handler/policy, exact B tuple; runtime missing/denied authority/old adapter | B draft.3 semantics + binding domain; A/H2 approval không reuse. Invalid input trước T0 không receipt/op/effects. Pending cần original B grant, finalized không cần semantic authority |
| G3 | Pure own append/unrelated session/changed dependency; runtime registry pin and fixed R controls; all process recovery | Full T0 Record/event/owner/profile/snapshot/archive pin immutable. Whole current canonical checks riêng. Own phases exact; new valid appends không refresh history/intent. R0/R1 upgrade pending đều không được nhận khi R đổi |
| G4 | Original focused A129 / original oracle13 / supplement8 và full regression | Old A semantics/assertions/oracle bytes nguyên; B result không nới A input checker hoặc bỏ publisher assessment. Counts mới ghi riêng, không dùng history làm pass mới |
| S1/E20 | test_S1_two_OS_preparers_same_command_intent [same/different]; different_registry_pin; two_OS_resumers [before_seal/before_finalize] | ≥2 independent PIDs, same receipt/command hội tụ đúng reserved Run/raw/config/start; different raw/registry intent conflict. Một sealed plan/finalized event, winning allocations/times, same outcome |
| S2/E20 | two_AS_only_publishers_paired_CAS; valid_Model_AS_opponent | AS-only và valid Model+AS rivals; one winner, loser stale/null result pair, no planned AS/Issue. Exact stale Run transform và exact planned Artifacts/promotions; không SQL head corruption/mock CAS |
| S3/E21 | T0_seal_T3_crash_rollback_lost_ack_unknown | Prepare/seal/finalize × before_commit rollback/kill; after_commit kill/lost ACK/unknown. Original failed DB+sidecars trước recovery; process mới checked report/reopen. T0 rollback=not_prepared+explicit same command, committed=original identity. Seal0/1, T3pending/final đúng durable fact |
| S4/E18/HR-P/E21 | original_registry_process_restart_restore [after T0/after seal × missing/tamper/ancestor missing/other-session missing] | Actual4 human-evidence entries gồm hai session/ancestors, actual2 application events. Missing/invalid fails without DB writes; original file/tuple restore resumes exact command/plan. Finalized report không analysis/work/authority file nhưng vẫn cần registry |
| S5 | revalidate_effects_paths_crash_reopen [guard_pass/guard_held × before/after seal/T3 kill + T3 lost ACK]; preT0 rejects | Actual code-origin guard successor resolved/open đúng structured proof, all old keys retained, no Model/Change edit. Fault/reopen trên mỗi supported effects class, không chỉ adopt happy path. Rejection trước T0 không dựng phase giả |
| S6 | exact()/readback() trong toàn process cases; providerless runtime replay | Exact reserved Run/start/raw/config bytes/SHA/length, one seal, selected plan bytes/IDs/times/allocations, three stages/events, one final, promotions actual DB blobs, planned→actual Record bytes và application rows before=after. Replay không cấp ID/clock/effects |

## Measurements candidate cuối

Release v2: focused B111/111 và full S02 1217/1217 mỗi backend,0 failures/errors/skips. Matrix `CASE_MATRIX_FINAL.json` trong evidence root ở START_HERE được xuất từ2434 JUnit cases, gồm80 safety cases và268 OS-worker invocations của lượt full; mỗi case có phase/path/backend/oracle và actual DB/readback locators. B111 gồm36 pure,35 runtime,40 OS-process safety/backend. Đây là implementer evidence, không kết luận audit hoặc nghiệm thu.

## Scope E01–E24

E01–E17/E24 pure A controls được bảo toàn trong regression/oracles. B runtime HR-P nhận DIRECT/CARRY/REPLACEMENT human history có sẵn, giữ toàn old Record bytes/current selection và application rows; revalidate chỉ supported existing H2 technical guard. Model+A2 structural continuation/proof creation/repair của E01–E17/E24 thuộc C, chưa triển khai hoặc claim B evidence thay C.

B controls áp dụng E06/E09/E14/E18/E19/E20/E21/E22/E23 và AS-only E24: stale pair, source/raw/version mismatches, exact registry inventory/dependency, unsupported mode/step/source-switch/repair request và H1 publisher chưa bridge phải reject/unsupported không drop Records. Existing steps5–9/review/bundle/non-E1/migration checks dùng checked HistoryData/store profile gates; source không bỏ check để nhận entry. CLI/four-worker/stress mở rộng E25 thuộc D, không dùng D hoãn safety cơ bản B.

Case-level phase/path/backend/PID/exit/oracle locator được xuất riêng vào evidence từ final JUnit và process command/readback files. Failed development rounds/DBs giữ nguyên; selected debug runs có deselected counts rõ, không coi là full coverage.
