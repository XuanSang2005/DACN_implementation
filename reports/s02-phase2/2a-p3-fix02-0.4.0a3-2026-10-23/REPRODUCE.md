# Tái lập bản sửa riêng P3-02

Trạng thái: đã sửa, chờ audit độc lập; không tự đóng finding. Chỉ fixture synthetic mới, không operational/live hoặc dataset thật.

1. Chạy kiểm read-only trước: `.runtime/python/bin/python3.13 -B reports/s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/verify_handoff.py --source` từ repository implementation.
2. Chọn một output **chưa tồn tại, ngoài checkout**, rồi chạy:

```sh
/Users/macbookpro/Documents/DACN_implementation/.runtime/python/bin/python3.13 -B \
  /Users/macbookpro/Documents/DACN_implementation/reports/s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/reproduce.py \
  --output /private/tmp/dacn-p3-a3-independent-NEW
```

Wrapper tạo bốn venv mới từ lock offline, build từ bản sao input sạch, cài wheel non-editable, gọi nguyên bốn oracle cũ+mới qua runner hiện hành với helper adapter đã có. Source production không được đưa vào Python path; pytest chạy ở cwd temp ngoài checkout. Runtime pin CPython 3.13.16 có GIL, SQLite 3.53.1/macOS arm64; không đổi dependencies/locks. Các lệnh, cwd, exit, JUnit và observations được lưu vào output mới.

Kỳ vọng baseline a2: hai oracle cũ 14 pass/backend; hai oracle mới 1 pass/7 fail/backend, không skip/setup error. Kỳ vọng a3: bốn oracle 22 pass/backend, reservation regression cũ 34 và regression mới 43 pass/backend; CLI supplement 14 pass/backend với factory counts thực của subprocess C/Python. Full S02: 666 pass/backend. Các suites có overlap; không cộng thành coverage duy nhất.

Rebuild đối chiếu mọi ZIP entry, gồm METADATA/WHEEL/RECORD; không ép hash ZIP bằng bản phát hành. Collector đối chiếu source–wheel–installed cả S01/S02, giữ baseline S01 a6; diff cross-version S02 ghim đúng wheel a2. Wheel được build khi tái lập là rebuild; wheel phát hành duy nhất và SHA nằm trong `handoff.json`/`release/`.

Full S01 được chạy riêng trên chính candidate venv của output mới, bằng `<OUTPUT>/candidate-venv/bin/python -B /Users/macbookpro/Documents/DACN_implementation/tools/run_checks.py --package s01 --report-dir <OUTPUT>/full-s01`. Kỳ vọng 986 pass/backend; runner vẫn giữ encoder instrumentation. Lệnh thực tế của lượt bàn giao ở `full-s01.command.json` bên cạnh file này.

Oracle CLI nguyên bản dùng `-m dacn_s02` với codec mặc định của executable. Chạy file đó trong hai pytest lanes không chứng minh riêng Python fallback của subprocess. `test_cli_policy_controls.py` bổ sung dùng harness `cli_probe.py` hiện hành để chọn/đếm backend trước khi gọi installed CLI, giữ nguyên cả bốn oracle độc lập.

Không chạy script finalization/seal vào bàn giao đã niêm phong. Không dùng thư mục lịch sử làm output. Lượt thử helper test đầu tiên được giữ nguyên ở thư mục execution không có hậu tố `-verified`; kết quả dùng bàn giao chỉ lấy từ lượt `-verified`.
