# Failures, corrections và giới hạn H3-B

Đây là evidence implementer, chưa audit/nghiệm thu runtime. Mọi failed log/JUnit/DB/sidecar và provisional wheels giữ nguyên ở evidence root, không rerun vào output cũ hoặc sửa sealed A/H2/oracle. Kết quả cuối lấy START_HERE, không dùng counts lịch sử làm pass mới.

## Development failures đã ghi

| Round | Kết quả mỗi backend | Lý do/correction |
| --- | --- | --- |
| pure-v1 | 3 pass,3 fail,17 errors /23 | B chưa normalize H2 selector field version; sửa adapter B, không nới A schema |
| pure-v2 | 3 pass,3 fail,17 errors /23 | Owner/profile map hash xây lại sai exact-codec order; lọc immutable inventory theo original order |
| pure-v3 | 5 pass,1 fail,17 errors /23 | Equal assessments trùng uniqueItems; dedup array, per-unit metadata/parent hashes đầy đủ |
| pure-v4 | 21 pass,2 fail /23 | Expected E06 bỏ supplied Actor khỏi actual outputs; sửa expected literal Actor+Action theo graph. Guard predicate phải phân biệt proven builder task với surviving business hold qua actual origin, không prefix/kind guessing |
| pure-v7 | 5 pass,4 fail,19 setup errors /28 | Khi giữ target/role thật, một seed checker còn truyền task_origins rỗng. Bổ sung đúng checked TaskOrigin argument, giữ nguyên validator/assertions; không reset target hoặc miễn blocker để pass |
| pure-v9 | 34 pass/2 fail /36 mỗi backend | Hai positive retained-stage controls đã đổi raw/selected units sau khi helper pin cùng command. Shared Budget đúng khi reject raw_input_slot_changed. Helper nay dựng đúng intent một lần trước validation; không reset Budget, đổi caps hoặc hạ expected stage |
| runtime-v1 | 5 pass,1 fail /6 | Test retained step2 chọn mọi unit kể cả U chưa stage2; request đúng V, giữ exact stage proof gate |
| runtime-v2 | 14 pass,6 setup errors /20 | Foreign synthetic session replay trùng global staged blob IDs; namespace IDs của fixture qua Repository API, không sửa DB2 uniqueness |
| hr-focus-v1 | 1 setup error | Synthetic event IDs prep/final bị reuse across commands; namespace EventRef theo command/event pair. HR-P sau đó chạy qua với4 entries/2 applications |
| focused-v1 | C102 pass/1 fail /103; Python102 pass/1 fail /103 | New fresh-report assertion sai ở seal after_commit/lost_ack: original worker reconcile seal ACK rồi tiếp T3 hợp lệ, nên report finalized/blocked2, không prepared0. Sửa exact expected endpoint và thêm assertion exact durable phase; không mở tập acceptable statuses, hạ assertion hoặc đổi timeout/caps. Original failed DB/log/worker exit giữ |

Initial pre-writer G1–G3: pure-v5 24/24/backend; later pure-v6 26/26/backend, runtime-v3 30/30/backend và selected process-focus-v1 6/6/backend là precursor evidence theo đúng payload snapshots. Focused-v1 trước preservation TaskOrigin bổ sung cũng là precursor, không release authority. Selected debug runs có deselected counts rõ, không phải skipped/full coverage.

Conformance review trước release bổ sung typed H2 TaskOrigin inventory (origin/root/predicate/unit/target/current ID/plan SHA), không cấp B build permit; task Records/blockers không đổi; selectors phải giữ target_step/role gốc, không biến task bước sau thành blocker bước1. Thêm positive unit độc lập chưa có output được current ở stage0, vẫn không có completed work/build permit. Stale readback được siết exact planned Artifacts/reserved Run transform. Current package/init version/docstring đổi sang B; mọi old A/H2/S01 source/tests/locks còn lại giữ byte. Test expectation deltas có trong source snapshots/diffs, không sửa sealed/auditor originals.

Tooling observations không là product test failures: ba apply_patch no-op attempts không match whole-line Markdown và một read tìm REPRODUCE.md không có trong audit A a2 (START_HERE dùng SUPPLEMENT_RESULTS.json). Một orchestration call khác thiếu biến JavaScript E, dừng trước shell; một render-script drafting call có template syntax error trước shell; không file nào bị đổi bởi các attempts này, không pytest/JUnit chạy từ chúng.

Release-focused-v1: C103/103,0 fail/error/skip; Python bị dừng khi artifact được thay trước handoff để bổ sung pure mode/goal/own-request controls khớp API. `RELEASE_V1_SUPERSEDED.json` ghi process group/argv/lý do; toàn partial logs/DBs/sidecars và ZIP v1 giữ nguyên, không claim Python/full pass hoặc lấy counts đó cho release cuối. Lượt cuối phải chạy toàn111 focused và1217 full/backend trên wheel mới. V1 dừng không nhằm giấu failure; các invalid-goal/request cases mới chưa có trong bộ103.

Expression của seal-ack-focus-v1 match cả15 S3 variants thay vì chỉ một ACK case; thực chạy15/15/backend,25 deselected,0 skips. Ghi đúng phạm vi, không gọi đó là toàn40 safety cases.

## Kết quả candidate cuối

Release v2 trên wheel `0.10.0a1` đã chạy mới: focused B111, focused A129, oracle gốc13, supplement8, diagnostics3, full S02 1217 và full S01 986 mỗi backend; tất cả0 failures/errors/skips. Diagnostics3 giữ mismatch A, không là B runtime pass. Wrappers339 pass (8 subtests pass), layout/pip/collector đạt. Full S02 C3244.08s và Python3507.33s; C rồi Python tuần tự. Các failed/partial rounds ở trên vẫn giữ nguyên, không được thay bằng counts này.

Matrix cuối xuất từ2434 JUnit cases và80 safety cases/268 OS-worker invocations, kèm actual DB/sidecars/readbacks. Original manifests của3 audit/2427 entries và accepted A2 wheel đối chiếu nguyên byte. Paths/hashes/commands ở START_HERE và evidence root. Đây là kết quả implementer, chờ auditor độc lập và người dùng nghiệm thu.

## Giới hạn

Final seal attempt1 dừng trước khi tạo FINAL_RESULTS/MANIFEST/SEAL/AUDIT_READY: script metadata expect JUnit tests=339, trong khi pytest ghi339 testcase nodes +8 passed subtests =347 logical results ở suite attribute. JUnit/log đều0 fail/error/skip. Giữ script attempt1 và SEAL_ATTEMPT_1.json; sửa riêng seal verifier kiểm đủ347 logical results,339 nodes và exact terminal summary339+8, không sửa JUnit/tests hoặc chạy lại application suites. Final review v2 giữ như snapshot trước correction; final-review-v3 gồm ghi nhận này.

- Chỉ API B local/synthetic checked adoption/AS-only revalidate và existing code-origin H2 guard; unknown/non-code impact giữ global holds. No-anchor existing outputs stage0/needs_revalidation. Không domain build/repair, human decision/Answer/application/source switch hoặc semantic/business acceptance.
- Registry/trusted tuple do invoker cấp ngoài DB, fixed all-store R. Test controller dựng lịch sử human đã có bằng APIs cũ là synthetic fixture, không production B tạo người review. R thay đổi trong khi pending là vi phạm precondition; B fail closed cả R0/R1, không hứa tự nâng registry để phục hồi.
- Finalized outcome là lịch sử; current_head/is_current và authorization hiện hành tách riêng. Finalized report vẫn cần original registry, không semantic work authority/candidate file cũ.
- Cooperative30s Budget/numeric caps và SQLite local baseline giữ nguyên. Tests fault injection dùng real OS workers/os._exit71, rollback journal, actual COMMIT probes/rename-to-unavailable; không claim durability/network filesystem/platform khác hoặc liveness mọi contention.
- B-AS safety không là C Model+A2 continuation safety. Chưa C/D/CLI/four-worker stress/LLM/live/operational migration/dataset; S01/H1/H2 acceptance lịch sử và H2-B V01 không mở lại. I02 cleanup provenance review riêng, không rollback/gộp acceptance A/B.
- Independent auditor kiểm lại, người dùng nghiệm thu cuối. Không stage/commit/push hoặc tự đóng findings/runtime acceptance.
