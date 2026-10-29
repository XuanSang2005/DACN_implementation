# Tái lập ở output mới

Không chạy đè evidence seal. Repo phải khớp before inventory/wheel a2; nếu đã đổi, dùng đúng snapshot/helper versions. Không di chuyển venv cũ.

1. Tạo thư mục NEW ngoài checkout. Copy từ [evidence](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29): setup.py, run_target.py, v01_trace.py, v01_worker_v2.py, v01_launch_v2.py, test_release_boundaries_v02.py, test_before_write_control.py, test_hot_deadline_v3.py.
2. Chạy python3 -B NEW/setup.py. Driver cài locks offline rồi exact a2, pip check và source–wheel–installed. Dùng runtime/wheelhouse pin trong repo; không bỏ qua hash/import failure. Driver tạo E1 helpers/ADAPTER, original test và original deadline oracle.
3. Chạy tuần tự, mỗi runner tự chạy C rồi Python:

    python3 -B NEW/run_target.py measured-original test_original.py

    python3 -B NEW/run_target.py proposed-release test_release_boundaries_v02.py test_before_write_control.py

    python3 -B NEW/run_target.py deadline-verification test_hot_deadline_v3.py test_deadline_original.py

Runner giữ basetemp/DB thay vì xóa; plugin autoload off, production imports installed wheel. **Xem command.json/JUnit: runner tiếp tục backend sau failure để thu evidence; exit của runner không thay pytest exit codes.**

Deadline test phụ thuộc snapshots measured-original, chọn invocation đúng receipt store ID, copy DB+journal crash sang tmp mới. Hash/command/reserved/store identity được kiểm; không fake header, không mở/ghi snapshot seal. Wall v3 giữ input lớn gốc, chèn chờ tại after_seal hoặc đầu published_plan; Budget mới chỉ ở API invocation mới.

Đọc HARNESS_ERRATUM; các exploratory v1/v2 giữ để tái lập lỗi writer/import/hypothesis, không phải gate mặc định hay production fixes. Không cần full suite để tái lập kiểm V01 này. Full mới cần giả thuyết/phạm vi quyết định riêng.

[Before](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/before.json), [preservation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/PRESERVATION.json), [manifest](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/MANIFEST.json). Wheel a2 SHA-256: b5fcdba097c7fec74d87cd5a548c550764fdc05827301944bfa9bcbff307fb76.
