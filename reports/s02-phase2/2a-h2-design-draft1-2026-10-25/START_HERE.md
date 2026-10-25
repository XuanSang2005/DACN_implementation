# Bàn giao thiết kế 2A-H2 draft.1

Ngày 25/10/2026. **Hoàn tất mốc tài liệu; H2 chờ audit thiết kế, chưa triển khai.** H1 `0.5.0a2` đã nghiệm thu kỹ thuật local/synthetic, fresh E1/full scope; H1-01/02 đóng theo [audit](../../../docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md) và [biên bản](../../../docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json). Không nghiệm thu toàn S02 hoặc chất lượng nghiệp vụ/LLM/renderer.

1. [Proposal H2 — s02-2a-h2/0.1.0-draft.1](../../../docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md): contracts, nguồn/basis, ảnh hưởng trước Parts, fixed point mở đủ action_ids của mọi Part, kiểm union khi ghép, progress và safety H1.
2. [Thay đổi và yêu cầu auditor](DESIGN_HANDOFF.md): phạm vi thực tế, các quyết định D1–D4, tiêu chí và giới hạn.
3. [Danh sách thay đổi / commit message](COMMIT_PREPARATION.md): tách code/tests H1 đã có trước với tài liệu sửa lượt này. Người dùng tự chọn/stage/commit; agent chưa stage/commit/push.
4. [Bằng chứng mới](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/STATIC_CHECKS.json), [diff riêng lượt tài liệu](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/documentation.diff.patch), [inventory bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/protected-verification.json), [hashes/seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/SEAL.json). Đây là kiểm tĩnh, không phải một lượt chạy regression/build mới.

Mốc H2 đề nghị: cùng snapshot S01 test store, giữ family U thiếu thông tin ở hold, cho V đủ căn cứ đi qua handlers 2→3→4; full Model/mapping/Issues và toàn inventory vẫn được kiểm sau ghép/reopen/resume. Các mock/expected assessments là synthetic. Run còn hold vẫn blocked dù V đã xong việc.

D1 authority/binding, D2 guard-only khi merge chưa đủ proof, D3 units/entry/protocol/CLI và D4 limits/stress **còn cần chốt**. Chưa có quyền code H2/H3; không đổi storage/schema, gọi LLM/live hoặc phát hành wheel trong lượt này. Mọi bàn giao/evidence cũ giữ nguyên byte.
