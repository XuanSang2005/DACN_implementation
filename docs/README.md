# Mục lục tài liệu

S01 a6, S02 Đợt 1/P1/P2/P3 đã nghiệm thu kỹ thuật trong từng phạm vi. S02 hiện hành **0.4.0a3**, [P3 local/synthetic](acceptance/P3_AUDIT_REPORT.md), findings P3 01/02 đã đóng. Chưa nghiệm thu toàn S02/nghiệp vụ/LLM/live hoặc cấp quyền operational migration/cutover/2B/2C. [Biên bản và nguồn/hash](acceptance/).

- [Workspace và trạng thái hiện hành](../README.md), [bootstrap từ checkout sạch](BOOTSTRAP.md).
- [S01 code/CLI](s01/README.md), [S02 code/CLI](s02/README.md), [migration P3](S02_2A_P3_IMPLEMENTATION.md).
- [Reports lịch sử](../reports/README.md), [archive/restore](ARTIFACTS.md), [cleanup GitHub](GITHUB_CLEANUP_2026-10-23.md).
- [Nguồn nghiên cứu ngoài repo](EXTERNAL_REFERENCES.md), [AGENTS](../AGENTS.md).

| Giai đoạn | Contract và kế hoạch | Ví dụ |
| --- | --- | --- |
| S01 | [Output draft.2](S01_OUTPUT_CONTRACT_PROPOSAL.md), [plan](S01_IMPLEMENTATION_PLAN_PROPOSAL.md) | [Envelopes](examples/s01/), [synthetic input](examples/s01-local/) |
| S02 | [Output draft.3](S02_OUTPUT_CONTRACT_PROPOSAL.md), [plan draft.3](S02_IMPLEMENTATION_PLAN_PROPOSAL.md) | [JSON minh họa](examples/s02/) |
| S02 phase 2 | [Storage/migration plan](S02_PHASE2_2A_SCHEMA_MIGRATION_PROPOSAL.md) | [P1](S02_2A_P1_IMPLEMENTATION.md), [P2](S02_2A_P2_IMPLEMENTATION.md), [P3](S02_2A_P3_IMPLEMENTATION.md) |

Contract/examples và reports cũ giữ nguyên bytes/trạng thái lịch sử. Generated `STATIC_CHECKS*.json` đã archive và ngừng tracking; trên máy hiện tại vẫn giữ, máy mới xem bản restore ngoài checkout. Examples là minh họa cấu trúc, không phải kết quả LLM/renderer hoặc xác nhận nghiệp vụ. Dùng biên bản đúng phiên bản để xác định nghiệm thu; không sửa report cũ theo trạng thái mới.
