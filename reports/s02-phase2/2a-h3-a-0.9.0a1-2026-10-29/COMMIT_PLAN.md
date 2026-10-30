# Commit plan để người dùng review — chưa stage/commit/push

Giữ HEAD `b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57` và các docs design đã có lúc bắt đầu. Không reset. Gợi ý commit message sau audit/review:

`feat(s02): add H3-A pure history contracts and policy`

Đề nghị review riêng các nhóm:

- D1–D5/design status: biên bản mới tại `docs/acceptance/s02-2a-h3-design-draft2-2026-10-29/`, current navigation/AGENTS, link audit external. Không sửa proposal/snapshots/handoff/audit đã seal hoặc NEXT_PROMPT draft.1.
- H3-A mới: năm `h3_*.py` modules, helper/controls/tests `h3_fixtures.py` và `test_h3_a_*.py`, runner tooling `run_h3_a_checks.py`, package version/description `0.9.0a1` và `__init__` version. Không code H3-B/C/D hoặc thay dependency/locks/canonical validators/DB2/H1/H2/S01.
- API/contract details/coverage/reproduce/failures/handoff mới. Raw logs/JUnit/DB/builds/delivery wheel/manifest/seal ngoài checkout theo START_HERE, không đưa dataset/runtime/venv vào commit.

Đọc IMPLEMENTATION_DELTA.patch là delta từ **working tree trước H3-A**, khác với diff toàn repo so HEAD vốn gồm các docs design hợp lệ từ trước. PRESERVATION.json/CURRENT_SOURCE_INVENTORY và static checks xác nhận trước/sau, hashes/payload và index. Không `git add .`; người dùng chọn đúng files sau review, lưu ý JSON/TXT/patch artifacts có thể bị gitignore và được inventory external. Không tự force-stage hoặc sửa ignore.

Tests pass không tự là auditor đóng implementation findings hoặc người dùng nghiệm thu. H3-B/C/D cần giao riêng sau mốc tương ứng; commit không mở operational/LLM/live. Agent dừng sửa sau seal + AUDIT_READY để auditor đọc đúng payload.
