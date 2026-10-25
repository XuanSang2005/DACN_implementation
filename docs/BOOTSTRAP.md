# Bootstrap và kiểm checkout

Trạng thái 25/10/2026: H1 `0.5.0a2` đã [nghiệm thu local/synthetic](acceptance/s02-2a-h1-0.5.0a2-2026-10-25/S02_2A_H1_ACCEPTANCE.json). Lane tools/bootstrap.py bên dưới giữ kiểm source P3 `0.4.0a3` với bundle accepted-only. Source H1 dùng [driver offline và commands H1](../reports/s02-phase2/2a-h1-fixes-0.5.0a2-2026-10-25/REPRODUCE.md), cùng bundle/locks; không ép equality khác version hoặc sửa baseline hash. H2 chưa triển khai.

Chạy hai lệnh trong README bằng Python hệ thống. Platform đã kiểm: macOS arm64; runtime trong bundle là CPython 3.13.16 GIL/SQLite 3.53.1. Các platform khác chưa có bundle được nghiệm thu; tool từ chối thay vì tự tải/nâng runtime.

`artifacts/bootstrap-bundle.json` pin archive SHA-256/size và inventory SHA; `artifacts/bootstrap.inventory.json` pin từng file/mode/symlink. Bundle tên `bootstrap-macos-arm64-2026-10-23.tar.gz`. Giữ nguyên file, không tự giải nén bằng lệnh ghi đè lên checkout.

Bootstrap restore create-only vào `.runtime/`, `.tools/`, `.bootstrap/` đã ignore. Nếu file có sẵn khác bytes/mode hoặc parent là symlink, dừng; không xóa/sửa để tiếp tục. Hash sai hoặc graph symlink thoát root/cycle dừng trước khi tạo runtime hoặc venv. Symlink kiểm bằng resolve từng thành phần (mở rộng link trước `..`), có xét links sẵn ở đích; giữ chín runtime aliases trong bundle đã pin. Policy và giới hạn tại [ARTIFACTS](ARTIFACTS.md). Venv/output phải là thư mục mới ngoài checkout; không di chuyển venv.

Ba venv candidate/P1/legacy cài offline từ `packages/s02/requirements-dev.lock` với `--require-hashes`, dùng `.tools/wheelhouse` và `.bootstrap/wheels`. S01 a6 được cài lại từ đúng wheel có hash trong lock để ghi non-editable direct URL; không đổi payload. S02 legacy `0.1.0a3` và P1 `0.2.0a3` chỉ tạo/đọc fixture synthetic. `tools/requirements-tools.lock` vẫn là pin uv duy nhất; binary uv được kiểm bằng member trong wheel uv đã pin lúc tạo bundle.

Build S01/S02 từ bản sao source/pyproject và `tools/build_packages.py` ngoài checkout. So toàn bộ payload/METADATA/WHEEL/RECORD với accepted wheels trước khi cài rebuild cùng version. Collector nhận explicit baseline S01 a6 và S02 a3 từ bundle. Không gọi raw `pip install .` tại workspace và không thêm production source vào PYTHONPATH.

`<ENV>/environment.json` ghi interpreter/helpers cho `tools/verify_checkout.py`. Full verifier dùng adapter hiện hành để chạy S02 E1, hai backend ở process riêng, cùng các old-reader/migration workers; full S01 giữ nguyên suite. Bốn oracle độc lập và CLI supplement giữ nguyên bytes, được chép từ bundle vào runner; không chỉnh assertions. CLI oracle gốc dùng codec executable mặc định; supplement riêng đo factory C/Python trong subprocess. Logs/argv/cwd/exit/JUnit nằm trong output, không ghi reports lịch sử.

Các entry points build/check/collect cũ vẫn có thể dùng bằng interpreter đã bootstrap. Riêng raw S02 `tools/run_checks.py --package s02` không thay runner có E1 adapter/baseline env. `--focused-only` của verifier bỏ full suites và ghi rõ phạm vi.

Đầu ra chuẩn: `<ENV>/package-evidence/manifest.json`, các `*.command.json`/logs của bootstrap, `<CHECKS>/results.json`, JUnit và logs từng backend. Bản acceptance/bundle được ghim hash; đây là kiểm implementation synthetic/local, không xác nhận nghiệp vụ hoặc cấp quyền operational/live.
