# H3-A fixes 0.9.0a2 — bàn giao để audit lại

**Hoàn tất sửa/kiểm local-synthetic riêng ba findings; chưa audit lại hoặc người dùng nghiệm thu.** S02-2A-H3-A-01/02/03 vẫn **OPEN chờ auditor độc lập**. D1–D5 đã chấp thuận, D01/D02 đóng design-only; không H3-B/C/D.

- [FINDINGS_RESPONSE](FINDINGS_RESPONSE.md): từng ID/vị trí sửa, source-test E06 diff/lý do, không always-reject.
- [CONTRACT_DELTA](CONTRACT_DELTA.md), [coverage](COVERAGE_MATRIX.md), [API](../../../docs/S02_2A_H3_A_IMPLEMENTATION.md).
- [Reproduce](REPRODUCE.md), [mọi failures/limits](FAILURES_AND_LIMITS.md), [commit plan chưa thực thi](COMMIT_PLAN.md).
- [Evidence START_HERE](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/START_HERE.md), [kết quả mới](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/DELIVERY_RESULTS.json), [mọi attempts](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/TEST_RESULTS.json), [exact commands/logs](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/COMMANDS.json).
- [Delta a1-working-tree→a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/A2_DELTA.patch), [bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/PRESERVATION.json), [source inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/CURRENT_SOURCE_INVENTORY.json), [snapshot inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/REPOSITORY_SNAPSHOT_INVENTORY.json), [static checks](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/STATIC_CHECKS.json), [typed-field catalogue](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/REFERENCE_FIELD_AUDIT_FINAL.json).
- [Manifest](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/MANIFEST.json), [seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/SEAL.json), [seal check](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/SEAL_CHECK.json), [AUDIT_READY](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/AUDIT_READY.json), [verify read-only](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/verify_handoff.py).

## Authoritative wheel duy nhất

[Delivery wheel](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/delivery-release/wheels/dacn_s02-0.9.0a2-py3-none-any.whl), 183910 bytes; SHA-256:

`483c9b960c481653b35c0efbae0d5c194d46e6d6895790e69205dbb193ad0e15`

ZIP bằng exact environment-v5/build ZIP đã chạy focused/oracle, sau đó cài lại chính delivery path non-editable trước full/collector. environment-v1/v2/v3/v4 cùng delivery/ và delivery-final/ là precursor/provisional; các build/rebuild ZIPs còn lại chỉ evidence, không release authority. Hai copied builds S02 bằng payload/METADATA/WHEEL; S01 rebuild toàn20 entries bằng a6 trước thay same-version rebuild. Baseline a1 ZIP SHA `12dfe52698fa24cfc80280a80b1e34afc5a612dab9cac9578243b3306a0744f5` giữ nguyên, khác version nên collector ghi diff a1→a2 riêng. [Private schema exports](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/delivery-release/private-contracts/INDEX.json).

## Kết quả mới của implementer a2

| Gate | C | Python |
| --- | --- | --- |
| Focused final v7 (gồm assessment-chain transport) | 129/129 | 129/129 |
| Hai oracle nguyên bản replay bằng original helper | 13/13 | 13/13 |
| Full S02, gồm129 H3-A controls | 1106/1106 | 1106/1106 |
| Full S01 | 986/986 | 986/986 |

Không failure/error/skip trong delivery gates này; wrappers/layout/pip check/source→wheel→installed/direct URL đạt. Một job nặng, C rồi Python, internal race/crash concurrency giữ. Focused129 là129 distinct H3-A cases trong full, không cộng repeats/oracles thành số ca độc lập hoặc gọi là auditor tự chạy.

Audit **a1** tự chạy focused99 pass/backend nhưng oracle13 có8 fail/5 pass/backend, không harness error; full1076/986 lịch sử là implementer a1. Kết quả a2 trên là **implementer replay**, findings vẫn chờ audit độc lập. V1 có5 failures/backend, V2 có2/backend; full provisional v2 bị SIGINT sau partial C1049 cases để bổ sung Plan base/from-pair correspondence; v3 dừng partial C675 để hoàn tất catalogue typed refs, cả hai không là full pass cuối; logs/JUnit/DB/source copies giữ. Oracle-v3 là launcher failure không JUnit: original helper resolve symlink ra runtime ngoài venv. [ORACLE_LAUNCHER](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30/ORACLE_LAUNCHER_V5.json) chứng minh physical interpreter copy nguyên byte tại candidate/bin, đúng sys.prefix/installed packages, để original helper/oracles chạy nguyên assertion vào oracle-v7. Không sửa original files/caps/timeout/assertions, không ghi đè output hoặc che failure.

## Phạm vi và điểm dừng

Progress/config/admission/anchor được buộc vào finalized/promoted provenance. Unit được claim phải có complete publisher stage/output inventory; unit thiếu proof giữ IDs unassessed/held. No-anchor existing output không build đè; independent no-output unit vẫn bắt đầu step1, full valid stage2/current cho step3 chứ không lặp step2. Valid assessment-chain transport giữ stage và guard needs_revalidation, hashes sai reject. Summary A2 khớp canonical branch/assessment/ID/SHA/inventory; Plan.from_pair pin actual operation/Run base, không tự chọn result_pair để bỏ inventory; Pair/typed keys/Workflow Edge counters đủ occurrences theo exhaustive schema catalogue, atomic StageRef/SourceRef không đếm hai lần, ceilings/shared Budget giữ.

[Delta API/counter draft.3](CONTRACT_DELTA.md) là đối tượng audit trước writer B/C, không thay canonical A1/A2 hoặc tạo human decisions/Answer/application/source switch/completed-output edits. Không loader/Repository factory/I/O/CLI/writer/operational/LLM/live/dataset; B-AS/C-Model+A2 safety §7.1 chưa được A chứng minh. Proposal/schemas/registry/DB2/H1/H2/S01/locks, a1 snapshots/handoff/patch/hashes và pinned auditor inputs giữ byte theo inventory. NEXT_PROMPT draft.1 mismatch không restore/reseal.

HEAD b0d6ff2/index giữ nguyên, chưa stage/commit/push. MANIFEST→SEAL→SEAL_CHECK rồi AUDIT_READY last; sau marker dừng sửa để auditor đọc đúng payload. Người dùng nghiệm thu cuối.
