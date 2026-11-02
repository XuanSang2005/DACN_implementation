# S02 — chỉ dẫn hiện hành

Ngày 02/11/2026 — phạm vi mới: người dùng giao **LLM local + CLI S01→S02 bước1–4**, không cloud/download model mới. H3-C `0.11.0a2` đạt audit delta local/synthetic, findings01/02 CLOSED; auditor chạy mới10 ca/backend, không full a2. **`0.12.0a1` chỉ transport/prompts trước gate LP-01**, chưa CLI tích hợp hoặc inference. Đọc [README mốc](../S02_LOCAL_LLM_PRIMITIVES.md) và [delta cần audit](../S02_LOCAL_LLM_CONTRACT_DELTA_PROPOSAL.md). Capture/provenance/authority/budget và writer live chờ audit trước implementation phụ thuộc; không dùng LocalSyntheticContinuationAuthority cho chạy thật. Giữ thay đổi chưa commit, không stage/commit/push, không sửa evidence lịch sử. Chính sách test mới: focused C trước, Python khi codec/serialization hoặc release; một job nặng/lần, không full mặc định.

**Thông tin phạm vi các lượt trước (lịch sử; phạm vi mới ở trên):**
Ngày02/11/2026: người dùng giao riêng **H3-C append-only continuation bước1–4 trên A2**, API trước CLI, tạm gác LLM. B `0.10.0a2` đã qua audit delta, finding01 CLOSED; lượt sửa B chỉ7 ca/backend, không full a2. **C-P01 draft.1 PASS_DESIGN_ONLY** theo [audit thiết kế C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-c-contract-draft1-2026-11-01/AUDIT_REPORT.md). [API C](../S02_2A_H3_C_IMPLEMENTATION.md) có candidate sửa riêng `0.11.0a2` chờ re-audit. Audit độc lập `0.11.0a1` trả **CHANGES REQUIRED**, findings S02-2A-H3-C-01/02 còn OPEN; bản sửa không tự đóng findings hoặc nghiệm thu C. Các proposal/bàn giao trước audit giữ nguyên bytes/trạng thái lịch sử. Không H3-D/CLI mới/LLM/live; giữ working tree, không stage/commit/push.

Source **0.10.0a1 — H3-B candidate chờ audit**, chưa nghiệm thu runtime; **0.9.0a2 — [H3-A đã nghiệm thu pure policy local/synthetic](../acceptance/s02-2a-h3-a-0.9.0a2-2026-10-31/README.md)**; baseline **0.8.0a1 — H2-C đã nghiệm thu kỹ thuật local/synthetic ngày 29/10/2026**, theo [audit/phạm vi và biên bản](../acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md). Auditor tự chạy **18+2 ca/backend**, full S02 **977/977** và S01 **986/986/backend** là supporting evidence implementer. AS-only presealed plans tranh T3; recovery không bảo đảm liveness mọi contention. H2-B V01 giữ safety verified và full lịch sử C959/959, Python958/959. Đợt 1/P1/P2/P3/H1/H2-A giữ nghiệm thu từng phạm vi; contract draft.3, E1/DB2 và locks nguyên. Chưa nghiệm thu toàn S02/nghiệp vụ/LLM/renderer/live hoặc operational migration/cutover. [H3 draft.2](../S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md) đạt audit thiết kế; H3-A a2 đã nghiệm thu pure; H3-B được giao tiếp, [B-P01 đã chấp thuận; runtime B đã có candidate chờ audit](../S02_2A_H3_B_CHECKPOINT_CONTRACT_DELTA_PROPOSAL.md). [Môi trường H3-B](../../reports/s02-phase2/2a-h3-b-0.10.0a1-2026-10-31/REPRODUCE.md); [bootstrap P3](../BOOTSTRAP.md) giữ lane accepted-only riêng.

[Code/config](../../packages/s02/), [tests](../../packages/s02/tests/), [tools](../../packages/s02/tools/). [README gốc](../../README.md) chỉ cách cài locks và build; S02 dependency vẫn là distribution S01 a6, không import source chéo. Với source H3-B, dùng [driver kiểm tuần tự của bàn giao](../../reports/s02-phase2/2a-h3-b-0.10.0a1-2026-10-31/REPRODUCE.md); `tools/verify_checkout.py` mặc định vẫn chạy full S02 song song. S02 giữ E1 adapter/baseline helpers, không raw suite L1 cũ.

CLI có init, checked intake S01, lookup, [handlers H1](../S02_2A_H1_IMPLEMENTATION.md) bootstrap/analyze-step/prepare-work/resume/progress và [migration offline P3](../S02_2A_P3_IMPLEMENTATION.md); không LLM/renderer. [H2 partial scope draft.2](../S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) đã [đạt audit thiết kế](../acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md), **[H2-A pure policy](../S02_2A_H2_A_IMPLEMENTATION.md) đã nghiệm thu trong phạm vi hàm thuần**. [CLI H2-B](../S02_2A_H2_B_IMPLEMENTATION.md) đã triển khai scoped bootstrap/step/revalidate/resume/progress với local synthetic authority; H2-C mở rộng kiểm chứng trên handler H2-B a2 nguyên byte và đã nghiệm thu đúng giới hạn nêu trên. [H3-B history API](../S02_2A_H3_B_IMPLEMENTATION.md) đã có candidate, đang kiểm chứng và chờ audit/nghiệm thu; chưa CLI H3. CLI H1 giữ nguyên. Sau ví dụ [S01](../s01/README.md), tạo `$DACN_WORK/s02.toml` bên ngoài checkout với nội dung:

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

H3-A a1 có [ba findings OPEN theo audit độc lập](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-a-0.9.0a1-2026-10-30/AUDIT_REPORT.md); a2 đã được [audit đóng findings và người dùng nghiệm thu pure/local/synthetic](../acceptance/s02-2a-h3-a-0.9.0a2-2026-10-31/README.md). Auditor a1 tự chạy focused99 pass/backend, oracle13 có8 fail/5 pass/backend; full1076/986/backend thuộc implementer a1. B a2 đã qua audit delta; H3-C a1 nhận CHANGES REQUIRED (findings01/02 OPEN); candidate sửa riêng a2 chờ re-audit, chưa nghiệm thu C/H3-D/CLI mới.
