# Audit lại H3-A dacn-s02 0.9.0a2 — 31/10/2026

**ĐẠT audit kỹ thuật H3-A pure contracts/history policy local/synthetic trên release wheel đã pin. S02-2A-H3-A-01/02/03 CLOSED.** Không phát hiện finding implementation mới chặn phạm vi A qua review và kiểm thực chạy dưới đây. Người dùng chưa nghiệm thu cuối; chưa giao H3-B/C/D hoặc quyền live.

**Tách riêng working tree:** sau lúc xác minh đầu lượt, `.gitignore` và `packages/s02/tools/prepare_p2_tests.py` thay bytes ngoài bàn giao. Ghi **S02-2A-H3-A-I02**, mức Thấp, nguồn thay đổi chưa rõ. Wheel, production source và copied test inputs được kiểm vẫn khớp release. Kết luận kỹ thuật này không tự duyệt hai thay đổi ngoài scope để commit. Không ghi “toàn repo nguyên byte suốt audit”.

## 1. Phiên bản và phương pháp

- Repo `/Users/macbookpro/Documents/DACN_implementation`; HEAD baseline **b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57**, index giữ nguyên, chưa commit H3-A.
- Repo handoff: `reports/s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/START_HERE.md`. Marker/manifest/seal authoritative ở workspace `outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/`.
- Wheel duy nhất: `delivery-release/wheels/dacn_s02-0.9.0a2-py3-none-any.whl`, **183910 bytes**, SHA-256 **483c9b960c481653b35c0efbae0d5c194d46e6d6895790e69205dbb193ad0e15**. Provisional delivery/ và delivery-final/ không phải target audit.
- Căn cứ: AGENTS hiện hành; H3 design draft.2 SHA **7980042c558bb7f9dd0dc5058af8fb3a06c07c80566f5db6273e54fe6a4435d4**, D1–D5 đã chấp thuận; [audit a1](../s02-2a-h3-a-0.9.0a1-2026-10-30/AUDIT_REPORT.md); FINDINGS_RESPONSE/CONTRACT_DELTA/COVERAGE/FAILURES/REPRODUCE a2. Đối chiếu toàn code delta, shapes/API/bounds và test expectation changes, không chỉ replay count.
- Tạo **môi trường mới ngoài checkout**, offline locks, CPython3.13.16 có GIL/SQLite3.53.1. Hai copied builds S02 bằng toàn53 ZIP entries; S01 rebuild bằng toàn20 ZIP entries a6 trước thay same-version wheel. Cài chính release ZIP S02 non-editable, kiểm source/wheel/installed/direct URL. Không import production từ source hoặc dùng venv implementer.
- Chạy **tuần tự**, oracle C→Python, focused C→Python, supplement C→Python; không jobs nặng song song. Concurrency trong fixtures H2 giữ nguyên. Synthetic DB/journal mới trong basetemp, không operational store/dataset. Những H2 publications dùng làm anchor provenance là fixture thực chạy, không bằng chứng H3 writer/CAS/resume.

## 2. Kết quả auditor tự chạy mới

| Gate | C | Python | Bằng chứng |
| --- | --- | --- | --- |
| Hai oracle a1 nguyên bản, original replay helper | **13/13 pass** | **13/13 pass** | [commands](original-oracle-replay/commands.json), [C log](original-oracle-replay/c/pytest.log), [Python log](original-oracle-replay/python/pytest.log), JUnit từng lane |
| Focused H3-A a2 | **129/129 pass** | **129/129 pass** | [commands](focused/commands.json), [C log](focused/c/pytest.log), [Python log](focused/python/pytest.log), JUnit từng lane |
| Controls bổ sung do auditor viết cho a2 | **8/8 pass** | **8/8 pass** | [SUPPLEMENT_RESULTS](SUPPLEMENT_RESULTS.json), [C log](supplement-c/pytest.log), [Python log](supplement-python/pytest.log), [oracle mới](test_independent_a2_controls.py) |

Mỗi gate trên **0 failures/errors/skips**. Giữ original oracle bytes/assertions/fixture inputs, kiểm cả921 entries của audit a1 nguyên byte. Không chuyển failures a1 thành pass lịch sử: a1 vẫn8 fail/5 pass, a2 fresh replay mới13 pass. Focused là subset của full implementer, không cộng repeats thành số ca độc lập.

Original helper có `.resolve()` trên Python locator. Auditor dùng physical interpreter copy nguyên byte trong `candidate/bin/python-replay`, kiểm SHA/prefix/package paths trước chạy ([ORACLE_LAUNCHER](ORACLE_LAUNCHER.json)). Không sửa helper/oracles, không di chuyển venv/đổi locks. Lượt auditor này **không có launcher/harness failure**. Provisional/harness failures implementer đã giữ trong handoff là lịch sử riêng.

**Supporting evidence, không phải auditor chạy mới:** full S02 **1106/1106**, S01 **986/986** mỗi backend của implementer release; logs/JUnit nằm trong manifest đã xác minh. Auditor không chạy lại full, external P1/P2/P3/H1/H2 oracle suites hoặc L1 differential413 ở lượt này. Focused + original oracle + controls mới kiểm trực tiếp bốn H3 modules đổi; canonical/H1/H2/S01 payload được chứng minh giữ byte. Không broaden tests nặng khi không có failure hoặc concern mới về các modules nền tảng.

## 3. Đóng từng finding

### S02-2A-H3-A-01 — CLOSED, trong phạm vi pure checks/policy

Vị trí chính: [h3_bindings.py:78](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h3_bindings.py:78), [check_anchor:165](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h3_bindings.py:165), [_checked_progress:253](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h3_bindings.py:253), [check_admission:263](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h3_bindings.py:263), check_config và h3_policy.admit.

- `_published/_output_origin` so finalized/promoted plan/config/raw với actual immutable graph: command/Run/session/source/result pair, exact batch Records, stage/output inventory, result hashes/state/output refs và parent assessment chain. Output có đúng raw/origin pin nhưng sai publication không tự được nhận.
- Anchor unit được claim phải có **toàn stages/outputs** của publisher cho unit ấy; không prefix/subset/duplicate. Hoàn toàn bỏ một unit thì giữ unassessed IDs/hold, không lấy current assessment của toàn publisher gán vào stage0.
- Parent/result assessment hashes của transition được định nghĩa và kiểm là **digest toàn progress_by_unit của promoted base/result plans**. Pair, diff, closure, typed correspondence được kiểm riêng. Khi intervening publisher làm stage tiến thêm, không transport prefix cũ thành current; phải dùng full publisher anchor mới.
- `_checked_progress` tái chứng minh từ exact anchor bytes; forged dataclass/raw cũng không vượt. Config/admission progress phải bằng projection đã chứng minh hoặc bằng `unassessed_progress` khi không evidence, không nhận stage tự khai. Binding kiểm progress/anchor/retained pins.
- `admit` no-anchor existing outputs giữ **PROGRESS_PROOF_REQUIRED** cho build. Inspection/admission read-only vẫn có thể thực hiện theo scope; không đổi unknown/hold thành completed và không xóa output. Full stage2/current chỉ cho bước3, chặn lặp bước2.

**Thực chạy:** năm phản chứng progress/anchor của original13 đều pass. Focused controls gồm full anchor, no-output independent unit được bắt đầu bước1, no-anchor output held, valid AS-only guard transport giữ stage2 nhưng needs_revalidation, hash sai reject. Auditor bổ sung kiểm riêng **step2 blocked/step3 allowed**, bỏ toàn unit vẫn giữ IDs/unassessed/hold và sửa raw của typed `ProgressEvidence` sau verify bị reject. Không phải always-reject để đạt oracle.

### S02-2A-H3-A-02 — CLOSED

Vị trí: [h3_bindings.py:283](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h3_bindings.py:283), check_admission; check_plan actual operation/Run/base checks.

Summary now phải khớp **canonical branch + assessment + current Issue ID + SHA**. Key inventory unique, current-key coverage và changed-key summaries kiểm qua from/result pair; old keys không biến mất. Checked Plan pin Admission.from_pair bằng actual operation/Run/config base, không tự chọn self-pair=result để bỏ changed inventory. Origin map keys cũng đối chiếu.

**Thực chạy:** false DIRECT/complete summary trên CARRY undetermined trong oracle gốc bị từ chối. Focused positives DIRECT/null, CARRY applicable/undetermined, REPLACEMENT complete/incomplete đúng vẫn nhận; sai/duplicate rejects. Coherent sealed Plan fixture có Artifact/SHA thật và sai from_pair bị đúng correspondence gate từ chối, không chỉ outer hash gate. Auditor bổ sung changed Issue nhưng missing summary bị reject; đúng canonical summary nhận; duplicate có reason text khác vẫn reject.

Diagnostic `reason_codes/full_hold_reasons` được phân biệt raw text với verified facts; list rỗng không tự cấp quyền build/resolve. Không thay validators A2 hoặc biến canonical undetermined thành complete.

### S02-2A-H3-A-03 — CLOSED

Vị trí: [h3_limits.py:47](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h3_limits.py:47).

Named typed Pairs (kể cả to_pair/latest_checked_pair/head) đếm đủ ID occurrences, không unique-ID dedup. SourceRef/StageRef/handles nguyên tử không double count. Bổ sung unresolved keys/store/dispatch/analysis keys và canonical Edge endpoints; declaration ID/prose/guard text không tự thành refs. Shared Budget/slot identity và numeric ceilings giữ.

**Thực chạy:** hai original Pair count/limit failures đã sửa; focused kiểm under/exact/over caps, mixed/aggregate registry-history-config-plan-authority, same-slot replay và changed-slot rejection. Auditor tự kiểm mixed object **15 occurrences viết tay**, cap14 reject, cap15/16 nhận; replay cùng slot không cộng lại. Catalogue copied script chạy mới từ installed schemas: **2132 typed field occurrences, zero unclassified** ([catalogue](REFERENCE_FIELD_AUDIT_FINAL.json)); đây là static coverage hỗ trợ, không thay runtime expected counts độc lập.

## 4. Đánh giá contract delta trước writer

Delta a2 phù hợp scope A và đóng các invariants đã chốt; **không cần nới canonical semantics hoặc caps**:

- Closed shapes giữ draft.2, handler/package đổi0.9.0a2. `check_admission/check_plan(progress=...)` là pure API correspondence concretization, không loader/writer mới.
- Aggregate transition assessment hash pin toàn progress map làm rõ binding trước đây còn thiếu, không chọn một unit thuận tiện để bỏ phần còn lại.
- Transport conservative: stage mới xen giữa cần full current publisher anchor. Missing proof giữ outputs/hold; đây là giới hạn công khai, không bảo đảm liveness cho mọi history topology.
- Limits counter version **draft.3** ghi nhận cách đếm sửa, numeric caps/Budget30s giữ. Canonical E1/L1 schemas/registry không đổi.
- Source tests a1 có expectation E06 sai đã sửa có diff/lý do: existing-output/no-anchor không build step1; ca V độc lập có output đổi sang revalidate/admission phù hợp scope. Các negative reason assertions bổ sung PROGRESS_PROOF_REQUIRED, không bỏ lý do cũ. Original/sealed a1 tests và auditor oracle giữ byte. Test expectation đổi đúng contract, không hạ assertions/caps/timeout.

Chấp nhận delta này ở mức **audit H3-A**, không ghi runtime H3-B/C đã đạt. B-AS/C-Model+A2 vẫn cần riêng các gates §7.1: loader/trust trước checked read, durable prepare/seal/T3, OS processes, CAS/stale/crash/lost-ACK/registry restart và exact identity/effects trên từng writer path.

## 5. Integrity, package và working-tree observation I02

[INPUT_VERIFICATION](INPUT_VERIFICATION.json) xác minh lúc đầu:

- Marker/pins/manifest/seal/wheel khớp; **20.507 entries**, **431 snapshot files** khớp actual repo. Whole file manifest được hash/size hoặc symlink target kiểm độc lập, không tin status đơn thuần.
- [PACKAGE_VERIFICATION](PACKAGE_VERIFICATION.json): release ZIP bằng cả53 entries rebuild,52 installed entries kiểm trực tiếp (trừ generated RECORD), source payload/direct URL khớp; pip check đạt. A1 baseline wheel SHA12dfe52698fa24cfc80280a80b1e34afc5a612dab9cac9578243b3306a0744f5 giữ nguyên.
- Payload a1→a2 chỉ version init + h3_bindings/contracts/limits/policy đổi. h3_history, canonical schema/registry/A1/A2/persistence/H1/H2 giữ byte. S01 toàn20 entries bằng a6. Chưa claim runtime full/differential mới từ byte equality.

**S02-2A-H3-A-I02 — Thấp; working-tree drift, nguồn chưa rõ, cần tách review trước commit.** Vị trí `.gitignore` và `packages/s02/tools/prepare_p2_tests.py`:

| File | Hash snapshot/audit-start | Hash quan sát sau đó |
| --- | --- | --- |
| .gitignore | 1fb8b5c50e8482ac3a522097feca551d3d672b201fa7e37b125d979bea56eeed | c46f5256d589b2563885bd54013390ea8dc2da0d2e2e1e788579efdf41f57ada |
| prepare_p2_tests.py | f1ddd980bc0c911a6ad905cd396bbe18521f008c3eaf39aa54c66220137f094b | 9b05a6ff40b6c2a929fe8ffede563ead02a144d45162df6aab3c058bd4d89865 |

Diff hiện quan sát: thêm ignore cache/local env patterns; bỏ unused `shutil` import của adapter. Không thay product payload hoặc semantics của adapter trong diff này, nhưng **không thuộc release snapshot đã pin**. Chưa biết ai/công cụ nào/thời điểm thực hiện chính xác; không quy cho implementer hoặc tự restore/reseal. Auditor không viết hai files đó.

[WORKTREE_DRIFT](WORKTREE_DRIFT.json), [diff](WORKTREE_DRIFT.patch), [observed copies](observed-during-audit/), [strict attempt](PRESERVATION_ATTEMPT_1.txt). Strict preservation script đã dừng vì hai mismatches; v2 ghi đúng exception hashes, không gọi toàn tree unchanged. Release STATE_BEFORE423 có16 changes được khai báo/407 unchanged tại bàn giao; sau drift là18 changes/405 unchanged. Các source modules/tests/locks còn lại của snapshot431 giữ bytes. Focused tests/adapter đã copy trong audit trước khi drift; supplement dùng chính copied fixtures/conftest, không nhận adapter mới để tạo pass. Full old audit a1 **921 entries** và **11 pinned protected inputs** vẫn nguyên ([PRESERVATION_VERIFICATION](PRESERVATION_VERIFICATION.json)).

Technical pass áp dụng **wheel/source scope A đã kiểm**, không duyệt cleanup song song. Trước commit, người dùng cần xác định hai thay đổi ngoài handoff thuộc công việc nào, review và tách chúng khỏi phạm vi acceptance nếu chưa duyệt. Không cần sửa H3-A code để “xóa” observation; không xóa/rollback công việc của người khác.

## 6. Kết thúc và giới hạn

**Ba findings implementation01/02/03 CLOSED trên0.9.0a2. H3-A đủ cơ sở để người dùng nghiệm thu kỹ thuật pure policy local/synthetic.** Chưa tự nghiệm thu thay người dùng; I02 phải được đối soát riêng trước gom commit toàn tree.

[USER_REVIEW](USER_REVIEW.md) có checklist nghiệm thu/commit và bước tiếp theo. H3-B chỉ được giao sau quyết định người dùng; chưa B/C/D, I/O/CLI/writer/migration/operational/LLM/live. Không stage/commit/push, gửi chat khác hoặc đổi automation. Audit chỉ tạo evidence mới ngoài checkout, không sửa implementation/tests/oracles/dataset/history để đạt.

[FINAL_INTEGRITY](FINAL_INTEGRITY.json), [MANIFEST](MANIFEST.json), [SEAL](SEAL.json) pin report/new controls/logs/DBs/hash observations. Counts/timestamps trong artifacts phân biệt rõ auditor tự chạy và implementer supporting evidence. Rerun vào output mới; các venv/cache runtime được exclude rõ trong manifest, không claim toàn runtime đã seal.
