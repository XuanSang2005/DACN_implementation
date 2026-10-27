# Kết quả kiểm mới — H2-A 0.6.0a2 vòng 1

Môi trường mới ngoài source, CPython3.13.16 GIL/SQLite3.53.1, wheel **non-editable**, cwd ngoài source. Locks/offline bundle nguyên byte. Mỗi build/suite/backend chạy tuần tự, không dùng default verifier parallel; các test concurrency/fault vốn có vẫn giữ nguyên workers/assertions. [Commands/cwd/env/exits](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/commands), [JUnit/summary](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/TEST_SUMMARY.json).

## Tái hiện và oracle cuối

Baseline a1 fresh venv: oracle v2 **4 fail +4 pass/backend**, oracle limits **2 fail +2 pass/backend**, tổng **6 fail +6 pass/backend**. Mỗi encoder thật được instrument; [baseline logs/JUnit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/baseline-oracles/checks). Không sửa assertion/helper/skip/xfail.

Final wheel a2: oracle v2 **8 pass/backend**. Oracle limits nguyên bản **2 fail +2 pass/backend**: cả hai negatives đã nhận S02Error đúng rồi lỗi accessor `.value.code`; positive204 và49991 pass. [Final raw logs/JUnit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/h2-oracles/checks). **Không gọi đây là oracle limits pass.** Không sửa oracle hoặc production error API để đáp ứng accessor không có. [Phản chứng và contract](/Users/macbookpro/Documents/DACN_implementation/reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/FINDINGS_RESPONSE.md#s02-2a-h2-a-03).

Replay diagnostic nguyên `example` trên final wheel, C→Python, xác nhận cap190/result204 và cap50000/result50043 đều `error["code"]=H2_LOCAL_LIMIT`, `details.reason=refs`, traceback qua `_aggregate(candidate, issues)`. Controls cap204/result204 và default/result49991 allowed. [Replay C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/limits-replay-c.json), [Python](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/limits-replay-python.json), counts/tracebacks trong logs. Input totals49916/49864 hợp lệ; result check không reset/charge input counter. Đây là diagnostic, không là oracle assertion thay thế. Auditor quyết định erratum/đóng finding03.

## Full suites trên final wheel

| Suite/backend | Pass thực chạy | Fail/error/skip | Gồm H2-A | Factory instrumentation |
| --- | ---: | --- | ---: | --- |
| s02-c | 893 | 0/0/0 | 124 | S02_ENCODERS selected=c calls={'c': 747227, 'python': 0} |
| s02-python | 893 | 0/0/0 | 124 | S02_ENCODERS selected=python calls={'c': 0, 'python': 747215} |
| s01-c | 986 | 0/0/0 | 0 | Observed real encoder factory calls: {'c': 6597, 'python': 0}; selected=c |
| s01-python | 986 | 0/0/0 | 0 | Observed real encoder factory calls: {'c': 0, 'python': 6597}; selected=python |

Full S02 gồm109 tests H2-A cũ nguyên byte và15 cases mới, assertions expected scopes viết tay độc lập. [Full S02](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/full-s02), [Full S01](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/full-s01). Conftest/helpers/E1 adapter giữ nguyên. H1 safety/reopen/concurrency/crash regression pass bảo toàn nền tảng, không chứng minh pipeline H2 chưa viết.

Oracle hồi quy mới/backend: P1 sáu file **[4, 5, 3, 6, 4, 5] = 27 pass**; P2v2/a2/a3 boundaries **[9, 8, 4] = 21 pass**; H1 officialv4 **10 pass**; P3 bốn file + CLI controls **[10, 4, 4, 4, 14] = 36 pass**. Raw files/hashes/argv trong từng thư mục `final/oracle-*`. V1 H2 fixture erratum và P2 old wrong harness không dùng làm gate. Không monkeypatch production để qua tests.

Wrappers **339 tests pass**, layout/schema materializer đạt, pip check0. Differential L1 nguyên script/fixtures trên legacy0.1.0a3/candidate0.6.0a2, C/P tuần tự: **413 outcomes bằng nhau**, 67 accepted; [comparison](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/differential-l1/COMPARISON.json), instrumentation từng process.

## Development failures giữ nguyên

Focused01: oracle v2 pass8/backend; limits negatives phát hiện accessor harness, giữ2fail+2pass. Focused02 pure C có3fail/121pass: một incompat outcome rejected thay guard_required của Part bridge (đã sửa vẫn atomic), hai fixture mới do shallow alias affected/blocking (đã detach). Focused03 pure C có2fail/122pass: expected aggregate204 nhưng fixture đếm trước hai successor refs (202); đã dựng đủ successor trước đo, không đổi expected204. Không chạy tiếp Python sau Cfail ở các lượt ấy, không báo skipped là pass. Focused04 reuse cùng production payload sau khi chỉ sửa fixture mới: **124 pass/backend**; no skip/xfail. Các lỗi phát triển không xoá, không ghi đè logs. Không full suite/build lặp sau mỗi chỉnh nhỏ.

## Đóng gói/bảo toàn và giới hạn

Hai build sạch tuần tự bằng mọi **42 ZIP entries** S02, gồm METADATA/WHEEL/RECORD. S01 rebuild20 entries bằng baseline a6 trước thay wheel pin. [Build comparisons](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final-environment/environment.json). [Source–wheel–installed/direct URL](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/package-evidence/manifest.json) đạt và trỏ đúng final wheel. Payload delta a1→a2 chỉ `__init__` version và hai module H2 policy/graph; h2_limits/error API/H1/L1/schema/registry/DB2/S01/locks/tests cũ nguyên byte. [Preservation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/PRESERVATION.json), [diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/final/change.diff).

Không có timeout failure mới trong final full/oracle hồi quy. Hai assertion harness limits được tách ở trên; không tăng timeout/thay API/skip để đạt. Source snapshot/inventory và seal bao phủ outputs reviewable; venv/cache/DB generated không là authority. `AUDIT_READY` ghi sau seal và không tự nằm trong manifest. Chưa H2-B/C/H3/provider/CLI/writer/LLM/live. **Đã sửa, chờ audit lại; user nghiệm thu cuối.**
