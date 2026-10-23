# Kết quả kiểm chứng thực chạy — 2A-P1

Ngày 22/10/2026. **Tự kiểm implementation, chưa audit độc lập/ nghiệm thu P1.** Tests chạy trên dữ liệu synthetic và installed wheels; không live LLM, renderer, semantic benchmark hoặc xác nhận nghiệp vụ.

| Nhóm | C extension | Python fallback | Fail/error/skip |
| --- | ---: | ---: | --- |
| S01 a6 regression | [986 passed](final-checks/s01-c.log) | [986 passed](final-checks/s01-python.log) | 0 / 0 / 0 |
| S02 a3 lane nguyên bản | [217 passed](baseline-checks/s02-c.log) | [217 passed](baseline-checks/s02-python.log) | 0 / 0 / 0 |
| S02 P1 release | [307 passed](release-checks/s02-c.log) | [307 passed](release-checks/s02-python.log) | 0 / 0 / 0 |
| Oracle audit a1 | [7 passed](release-checks/audit-1-c.log) | [7 passed](release-checks/audit-1-python.log) | 0 / 0 / 0 |
| Oracle audit a2 | [4 passed](release-checks/audit-2-c.log) | [4 passed](release-checks/audit-2-python.log) | 0 / 0 / 0 |

S02 release gồm 217 tests legacy nguyên bản + 90 tests P1 mới mỗi backend. Các số S01/a3 trên là lần chạy mới ở đây; không chép từ biên bản lịch sử. Oracle audit 7+4 là regression file lịch sử chạy lại, không phải auditor đã review P1.

Full runner dùng process riêng/backend, cwd tạm ngoài source, instrumentation thật. Counts:

```text
S01 a6 regression / c: Observed real encoder factory calls: {'c': 6597, 'python': 0}; selected=c
S01 a6 regression / python: Observed real encoder factory calls: {'c': 0, 'python': 6597}; selected=python
S02 a3 lane nguyên bản / c: S02_ENCODERS selected=c calls={'c': 88480, 'python': 0}
S02 a3 lane nguyên bản / python: S02_ENCODERS selected=python calls={'c': 0, 'python': 88480}
S02 P1 release / c: S02_ENCODERS selected=c calls={'c': 213902, 'python': 0}
S02 P1 release / python: S02_ENCODERS selected=python calls={'c': 0, 'python': 213902}
Oracle audit a1 / c: S02_ENCODERS selected=c calls={'c': 5632, 'python': 0}
Oracle audit a1 / python: S02_ENCODERS selected=python calls={'c': 0, 'python': 5632}
Oracle audit a2 / c: S02_ENCODERS selected=c calls={'c': 1990, 'python': 0}
Oracle audit a2 / python: S02_ENCODERS selected=python calls={'c': 0, 'python': 1990}
```

Differential L1: **413/413 outcomes giống nhau** ở a3/P1 × C/Python (67 accepted, 346 rejected), cùng diagnostics/walk paths; không unexpected errors. [Machine summary](differential-release-summary.json). Corpus hữu hạn, không phải proof mọi đầu vào.

Release [package evidence](release-package-evidence/manifest.json): S01 16 và S02 20 payload files, source = wheel = installed; recursive resources/METADATA/WHEEL đạt. [pip check](release-pip-check.log): exit 0. [Materializer](materialized-profile-check.log): bytes E1/registry khớp. [5 canonical graphs](release-verify-fixtures.log): đọc và validate lại đạt; review inputs synthetic không phải người dùng xác nhận.

Frozen [test inputs](test-inputs-release.json) và [source inputs](source-inputs-release.json) được kiểm lại sau tests. [Bản sao lane a3](baseline-lane-integrity.json) khớp byte inventory trước sửa, không adapter thay oracle. [Machine results](test-results-release.json) liên kết logs/JUnit.

Các lượt diagnostic trước release có lỗi đã công khai và giữ logs trong [implementation report](IMPLEMENTATION_REPORT.md); không lấy chúng làm kết quả release. Không chạy P2/P3 migration/storage hoặc E1 concurrency/durability; legacy DB1 tests không chứng minh những phần đó.
