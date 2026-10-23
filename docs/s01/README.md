# S01 — chỉ dẫn hiện hành

Package **0.1.0a6**, [nghiệm thu kỹ thuật CLI local](../acceptance/S01_ACCEPTANCE.json); không xác nhận đúng nghiệp vụ. [Code/config](../../packages/s01/), [tests](../../packages/s01/tests/), [tools](../../packages/s01/tools/). Root pyproject không còn là package S01.

Xem [hướng dẫn workspace](../../README.md) để cài wheel non-editable, build riêng và chạy hai backend. Namespace/CLI vẫn `dacn_s01`. Runner riêng: `python packages/s01/tools/run_checks.py --report-dir <thư mục mới>`; chạy bằng interpreter venv đã cài package, không PYTHONPATH src.

Ví dụ smoke synthetic (các biến lấy theo README gốc; không phải log chạy):

```sh
DACN_WORK=$(mktemp -d -t dacn-local)
"$DACN_PY" -B -m dacn_s01 --state-dir "$DACN_WORK/s01-state" init
"$DACN_PY" -B -m dacn_s01 --state-dir "$DACN_WORK/s01-state" submit \
  --mode create --input "$DACN_ROOT/docs/examples/s01-local/synthetic-clinic.input.json" \
  --receipt "$DACN_WORK/s01.receipt.json"
"$DACN_PY" -B -m dacn_s01 show-run --receipt "$DACN_WORK/s01.receipt.json"
```

State/receipts ở ngoài checkout và dataset; khai báo dataset_roots thật khi dùng dữ liệu nguồn. [Hướng dẫn CLI a6 cũ](../S01_LOCAL_GUIDE.md) giữ chi tiết flags, exit codes, config, receipt/recovery; **đường dẫn package/locks/venv ở phần môi trường của file cũ thuộc layout lịch sử**, thay bằng vị trí trong README mới. Không sửa tài liệu cũ hoặc kết quả [Đợt 4](../../reports/s01-phase4/IMPLEMENTATION_REPORT.md).

Contract [draft.2](../S01_OUTPUT_CONTRACT_PROPOSAL.md), [kế hoạch](../S01_IMPLEMENTATION_PLAN_PROPOSAL.md), [schema đóng gói](../../packages/s01/src/dacn_s01/schemas/input/1.0.0/). Source/resources/locks giữ nguyên bytes trong đợt layout; DB structure 1, chưa đổi semantics.
