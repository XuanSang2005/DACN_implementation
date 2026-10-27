# Tái lập H2-A vào output mới

Cần checkout đúng source trong diff/inventory, bundle macOS arm64 đã pin `06222091b5d518e194ba9a5da28f210ae9ed66096eca4ae9ae0def1fa2c87201`, CPython 3.13.16 GIL/SQLite 3.53.1 từ bundle. Không online resolve, không `pip install -e`, không production source vào PYTHONPATH. Lock giữ nguyên. Driver tự tạo candidate/p1/legacy venv ngoài checkout; restore chỉ các member bundle qua tooling đã audit.

[reproduce_environment.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/reproduce_environment.py) là tooling evidence mới ngoài repo; dùng output chưa tồn tại. `--expected-wheel` ở driver này là **baseline S02 khác phiên bản** dùng collector, không đòi payload 0.6a1 bằng 0.5a2. S01 rebuild chỉ thay wheel pin sau chứng minh mọi entry bằng a6. Hai build S02 cùng version phải bằng mọi entry, gồm METADATA/WHEEL/RECORD.

```sh
python3 -B /path/to/reproduce_environment.py \
  --checkout /path/to/DACN_implementation \
  --bundle /path/to/bootstrap-macos-arm64-2026-10-23.tar.gz \
  --output /outside-checkout/h2-a-env-NEW \
  --expected-wheel /path/to/accepted-h1/dacn_s02-0.5.0a2-py3-none-any.whl
/outside-checkout/h2-a-env-NEW/candidate/bin/python -B \
  /path/to/DACN_implementation/tools/verify_checkout.py \
  --environment /outside-checkout/h2-a-env-NEW/environment.json \
  --output /outside-checkout/h2-a-checks-NEW
```

Nguồn scripts/argv thực của lượt này tại [commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/commands), [final_checks.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final_checks.py), [differential_checks.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/differential_checks.py). Scripts điều phối evidence có paths của máy hiện tại; sao chép/adapt đường dẫn root/output nếu tái lập, không sửa tests/assertions. Full verifier dùng lane adapter E1 nguyên bản, baseline helpers đã pin; mỗi package/backend process riêng. Oracle H1 v4 là corrected harness do auditor phát hành; không chỉnh v3 để cho pass. Oracle lịch sử P1/P2/P3 giữ hash/file/assertions, chỉ adapter tìm helpers của runner hiện hành.

Bản final được copy từ clean build vào thư mục wheel duy nhất, cài lại chính ZIP đó non-editable (direct_url trong collector), pip check và collector lần cuối. Auditor có thể cài wheel này vào venv mới khác thay vì rebuild; S01 vẫn a6 và các dependencies từ lock. Đầu ra mới phải tách mọi thư mục đã có; không chạy các reproduction script trên operational DB hoặc ghi vào evidence cũ.

Differential dùng [script nguyên byte](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/final/differential-l1/differential_l1.py) và canonical-fixtures copy nguyên byte; truyền backend và output mới, cwd ngoài source. So toàn outcomes, không chỉ accepted counts; encoder instrumentation mỗi process. Script inventory/seal [verify_handoff.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-0.6.0a1-2026-10-25/verify_handoff.py) tái kiểm hashes/bảo toàn; chỉnh output nếu cần tạo bằng chứng mới.
