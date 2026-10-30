# Tái lập H3-A — offline, installed wheel, output mới

Evidence root của lượt bắt đầu 29/10/2026: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-0.9.0a1-2026-10-29`. Các đường dẫn là provenance local; dùng bản artifact đã kiểm hash trên máy tái lập, output/venv mới **ngoài checkout**. Không chạy vào thư mục đã seal.

1. Đọc START_HERE/manifest/seal/AUDIT_READY và scope H3-A. Baseline repo audit `b0d6ff2` có valid docs design đang chưa commit; không reset chúng. Baseline wheel S02 là H2-C `0.8.0a1`, SHA `89904528b6978217b3237a560389188805577a625d80e0e5cbe1e2058b5c1a14`; khác version, không ép ZIP/payload 0.9 bằng 0.8.
2. Dùng `reproduce_environment.py` trong evidence (copied unchanged offline driver), `--checkout <checkout> --output <NEW> --expected-wheel <S02 0.8.0a1 wheel>`, tùy chọn `--bundle <pinned bundle>`. Driver kiểm inventory runtime/wheelhouse/baseline bundle; tạo ba venv mới từ locks; CPython3.13.16/GIL/SQLite3.53.1 macOS arm64; hai copied builds; chứng minh toàn20 entries S01 rebuild bằng a6 trước thay same-version wheel; S02 hai rebuilds cùng payload/METADATA/WHEEL. Không online resolve/editable/move venv.
3. Cài **delivery ZIP duy nhất** theo AUDIT_READY/WHEEL trong `delivery/wheels`; các ZIP dưới environment-v*/build/rebuild hoặc provisional `final/wheels` là build/trial artifacts, không release authority. Dùng pip force-reinstall/no-index/no-deps rồi pip check. Collector `--package s02 --wheel-dir <delivery/wheels> --baseline-wheel s02=<0.8.0a1> --report-dir <NEW>` kiểm source→wheel→installed/METADATA/WHEEL/direct URL; giữ baseline version/hash diff riêng.
4. Chạy focused trước bằng candidate Python:

```text
<NEW>/candidate/bin/python -B packages/s02/tools/run_h3_a_checks.py \
  --environment <NEW>/environment.json --scope focused --report-dir <NEW_FOCUSED>
```

Runner từ chối source–installed mismatch trước khi tạo report; dùng original E1 adapter/conftest nguyên byte, bản sao tests có input/output hashes, unset PYTHONPATH/pytest plugin overrides. C rồi Python **tuần tự**, giữ raw commands/logs/JUnit/basetemp/DB/sidecars, không retry/skip/xfail/hạ assertions/nới timeout/caps.

5. Khi focused đạt, `--scope full` cùng runner lấy toàn S02; S01 `tools/run_checks.py --package s01 --report-dir <NEW>`, wrappers/layout/pip check/collector là gates riêng. `release_final.py` trong evidence ghi exact serial commands; điều chỉnh locator/đích mới trên bản copy nếu tái lập, không chạy đè artifacts. Các workers concurrency bên trong tests cũ vẫn được giữ, không biến suite nặng thành nhiều jobs song song.
6. Đọc mọi failure/provisional/aborted metadata. V1/V2 có failures thực; V3/V4 focused là precursor payloads. Full V4 đã aborted khi source thêm bounded origin parsing; không count nó thành full pass của delivery. V5/final results được pin riêng ở START_HERE. Không dùng counts H2-C/S01 lịch sử thay kết quả mới.

H3-A không có filesystem registry loader, Repository factory, CLI/work writer, restart orchestration, new Model+A2 publication hoặc LLM/live. Tests pure không thay safety runtime B/C hoặc semantic/user acceptance. Không sửa historical NEXT_PROMPT draft.1 bị audit ghi mismatch; dùng audit draft.2 và prompt giao H3-A hiện tại.
