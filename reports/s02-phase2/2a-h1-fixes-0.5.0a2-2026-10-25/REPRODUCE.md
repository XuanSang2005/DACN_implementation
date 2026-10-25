# Tái lập bản sửa vào output mới

Chỉ synthetic/local; cwd/state/venv/output ngoài checkout và dataset. Không dùng DB evidence làm operational state. Mỗi NEW phải chưa tồn tại. Evidence gốc bắt đầu 24/10, kết thúc 25/10/2026 ở /Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24.

## Build, cài exact audit wheel

Driver [reproduce_environment.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/reproduce_environment.py) giữ nguyên workflow offline: verify/restore bundle pin, locks require-hashes, ba venv mới, hai copied-source builds, so mọi ZIP entry/METADATA/WHEEL và S01 với accepted a6. Không dùng lane bootstrap accepted-only P3 để so source H1 khác version.

Chạy từ cwd ngoài source:

    python3 -B '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/reproduce_environment.py' --checkout <repo> --bundle <pinned-bundle.tar.gz> --output <outside/env-NEW> --expected-wheel '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final/wheels/dacn_s02-0.5.0a2-py3-none-any.whl'

Driver cài wheel rebuild non-editable và kiểm payload; ZIP timestamp có thể khác. Để kiểm **đúng ZIP bàn giao** sau proof equality, cài cả hai wheels trong final/wheels (S01 payload đã chứng minh bằng accepted):

    <env-NEW>/candidate/bin/python -B -m pip install --no-index --no-deps --force-reinstall '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final/wheels/dacn_s01-0.1.0a6-py3-none-any.whl' '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final/wheels/dacn_s02-0.5.0a2-py3-none-any.whl'
    <env-NEW>/candidate/bin/python -B -m pip check
    <env-NEW>/candidate/bin/python -B <repo>/tools/collect_evidence.py --package all --wheel-dir '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final/wheels' --baseline-wheel s01=<repo>/.bootstrap/wheels/dacn_s01-0.1.0a6-py3-none-any.whl --baseline-wheel s02=<a1-wheel> --report-dir <outside/package-NEW>
    <env-NEW>/candidate/bin/python -B <repo>/tools/verify_checkout.py --environment <env-NEW>/environment.json --output <outside/full-NEW>

Bundle SHA-256 **06222091b5d518e194ba9a5da28f210ae9ed66096eca4ae9ae0def1fa2c87201**, CPython3.13.16 GIL/SQLite3.53.1/macOS arm64. Không resolve online, thay locks hoặc ép hash ZIP rebuild bằng ZIP lịch sử.

## Oracle H1 v3 giữ nguyên

    <candidate-python> -B <repo>/packages/s02/tools/run_p2_checks.py --baseline-python <env-NEW>/p1/bin/python --baseline-helpers <repo>/.bootstrap/p1-helpers --legacy-python <env-NEW>/legacy/bin/python --audit-only --audit-file '/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a1-2026-10-24/test_independent_h1_v3.py' --report-dir <outside/v3-NEW>

Không sửa file/assertions, skip/xfail hoặc monkeypatch production. Hash v3 **9b7d8379a6551e1bc4c868cf46e98b1de47940010346b83ce7a9fccb766e3f9e**. Expected fixed result hiện tại là **9 pass/1 logger fail/backend**, xem [HARNESS_NOTES](HARNESS_NOTES.md); không diễn giải là 10 pass. New full lane chạy thêm 18 regressions trong test_h1_audit_fixes.py, gồm ca ref-limit xuyên suốt đạt cả assertions và controls.

Để tái hiện baseline, tạo venv mới từ cùng locks rồi cài wheel H1 a1 chính xác từ bàn giao cũ bằng --no-index --no-deps; không build source a2 rồi tự gọi là baseline a1. Commands thực của đợt này ở commands/baseline-environment.json, baseline-oracle-v3.json, baseline-ref-integration-{c,python}.json; baseline source đã được copy trước sửa và mọi entry bằng wheel a1.

## Regressions, compatibility, differential

Commands mới gồm argv/cwd/env/exit và logs dưới [commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/commands/). Historical oracle controller dùng sáu P1, P2 gốc và v2/boundaries/P3 a3 nguyên byte; full verifier dùng bốn P3 bundle và CLI controls, full S01/S02 có instrumentation. ADAPTER.json khai báo đúng adapter E1 đã có, không dùng production source trong sys.path.

Nếu full có worker timeout, giữ nguyên failure/JUnit và chạy riêng nguyên case/nguyên timeout vào output mới; không đổi full result dựa vào retry. Xem TEST_RESULTS và HARNESS_NOTES cho kết quả thực.

[Compatibility driver](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/check_h1_version_compatibility.py) tạo a1 finalized/prepared checkpoints trong store synthetic riêng rồi kiểm bằng a2: finalized report nguyên, prepared bị unsupported-version, DB bytes không đổi. Không gọi migration/repair hoặc đổi schema.

Differential dùng nguyên script/corpus lịch sử reports/s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22/differential_l1.py, args backend c|python và output JSON mới, trên legacy0.1.0a3 và fixed0.5.0a2. So toàn outcomes/diagnostics/walk pointers; không so encoder counts hai versions như identity.

Không chạy vào output/evidence cũ, không stage/commit/push hoặc dọn artifacts trong đợt này.
