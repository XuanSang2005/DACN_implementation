# Kết quả kiểm chứng 0.2.0a3 — finding 04

Các kết quả sau đã thực thi mới trong lượt sửa, bằng wheels non-editable trong các venv mới ngoài checkout. Đây là Astra chạy nguyên oracle của auditor và tự kiểm, không phải kết luận audit độc lập cho a3. Năm files audit và mọi helpers hiện hữu nguyên byte, được hash trước/sau. Không skip/xfail, không thay assertions.

| Kiểm tra | C extension | Python fallback | Evidence |
| --- | --- | --- | --- |
| Baseline a2: test_independent_a2.py | 5 pass / 1 fail | 5 pass / 1 fail | baseline-audit/audit-1-*.log/xml |
| Baseline a2: test_independent_mapping_carry.py | 3 pass / 1 fail | 3 pass / 1 fail | baseline-audit/audit-2-*.log/xml |
| Release a3: hai files mới | 10 pass | 10 pass | release-audit/audit-1/2-*.log/xml |
| Release a3: ba files a1 | 12 pass | 12 pass | release-audit/audit-3/4/5-*.log/xml |
| Full S02 a3 | 383 pass | 383 pass | full-regression/s02-*.log/xml |
| Full S01 a6 | 986 pass | 986 pass | full-regression/s01-*.log/xml |
| Differential L1 0.1.0a3 / P1 0.2.0a3 | 413/413 bằng nhau | 413/413 bằng nhau | differential-summary.json |
| Replay 2 graph lỗi trên a2 | 2 accepted | 2 accepted | baseline-replay-*.log |
| Replay 2 graph lỗi trên release a3 | 2 rejected đúng invariant | 2 rejected đúng invariant | release-replay-*.log |

Baseline có đúng 2 failures oracle/backend, không error/skip. Mọi suite release không fail/error/skip. Exit 1 ở replay release là rejection kỳ vọng: carry_structural_proof / replacement_structural_continuation. `replay-summary.json` kiểm đúng S02Error và instrumentation, không chỉ kiểm exit khác 0.

Hai files audit a2 gồm mapping controls unchanged, swap_review, swap_hold và task-split coverage. Ba files a1 kiểm findings 01/02/03 và các A1/source/criterion controls. 39 regression mới bao gồm cả nguồn requirement và hai acceptance criteria, swap source, reparent Part, row identity/assessment, reorder rows/Parts/ID sets, fresh/stale review, hold và kiểm riêng closure/reverse impact/target footprint. File mới chạy focused 39/39 mỗi backend trên candidate, rồi chạy lại toàn bộ trong release. 344 tests cũ giữ nguyên byte. Không lấy số tests cũ làm kết quả mới.

CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64. Runner chạy package/backend trong process riêng, cwd tạm ngoài source; helpers được định vị bằng adapter hiện hành, production import site-packages. Replay adapter chỉ toggle/instrument encoder rồi `runpy` nguyên script gốc, không import helpers. Logs/observations ghi factory calls C/Python thực. `*.command.json` ghi exact argv/cwd/environment/exit; campaign.py là script điều phối producer của lượt này.

Differential: corpus L1 cố định nguyên bytes, bốn lanes được chạy mới với interpreters legacy a3 và P1 a3 riêng. 67 accept/346 reject, toàn outcomes/diagnostics/walk paths bằng nhau, không unexpected exception. Corpus hữu hạn, phần lớn shape mutations; không chứng minh equivalence mọi graph hoặc 413 ca nghiệp vụ độc lập. Không chạy lại full suite trên wheel legacy a3 riêng; full S02 hiện hành vẫn chạy toàn tests legacy trên release.

Đóng gói: source–wheel–installed đạt 20 S02 và 16 S01 payload, METADATA/WHEEL/direct_url hashes khớp. Hai clean builds từ copies riêng có 22 entries payload+METADATA/WHEEL bằng nhau; không yêu cầu ZIP hash bằng nhau. Wheel S01 release là bản sao nguyên ZIP a6 từ dist, không rebuild/đổi lock. Materializer byte-check và pip check pass. Payload diff a2→a3 chỉ __init__.py và resolution.py, cộng METADATA version; validation.index_model, scope, profile_graph và storage legacy nguyên byte.

Tất cả output tạo vào thư mục mới. Những exit nonzero có chủ đích là baseline failures và replay reject sau sửa; không có test/harness failures bị che hoặc chuyển thành skip. Candidate/focused pass chỉ là tự kiểm trung gian; kết quả release ở các thư mục chỉ định ở trên.

Giới hạn: tests dùng nguồn/DB/reviews synthetic; unit proof tests không thay whole-graph validation. Code kiểm cấu trúc/source association/footprint đã biểu diễn, không xác nhận đủ nghĩa vụ nghiệp vụ hoặc có người thật review. Không chạy operational store/migration, E1 persistence/transactional CAS/claims mới, live LLM/renderer hoặc dataset evaluation. Không suy kết quả code thành nghiệm thu P1 hay quyền P2/P3/2C.
