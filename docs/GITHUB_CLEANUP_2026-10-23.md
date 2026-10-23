# Cleanup GitHub — 23/10/2026

**Đã sửa riêng DACN-CLEANUP-01, chờ audit lại; chưa commit hoặc push.** Thay đổi docs/tooling/tracking riêng sau [nghiệm thu P3 a3](acceptance/P3_AUDIT_REPORT.md). Production payload, schemas, toàn bộ tests và locks giữ nguyên byte; không refactor nghiệp vụ hoặc chạy operational/live.

## Thay đổi và dung lượng

- Bỏ tracking **612 artifacts/snapshots**, gồm 607 files trong reports và 5 generated STATIC_CHECKS. Mọi file gốc vẫn tồn tại nguyên bytes, không xóa evidence lịch sử. Reports Markdown và CLI regression viết tay của P3 a3 tiếp tục track, nguyên byte.
- Tree trước cleanup: **853 files, 94,47 MB**. Tree dự kiến sau cleanup khoảng **269 files, 3,38 MB**; giảm khoảng **91,11 MB (96,4%)**. Đây là dung lượng files của commit/checkout, không phải `.git` hoặc evidence local. Không rewrite Git history; objects/commits cũ vẫn còn.
- Cập nhật README/AGENTS/docs theo P3 0.4.0a3 đã nghiệm thu, thay navigation phụ thuộc đường dẫn máy cá nhân bằng bản sao biên bản nguyên byte và provenance/hash.
- Thêm bootstrap/restore/verification tooling stdlib; `.gitignore` giữ outputs/bundles/runtime ngoài tracking. Smoke tool chỉ đổi lookup `result.body` thành `result.record.body` theo API S02 hiện hành. Không sửa test assertions.

## Archive và restore

Archive evidence có **12.893 members**, **2.267.394.570 bytes** file gốc, **195.295.587 bytes** nén; bootstrap bundle **65.353.334 bytes**, **1.905 members**. [Descriptors và SHA-256](../artifacts/README.md), [restore](ARTIFACTS.md), [bootstrap](BOOTSTRAP.md).

Trước `git rm --cached`: đã lập inventory/hash, tạo archive, đọc lại mọi member/hash, ghi RESTORE.md và **restore đầy đủ ra thư mục mới ngoài checkout**. Archive gồm reports trước cleanup, năm STATIC_CHECKS, audit/findings/acceptance P3 a3; không gồm toàn bộ external execution hoặc venv/cache. Bản gốc ngoài repo giữ nguyên. 129 canonical inputs (packages và tool lock) cùng 30 build-cache files local được hash-check không đổi; toàn bộ artifacts lịch sử được archive giữ hash, trừ reports/README.md là navigation được cập nhật và bản trước nằm trong archive.

## Kiểm trước và sau

| Bộ kiểm thực chạy | Trước cleanup | Sau, từ checkout sạch |
| --- | --- | --- |
| Source–wheel–installed | S01 16 / S02 26 payloads đạt | 16 / 26 đạt; METADATA/WHEEL/direct URL, pip check đạt |
| Bốn oracle P3 nguyên byte | 22 pass/backend | 22 pass/backend |
| CLI policy controls | Không chạy lại riêng trước cleanup | 14 pass/backend, factory instrumentation subprocess |
| Full S02 | Kết quả audit P3 trước cleanup: 666/backend, không nhận là lượt mới của cleanup | **666 pass/backend**, thực chạy mới |
| Full S01 a6 | Kết quả audit trước cleanup: 986/backend, không nhận là lượt mới của cleanup | **986 pass/backend**, thực chạy mới |
| Wrapper tooling | Không chạy lại trước cleanup | **339 pass** |
| Layout/CLI smoke | Fail ở tool cũ: KeyError body | **18 commands, 6 guards, 125 links đạt** |
| Archive/hash controls | Archive verified trước untracking | Full restore verified; hash mismatch/traversal/links/overwrite/noncanonical names đều refused |

Không fail/error/skip ở suites sau cleanup. Suites overlap, không cộng thành coverage độc nhất. C/Python instrumentation vẫn hoạt động; S02 dùng E1 adapter và helpers đã có, không sửa conftest hoặc assertions. Full suites chạy trên rebuild non-editable từ source có **mọi ZIP entry bằng wheel nghiệm thu**: S01 20 entries, S02 30 entries. Chỉ ZIP metadata/timestamps có thể làm SHA archive rebuild khác; locks không đổi.

Checkout thử được clone `--no-checkout --no-hardlinks`, checkout Git tree của thay đổi dự kiến bằng temporary index, không tạo commit. Trước bootstrap không có `.runtime`, `.tools`, `.bootstrap`, venv hoặc dist. Bundle được kiểm SHA/inventory/members trước extraction; ba venv mới, build inputs và output kiểm ngoài checkout, không thêm production source vào PYTHONPATH, không tải/resolve online. Không copy runtime có sẵn từ worktree vào checkout thử ngoài cơ chế bundle.

## Bàn giao commit riêng

`git rm --cached` được stage lại đúng 612 removals theo `untrack.paths`, cùng docs/tooling đã sửa. Kiểm tree và hashes nằm trong bàn giao sửa DACN-CLEANUP-01; chưa commit/push. `git add -A` sau review dùng ignore policy mới; không dùng `git add -f` cho raw artifacts. Không xóa file trên đĩa theo staged D. Rollback tracking có path list NUL và hướng dẫn ở archive; không chép đè index nếu phát sinh công việc mới.

Diff đầy đủ/summary, inventory/SHA, exact byte counts, Git tree IDs, commands/exit/logs/JUnit trước–sau và hướng dẫn restore nằm trong thư mục archive cleanup: `github-cleanup-2026-10-23`. Bàn giao này chưa thay audit độc lập đối với cleanup và không mở quyền operational/live hoặc nghiệm thu toàn S02.

## Sửa riêng DACN-CLEANUP-01

Audit cleanup ngày 23/10 phát hiện lexical normalization bỏ mất thứ tự resolve symlink và `..`. `tools/artifact_bundle.py` nay kiểm toàn graph trước effects ở cả verify/restore, từ chối escape/cycle/ambiguous aliases và xét links sẵn ở đích; giữ runtime aliases của bundle đã pin. Regression mới ở `tools/tests/test_artifact_bundle.py`; mọi test có sẵn, production và locks giữ nguyên. Kết quả mới, bootstrap sạch, tree cuối, hashes/seal tại bàn giao ngoài checkout `github-cleanup-fix01-2026-10-23`. Các số full suites trong bảng trên là lịch sử cleanup đầu, không dùng làm số chạy mới của lượt sửa này. Finding chờ auditor quyết định, không tự đóng.
