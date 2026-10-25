# Tái lập H1 vào output mới

Chỉ synthetic/test local, macOS arm64. Không dùng operational state hoặc evidence DB làm state chạy. Mọi đường dẫn `NEW` phải chưa tồn tại. Repo không cần source PYTHONPATH; test helpers chỉ dùng ở driver/oracle harness.

Evidence gốc ở `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24`. Script/command hashes trong seal của bàn giao; xem `commands/*.json` cho argv/cwd/môi trường/exit, logs và JUnit không bị rút gọn.

## Môi trường offline và build

`tools/bootstrap.py` giữ lane accepted P3 a3 nguyên byte; không chạy lane so source P3 với checkout H1 khác version. Driver evidence riêng dùng chính verify/restore có path guards của bundle, locks nguyên và copied inputs:

```sh
python3 -B '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/reproduce_environment.py' \
  --checkout /path/to/DACN_implementation \
  --bundle /path/to/bootstrap-macos-arm64-2026-10-23.tar.gz \
  --output /outside/repro-NEW \
  --expected-wheel '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/release/wheels/dacn_s02-0.5.0a1-py3-none-any.whl'
/outside/repro-NEW/candidate/bin/python -B /path/to/DACN_implementation/tools/verify_checkout.py \
  --environment /outside/repro-NEW/environment.json --output /outside/full-NEW
```

Driver restore create-only, kiểm bundle hash `06222091b5d518e194ba9a5da28f210ae9ed66096eca4ae9ae0def1fa2c87201`, runtime 3.13.16 GIL/SQLite3.53.1; tạo ba venv, require-hashes offline, hai clean source builds, S01 equality, H1 payload equality với expected wheel và independent rebuild, non-editable install/pip check/collector. Không resolve online. `reproduction-environment/` là lần thực thi mới của driver tại bàn giao.

## M1 CLI thực tế

```sh
/outside/repro-NEW/candidate/bin/python -B '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/reproduce_m1.py' \
  --checkout /path/to/DACN_implementation --output /outside/m1-c-NEW --backend c
/outside/repro-NEW/candidate/bin/python -B '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/reproduce_m1.py' \
  --checkout /path/to/DACN_implementation --output /outside/m1-python-NEW --backend python
```

Driver tạo S01 bằng Service thật và gọi CLI installed qua test-only factory observer ở mỗi subprocess; không monkeypatch validator/production handlers. Input/mock fixtures đến từ `packages/s02/tests/h1_fixtures.py`; production không import file này. Bốn mock/receipts/Models/mappings/Issues/stdout/backend counts và blocked branch được lưu. Đây là synthetic draft, không dữ liệu nghiên cứu hoặc phân tích nghiệp vụ thật.

## Oracles và differential

Lấy argv gốc trong `commands/oracle-*.json`; thay interpreter bằng `/outside/repro-NEW/candidate/bin/python`, baseline-python bằng lane `p1`, legacy-python bằng lane `legacy`, report-dir thành mới. Giữ nguyên `--audit-file` tới audit gốc, helper bundle và assertions. Lệnh runner:

```text
<candidate-python> -B <repo>/packages/s02/tools/run_p2_checks.py
 --baseline-python <repro-NEW>/p1/bin/python --baseline-helpers <repo>/.bootstrap/p1-helpers
 --legacy-python <repro-NEW>/legacy/bin/python --audit-only
 --audit-file <original-audit-file.py> [--audit-file ...] --report-dir <outside/oracle-NEW>
```

P1 sáu files, P2 gốc ba files và P2 v2+boundaries/P3 a3 boundaries dùng ba output riêng. P2 gốc dự kiến exit1 vì lỗi thứ tự setup đã được auditor xác nhận; không sửa/skip file gốc. Full verifier còn chạy bốn oracle P3 bundle và CLI controls. `checks/commands.json` lưu input audit SHA trước/sau; `ADAPTER.json` ghi mọi setup change của legacy full lane.

Differential dùng nguyên `reports/s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22/differential_l1.py` và corpus lịch sử, chạy baseline legacy `0.1.0a3` và H1 trên cả backend với args `<c|python> <output-NEW.json>`; cwd ngoài source. So toàn `outcomes` gồm diagnostic/walk pointers, không yêu cầu encoder call counts hai versions bằng nhau. Kết quả bàn giao trong bốn `differential-*.json` và `differential-comparison.json`.

Không chạy lại vào output/evidence cũ, không stage/commit/push hoặc dọn artifacts để tái lập.
