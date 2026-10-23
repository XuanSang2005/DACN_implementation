# S02 — chỉ dẫn hiện hành

Package **0.4.0a3**, contract **draft.3**, DB structure **2**. Đợt 1/P1/P2/P3 đã nghiệm thu kỹ thuật trong phạm vi riêng; [P3 a3](../acceptance/P3_AUDIT_REPORT.md) đóng findings P3 01/02, chỉ local/synthetic. Chưa nghiệm thu toàn S02, nghiệp vụ/LLM/live hoặc migration operational/cutover. [Bootstrap/verification](../BOOTSTRAP.md).

[Code/config](../../packages/s02/), [tests](../../packages/s02/tests/), [tools](../../packages/s02/tools/). [README gốc](../../README.md) chỉ cách cài locks và build; S02 dependency vẫn là distribution S01 a6, không import source chéo. Kiểm suite hiện hành bằng `tools/verify_checkout.py` và environment đã bootstrap; S02 dùng E1 adapter/baseline helpers, không raw suite L1 cũ.

CLI có init, checked intake S01, lookup và [nhóm migration offline P3](../S02_2A_P3_IMPLEMENTATION.md); không chạy LLM/renderer. Sau ví dụ [S01](../s01/README.md), tạo `$DACN_WORK/s02.toml` bên ngoài checkout với nội dung:

```toml
state_dir = "s02-state"
[s01_stores]
synthetic = "s01-state/s01.sqlite3"
```

```sh
"$DACN_PY" -B -m dacn_s02 --config "$DACN_WORK/s02.toml" init
# S01_RUN_ID và S02_COMMAND_ID lấy từ kết quả thực, không dùng literal placeholder.
"$DACN_PY" -B -m dacn_s02 --config "$DACN_WORK/s02.toml" start \
  --store-key synthetic --s01-run-id S01_RUN_ID --receipt "$DACN_WORK/s02.receipt.json"
"$DACN_PY" -B -m dacn_s02 --config "$DACN_WORK/s02.toml" show-command \
  --receipt "$DACN_WORK/s02.receipt.json"
```

Đường dẫn TOML tính từ thư mục config. Có thể khai `dataset_roots`/`protected_roots` ở root TOML khi dùng nguồn thật. State S02 tách S01/dataset/checkout; guard nhận root qua AGENTS.md + pyproject.toml, bao gồm cả hai thư mục package sau di chuyển.

[Contract](../S02_OUTPUT_CONTRACT_PROPOSAL.md), [plan](../S02_IMPLEMENTATION_PLAN_PROPOSAL.md), [examples](../examples/s02/) giữ vị trí. Báo cáo [a1](../../reports/s02-phase1/IMPLEMENTATION_REPORT.md), [a2](../../reports/s02-phase1/fixes-0.1.0a2/IMPLEMENTATION_REPORT.md) và lệnh cũ là lịch sử. Trạng thái mới lấy từ audit đúng phiên bản, không sửa báo cáo cũ thành kết quả mới.

Materializer hiện hành: `python packages/s02/tools/materialize_schema.py --check`, mặc định chỉ so bytes; `--output <file mới>` tạo artifact đối chiếu, không ghi đè schema. Các scripts snapshot trong [tools/legacy](../../packages/s02/tools/legacy/README.md) không phải runner hiện hành.
