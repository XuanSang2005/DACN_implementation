# Local LLM — README mốc primitives 0.12.0a1

**Chưa có CLI chạy LLM S01→S02.** Đây là mốc độc lập trước [gate LP-01](S02_LOCAL_LLM_CONTRACT_DELTA_PROPOSAL.md): transport loopback và templates bước 1–4. Capture bền vững, budget journal, authority mới, live writer và CLI analyze/resume chờ audit thiết kế theo yêu cầu người dùng. Không dùng H3-C synthetic authority để nối tạm.

[Bàn giao auditor](../reports/s02-phase2/local-llm-gate-0.12.0a1-2026-11-02/START_HERE.md) chứa wheel/SHA, tests, diff và seal. H3-C `0.11.0a2` vẫn là baseline audit delta; version `0.12.0a1` không có nghĩa LLM integration đã đạt.

## Đã có và cách dùng thực tế

Wheel cung cấp `dacn_s02.local_transport.exchange` và `dacn_s02.local_prompts.render`, không thêm CLI vào `dacn_s02`. Dùng môi trường wheel non-editable theo bàn giao; không thêm production source vào PYTHONPATH.

Ví dụ chạy **probe GET**, không gửi nguồn/prompt hoặc sinh nội dung. Nếu endpoint chưa chạy, mở terminal riêng với binary Ollama đã cài (không dùng lệnh pull):

```sh
OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11434 ollama serve
```

Cấu hình server và API đối chiếu với [Ollama FAQ](https://docs.ollama.com/faq), [chat API](https://docs.ollama.com/api/chat) và [tags API](https://docs.ollama.com/api/tags); khả năng model trên máy được báo riêng bằng preflight bên dưới.

Chọn `PY` là interpreter cài wheel candidate. Môi trường kiểm thực của mốc này:

```sh
PY=/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-local-llm-gate-0.12.0a1-2026-11-02/delivery/candidate/bin/python
"$PY" -B - <<'PYCODE'
from dacn_s02.local_transport import exchange
r = exchange('http://127.0.0.1:11434', method='GET', path='/api/tags', body=b'',
             timeout_seconds=2, response_limit_bytes=1048576)
print(r)
raise SystemExit(0 if r.complete_body and r.status == 200 else 3)
PYCODE
```

Endpoint chỉ nhận literal IPv4 loopback `http://127.0.0.1:PORT`; không hostname, proxy, redirect hoặc retry. POST primitive dùng exact body bytes nhưng **không phải entry được phép gửi LLM từ CLI**: caller vẫn cần durable budget/claim/capture đã audit. Timeout là wall deadline cả headers và body, kể cả trickle. Partial/oversize giữ prefix và complete_body=false. Transport không parse/decompress/normalize response, không chứng minh server không forward cloud.

Templates version `s02-local-prompts/1` nằm trong wheel `prompts/local_v1/`. `render(step, context)` dùng candidate schema H1 đã có, trả messages bytes/hash và hashes từng template; input caller không tự thành trusted source. Chỉ renderer thuần, không xác nhận nội dung LLM. Templates yêu cầu đọc facts sẵn có trước khi hỏi, giữ unknown/holds, explicit/inferred, đủ inventory và không tạo quyền/yêu cầu mới.

## Cấu hình mẫu — đề nghị, chưa có parser CLI

Không chứa secrets. Chỉ dùng sau khi LP-01 được audit và service được implement; không phải lệnh/cấu hình đang chạy được:

```toml
[local_llm]
endpoint = "http://127.0.0.1:11434"
model = "qwen2.5:7b"
model_digest = "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
timeout_seconds = 120
max_calls = 4
max_output_tokens = 4096
context_tokens = 32768
retry = 0
repair = 0
```

Digest trên là model đã đọc tại máy này; máy khác phải preflight model local của mình, không tải để khớp mẫu. Root state/output ngoài checkout và dataset, theo Settings hiện hành. Grant/slots/journal chỉ được tạo qua service đã audit, không suy từ đoạn TOML này.

## Bằng chứng và giới hạn

- Đã thực thi: build offline một wheel; source–wheel–installed bằng nhau; S01 a6 payload giữ nguyên. Preflight Ollama `0.33.2`, GET tags/version, qwen2.5:7b Q4_K_M 7.6B context32768, digest manifest khớp. Layer sizes đã kiểm, chưa hash toàn 4.68 GB model. Daemon tạm cloud-disabled do lượt này mở đã dừng.
- Kiểm cuối: **39/39 C, 39/39 Python**, lần lượt 9.22s/9.64s; 37 ca primitives và 2 H1 integrations. Lượt đầu 37 pass/1 fail do fixture connect-refused; giữ log, sửa fixture dùng injected refusal + thêm timeout control, không đổi production/timeout/assertions để che lỗi.
- Mock: S01 submit thật và H1 handlers thật với bốn responses synthetic, checkpoint/reopen; model/mapping/Issues và messages templates được lưu trong `mock-demo/`. Đây không phải output model local.
- Chưa chạy: inference **0 calls**, không semantic quality result; live adapter orchestration/capture/budget/CLI, journal race/crash và live resume chưa implement. Không full S01/S02/safety/stress; legacy production byte-unchanged, chỉ hai integration smoke cần cho reuse H1.
- Prompt render mẫu 27,126 / 27,621 / 34,004 / 35,108 bytes. Chưa tokenizer/context proof; conservative byte-based bound có thể chặn bước3–4. Phải kiểm tokenizer/template hoặc projection giữ đủ nghĩa trước demo, không truncate để qua gate.

Mốc này dừng sau seal/AUDIT_READY cho **design + primitives**, chờ audit; chưa phải bản runnable bước1–4. Mốc kế tiếp sau gate: journal/authority + CLI thật, fake capture/resume tests, rồi demo synthetic tối đa bốn calls theo limits được duyệt. Không bước5–9, Answer workflow, source switch hoặc migration operational.
