# Kết quả kiểm thử bản sửa P1 a2

Tất cả kết quả dưới đây đã thực thi trong lượt sửa này. Đây là Astra chạy lại oracle độc lập và tự kiểm, **không phải kết luận re-audit của auditor**. Production code import từ site-packages của wheel non-editable; test helpers được định vị bằng adapter hiện hành. Không đổi assertions/skip/xfail của ba files audit.

| Lane | C extension | Python fallback | Bằng chứng |
| --- | --- | --- | --- |
| a1 trước sửa: audit nhóm 1 | 4 fail | 4 fail | baseline-audit/audit-1-*.log |
| a1 trước sửa: audit followup | 4 pass, 1 fail | 4 pass, 1 fail | baseline-audit/audit-2-*.log |
| a1 trước sửa: controls | 3 pass | 3 pass | baseline-audit/audit-3-*.log |
| Release a2: audit nhóm 1 | 4 pass | 4 pass | release-audit-02/audit-1-*.log |
| Release a2: audit followup | 5 pass | 5 pass | release-audit-02/audit-2-*.log |
| Release a2: controls | 3 pass | 3 pass | release-audit-02/audit-3-*.log |
| Full S02 | 344 pass | 344 pass | full-regression/s02-*.log/xml |
| Full S01 | 986 pass | 986 pass | full-regression/s01-*.log/xml |
| Differential L1 a3/a2 | 413/413 khớp | 413/413 khớp | differential-summary.json |

Các lane release không error/fail/skip; baseline có đúng 5 failures oracle/backend, không error/skip. 37 tests mới gồm operation identity/uniqueness trước dispatch, scope task ở cùng Model và qua một/hai cạnh Model, missing/removed correspondence, Part vs action, modified correspondence, footprint target cùng/khác Model và review binding. Các assertions/tests a1/a3 hiện hữu giữ nguyên byte.

C/Python chạy process riêng, `simplejson` factories được instrument thật, counts trong logs và observations.json. CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64. Bốn venv mới ngoài checkout cho baseline a1, candidate, release a2 và a3 differential; bootstrap từ locks không thay dependencies. Exact commands/cwd/exit codes ở `*.command.json` và từng runner `commands.json`.

Differential dùng corpus L1 cố định của handoff a1, nguyên bytes; 67 accepted/346 rejected, toàn outcomes/diagnostics/schema-walk paths bằng nhau, không unexpected exception. Đây là corpus hữu hạn, phần lớn mutations là shape; không chứng minh equivalence mọi graph hay 413 ca nghiệp vụ độc lập. Hash corpus và lane nằm trong manifest.

Source–wheel–installed: collector đạt S01 16 payload và S02 20 payload, METADATA/WHEEL và direct_url SHA khớp. S01 release là bản sao nguyên ZIP a6 lịch sử. S02 clean build-01/release có payload + METADATA/WHEEL bằng nhau; không ép ZIP hashes. Baseline a1 → a2 diff chỉ __init__, profile_graph, resolution và METADATA version. Source schema L1/E1/registry giữ nguyên hash; materializer byte-check pass, pip check pass. Năm canonical graphs lịch sử validate bằng installed a2, log `canonical-validation.log`; đây là fixtures synthetic, không phải export production hoặc business acceptance.

## Diagnostics đã giữ nguyên

- `focused-01`: gọi adapter audit cho test nằm ngay trong thư mục tests khiến pytest nạp conftest hai lần, lỗi option --encoder-backend. Không có kết quả sản phẩm từ lane này. Chạy `focused-02` bằng bản sao nguyên byte ở ngoài cây tests: 30/30 pass mỗi backend. Snapshot bản test khi đó ở `focused-02-test-snapshot.py`; bảy ca bổ sung sau đó được chạy trong full suite final 344.
- `release-audit`: lỗi gõ thiếu đường dẫn file controls, FileNotFoundError trước khi chạy test. `release-audit-02` dùng đường dẫn lấy từ inventory đã lưu và đạt 12/12 mỗi backend. Không sửa oracle để xử lý lỗi harness.
- Candidate build-01 cũng đạt ba files audit và 30 focused tests/backend. Bản release được build từ copy mới, cài trong venv mới và chạy lại đầy đủ. Không dùng candidate pass thay final checks.

Không chạy audit legacy 7+4 thành lane ngoài riêng trong lượt sửa này; full S02 vẫn chạy nguyên 307 tests a1 (bao gồm regression legacy). Không chạy live LLM/renderer, benchmark nghiệp vụ, operational migration, E1 persistence/CAS/claims. Synthetic human reviews chỉ kiểm structural binding; không xác nhận có người thật xem hoặc chấp thuận nội dung.
