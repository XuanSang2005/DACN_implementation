# Chuẩn bị commit — người dùng tự thực hiện

**Agent chưa stage/commit/push.** Index đầu lượt rỗng; HEAD `4c7e69719dbd1a6e4215cfd01764c6750962ee7f`. Đây là danh sách để review, không khẳng định các file đã nằm trong Git index.

Lượt này chỉ đổi 7 tài liệu hiện hành và thêm 9 files tài liệu/provenance. Code/config/tests H1 đã có trong working tree trước lượt này và giữ nguyên bytes. Cụ thể, pyproject.toml/__init__.py/cli.py S02, 7 h1_*.py production và 9 files tests/helpers là **19 files implementation H1 có sẵn**, không phải code H2. Execution draft.2 và các bàn giao H1 cũng là công việc có sẵn, giữ lịch sử.

## Commit message đề nghị cho mốc H1 + tài liệu H2

Nếu gom toàn bộ mốc H1 đã audit cùng tài liệu hiện hành thành một commit, dùng:

~~~text
feat(s02): add accepted H1 local flow and H2 design proposal

Add the audited 0.5.0a2 offline handlers 1-4 and their regressions.
Record H1 local/synthetic acceptance and closure of H1-01/02.
Propose H2 scope admission, impact closure and merge checks for design audit.
Keep H2 unimplemented and preserve S01, schemas, DB2, locks and evidence.
~~~

Message nói implementation H1 vì tree còn 19 files code/tests H1 chưa commit từ trước. H1 nghiệm thu chỉ local/synthetic/fresh E1/full scope, không nghiệm thu nghiệp vụ/toàn S02. Nếu người dùng tách commit H1 riêng, message cho phần tài liệu là `docs(s02): record H1 acceptance and propose H2 partial scope`; cần chọn hunks/paths phù hợp, giữ navigation không trỏ tới files chưa đưa vào commit. Không dùng thao tác stage toàn repo một cách mặc định.

## Danh sách paths ứng viên của tree hiện tại

Danh sách gồm công việc có sẵn + tài liệu lượt này; chỉ files visible, không wheels/venvs/logs/generated snapshots. [COMMIT_CANDIDATES.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/COMMIT_CANDIDATES.json) ghi SHA-256, tracked/untracked và phân loại trước/lượt này; [documentation.diff.patch](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/documentation.diff.patch) chỉ chứa delta tài liệu lượt này. Người dùng review tree/index sau khi tự chọn staging, trước commit.

- AGENTS.md
- README.md
- docs/BOOTSTRAP.md
- docs/README.md
- docs/S02_2A_H1_IMPLEMENTATION.md
- docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md
- docs/S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md
- docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_ERRATUM_A1.md
- docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/AUDIT_REPORT.md
- docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json
- docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/SOURCES.json
- docs/acceptance/s02-2a-h1-0.5.0a2-2026-10-25/oracle-correction.json
- docs/s02/README.md
- packages/s02/pyproject.toml
- packages/s02/src/dacn_s02/__init__.py
- packages/s02/src/dacn_s02/cli.py
- packages/s02/src/dacn_s02/h1_builders.py
- packages/s02/src/dacn_s02/h1_candidates.py
- packages/s02/src/dacn_s02/h1_cli.py
- packages/s02/src/dacn_s02/h1_limits.py
- packages/s02/src/dacn_s02/h1_recovery.py
- packages/s02/src/dacn_s02/h1_service.py
- packages/s02/src/dacn_s02/h1_store.py
- packages/s02/tests/h1_fixtures.py
- packages/s02/tests/h1_worker.py
- packages/s02/tests/test_h1_audit_fixes.py
- packages/s02/tests/test_h1_candidates.py
- packages/s02/tests/test_h1_cli.py
- packages/s02/tests/test_h1_flow.py
- packages/s02/tests/test_h1_integrity.py
- packages/s02/tests/test_h1_limits.py
- packages/s02/tests/test_h1_safety.py
- reports/README.md
- reports/s02-phase2/2a-h1-0.5.0a1-2026-10-24/IMPLEMENTATION_REPORT.md
- reports/s02-phase2/2a-h1-0.5.0a1-2026-10-24/REPRODUCE.md
- reports/s02-phase2/2a-h1-0.5.0a1-2026-10-24/START_HERE.md
- reports/s02-phase2/2a-h1-0.5.0a1-2026-10-24/TEST_RESULTS.md
- reports/s02-phase2/2a-h1-design-draft2-2026-10-23/START_HERE.md
- reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/FINDINGS_RESPONSE.md
- reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/HARNESS_NOTES.md
- reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/REPRODUCE.md
- reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/START_HERE.md
- reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/TEST_RESULTS.md
- reports/s02-phase2/2a-h2-design-draft1-2026-10-25/COMMIT_PREPARATION.md
- reports/s02-phase2/2a-h2-design-draft1-2026-10-25/DESIGN_HANDOFF.md
- reports/s02-phase2/2a-h2-design-draft1-2026-10-25/START_HERE.md

Không cleanup/remove artifacts, đổi locks, sửa history hoặc phát hành version mới trong lượt tài liệu. Outputs/hashes bên ngoài checkout phục vụ audit, không nằm trong danh sách commit. Trạng thái thiết kế: **H2 chờ audit; chưa triển khai**.
