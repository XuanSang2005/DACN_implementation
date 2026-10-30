# Tái lập a2 — output mới, installed wheel, offline

Evidence root của lượt bắt đầu 30/10/2026: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-a-fixes-0.9.0a2-2026-10-30`. Không chạy ghi vào a1/audit hoặc thư mục đã seal. Paths local là provenance; khi tái lập dùng copies đã kiểm hash và locator mới, không overwrite/reseal originals.

1. Đọc START_HERE, FINDINGS_RESPONSE và CONTRACT_DELTA. HEAD b0d6ff2 có working tree H2-C/H3 docs và H3-A a1 hợp lệ, không reset. STATE_BEFORE pin423 files khớp snapshot a1 lúc bắt đầu, HEAD/index/status và before copies. PROTECTED_INPUTS pin a1 marker/manifest/seal cùng hai oracle/replay/report audit a1.
2. `python3 -B reproduce_environment.py --checkout <CHECKOUT> --output <FRESH_ENV> --expected-wheel <a1 authoritative wheel>`: driver offline nguyên byte từ bàn giao a1 kiểm bundle/runtime/wheelhouse/locks; tạo candidate/p1/legacy venv mới ngoài checkout, không editable/online resolve/move venv. Candidate Python3.13.16/GIL/SQLite3.53.1; hai copied builds S02 bằng mọi payload/METADATA/WHEEL; S01 rebuild bằng toàn20 ZIP entries a6 trước thay same-version wheel. A1 baseline SHA `12dfe52698fa24cfc80280a80b1e34afc5a612dab9cac9578243b3306a0744f5`, khác version nên không ép a2 bằng a1.
3. Cài chính delivery ZIP duy nhất được START_HERE/WHEEL/AUDIT_READY pin bằng pip no-index/no-deps/force-reinstall, non-editable; pip check + collector source→wheel→installed/direct URL, giữ baseline a1 diff riêng. Build/trial ZIPs environment-v* là provenance, không release authority.
4. Focused mới trước: candidate Python `-B packages/s02/tools/run_h3_a_checks.py --environment <FRESH_ENV>/environment.json --scope focused --report-dir <NEW_FOCUSED>`. Runner kiểm source–installed trước tạo output, dùng E1 adapter/conftest nguyên byte, giữ copied tests/DBs/basetemp/logs/JUnit. C rồi Python, không jobs nặng song song.
5. Dùng **nguyên** hai oracle và helper trong [REPRODUCE audit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-a-0.9.0a1-2026-10-30/REPRODUCE.md):

```text
python3 -B /Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-a-0.9.0a1-2026-10-30/replay_oracles.py \
  --python <FRESH_ENV>/candidate/bin/python-replay \
  --environment <FRESH_ENV>/environment.json --output <NEW_ORACLE_OUTPUT>
```

Lưu ý launcher: helper nguyên bản gọi `Path.resolve()` trên `--python`. Nếu candidate/bin/python là symlink ra runtime, helper sẽ chạy ngoài venv và báo `No module named pytest` (oracle-v3 không tạo JUnit). Không sửa helper: dùng một bản physical interpreter nguyên byte trong cùng candidate/bin, ví dụ python-replay, kiểm SHA bằng runtime đã pin và xác nhận sys.prefix/package paths vẫn thuộc candidate. ORACLE_LAUNCHER_V5.json ghi exact hashes/argv/prefix; không move venv, đổi locks/site-packages hoặc install online. Dùng locator physical đó cho --python trong command trên.

Helper đọc original `oracle-workspace/tests/test_independent_h3_a.py` và `test_independent_anchor.py`; root copies phải khớp originals. Không sửa fixture/assertions/caps/timeout của auditor. C rồi Python tuần tự; kỳ vọng13 pass/backend sau sửa, chỉ ghi pass theo JUnit mới. 8 fail/5 pass a1 là kết quả lịch sử của auditor, không kết quả mới a2.

Focused final129 đã gồm control transport assessment chain đúng trên existing H2 AS-only guard: `run_transport_control.py` dùng adapter/conftest nguyên byte, fresh copied tests/basetemp, C rồi Python. Lượt focused riêng transport-control1/backend trong environment-v2 giữ như precursor; không thay 13 original oracles và không là H3 writer safety.

6. Chỉ full khi focused129 + oracle13 và catalogue zero-unclassified ổn định: runner `--scope full`; S01 `tools/run_checks.py --package s01`; wrappers/layout/pip check và collector. Một job nặng, C rồi Python; internal race/crash workers giữ. COMMANDS.json/commands/*.json/log giữ exact argv/cwd/exit/time; JUnit từng backend. Không skip/xfail/hạ assertions/nới timeout/caps/retry vào output cũ.
7. Đọc mọi failed attempts; source-test expectation E06 delta được công khai trong response/diff, không sửa sealed a1 tests. Kiểm snapshot/current source inventory/protected inputs/static links/hashes; MANIFEST→SEAL→SEAL_CHECK rồi AUDIT_READY last. Sau marker dừng sửa; verifier chỉ đọc, không tự nghiệm thu.

H3-A pure only. Không mới filesystem loader/Repository factory/CLI/writer/CAS/resume, human decisions/Answer/application/source switch/completed-output repair, dataset/operational/LLM/live. B/C safety §7.1 và audit private contract vẫn là gates riêng trước writer.

Final payload dùng environment-v5 và `delivery-release/wheels`; old `delivery/` thuộc provisional v2 đã dừng khi bổ sung actual-base/Admission.from_pair check. Không dùng ZIP/SHA hoặc partial full count của provisional cho final. `focused_oracles_complete.py` và `release_complete.py` ghi exact final serial commands; không chạy lại scripts vào output đã có.

`reference_field_audit.py` đọc shipped schemas từ candidate installed, quét cả nested ID scalars/arrays/maps/Pairs và ghi REFERENCE_FIELD_AUDIT_FINAL.json. Zero unclassified fields là gate trước full, runtime tests vẫn dùng expected counts viết tay. Final focused129 đã gồm all mixed ref boundaries. `delivery-final/` + env3 và env4 cũng chỉ precursor; partial C675, không full pass. Sole wheel authority: delivery-release/WHEEL.json + AUDIT_READY pins.
