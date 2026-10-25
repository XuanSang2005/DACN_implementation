# Mục lục tài liệu

S01 a6, S02 Đợt 1/P1/P2/P3/H1 đã nghiệm thu kỹ thuật trong từng phạm vi. **H1 `0.5.0a2` đạt local/synthetic, fresh/full scope**, H1-01/02 đóng theo [audit](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) và [biên bản](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json); [hướng dẫn](S02_2A_H1_IMPLEMENTATION.md), [bàn giao lịch sử](../reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md). H2 draft.2 đã [đạt audit thiết kế](acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md), D01/D02 đóng ở mức thiết kế; chưa code/nghiệm thu implementation. Chưa nghiệm thu toàn S02/nghiệp vụ/LLM/renderer/live hoặc cấp quyền operational/cutover/H2/H3/2B/2C.

- [Workspace và trạng thái hiện hành](../README.md), [bootstrap từ checkout sạch](BOOTSTRAP.md).
- [S01 code/CLI](s01/README.md), [S02 code/CLI](s02/README.md), [migration P3](S02_2A_P3_IMPLEMENTATION.md).
- [Reports lịch sử](../reports/README.md), [archive/restore](ARTIFACTS.md), [cleanup GitHub](GITHUB_CLEANUP_2026-10-23.md).
- [Nguồn nghiên cứu ngoài repo](EXTERNAL_REFERENCES.md), [AGENTS](../AGENTS.md).
- [Thiết kế điều phối và handlers bước 1–4 draft.2](S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md) — audit thiết kế đạt 24/10; H1 a2 đạt kỹ thuật 25/10; proposal/bàn giao cũ giữ nguyên.
- [H2 partial scope/G2 draft.2](S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) — D1–D4 đạt thiết kế local/synthetic theo [biên bản](acceptance/s02-2a-h2-design-draft2-2026-10-25/DESIGN_ACCEPTANCE.json); [bàn giao delta lịch sử](../reports/s02-phase2/2a-h2-design-draft2-2026-10-25/START_HERE.md). Proposal giữ nguyên byte đã audit; H2-A pure policy chỉ triển khai khi có giao riêng.

| Giai đoạn | Contract và kế hoạch | Ví dụ |
| --- | --- | --- |
| S01 | [Output draft.2](S01_OUTPUT_CONTRACT_PROPOSAL.md), [plan](S01_IMPLEMENTATION_PLAN_PROPOSAL.md) | [Envelopes](examples/s01/), [synthetic input](examples/s01-local/) |
| S02 | [Output draft.3](S02_OUTPUT_CONTRACT_PROPOSAL.md), [plan draft.3](S02_IMPLEMENTATION_PLAN_PROPOSAL.md) | [JSON minh họa](examples/s02/) |
| S02 phase 2 | [Storage/migration plan](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md) | [P1](S02_2A_P1_IMPLEMENTATION.md), [P2](S02_2A_P2_IMPLEMENTATION.md), [P3](S02_2A_P3_IMPLEMENTATION.md) |

Contract/examples và reports cũ giữ nguyên bytes/trạng thái lịch sử. Generated `STATIC_CHECKS*.json` đã archive và ngừng tracking; trên máy hiện tại vẫn giữ, máy mới xem bản restore ngoài checkout. Examples là minh họa cấu trúc, không phải kết quả LLM/renderer hoặc xác nhận nghiệp vụ. Dùng biên bản đúng phiên bản để xác định nghiệm thu; không sửa report cũ theo trạng thái mới.
