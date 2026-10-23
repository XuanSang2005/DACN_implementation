# Sửa riêng S02-2A-P3-02 — dacn-s02 0.4.0a3

Ngày 23/10/2026, Asia/Ho_Chi_Minh. **Đã implement và kiểm thử, chờ audit độc lập. Không tự đóng finding 02 hoặc nghiệm thu toàn P3.** Fix 01 giữ kết luận audit a2 trong đúng phạm vi auditor đã đóng.

## Phạm vi và kết quả

Guard mới chặn namespace và marker reservation tự sinh trước khi ghi vào source, dataset/protected roots, thư mục S01 hoặc checkout. Áp dụng cho copy mới và resume, kể cả instance Migration đã tạo trước khi layout/policy fixture thay đổi. Chỉ kho synthetic/test mới; mọi lần từ chối giữ inventory đường dẫn/bytes của fixture, không tự đổi namespace để tiếp tục.

Wheel phát hành duy nhất: `release/dacn_s02-0.4.0a3-py3-none-any.whl`.

SHA-256: `fa50f818ae572d2139daeafb60de2f395b92adddce5c4e18cc4d9de8c3a95214`.

Baseline duy nhất là wheel a2 đã audit: `/Users/macbookpro/Documents/DACN_implementation/reports/s02-phase2/2a-p3-fix01-0.4.0a2-2026-10-23/handoff-wheel/dacn_s02-0.4.0a2-py3-none-any.whl`, SHA-256 `7fbd0fb483989f7e57f53ee2b4545aa72b2efec07e36c9436401af55cd5d97ab`. Checkout có dirty state từ các đợt trước; diff đợt này lấy snapshot a2 đã đối chiếu hash, không dùng git HEAD thay baseline release.

## Thay đổi

`reservation.check_paths(settings, destination, source)` kiểm cả namespace lẫn leaf marker bằng `local_io.writable` hiện hành, sau khi từ chối symlink ở mọi component. `within`/`samefile` loại đường dẫn thuộc source và nhận aliases thực trên filesystem. Marker có sẵn phải là regular file, một link. Không đổi cách ghép tên: leaf giữ nguyên spelling để case/Unicode aliases tiếp tục dùng chung marker.

Migration gọi guard ở constructor, đầu copy/resume trước receipt effects, trong shared parent lock, và ngay đầu `publish` trước mkdir/open/write/fsync. Việc kiểm lại tại publish cũng chặn namespace vừa mang dấu checkout ở checkpoint `before_reserve`. Với namespace đã thuộc vùng cấm, resume bị từ chối cả khi target đã committed; không tự di chuyển, xóa hoặc sửa reservation để tiếp tục.

Chỉ bốn file có sẵn thay đổi: `packages/s02/pyproject.toml`, `__init__.py`, `migration.py`, `reservation.py`; thêm `test_reservation_path_policy.py`. CLI regression supplement nằm trong bàn giao. [SOURCE_DIFF.patch](SOURCE_DIFF.patch) thể hiện toàn bộ diff product và test mới. [WHEEL_DIFF.patch](WHEEL_DIFF.patch) cho thấy payload chỉ đổi version, migration và reservation. DDL/schema, registry/L1 resources, local_io, repository và các executable khác giữ bytes a2.

[invariant-preservation.json](invariant-preservation.json) kiểm 28 function/method AST cũ: các hàm không sửa giữ AST; constructor/copy/publish giữ toàn bộ AST cũ sau khi bỏ đúng guard additions và policy arguments mới. Shared flock, create-only marker, thứ tự fsync/hook, partial refusal, receipt/manifest/activation và tên alias của fix 01 không đổi.

## Kiểm thử thực chạy

Mỗi số trong bảng là mỗi backend, không cộng hai lanes hoặc suites overlap thành coverage độc nhất. Candidate không có fail/error/skip ở các bộ dưới.

| Bộ kiểm | C | Python |
| --- | --- | --- |
| Baseline a2, nguyên bốn oracle P3 | 15 pass / 7 fail | 15 pass / 7 fail |
| a3, `test_independent_p3_partial.py` | 10 pass | 10 pass |
| a3, `test_independent_p3_preservation.py` | 4 pass | 4 pass |
| a3, `test_independent_reservation_paths.py` | 4 pass | 4 pass |
| a3, `test_independent_reservation_cli.py` | 4 pass | 4 pass |
| Reservation regression fix 01, nguyên byte | 34 pass | 34 pass |
| Regression guard/resume/alias mới | 43 pass | 43 pass |
| CLI supplement có instrumentation subprocess | 14 pass | 14 pass |
| Full S02 trên installed wheel | 666 pass | 666 pass |
| Full S01 a6 trên cùng venv | 986 pass | 986 pass |

Execution verified tại [/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-p3-fix02-0.4.0a3-2026-10-23-verified](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-p3-fix02-0.4.0a3-2026-10-23-verified). Lệnh gốc, cwd, exit và thời gian có ở `*.command.json`; JUnit/logs/observations ở các thư mục suites. `test-results.json` tổng hợp trực tiếp các JUnit. API codec factory counts xác nhận C/Python thực; worker observations giữ IPC checkpoints/PID và kill exit. Hai oracle cũ và 34 regressions cũ chạy lại trên a3, không thay kết quả bằng evidence a2.

43 ca mới gồm policy protected/S01/checkout trên fresh, receipt-only resume, committed resume; constructor mới và instance tái sử dụng; namespace/marker trùng source; protected/S01 roots với aliases case/Unicode; symlink namespace/marker, hardlinked marker; resume hợp lệ với aliases tên đích; recheck ngay trước publish. Fixture resume-source dùng receipt synthetic hợp dạng, IDs/fingerprint/path của layout cuối; đây là fixture kiểm guard, không receipt operational.

Oracle CLI nguyên bản gọi `-m dacn_s02` theo codec mặc định của executable. Chạy nó trong hai pytest lanes không tự chứng minh Python fallback của subprocess. 14 ca bổ sung dùng `cli_probe.py` hiện hành để chọn/đếm codec trước installed CLI: 12 refusal cases và hai allowed alias resume controls mỗi backend. Observations ghi 12 subprocess/lane với 2 factory calls, hai subprocess/lane với 3 calls; backend còn lại 0.

Bốn oracle độc lập giữ nguyên file/hash/assertions; [oracle-inputs.json](oracle-inputs.json) và audit_sha256 trong runner commands ghim inputs. Test adapter/helper runner hiện hành không sửa. Lượt thử đầu tiên gặp hai lỗi trong test mới: helper kỳ vọng OSError thay S02Error bọc lỗi receipt ACK, và trùng tên tham số `kind` khi ghi evidence. Chỉ sửa test, giữ inventory/refusal assertions. Logs lượt đó được giữ riêng ở execution không có hậu tố `-verified`, gồm 33 failures của test API và 4 failures của CLI fixture mỗi backend. Không dùng lượt lỗi làm kết quả bàn giao; production wheel payload không đổi giữa hai lượt.

## Package và bảo toàn

Bốn venv mới từ lock offline; runtime CPython 3.13.16 có GIL, SQLite 3.53.1, macOS arm64/filesystem local. Build từ copied inputs ngoài checkout, cài non-editable, pytest cwd ngoài checkout, không đưa production source vào Python path. Full S02 hai backend ở hai process riêng; full S01 gọi runner nguyên bản. Baseline S01 a6 và locks/dependencies giữ nguyên.

Rebuild từ bản sao input sạch khớp mọi ZIP entry, gồm METADATA/WHEEL/RECORD. Collector kiểm source–wheel–installed S01/S02 và ghi cross-version diff a2→a3; pip check đạt. Payload wheel a3 giữ đúng tập file a2 và chỉ ba Python payloads thay đổi như trên. Wheel dùng audit lại ghim đúng SHA ở đầu báo cáo, không chọn nhầm wheel build của lượt thử.

Collector đầu tiên của lượt verified dừng vì S01 cài qua uv từ lock thiếu `direct_url.json`. Đã kiểm toàn bộ 16 payload S01 bằng wheel a6 trước/sau, cài lại chính wheel a6 bằng pip non-editable để bổ sung provenance; mọi payload bytes giữ nguyên. Collector chạy lại đạt ở `package-evidence-verified/`, pip check lại đạt; giữ nguyên log/output lỗi metadata. Đây là sửa tooling cài đặt, không thay mã S01 hoặc test assertions. Wrapper bàn giao bổ sung bước pin wheel này; [REPRODUCTION_TOOLING_DIFF.patch](REPRODUCTION_TOOLING_DIFF.patch) ghi đúng khác biệt với wrapper đã chạy full suite. Một lượt `--focused-only` mới ở output `-repro-check` đã chạy trọn wrapper cập nhật, gồm bốn oracle, 77 regressions reservation, 14 CLI controls, rebuild và collector; payload wheel bằng wheel phát hành. Full S02/S01 lấy đúng lượt verified đã nêu, không cần thay bằng lượt mới vì product/S01 payload không đổi.

Đối chiếu cuối giữ 4.111 artifacts bàn giao a2, 8.783 protected files đã khai báo của repository, 815 files audit a1 và 1.080 files audit a2; seal a2 khớp audit độc lập. Trong 129 current-code inputs a2, chỉ đúng bốn file dự kiến đổi. Git HEAD giữ nguyên. Đây là kiểm hash các inventory đã nêu, không tuyên bố đã kiểm inventory toàn dataset ngoài repository. Test fixtures tạo ở temp riêng; không thực hiện ghi hoặc migration vào dataset/operational stores.

`ARTIFACT_HASHES.json`/`SEAL.json` niêm phong bàn giao; `EXECUTION_HASHES.json` ghim logs, JUnit, fixtures/artifacts được giữ, build inputs/wheels và failed attempt. Venv/cache không đưa vào seal; tái tạo từ locks. Chạy verify read-only theo [REPRODUCE.md](REPRODUCE.md).

## Giới hạn và bàn giao

Chưa chạy lại riêng toàn bộ oracle P1/P2 hoặc differential L1 trong đợt fix hẹp này; full S02 hiện hành bao gồm regressions của các phần đó. Không suy tests synthetic hoặc metadata reviewer thành xác nhận nghiệp vụ/người thật. Không chứng minh hardware power loss, disk-full thực, network FS, executable cũ/raw SQL, xóa marker hoặc thay parent inode ngoài cooperating protocol. Partial a1 cũ thiếu marker/metadata vẫn phải cách ly, không retro-fit hoặc repair.

Không cleanup, thay config/cutover operational, gọi LLM/live, commit hoặc push. Source và evidence lịch sử giữ nguyên, ngoài đúng thay đổi product hiện hành đã nêu. Cần auditor độc lập quyết định S02-2A-P3-02 và kiểm hồi quy fix 01 trên wheel phát hành; trạng thái hiện tại là **chờ audit lại**.
