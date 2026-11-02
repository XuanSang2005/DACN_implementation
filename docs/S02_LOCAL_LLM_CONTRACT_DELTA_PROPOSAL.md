# LP-01 — Local LLM bước 1–4: delta cần audit

`s02-local-llm/0.1.0-draft.1`, 02/11/2026. **PROPOSED / NOT APPROVED.**
Một gate cho capture/provenance, quyền chạy nháp và ngân sách; chưa phải nghiệm
thu implementation. Người dùng đã giao local LLM + CLI riêng, thay giới hạn
“tạm gác LLM” của lượt H3-C. Không dùng quyền đó như xác nhận nghiệp vụ.

Căn cứ: [plan Đợt 2 §7.1/9/11](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md),
[H3-C](S02_2A_H3_C_IMPLEMENTATION.md), [audit a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-c-0.11.0a2-2026-11-02/AUDIT_REPORT.md)
và LaTeX 18/10, phần bước 1–4/làm rõ. H3-C a2 PASS delta, 10 ca/backend do
auditor chạy mới; không full a2, không nghiệm thu LLM. G3/G4 của plan chưa đóng.

## 1. Quyền và phạm vi đề nghị

Lát cắt đầu **fresh E1, toàn nguồn, một snapshot cố định**, tạo qua public S01
Service hoặc checked run lookup + expected snapshot; không nhận JSON tự xưng
validated. S01 giữ nguyên. Bootstrap và bốn bước dùng parser/schema candidate,
Builder và validators thật của H1 qua service/plan **version mới** sau audit;
không gọi H1Service để đóng gói output thật thành synthetic_mock/replay. Sửa
provenance builder chỉ qua tham số tường minh, default H1 và bytes lịch sử giữ.

Không adopt lịch sử A2/B/C vào live lane ban đầu; không sửa/clone completed
outputs, tạo Answer/application/review hoặc source switch. Reopen/resume áp
dụng đúng work mới của lane này. Lịch sử H3-C vẫn do API C và trust cũ đọc.
Đây là giới hạn triển khai đầu, không thay cơ chế partial-scope đã duyệt.

Quyền invoker là **cho phép tính toán bản nháp** trên nguồn pin, không là semantic
authority. Config pin local-execution grant `{version, store_id, campaign_id,
source_context_id, snapshot_id, source_sha256, endpoint, model, model_digest,
steps:[1,2,3,4], limits_sha256, purpose:'draft_analysis'}` do CLI tạo từ thao tác
tường minh, không từ LLM. Không dùng LocalSyntheticContinuationAuthority,
historical reviews hoặc tự cấp review registry để cho model chạy thật.

Đề nghị admission fresh toàn nguồn: chỉ tiến khi kiểm kỹ thuật và inventory
đạt, không có held/unread/unrepresented hoặc business/quality blockers cho bước
đó. LLM usable là đánh giá chưa review, không proof độc lập/đủ nghĩa vụ. Dừng cả
scope nếu ảnh hưởng chưa rõ; không dùng LLM tự chứng minh partial independence.
Tasks kiểm chứng thuộc bước sau không giả làm business blocker. Các gates thật
của handlers giữ nguyên; nếu reuse không biểu diễn được quy tắc này thì fail
closed và báo lại, không bỏ gate. Report luôn `semantic_status=unreviewed_draft`;
`completed_through=4` chỉ là tiến độ đề xuất, không review/handoff S03.

## 2. Capture, ghép request và recovery — thay G3 bằng journal riêng

Đề nghị **journal SQLite riêng mới** dưới state allowroot, có version/store UUID,
permissions local; không thêm table/event/schema vào DB2. Đây là thay đổi so với
G3/G4 đề nghị cũ và phải audit, không lách bằng log/config không kiểm. Journal
lưu BLOB request/response và metadata trong transaction; FK/unique ràng buộc
campaign → work → dispatch. Một work chỉ một dispatch/capture. Reader kiểm
DDL/version/inventory/hashes/bindings; mất/corrupt journal ⇒ stop, không tạo lại.

Work binding bất biến: campaign/store/session/command/attempt, source archive +
snapshot, base Model/AnalysisSet IDs và hashes, step, whole inventory, aliases,
template bytes/version/hash, rendered messages, request bytes/hash, adapter +
package versions, endpoint/model digest/runtime version, options/limits/grant.
Source và base phải checked trước prepare, đối chiếu lại trước dispatch/publish.
Giữ exact HTTP entity bytes, status, allowlisted headers, elapsed, complete_body;
không ghi Authorization/cookie. Không gọi raw bytes là packet/TLS capture.

| Mốc | Quy tắc và crash/reopen |
| --- | --- |
| Prepare | Ghi immutable work + request và reserve call slot; prepare DB2 bằng đúng command/run IDs. Hai DB không có atomic transaction chung: chỉ chuyển bước khi cả pins khớp; thiếu nửa nào reconcile cùng IDs, không dispatch |
| Claim | Atomic journal compare-and-set prepared→claimed, giữ slot; chỉ owner vừa claim được send. Commit DB2 dispatch_intent cùng pins trước HTTP. Claim nhưng thiếu intent khi crash vẫn unknown/không resend, chấp nhận mất liveness |
| HTTP | Một POST, không redirect/proxy/retry/repair/fallback. Timeout kể từ claim giữ dispatch_unknown và slot, không suy no-send từ socket error |
| Capture | BLOB raw + transport metadata commit journal trước parse JSON nào. Crash trước capture ⇒ unknown, không resend; partial/oversize giữ prefix cùng complete_body=false, không gọi exact full response |
| Parse | Exact codec outer envelope → UTF-8 message.content nguyên nội dung, không strip/fences/coerce. Complete HTTP 200, model đúng pin, done=true/done_reason=stop, không tool_calls/thinking/stream/compression; nếu sai thì reject/unknown theo transport, không publish. Thiếu usage giữ null. response_received của DB2 trỏ raw đã stage, metadata derive một lần từ capture; không enrich record cũ |
| Publish | New handler kiểm journal→request→capture→candidate→plan, validators toàn graph và paired CAS hiện hành. T3 promote request/prompt/config/raw/capture manifest để report finalized không cần endpoint. DB2 commit mất ACK: lookup đúng command, journal reconcile; không gọi model lại |
| Resume | Capture hợp lệ cùng binding ⇒ parse/build/seal hoặc trả finalized. Capture khác work, changed source/base/model/template/config ⇒ reject/stale, không auto rebase. Pending cần journal; finalized có thể đọc từ artifacts đã promote và checked DB2, không cần quyền gửi |

Canonical Run `mode=live` khi gọi provider; Attempt có request/response thật.
`execution_origin=provider_local` trong config mới; recorded_replay là mode riêng,
trỏ capture gốc, không dispatch và không tính usage cũ thành mới. Mock chỉ tests.
Không thay canonical enums/DB2/profile/registry. Canonical metadata thiếu thì
null; capture lỗi không tạo Model; blocked chỉ publish nếu batch hợp lệ.

## 3. Provider, caps và token/context — thay G4/G5 cho local pilot

Một Ollama do invoker kiểm soát, cloud disabled (`OLLAMA_NO_CLOUD=1`), literal
`http://127.0.0.1:PORT`; không DNS, proxy, redirect, tools, pull hay model cloud.
Pin installed model digest từ tags/show và local manifest, kiểm trước/sau call;
changed digest ⇒ discard candidate. Đề nghị `qwen2.5:7b` đã có trên máy; không
tải gì. Endpoint local không tự chứng minh daemon không forward cloud: CLI chỉ
nhận daemon khởi chạy do lane kiểm soát với cloud disabled, không attach tùy ý.

Pilot đề nghị: **4 slots/campaign**, tối đa 1 call/step, 120 giây/call, retry=0,
repair=0, num_predict=4096, num_ctx=32768, temperature=0, seed=0, stream=false.
Outer request/response cap 1 MiB mỗi body; canonical caps H1 giữ nguyên. Không
chạy song song calls. Một campaign gắn state root và mọi sessions; start mới,
restart hoặc receipt mới không reset cap. Tăng cap cần thao tác tường minh mới
có evidence, chưa triển khai trong pilot; slot đã claim không bao giờ hoàn lại.
Atomic reservation/call ownership trong journal; session không tự chọn root khác.
Tạo state root mới là pilot mới tường minh, không đường resume lách cap.

Không nhận byte count làm đo token thật. Trước live phải chứng minh conservative
upper bound cho **tokenizer + chat template đã pin** (Qwen byte-level BPE, chỉ hai
messages, overhead từ template), rồi yêu cầu bound_input + num_predict ≤ num_ctx.
Không chứng minh được hoặc vượt context ⇒ blocked trước dispatch; không truncate.
Auditor kiểm bound bằng fixtures token biên/Unicode/template; chưa có tokenizer
proof trong mốc primitives này. Counts thực đọc usage nếu có, unknown vẫn null.
Caps slots/output/context/time là giới hạn local, không có tariff/API trả phí.
Không tuyên bố seed=0 deterministic hoặc timeout chắc chắn dừng compute server.

## 4. CLI và tiêu chí kiểm để mở gate

Sau PASS thiết kế: `local-analyze` nhận config + input S01 hoặc selected S01 run,
receipt; `local-report`, `local-resume` dùng receipt/store binding. Gọi public
S01 API với receipt/reserved identity; crash sau S01 submit chỉ lookup đúng run,
không submit ID mới. JSON stdout, stderr diagnostics. Dùng exit convention H1:
completed/prepared 0, blocked/rejected/stale 2, failed/unknown 3, not_found 4,
not_prepared 5, usage 64. Chưa có lệnh nhận/apply Answer trong lát cắt này.

Focused C trước, Python ở release/codec boundary; giữ tests/oracles cũ:

1. Fake socket: exact bytes, invalid JSON, errors/redirect/proxy, body cap,
   truncated/chunked body, wall timeout kể cả trickle; không resend.
2. Journal crash trước/sau claim, intent, capture, T3; reopen bằng process mới,
   request mismatch, journal missing/corrupt, race hai process với slot cuối:
   tối đa một POST, cap không reset. Canonical attempts khớp capture/promotions.
3. Fresh S01→1–4 fake responses qua handlers thật; missing permission/coverage
   blocked, invalid output giữ raw, no-response unknown; report/resume zero calls.
4. Prompts giữ nguồn/unknowns/inventory; ca thông tin đã có vs thiếu thực, không
   hỏi SLA bước sau. Chấm lỗi nghĩa riêng, không gọi static prompt tests là semantic pass.
5. Model/digest/cloud-disabled/context proof trước demo. Demo synthetic ≤4 calls,
   công bố calls/usage/latency/blocked và lỗi nội dung; không sửa output để đi tiếp.

**Mốc hiện tại:** chỉ transport byte-only + pure prompt templates được code/test
độc lập; không journal, authority, writer live, CLI analyze hay inference demo.
Audit LP-01 trước mọi phần phụ thuộc. Sau gate mới bàn giao candidate tích hợp;
AUDIT_READY mốc này chỉ có nghĩa **design + primitives ready**, không runnable1–4.
