# H2-C — merge, revalidation và stress local/synthetic

`dacn-s02 0.8.0a1`, baseline repo `ecc51bc09219a35e3d7aba7e22292d2ed7b316bc`.
Đợt này do người dùng giao riêng ngày 29/10/2026; implementer cung cấp bằng chứng,
auditor độc lập kiểm bàn giao và người dùng nghiệm thu cuối. Không tự ghi nghiệm thu.

Căn cứ là H2 draft.2 §6.2, §7–10 và API H2-B. Findings H2-B 01/02 đã đóng;
[V01](</Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/AUDIT_REPORT.md>)
xác minh an toàn deadline/recovery. Full **lịch sử H2-B** vẫn C959/959,
Python958/959; người dùng cho tiếp tục H2-C sau khi biết giới hạn này. Mọi kết quả
H2-C mới phải đọc riêng tại bàn giao, không dùng để sửa kết quả H2-B.

## Phạm vi và cách chạy

H2-C mở rộng kiểm chứng writer/policy H2-B bằng tests, harness và evidence.
Phiên bản package riêng phân biệt bản bàn giao; private handler H2-B giữ phiên bản
`s02-2a-h2-b/0.7.0a2` khi implementation handler không đổi. Không đổi contracts,
canonical schemas/registry/DB2, S01, locks hoặc thuật toán H1/H2-A để làm tests xanh.
Không H3/Answer/application/source switch, bước5–9, LLM, renderer hoặc live.

Fixture `h2_c_fixtures.ManyCase` tạo checked S01 synthetic qua service thật:
U thiếu quyền, bốn V độc lập, một NFR và một constraint trong stress chính (17 obligations).
Các controls merge dùng sáu V và23 obligations. Cả hai giữ toàn
criteria theo thứ tự, priority và unknowns. Các projections scoped đi qua handlers,
T0/seal/T3, whole-graph validation và external exact approvals. Không import Model
canonical vào DB để giả kết quả handler.

Kịch bản có tên cố định: bootstrap, inspection, bốn V qua2→3→4, hai guard và bốn
retained-output revalidations cho batches V1–V2 rồi V1–V3 đã tới4. Bốn command step2 trên cùng pair chạy trong bốn OS
process riêng; chỉ một thắng CAS, ba stale. Từng stale chỉ được resubmit bằng command,
current pair, candidate/analysis raw và approval mới. Approval cũ với input mới bị từ
chối trước T0. Tổng kỳ vọng là23 finalized command,20 publication; intake không tính
vào ngưỡng20 checkpoints. Một trace riêng kiểm bốn process tranh AS-only, giữ Model:
seal từng plan bằng handler trước, rồi bốn process mới resume cùng lúc tới T3.
Trace domain chạy cả build/seal trong bốn workers; hai trace đo contention ở các
điểm khác nhau, không được mô tả AS-only là bốn concurrent builders.

Mỗi worker dùng installed wheel, Repository/connection riêng và codec factory
instrumentation C hoặc Python. Reopen/resume dùng raw/plan đã pin; không retry hoặc
auto-rebase trong worker. Barrier20s và parent communicate45s chỉ thuộc test harness;
production vẫn một Budget30s mỗi invocation, không tăng/reset theo unit/phase.

## Oracle và các đối chứng

- `test_h2_c_stress.py`: inventory17 rows của stress chính, số stage/actions/responsibilities/Parts
  theo script riêng; U held/V tiến; exact retained entities/Parts/output IDs, assessment
  parent/result hashes, guard lineage. So planned domain Records với Records thực của
  kho: stale không publish Model/Change/Issue/AS dự kiến, không chỉ kiểm status.
- `test_h2_c_merge.py`: quan hệ blocking mới từ U tới retained action/Part của V1
  tạo guard-only và bỏ toàn candidate V2; cùng quan hệ chỉ thuộc affected context
  không blanket-block V2. Revalidation đánh giá output cũ, không tăng stage hoặc
  tự publish candidate bị bỏ. Unknown applicability tiếp tục chặn graph mới;
  shared component không tự kéo các actions khác vào scope.
- `test_h2_c_fixed_point.py`: graph synthetic thuần12 actions, chuỗi workflow trước
  Parts và chuỗi Parts sau đó; kiểm reverse ở cả base/candidate, bridge cuối,
  Part–row–source swap/reparent, set reorder, Support required/unknown/empty.
  Dependencies/Support ở đây là pure graph controls, không output của handler1–4.

Expected sets/counts/dispositions được viết từ topology và source fixture, không
gọi closure/reverse/union/admission để sinh expected. Approvals/basis vẫn là synthetic
test control, không bằng chứng độc lập ngữ nghĩa hoặc xác nhận nghiệp vụ.

## Tái lập

Dùng driver offline trong bàn giao để tạo venv mới từ locks, hai copied builds,
đối chiếu S01 a6 trước cài wheel rebuild cùng version, cài S02 non-editable và chạy
collector source–wheel–installed/METADATA/WHEEL/direct URL. Root bootstrap vẫn là
lane P3 accepted-only, không đổi baseline hash cho H2-C.

```sh
/NEW/environment/candidate/bin/python -B packages/s02/tools/run_h2_c_checks.py \
  --environment /NEW/environment/environment.json \
  --scope focused --report-dir /NEW/focused

/NEW/environment/candidate/bin/python -B packages/s02/tools/run_h2_c_checks.py \
  --environment /NEW/environment/environment.json \
  --scope full --report-dir /NEW/full
```

Runner dùng E1 adapter/conftest hiện có nguyên byte, C rồi Python tuần tự, không có
suite nặng khác chạy song song. Bốn workers trong concurrency tests vẫn chạy cùng
lúc. Mỗi output mới ngoài checkout chứa copied tests/adapter hashes, argv/cwd/env,
exit/log/JUnit, process artifacts và basetemp/DB/journals kể cả khi fail. Runner
không retry, skip/xfail hoặc biến targeted pass thành full pass. Full S01, original
oracles P1/P2/P3/H1/H2-A/H2-B và L1 differential chạy riêng theo driver bàn giao.

Giới hạn: phần mềm synthetic/local, chưa semantic quality, operational power loss
hay xác nhận người dùng. Caps không bảo đảm mọi payload dưới trần luôn xong trong30s.
Kết quả đo và failures thực tế nằm trong bàn giao; tài liệu này mô tả phương pháp.
