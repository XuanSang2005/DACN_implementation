# Kết quả kiểm thử thực chạy — S02 a3

Ngày 21/10/2026; wheel non-editable trong venv sạch, cwd ngoài checkout, không production PYTHONPATH. Fixtures/smoke là synthetic. Không skipped/xfail hoặc sửa tests audit để đạt.

| Nhóm | C | Python | Exit |
| --- | ---: | ---: | ---: |
| S01 đầy đủ | 986 passed | 986 passed | 0 |
| S02 đầy đủ (189 cũ + 28 mới) | 217 passed | 217 passed | 0 |
| Audit a1 nguyên bản | 7 passed | 7 passed | 0 |
| Audit S02-05 nguyên bản | 4 passed | 4 passed | 0 |

[Summary máy đọc](test-summary.json) và [evidence S02-05](config-pin-evidence.json) giữ số liệu/invariants. Toàn suite không failures/errors/skipped. Các file audit/hash/assertions giữ nguyên; expected refusal của hai ca S02-05 sai nay đạt, không đổi thành positive acceptance.

| Lệnh thực | Logs/JUnit/observations |
| --- | --- |
| [Wrapper S01](s01-runner-invocation.json) | [commands](s01-checks/commands.json), [observations](s01-checks/observations.json) |
| [Wrapper S02](s02-runner-invocation.json) | [commands](s02-checks/commands.json), [observations](s02-checks/observations.json) |
| [Wrapper audit](audit-runner-invocation.json) | [commands](independent-audits/commands.json), [observations](independent-audits/observations.json) |

Instrumentation process chính (worker observations được lưu riêng, không gộp giả vào số này):

- `s01-c`: `Observed real encoder factory calls: {'c': 6597, 'python': 0}; selected=c`.
- `s01-python`: `Observed real encoder factory calls: {'c': 0, 'python': 6597}; selected=python`.
- `s02-c`: `S02_ENCODERS selected=c calls={'c': 88480, 'python': 0}`.
- `s02-python`: `S02_ENCODERS selected=python calls={'c': 0, 'python': 88480}`.
- `audit-1-c`: `S02_ENCODERS selected=c calls={'c': 4837, 'python': 0}`.
- `audit-1-python`: `S02_ENCODERS selected=python calls={'c': 0, 'python': 4837}`.
- `audit-2-c`: `S02_ENCODERS selected=c calls={'c': 1777, 'python': 0}`.
- `audit-2-python`: `S02_ENCODERS selected=python calls={'c': 0, 'python': 1777}`.

S02 chạy lại 5 lịch hai process/backend (10 observations), 4 điểm kill/backend (8), lock SQLite thật, lost-ack và fault injection. Evidence/DB race-kill ở `s02-checks/process-artifacts/`. S01 vẫn chạy toàn bộ lịch concurrency/lock/kill/receipt/export của 986 tests. Không thay bằng mock hoặc tuần tự; không suy thành kiểm mất điện/disk-full.

28 regression mới có 17 rollback, 6 positive-before-dispatch, 2 checked-read fixtures (3 lookups/fixture), 2 dispatched positives và 1 positive request-only bổ sung mỗi backend. Output lưu 34 rollback, 12 positive marker, 12 checked-read marker ở hai backend. Các positive sau dispatch và request-only bổ sung được assert trong tests/JUnit; không giả chúng có marker riêng.

Tooling: **344 unittest tests passed**, gồm 339 wrappers + 5 collector-version tests. [Log](tooling-regression.log), [commands](verification-commands.json). Ma trận selector 336 tổ hợp và 3 nhóm help/workspace kiểm subprocess thật: exit 2, stdout rỗng, không report/output; parser từ chối trước đoạn launch suite. Bình thường: hai wrappers runner ở trên; hai wrappers collector và workspace all tại [packaging commands](packaging-commands.json); workspace s01/s02 và ba negative collector probes tại [probe commands](collector-probe-commands.json). Negative probes giữ exit 2/1 theo kỳ vọng và không công bố manifest. Wheel hỏng trong `collector-fixtures/` chỉ là fixture, **không phải wheel bàn giao**.

Smoke CLI/guards/schema/examples/links và từ chối overwrite: [commands/checks](layout-checks/checks.json), [invocation](smoke-invocation.json), exit 0: **18 commands, 6 guards, 15 JSON examples, 33 record shapes và 95 guide links**. Đây là smoke cấu trúc local, không semantic acceptance.

## Kết quả thất bại giữ nguyên trong lịch sử phát triển

- [Targeted lần đầu](targeted-config.log): **21 passed, 7 failed**, exit 1, fixture Error.stage ngoài enum. Đổi fixture processing → schema, không thay expected/refusal; [targeted sau sửa](targeted-config-corrected.log) **28 passed**, exit 0. JUnit cả hai giữ riêng.
- [Collector S01 lần đầu](s01-collector.log): exit 1 do thiếu direct_url.json khi uv resolve lock. Cài trực tiếp cùng wheel a6, giữ guard; collector/pip check sau đó exit 0.

Phần chưa chạy: LLM, renderer, semantic evaluation, S02 Đợt 2, S03 và power-loss/disk-full. Tests pass hỗ trợ audit kỹ thuật, không tự đóng findings hoặc nghiệm thu.
