# Tái lập diagnostics trong output mới

Target là **wheel A a2 nguyên bản**, không B implementation. Repo baseline đầu lượt HEAD9a1a44e; production/tests/locks phải bằng STATE_BEFORE. Output mới ngoài checkout; không ghi vào audit/hand-off cũ.

1. Dùng driver `reproduce_environment.py` nguyên byte ở handoff a2 để tạo environment mới offline từ locks/bundle, `--checkout <repo> --output <NEW>/environment --expected-wheel <a2 authoritative ZIP>`. Exact bootstrap command và per-command logs/argv được giữ ở evidence root và environment/*.command.json. Không dùng tools/bootstrap.py lane P3 để build a2 như P3.
2. Cài chính ZIP a2 SHA483c9b... non-editable bằng pip `--no-index --no-deps --force-reinstall`, như DIAGNOSTIC_COMMANDS.json. S01 rebuild20 entries bằng a6 trước replace same-version; S02 hai builds53 entries bằng nhau và same-version baseline metadata/payload bằng a2. Direct URL mới pin chính ZIP a2.
3. `prepare_p2_tests.prepare(<NEW>/workspace/packages/s02/tests)` copy current unchanged tests qua E1 adapter; copy package pyproject. Chép `test_h3_b_contract_diagnostics.py` từ evidence root vào tests mới; không sửa original helper/tests/oracles. Conftest chỉ thêm test-helper path, không production src.
4. Chạy candidate Python `-B -m pytest -c <copied pyproject> <copied diagnostics> -s -v --tb=short -p no:cacheprovider --encoder-backend=c --basetemp=<NEW>/c/tmp --junitxml=<NEW>/c/junit.xml`; xong mới Python backend với output riêng. Unset PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS; PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, DACN_P1_PYTHON/DACN_LEGACY_PYTHON/DACN_BASELINE_HELPERS từ environment.json. Commands/exit/time/logs/JUnit/DBs giữ đầy đủ.
5. Expected:3/3/backend để **xác nhận mismatch** a2 và existing H2 control, không B pass. Không chạy full hoặc nhận H2 fixture publications là coverage B. Auditor có thể dùng test script/probe khác để kiểm luận điểm trước khi review proposed delta.

STATIC_CHECKS/FINAL_STATE/DIFF/hash inventories chỉ kết luận phạm vi được pin; không sửa/reseal A a1/a2/design evidence. MANIFEST→SEAL→AUDIT_READY(scope CONTRACT_DELTA_ONLY) của lượt này riêng.
