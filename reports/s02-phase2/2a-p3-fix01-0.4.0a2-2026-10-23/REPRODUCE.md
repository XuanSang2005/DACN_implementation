# Tái lập vào output mới

Không dùng thư mục bàn giao làm output chạy lại. Scripts chỉ dùng kho synthetic/test do fixtures tạo; không mở operational store. Giữ nguồn DB1 mode=ro. Không cần network, LLM, migration dataset hoặc thao tác cleanup.

Từ repo, dùng runtime đã pin và một tên output chưa tồn tại ngoài checkout:

```sh
.runtime/python/bin/python3.13 -B reports/s02-phase2/2a-p3-fix01-0.4.0a2-2026-10-23/reproduce.py --output /private/tmp/dacn-p3-a2-audit-NEW
```

Thêm `--focused-only` để chỉ tái hiện a1 và kiểm hai oracle P3 + 34 regressions mới trên a2. Không thêm production source vào `PYTHONPATH`. Script kiểm hash source/oracles trước khi chạy, tạo venv mới non-editable cho a1/a2/P1/L1 từ locks offline, chạy từ cwd ngoài source; oracle/assertions nguyên file. Test mới được copy nguyên byte ra ngoài cây có conftest để tránh đăng ký plugin hai lần. Adapter helpers P2 giữ nguyên nội dung/hash như baseline; không monkeypatch production để làm oracle pass.

Lệnh đầy đủ chạy full S02 hai process backend độc lập, S01, sáu oracle P1, P2 nguyên bản/v2, differential 413 outcomes và rebuild từ copy sạch. Collector đối chiếu source–wheel–installed, METADATA/WHEEL, direct URL; `pip check`. Mọi stdout/stderr, argv/cwd/environment/exit code, JUnit và instrumentation đi vào output mới. Baseline a1 và P2 oracle nguyên bản có exit 1 dự kiến: a1 phải tái hiện 7 failures/backend; P2 có một lỗi setup đã được auditor ghi nhận, không được thay assertion. Xem bảng kết quả và tên ca cụ thể trong `test-results.json` của bàn giao.

`campaign.py` ghi lại cách đã chạy lượt implementation với label/env riêng. Không chạy lại labels cũ: runner dùng create-only và phải dừng nếu output đã tồn tại. Các thư mục `dev*`/`final*`/`release-*`/`audit-*` là attempts trước khi chốt marker theo filesystem aliases và giữ mã lỗi identity conflict tương thích; **chỉ `handoff-wheel/dacn_s02-0.4.0a2-py3-none-any.whl` là wheel được bàn giao audit**. `handoff-*` là kiểm chứng cho wheel này; không dùng kết quả attempts thay thế.

`reproduce.py --help` và chế độ `--focused-only` đã chạy end-to-end trên đúng wheel bàn giao trong bốn venv mới. Logs/JUnit/hash copies tại [reproduction-focused-evidence](reproduction-focused-evidence/summary.json). Chế độ đầy đủ của wrapper chưa được chạy thêm lần nữa; các lệnh thành phần đã chạy thật trong campaign và có logs riêng. Cần runtime/wheelhouse và các oracle/helper lịch sử tại các paths được ghim; script không tải hoặc tự thay chúng khi thiếu. Chưa chứng minh môi trường khác macOS arm64/filesystem local đã pin.
