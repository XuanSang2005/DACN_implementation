# Commit plan để người dùng review — chưa thực thi

Baseline `b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57`; index sạch. Đề nghị một commit docs-only:

`docs(s02): accept H2-C local synthetic and propose H3 history design`

Nội dung dự kiến sau review:

- Cập nhật navigation: `AGENTS.md`, `README.md`, `docs/README.md`, `docs/s02/README.md`, `reports/README.md`.
- Thêm `docs/acceptance/s02-2a-h2-c-0.8.0a1-2026-10-29/`: quyết định người dùng, README phạm vi và SOURCES SHA-256 của audit external; không sửa audit gốc.
- Thêm `docs/S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md`: draft.1 chưa audit/chưa implementation.
- Thêm bàn giao `reports/s02-phase2/h2-c-acceptance-h3-design-draft1-2026-10-29/`: START_HERE/plan, proposal snapshot, baseline/input/output hashes, static checks và documentation diff. Manifest không hash chính nó; patch chỉ chứa tài liệu chính, không chứa thư mục handoff để tránh tự tham chiếu.

Trước commit: kiểm `git diff --check`, đọc `git diff` và từng file mới, đối chiếu MANIFEST, xác nhận diff không đụng `packages/`, `tools/`, pyproject/locks hoặc historical evidence. Không `git add .`; chọn đúng danh sách sau khi người dùng review. HEAD/status/index cuối lượt được ghi trong STATIC_CHECKS; không dùng dự kiến message như bằng chứng đã commit.

Nếu audit yêu cầu sửa proposal, tạo vòng sửa/bàn giao mới, giữ draft.1 snapshot/hashes/evidence nguyên byte. Trạng thái H3 chỉ được đổi khi có audit/đặc quyền người dùng tương ứng. Không gộp code H3, source switch, deployment hoặc sửa failure lịch sử vào commit này.

Không chạy stage/commit/push trong lượt này; không có lệnh tự động trong bàn giao thực hiện các thao tác ấy.
