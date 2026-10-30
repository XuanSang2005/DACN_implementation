# H3 design draft.2 — sửa riêng D01/D02, chờ audit lại

Ngày 29/10/2026 · `s02-2a-h3-history/0.1.0-draft.2` · **Docs-only; chưa tự đóng findings, chưa ghi H3 đạt audit hoặc được giao code.** Người dùng chốt scope cuối sau auditor kiểm lại.

- [Proposal hiện hành](../../../docs/S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md), [snapshot draft.2 nguyên byte](PROPOSAL_DRAFT2.txt).
- [Phản hồi từng finding/vị trí sửa](FINDINGS_RESPONSE.md), [delta và quyết định còn chờ](DELTA.md).
- [Audit draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-design-draft1-2026-10-29/AUDIT_REPORT.md); metadata/nguồn đọc/hash tại [SOURCES](SOURCES.json).
- [Diff chính xác draft.1 → draft.2 của proposal/navigation](DRAFT1_TO_DRAFT2.patch), [proposal trước sửa](PROPOSAL_BEFORE.txt), [state/hash trước lượt](STATE_BEFORE.json), [kiểm tĩnh/bảo toàn](STATIC_CHECKS.json), [manifest SHA-256](MANIFEST.json).
- [Handoff draft.1](../h2-c-acceptance-h3-design-draft1-2026-10-29/START_HERE.md) giữ **toàn thư mục nguyên byte**, gồm snapshot/patch/hashes/static evidence; [hồ sơ H2-C](../../../docs/acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/README.md) không sửa.

D01: chọn protocol immutable local/synthetic registry do invoker pin ngoài DB; API/closed format/version/required Issue-ID inventory **toàn store**, dependency digests, T0/plan pins và loader trước checked read ở inspect/restart/resume/report. Có walkthrough prepare→seal→restart→resume/replay cùng identity và negatives missing/tampered/self-derived evidence. Historical lane tách semantic authority, không thêm human decisions/authentication/network/UI. Giới hạn R cố định khi có pending H3 work được nêu để review, không hứa online registry upgrade.

D02: E20/E21 và E18/registry restart là **core bắt buộc ngay B-AS và C-Model+A2**. B có hai OS processes/same-command/AS CAS/T0-seal-T3 faults; C kiểm path Model+Change+typed A2 successors mới, crash/reopen/lost ACK, exact plan/raw/reserved IDs/current-history refs/application counts, guard/rejection. D mở rộng CLI/four-worker/large-history stress, không là lần đầu kiểm safety C. Tên harness/cases hiện có được đối chiếu source, chưa chạy chúng.

HEAD vẫn `b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57`. Bắt đầu với docs draft.1 đang có trong working tree, index chưa stage; giữ toàn changes hợp lệ, không reset. Chỉ sửa proposal và nhãn/navigation H3 hiện hành; không mở lại H2-C/H2-B/V01. Diff trong thư mục này là **delta từ working tree draft.1**, không phải toàn diff so HEAD. Handoff draft.1 vẫn mô tả snapshot lịch sử của nó; manifest draft.1 không phải manifest live của proposal đã sang draft.2.

Đã thực hiện **kiểm tĩnh**: JSON/links/diff/hashes, before→after allowlist, HEAD/index và snapshot equality; kết quả cụ thể trong STATIC_CHECKS. Không application imports, suites/build/wheel, code H3, LLM/live, stage/commit/push. Các walkthrough/matrix/safety gates là **kế hoạch chưa chạy**, không kết quả đo runtime hoặc auditor xác nhận.

Các JSON/TXT/patch là artifacts local có inventory; gitignore hiện hành có thể không liệt kê chúng trong `git status`. Chúng tồn tại và được hash trong manifest, không sửa ignore hoặc tự force-stage. Review proposal + FINDINGS_RESPONSE + delta rồi giao auditor kiểm lại; không triển khai H3 trong lượt này.
