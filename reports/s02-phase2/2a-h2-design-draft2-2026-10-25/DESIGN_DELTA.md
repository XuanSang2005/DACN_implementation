# Delta draft.1 → draft.2 và kiểm bảo toàn

**Chỉ tài liệu, chờ audit lại.** Không triển khai adapter, handlers, commands, tests hay storage mới. Không mở store ứng dụng, build/bootstrap/install hoặc gọi LLM/live; không stage/commit/push.

## Tập thay đổi thực tế

| Path/nhóm | Lý do |
| --- | --- |
| docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md | Bump proposal/private protocol đề nghị draft.2; D01 provider/CLI/binding/restart; D02 guard/tasks/progress/P_guard/AS-only revalidate/result derivation; D3 H2 bootstrap riêng; D4 counters/budget; thêm traces/gates |
| AGENTS.md, docs/README.md, reports/README.md | Navigation hiện hành tới draft.2 và trạng thái findings chờ audit lại, không tự ghi accepted |
| docs/S02_2A_H1_IMPLEMENTATION.md | Chỉ đổi nhãn link H2 draft.1→draft.2, không đổi nghiệm thu/hành vi H1 |
| 3 Markdown bàn giao mới | START_HERE, FINDINGS_RESPONSE, tài liệu này; không sửa bàn giao/evidence cũ |

[Inventory đầu lượt](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/before.inventory.json) chụp trạng thái thực tế trước sửa; **13.139 files** gồm git-visible và reports lịch sử, snapshot306 visible files tại before/. HEAD/index/status trước có code/tests/docs H1 chưa commit; delta lần này so snapshot thực, không nhận phần code H1 đó thành thay đổi mới. [External inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/external.before.inventory.json) còn ghim toàn bộ output H2 draft.1, audit draft.1 và LaTeX; không chỉnh assertions/oracle hoặc evidence lịch sử.

[Diff proposal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/proposal.diff.patch), [diff toàn lượt](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/documentation.diff.patch), [hash tài liệu](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/documentation.inventory.json), [bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/protected-verification.json) và [STATIC_CHECKS](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/STATIC_CHECKS.json) cho auditor đối chiếu. Nguyên tắc: chỉ5 existing docs đổi, thêm3 docs bàn giao; toàn production/tests/locks/registry/schema/DB2/S01 và reports/evidence cũ trong inventory phải nguyên byte. Bản proposal draft.1 trước sửa phải khớp SHA `ca06434426b1022106e3d95a236b3bfc3c4b46e16cbb47e513d6dd1683ac60b6` đã audit.

## Thay đổi thiết kế có chủ ý

- Chọn một provider local rõ, interface/tuple/control flags và codes; không thay trust boundary bằng `trusted=true` hay hash DB. API provider là input caller tin cậy, không xác nhận business hoặc thêm authentication framework.
- Analysis raw được pin ở StageArtifact riêng trong T0 cùng candidate và **một** primary config; dùng persistence hiện có. Không nhét raw dài trong config để vượt string cap; serial caps/counters rõ. Không thêm bảng/schema/dependencies.
- Revalidate AS-only là work mode mới, không lần build thứ hai hoặc sửa input của sealed resume. Guard có predicate/origin/current selection; close guard kỹ thuật không close business holds hoặc global mapping task. Cần sửa output là terminal/out_of_scope H2, chưa tự mở H3.
- Hoãn bridge finalized H1 bootstrap; bootstrap H2 riêng đủ mốc. Correctness union/bridge/revalidation có ngay B; C chỉ stress4 workers/≥20checkpoints.
- Source inventory/criteria, all-action Part closure/fixed point, mapping-row/source context, CAS/receipt/T0/seal/T3/unknown/lost ACK của draft.1 giữ nền tảng; không thiết kế lại semantics A1/A2/G2.

## Kiểm mới và giới hạn

Kiểm tĩnh mới: SHA inventory/protected/external, bản sao before/final, local links/table structure, diff whitespace/replay, HEAD/index unchanged. [Commands/logs](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/commands/) và [seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft2-2026-10-25/SEAL.json). Không application tests/C/Python/build/install; mọi traces/gates trong proposal là kỳ vọng chưa chạy, không có wheel H2.

Hashes chứng minh bytes trong inventory, không chứng minh thiết kế đúng hoặc filesystem ngoài inventory. Không xác minh URLs Internet; không stress runtime, ký số/authentication hoặc power loss. Proposal/bàn giao H2 draft.1 và tài liệu H1 lịch sử giữ nguyên byte; chỉ source proposal hiện hành được sửa theo phạm vi người dùng giao. Kết luận: **đã sửa thiết kế, chờ audit lại**; quyền implementation cần audit/duyệt/phạm vi riêng.
