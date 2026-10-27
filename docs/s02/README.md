# S02 — chỉ dẫn hiện hành

Package **0.6.0a2 — H2-A đã nghiệm thu kỹ thuật pure policy local/synthetic**, theo [audit và quyết định người dùng 26/10](../acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/README.md); findings 01/02/03 đã đóng. Giữ contract **draft.3**, DB structure **2**. Đợt 1/P1/P2/P3/H1 đã nghiệm thu kỹ thuật từng phạm vi; [H1 a2](../acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) đạt local/synthetic fresh/full scope và đóng H1-01/02. Chưa nghiệm thu toàn S02/nghiệp vụ/LLM/renderer/live hoặc operational migration/cutover. [Môi trường H2-A](../../reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/REPRODUCE.md); [bootstrap P3](../BOOTSTRAP.md) giữ lane accepted-only riêng.

[Code/config](../../packages/s02/), [tests](../../packages/s02/tests/), [tools](../../packages/s02/tools/). [README gốc](../../README.md) chỉ cách cài locks và build; S02 dependency vẫn là distribution S01 a6, không import source chéo. Với source H2-A a2, dùng [driver kiểm tuần tự của bàn giao](../../reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/REPRODUCE.md); `tools/verify_checkout.py` mặc định vẫn chạy full S02 song song. S02 giữ E1 adapter/baseline helpers, không raw suite L1 cũ.

CLI có init, checked intake S01, lookup, [handlers H1](../S02_2A_H1_IMPLEMENTATION.md) bootstrap/analyze-step/prepare-work/resume/progress và [migration offline P3](../S02_2A_P3_IMPLEMENTATION.md); không LLM/renderer. [H2 partial scope draft.2](../S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) đã [đạt audit thiết kế](../acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md), **[H2-A pure policy](../S02_2A_H2_A_IMPLEMENTATION.md) đã nghiệm thu trong phạm vi hàm thuần**. H2-B/C/H3 và pipeline H2 chưa nghiệm thu; CLI/writer/provider I/O H2-B chưa triển khai và cần giao việc riêng; CLI H1 giữ nguyên. Sau ví dụ [S01](../s01/README.md), tạo `$DACN_WORK/s02.toml` bên ngoài checkout với nội dung:

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
