# Kết quả thực chạy — bản sửa S02 0.1.0a2

Wheel cài offline vào venv mới; tests chạy từ cwd tạm ngoài checkout. Toàn bộ dữ liệu test mới là synthetic. Các kết quả này do implementation chạy, chưa thay audit độc lập bản sửa.

| Suite | Backend | Passed | Failed / errors / skipped | Exit | Logs / JUnit |
| --- | --- | ---: | --- | ---: | --- |
| s02 | c | 189 | 0 / 0 / 0 | 0 | [s02-c.log](s02-c.log) / [XML](s02-c.xml) |
| s02 | python | 189 | 0 / 0 / 0 | 0 | [s02-python.log](s02-python.log) / [XML](s02-python.xml) |
| s01 | c | 986 | 0 / 0 / 0 | 0 | [s01-c.log](s01-c.log) / [XML](s01-c.xml) |
| s01 | python | 986 | 0 / 0 / 0 | 0 | [s01-python.log](s01-python.log) / [XML](s01-python.xml) |
| audit | c | 7 | 0 / 0 / 0 | 0 | [audit-c.log](audit-c.log) / [XML](audit-c.xml) |
| audit | python | 7 | 0 / 0 / 0 | 0 | [audit-python.log](audit-python.log) / [XML](audit-python.xml) |

S02: 141 ca cũ giữ nguyên + 7 ca audit chuyển thành regression + 41 ca mở rộng = 189. Bảy tests audit ngoài cũng chạy nguyên bản riêng; không cộng chúng vào số 189 như ca mới độc lập.

## Backend được đo

Factory counts trong process chính (workers ghi riêng trong observations/logs, không cộng ngầm):

- s02/c: `S02_ENCODERS selected=c calls={'c': 71681, 'python': 0}`.
- s02/python: `S02_ENCODERS selected=python calls={'c': 0, 'python': 71681}`.
- s01/c: `Observed real encoder factory calls: {'c': 6597, 'python': 0}; selected=c`.
- s01/python: `Observed real encoder factory calls: {'c': 0, 'python': 6597}; selected=python`.
- audit/c: `S02_ENCODERS selected=c calls={'c': 4837, 'python': 0}`.
- audit/python: `S02_ENCODERS selected=python calls={'c': 0, 'python': 4837}`.

## Bất biến và bằng chứng

- `test_audit_regressions.py`: 7 repro bắt buộc, rollback logical DB image trên các batch bị từ chối. `test_audit_guards.py`: positive/negative cùng identity, pin từng field, unknown outcome, reuse, 6 inventory cases và 6 checked-read fault-injection cases.
- [Observations S02](s02-observations.json) gồm 5 races × 2 backends và 4 kill points × 2 backends. Hai processes/connections thực, barrier/IPC/deadline như suite gốc; 18 DB quiescent được lưu. Lock thật, lost-ack và rollback tests cũng passed trong full suite.
- [Legacy store results](legacy-store-results.json): 12 DB a1 sai bị từ chối, 2 model trung gian vẫn readable nhưng gate blocked; 18 DB a1 hợp lệ readable. Chỉ thao tác bản sao tạm.
- [Manifest](manifest.json): CPython/SQLite/dependencies, 7 clean-install/pip/smoke commands đạt, 14 S02 + 16 S01 files source=installed=wheel và đầy đủ inventories; hashes/PRAGMA của 18 DB cạnh tranh/kill mới.
- [Protected after](protected-after.json): 3.492/3.492 file trong inventory đầu lượt không đổi; gồm đúng 198 file bảo vệ cũ. AGENTS/contract/dataset tham chiếu/a1 artifacts giữ nguyên.
- [Build commands](build-commands.json), [môi trường mới](fresh-test-environment.json), [S02 commands](s02-commands.json), [S01 commands](s01-commands.json), [audit commands](audit-commands.json) giữ argv/cwd/exit/logs.

## Lượt chưa đạt được giữ lại

- `before/`: 7 failed/backend trên wheel a1, đúng lỗi audit đã yêu cầu sửa.
- `development/`: 188 passed + 1 failed/backend do import nhầm trong fixture mới. Fixture đã sửa; không xóa log để che lần chạy này.
- `targeted.log`: 48 regression mới passed C sau sửa fixture. Bằng chứng cuối là bảng full suites phía trên.

Không chạy LLM, renderer, workflow đầy đủ, benchmark hoặc thử mất điện/disk-full. Không dùng số lượng tests để tuyên bố đủ chất lượng nghiệp vụ.
