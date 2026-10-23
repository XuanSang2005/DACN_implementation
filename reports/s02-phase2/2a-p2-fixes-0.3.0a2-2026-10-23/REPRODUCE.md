# Tái lập vào output mới

Wheel duy nhất để audit: `release/dacn_s02-0.3.0a2-py3-none-any.whl`. Không ghi vào thư mục evidence đã niêm phong. Chọn đường dẫn venv, copy build và report-dir mới; scripts evidence dùng create-only labels/directories. Cwd test thực đều ngoài source; production imports từ installed wheel, chỉ test helpers được thêm sys.path.

1. Tạo venv ngoài checkout từ CPython 3.13.16 bằng `venv --without-pip`; cài locks `packages/s02/requirements-dev.lock` offline bằng `.tools/uv`, `.tools/wheelhouse` và `dist`, `--require-hashes`. Cài wheel non-editable bằng pip `--no-index --no-deps`. `campaign.py` ghi exact argv/cwd/env/exit qua `run_command.py`. Các lanes a1, a2, P1, legacy và verify có venv riêng mới.
2. Tái hiện a1 trước sửa: `before-p2`, `before-review_contract`, `before-persistence_v2`. Các inputs trong thư mục audit a1 giữ nguyên byte; file persistence không-v2 bị loại đúng yêu cầu vì sai harness. `before-p1-review-contract` chứng minh lỗi revoked có từ P1. Expected exit 1 của negative trước sửa được ghi rõ, không gọi là pass.
3. Candidate: chạy `packages/s02/tools/run_p2_checks.py --baseline-python <P1-venv/bin/python> --baseline-helpers <frozen-P1-tests> --legacy-python <phase1-venv/bin/python> --report-dir <mới>`. Đây là full S02 P2 lane; adapter giống a1, không thay test/helper lịch sử. `--audit-only --audit-file <nguyên file>` cho ba file P2 và sáu file P1. Mỗi job có C/Python encoder instrumentation và JUnit.
4. `tools/run_checks.py --package s01 --report-dir <mới>` cho S01. Baseline P1/Đợt 1 dùng copies tests frozen có provenance từ bàn giao trước P2; legacy loại sáu modules chỉ thuộc P1, vẫn chạy đủ 217 case Đợt 1. Không dùng writer E1 để giả baseline legacy-write.
5. `differential_l1.py <c|python> <output.json>` với cùng `canonical-fixtures/l1-root.json` dưới wheel phase1 a3, P1 a3 và a2, so toàn outcomes. Đây là corpus hữu hạn; thêm kiểm explicit owner L1/E1 cho revocation trong regression mới.
6. `build_isolated.py <copy-mới> <output-mới> <label-mới>` dùng Python venv đã có build dependencies từ lock. Copy chỉ source/pyproject/build tool, không lấy build cache/egg-info. So payload/METADATA/WHEEL giữa release và rebuild, không ép ZIP hash bằng nhau.
7. `tools/collect_evidence.py --package all --wheel-dir <release> --baseline-wheel s02=<a1-wheel> --report-dir <mới>`. Venv verify có cả S01 a6 và S02 a2 cài từ đường dẫn wheel explicit để có direct_url.json. Venv chạy tests cài S01 a6 qua lock; payload của cả hai venv được đối chiếu cùng source/wheel. S01 wheel nguyên ZIP lịch sử, không đổi dependencies. `pip check` chạy riêng.

## Kết quả không được che giấu

Một oracle P2 còn fail do checked heads từ chối trước pytest.raises; xem [ORACLE_EXCEPTION](ORACLE_EXCEPTION.md). Không sửa assertions, skip/xfail hoặc monkeypatch production để qua nó. Regression mới lấy pins trước khi cố ý làm hỏng DB và kiểm riêng read/write/rollback.

Các lỗi harness phát triển được giữ: build đầu dùng base runtime thiếu setuptools.build_meta; focused test đầu trỏ vào source tests gây nạp conftest hai lần; collector đầu thiếu direct_url.json của S01 cài bằng uv lock. Lượt thay thế dùng build venv đúng lock, copy nguyên regression ra ngoài cây conftest và verify venv cài explicit S01 wheel. Không tính các lượt lỗi là kết quả release pass. Không thay production vì các lỗi harness này.

Các thao tác đọc, copy inventory và so AST trực tiếp ban đầu không có command transcript riêng cho từng lệnh; before inventory, Git status/diff/HEAD, snapshot bytes và commands kiểm/build/release được lưu. `ARTIFACT_HASHES.json` niêm phong toàn evidence mới. Không mở DB operational, dataset, migration/P3, LLM/renderer/live.

Mixed DB evidence ghim destination path trong manifest. Để tái lập, chạy test tạo fixture tại output mới; không chuyển bản sao DB rồi sửa manifest lịch sử cho nó qua path gate. `baseline-test-inputs.json` đối chiếu hashes test/helper frozen thực dùng.
