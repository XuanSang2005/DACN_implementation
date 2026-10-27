# Tái lập vòng sửa 1 — tuần tự

Checkout source trong [diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/change.diff), wheel duy nhất tại START_HERE. Dùng runtime CPython3.13.16 GIL/SQLite3.53.1 và offline bundle `06222091b5d518e194ba9a5da28f210ae9ed66096eca4ae9ae0def1fa2c87201`, locks nguyên byte. Mọi output/venv mới ngoài source; không production source trên PYTHONPATH, không editable/online resolve. Lượt này không chạy default tools/verify_checkout.py vì nó parallel hai full S02 backends.

[reproduce_environment.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/reproduce_environment.py) restore bundle có guard, tạo ba venv mới từ locks, copy sạch code, build/rebuild **tuần tự**, so tất cả ZIP entries/METADATA/WHEEL, chứng minh S01 rebuild bằng a6 trước khi thay wheel pin. Expected baseline S02 khác version a1 là delta, không ép payload a2 bằng a1.

```sh
python3 -B /path/to/reproduce_environment.py \
  --checkout /path/to/repo \
  --bundle /path/to/bootstrap-macos-arm64-2026-10-23.tar.gz \
  --output /outside-checkout/h2-fix-env-NEW \
  --expected-wheel /path/to/a1/dacn_s02-0.6.0a1-py3-none-any.whl
```

Các argv/cwd/env/exit codes thật tại [commands](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/commands) và [final-environment](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final-environment). [final_checks.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final_checks.py) cài lại chính final ZIP, collector/pip check, hai oracle H2 trước, diagnostic limits replay, rồi full S02 qua run_p2_checks.py (C→Python), S01 qua run_checks.py (C→Python), wrappers/layout/P1/P2/P3/H1 tuần tự. Scripts evidence có paths local, phải copy/adapt root/output **mới** khi tái lập; không chạy vào output cũ. Không sửa production/harness hoặc tăng timeout để đạt.

Oracle/h2_fixtures/conftest giữ nguyên. V1 fixture erratum không dùng làm gate. V2 hành vi là gate; limits nguyên bản giữ cả failed accessor assertion. [replay_limits.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/replay_limits.py) gọi nguyên example/quan sát error API hiện hành và controls, không phải bản oracle thay thế. Xem raw failure và phản chứng trong FINDINGS_RESPONSE trước khi đánh giá.

Baseline a1: [baseline_checks.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/baseline_checks.py), fresh baseline wheel non-editable, 6 failures +6 controls pass/backend. Final full evidence không dùng số baseline. Differential L1 giữ script/fixtures nguyên byte, baseline a3/candidate hai backend chạy tuần tự, so toàn outcomes/diagnostics. Bảo toàn/seal scripts chỉ ghi bằng chứng mới; không sửa STATE/counter auditor.

[verify_handoff.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/verify_handoff.py) đối chiếu snapshot/source/protected inputs. [seal_handoff.py](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/seal_handoff.py) tạo SHA256SUMS + SEAL sau khi docs/logs hoàn tất; marker AUDIT_READY viết cuối cùng và không nằm trong seal để tránh vòng hash. Auditor có thể rehash thuần; user quyết định nghiệm thu/commit, không tự suy transport check thành nghiệm thu code.
