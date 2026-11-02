# Findings response — candidate 0.11.0a2

Căn cứ: [audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-c-0.11.0a1-2026-11-02/AUDIT_REPORT.md), [C-P01](../../../docs/S02_2A_H3_C_CONTINUATION_CONTRACT_DELTA_PROPOSAL.md). Trạng thái cả hai finding: **OPEN theo audit a1; bản sửa gửi re-audit**, chưa có kết luận đóng finding/nghiệm thu.

## S02-2A-H3-C-01

Nguyên nhân: `project` giữ explicit findings nhưng union chỉ đọc analysis; candidate held/unread/unrepresented có thể biến mất khi analysis usable. A2/source authority không giải quyết mâu thuẫn đó.

`h3_continuation_plan.build` đưa payload candidate đã parse/kiểm pin vào pure `check_union`. Union giữ tập raw held + unrepresented; analysis không held tương ứng dẫn `CANDIDATE_SOURCE_HOLD_MISSING`. Raw unread dẫn `CANDIDATE_INVENTORY_UNINSPECTED`. Cả hai giữ toàn candidate dưới technical guard trên base: không Model/Change mới, không tăng stage, Run blocked, raw/analysis exact bytes và projection giữ nguyên. Không tự tạo business Answer/decision hoặc viết lại câu hỏi nguồn.

Compatible holds đi tiếp qua các kiểm canonical source coverage, independence, closure/fixed point, retained outputs và union base/candidate hiện có. Vì vậy U held có đủ proof vẫn cho V độc lập tiến; raw chỉ held mà analysis usable không đủ proof, kể cả đã được cấp synthetic authority. Thông tin giữ trong raw đã promote, failed raw hashes của guard và reason codes; không thay negative fact bằng claim usable.

Bằng chứng mới mỗi backend: oracle raw4 + runtime2; regression stage1/2 raw-negative4 và compatible U hold/unrepresented2; controls bridge thật2, shared component1, unknown hold1, raw rejection2, tamper reconstruction2. Hai oracle runtime kiểm actual DB, giữ nguyên application history và providerless report không ghi DB.

## S02-2A-H3-C-02

Nguyên nhân: gate chỉ kiểm assignment và remaining_gap, bỏ qua covered_portion. Dùng lại helper H1 `part_has_gap` mà không sửa helper/validator H1. Bước4 kiểm mọi Part trong selected closure của whole candidate; null coverage vẫn là gap, không suy hoặc tự điền coverage.

Candidate thiếu coverage giữ projection null, toàn Model trên base, stage3/needs_revalidation/blocked. Mapping có coverage đầy đủ tiếp tục pass bước4/current. Bằng chứng mới: oracle mapping2/backend, regression projection/null/base preservation1/backend, full steps1–4 positive, anchored tasks steps3/4 và bridge controls. Gate trước successors và publication, không chạm writer/CAS/canonical.

## Preservation và giới hạn

Distribution a2; C private contract/handler protocol bytes giữ nguyên. [Diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/fix.diff), [preservation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/PRESERVATION.json), [source–wheel–installed](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/delivery/package-evidence/manifest.json), [case matrix](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/CASE_MATRIX.json), [DB readbacks](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/DB_READBACK_SUMMARY.json). Canonical schemas/registry/DB2, H1/H2/B/S01, locks, tests/oracles/evidence cũ không đổi. Không full/safety rerun; kết quả cũ không được nâng thành kết quả a2.
