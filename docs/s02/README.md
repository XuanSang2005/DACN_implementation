# S02 — chỉ dẫn hiện hành

Source **0.9.0a1 — H3-A a2 đã bàn giao sửa ba findings để audit lại**; baseline **0.8.0a1 — H2-C đã nghiệm thu kỹ thuật local/synthetic ngày 29/10/2026**, theo [audit/phạm vi và biên bản](../acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md). Auditor tự chạy **18+2 ca/backend**, full S02 **977/977** và S01 **986/986/backend** là supporting evidence implementer. AS-only presealed plans tranh T3; recovery không bảo đảm liveness mọi contention. H2-B V01 giữ safety verified và full lịch sử C959/959, Python958/959. Đợt 1/P1/P2/P3/H1/H2-A giữ nghiệm thu từng phạm vi; contract draft.3, E1/DB2 và locks nguyên. Chưa nghiệm thu toàn S02/nghiệp vụ/LLM/renderer/live hoặc operational migration/cutover. [H3 draft.2](../S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md) đạt audit thiết kế; chỉ H3-A được giao, chưa nghiệm thu implementation. [Môi trường H3-A](../../reports/s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/REPRODUCE.md); [bootstrap P3](../BOOTSTRAP.md) giữ lane accepted-only riêng.

[Code/config](../../packages/s02/), [tests](../../packages/s02/tests/), [tools](../../packages/s02/tools/). [README gốc](../../README.md) chỉ cách cài locks và build; S02 dependency vẫn là distribution S01 a6, không import source chéo. Với source H3-A a2, dùng [driver kiểm tuần tự của bàn giao](../../reports/s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/REPRODUCE.md); `tools/verify_checkout.py` mặc định vẫn chạy full S02 song song. S02 giữ E1 adapter/baseline helpers, không raw suite L1 cũ.

CLI có init, checked intake S01, lookup, [handlers H1](../S02_2A_H1_IMPLEMENTATION.md) bootstrap/analyze-step/prepare-work/resume/progress và [migration offline P3](../S02_2A_P3_IMPLEMENTATION.md); không LLM/renderer. [H2 partial scope draft.2](../S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) đã [đạt audit thiết kế](../acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md), **[H2-A pure policy](../S02_2A_H2_A_IMPLEMENTATION.md) đã nghiệm thu trong phạm vi hàm thuần**. [CLI H2-B](../S02_2A_H2_B_IMPLEMENTATION.md) đã triển khai scoped bootstrap/step/revalidate/resume/progress với local synthetic authority; H2-C mở rộng kiểm chứng trên handler H2-B a2 nguyên byte và đã nghiệm thu đúng giới hạn nêu trên. H3 history entry chưa triển khai; CLI H1 giữ nguyên. Sau ví dụ [S01](../s01/README.md), tạo `$DACN_WORK/s02.toml` bên ngoài checkout với nội dung:

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

H3-A a1 có [ba findings OPEN theo audit độc lập](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-a-0.9.0a1-2026-10-30/AUDIT_REPORT.md); a2 chỉ sửa đúng ba findings, chưa nghiệm thu. Auditor a1 tự chạy focused99 pass/backend, oracle13 có8 fail/5 pass/backend; full1076/986/backend thuộc implementer a1. Không H3-B/C/D.
