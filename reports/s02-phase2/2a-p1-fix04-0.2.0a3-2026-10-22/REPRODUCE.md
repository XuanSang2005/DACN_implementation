# Tái lập bản sửa finding 04

Dùng output/venv mới, không chạy lại `campaign.py` hoặc `finalize_evidence.py` tại handoff đã niêm phong: các scripts đó tạo evidence cạnh chính file và dùng thư mục tạm riêng của lượt này. Mọi `*.command.json` ghi argv/cwd/environment/exit code thực; logs cùng tên. Chỉ scripts đọc như differential/replay adapter được chạy với output mới.

```sh
DACN_ROOT=/Users/macbookpro/Documents/DACN_implementation
DACN_HANDOFF="$DACN_ROOT/reports/s02-phase2/2a-p1-fix04-0.2.0a3-2026-10-22"
DACN_CHECK=$(mktemp -d /tmp/dacn-fix04-review.XXXXXX)
DACN_PY="$DACN_CHECK/venv/bin/python"
DACN_AUDITS=/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits
DACN_A2="$DACN_AUDITS/s02-2a-p1-0.2.0a2-2026-10-22-214859"
DACN_A1="$DACN_AUDITS/s02-2a-p1-0.2.0a1-2026-10-22-150954"
"$DACN_ROOT/.runtime/python/bin/python3.13" -B -m venv --without-pip "$DACN_CHECK/venv"
"$DACN_ROOT/.tools/uv" pip install --python "$DACN_PY" --no-index \
  --find-links "$DACN_ROOT/.tools/wheelhouse" --find-links "$DACN_ROOT/dist" \
  --require-hashes -r "$DACN_ROOT/packages/s02/requirements-dev.lock"
"$DACN_PY" -B -m pip install --no-index --no-deps --force-reinstall \
  "$DACN_HANDOFF/release/dacn_s02-0.2.0a3-py3-none-any.whl" \
  "$DACN_HANDOFF/release/dacn_s01-0.1.0a6-py3-none-any.whl"
cd "$DACN_CHECK"
unset PYTHONPATH PYTEST_ADDOPTS PYTEST_PLUGINS
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package all --report-dir "$DACN_CHECK/regression"
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package s02 --audit-only \
  --audit-file "$DACN_A2/test_independent_a2.py" \
  --audit-file "$DACN_A2/test_independent_mapping_carry.py" \
  --audit-file "$DACN_A1/test_independent_p1.py" \
  --audit-file "$DACN_A1/test_independent_p1_followup.py" \
  --audit-file "$DACN_A1/test_independent_p1_controls.py" \
  --report-dir "$DACN_CHECK/oracles"
"$DACN_PY" -B "$DACN_ROOT/tools/collect_evidence.py" --package all \
  --wheel-dir "$DACN_HANDOFF/release" \
  --baseline-wheel "s02=$DACN_ROOT/reports/s02-phase2/2a-p1-fixes-0.2.0a2-2026-10-22/release/dacn_s02-0.2.0a2-py3-none-any.whl" \
  --report-dir "$DACN_CHECK/package-evidence"
```

Wheel S01 là bản sao nguyên ZIP a6 từ dist, hash/payload giữ đúng lock. Cài lại bằng đường dẫn cụ thể để collector có direct_url, không thay wheel/dependency đã pin. Môi trường release, baseline a2 và differential legacy a3 của lượt này đều tạo mới từ locks; không dùng venv historical để thay bằng chứng mới.

Phát lại script và graphs gốc, không import test helpers:

```sh
for DACN_BACKEND in c python; do
  for DACN_CASE in carry replacement; do
    "$DACN_PY" -B "$DACN_HANDOFF/instrument_replay.py" "$DACN_BACKEND" \
      "$DACN_A2/replay_counterexample.py" "$DACN_A2/counterexample-$DACN_CASE.json" \
      > "$DACN_CHECK/replay-$DACN_CASE-$DACN_BACKEND.log" 2>&1
    DACN_RC=$?
    printf '%s %s exit=%s\n' "$DACN_CASE" "$DACN_BACKEND" "$DACN_RC"
  done
 done
```

Trên bản sửa, kỳ vọng exit 1 với **S02Error carry_structural_proof** hoặc **replacement_structural_continuation**; exception khác không được tính là reject đúng. Adapter chỉ bật/instrument encoder và chạy nguyên script bằng runpy. Trên a2, hai graph được accepted (exit 0). Positive controls nằm trong hai oracle mới, bao gồm unchanged, human-review mới và hold; script replay không sửa graph để thành control.

Để tái hiện baseline trước sửa, tạo venv riêng từ cùng locks, cài wheel a2 trong handoff a2; chạy nguyên hai file mới và replay. Kỳ vọng 8 pass/2 fail mỗi backend, không error/skip. Các lần tái hiện trước sửa thực tế ở `baseline-audit/` và `baseline-replay-*.log`.

Differential L1: venv riêng cài `reports/s02-phase1/fixes-0.1.0a3/builds/dacn_s02-0.1.0a3-py3-none-any.whl`; chạy `differential_l1.py c <file mới>` và `python <file mới>` bằng từng interpreter legacy a3 và release P1 a3. So toàn `outcomes`, diagnostics và walk paths; corpus cố định đọc từ `canonical-fixtures/l1-root.json`, không chỉnh corpus. Encoder counts có thể khác giữa versions.

Build lại bằng copy sạch của `packages/s02/src/dacn_s02`, `packages/s02/pyproject.toml`, `tools/build_packages.py` giữ relative layout, rồi dùng builder với output mới. `build_isolated.py` minh họa; nếu tái dùng cần điều chỉnh **bản sao script** cho ROOT/OUT mới, không ghi vào handoff. So đầy đủ payload + METADATA/WHEEL, không ép ZIP hash rebuild bằng release. `clean-build-comparison.json` so hai build sạch thực trong lượt này; `package-evidence/manifest.json` kiểm source/wheel/installed.

Không cần dataset, credentials, network hay operational store. Tests tạo DB synthetic riêng. `MANIFEST.json` bao phủ mọi artifact handoff trừ chính manifest; đối chiếu `release-inputs.json` với actual repo trước audit.
