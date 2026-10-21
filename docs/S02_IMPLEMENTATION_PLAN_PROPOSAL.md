# Đề xuất kế hoạch implementation S02

**Baseline thiết kế đã audit; Đợt 1 đã bàn giao, chờ audit implementation; chưa nghiệm thu** · Astra · 19/10/2026 · Kế hoạch `s02-plan/0.1.0-draft.3`, ứng với [contract `s02/0.1.0-draft.3`](S02_OUTPUT_CONTRACT_PROPOSAL.md).

Trạng thái hiện hành: [audit thiết kế draft.3 ngày 19/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/AUDIT_REPORT.md) đã đóng F01–F05 ở mức đặc tả và người dùng đã giao Đợt 1. Giữ nguyên version/quy tắc draft.3. [Báo cáo Đợt 1](../reports/s02-phase1/IMPLEMENTATION_REPORT.md) là bàn giao implementation riêng, chưa được audit. Các mô tả “chưa implement/chờ audit” bên dưới là lịch sử bàn giao proposal; không phải kết quả implementation hoặc cho phép các đợt sau.

Khuyến nghị triển khai **Python local, kho SQLite S02 riêng, một orchestrator tuần tự có kiểm tra revision, LLM qua adapter Responses API và renderer PlantUML local**. Code quản lý nguồn/phiên bản/gates; LLM đề xuất phân tích; người dùng trả lời nghiệp vụ và xác nhận đúng gói. Đây là kế hoạch, chưa tạo module, schema thực thi, prompt, DB hay gọi dịch vụ.

## 1. Kế thừa, thay đổi hướng dẫn và giới hạn

Đã đọc nguồn LaTeX cập nhật 18/10, năm tài liệu readiness được giao, biên bản S01_ACCEPTANCE, AGENTS cũ và đề xuất/diff, ba tài liệu S01 và code validation/envelope/repository/revision/service. [Contract S02 mục 1](S02_OUTPUT_CONTRACT_PROPOSAL.md#1-căn-cứ-đã-có-và-phạm-vi-đề-xuất) dẫn đường dẫn căn cứ.

Baseline được kế thừa là package S01 `0.1.0a6`, schema `1.0.0`, output `0.1.0-draft.2`, DB `1`. Biên bản nghiệm thu và audit 18/10 xác nhận kỹ thuật CLI local; không phải đánh giá S02 hay nghiệp vụ. `pyproject.toml` hiện khai báo đúng a6, `jsonschema==4.26.0`, `simplejson==4.2.0`. Kế hoạch dùng runtime đã có trong manifest S01: CPython 3.13.16 GIL, SQLite 3.53.1, macOS arm64. Lượt này đọc code/manifest và hashes, **không chạy lại suites hoặc cài môi trường**.

Ở lượt draft.1, AGENTS đã được đồng bộ theo nguồn: bỏ nhiệm vụ khởi tạo; ghi baseline/acceptance; bổ sung operation–data–rule, căn cứ nhóm/tách/dependency, tình huống, tác động ranh giới ở bước 6, bước 8.1–8.5 và làm rõ theo phạm vi; tách origin với review. Không thay vai trò Astra/audit/user. Schema S02/stack/model/prompt/storage/giới hạn/rubric vẫn cần review. Trạng thái cũ trong S01_LOCAL_GUIDE và proposals được giữ lịch sử; AGENTS dẫn biên bản nghiệm thu hiện hành (xử lý khả năng đọc nhầm trạng thái mà không sửa tài liệu S01 ngoài phạm vi).

Lượt draft.3 chỉ sửa F04 về mapping part nhiều actions: quy tắc closure, ví dụ và kế hoạch kiểm thử liên quan; [báo cáo đáp ứng draft.3](S02_DRAFT3_AUDIT_RESPONSE.md) ghi bằng chứng. Theo [audit draft.2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft2-2026-10-18/AUDIT_REPORT.md), F01/F02/F03/F05 đã đóng ở mức đặc tả, giữ nguyên quyết định. Giữ AGENTS, S01, nguồn LaTeX/PDF, schema, ví dụ S01, báo cáo/audit/dataset; không source/tests/migration/prompt thực thi, dependency files, LLM, renderer hoặc Git. S03 chỉ mô tả gate. Mọi ngưỡng/lệnh/phases dưới đây là **đề xuất chưa chạy**. Các nguồn API/giá/tool ở §2.1/5.2 giữ căn cứ tra cứu của draft.1 ngày18/10, không phải live verification mới.
## 2. Stack khuyến nghị và mức xác minh

| Thành phần | Khuyến nghị | Căn cứ / đánh đổi / còn phải kiểm |
| --- | --- | --- |
| Runtime/package | CPython 3.13.16 GIL hiện có; package `dacn-s02` riêng, namespace `dacn_s02`, phụ thuộc wheel `dacn-s01==0.1.0a6` | Giữ S01 và locks cũ; S02 tạo venv/locks riêng khi được giao. Không nâng dependency chung để tiện SDK |
| JSON và validation | Tái dùng API codec S01; jsonschema 4.26.0, Draft 2020-12, validator S02 riêng | Decimal exact, duplicate keys trước dict; không dùng `ProfileValidator` S01 vốn chỉ hỗ trợ pattern W của schema input. Không Pydantic coercion/default/model dump trên snapshot |
| Lưu trữ | sqlite3 3.53.1 hiện có; kho `s02.sqlite3` riêng, STRICT, explicit transaction | Local dễ audit; không ORM/PostgreSQL cho bản đầu. Không thêm bảng vào DB S01 vì `_verify_structure()` so đúng DDL |
| CLI/config | argparse, tomllib, pathlib, hashlib, uuid, datetime, subprocess | Tái dùng nguyên tắc receipt/path protection; không import hàm private rồi dựa vào chúng như API ổn định |
| HTTP LLM | urllib.request/ssl trong stdlib, Responses REST không streaming, không SDK trong bản đầu | Serialize request exact bytes/parse response raw qua codec; ít deps. Đổi lại phải test timeout/status/headers/usage rõ; SDK sau này chỉ thêm nếu chứng minh không làm mất số và tắt retry ngầm |
| Model ứng viên chính | OpenAI `gpt-6.1-sol`, reasoning `medium`, service tier `default`, tools rỗng, structured `text.format` | Chi phí phù hợp thử nghiệm có nhiều lượt; chưa đo chất lượng DACN. Đối chứng `gpt-6-astra` trên tập phát triển, không tự đổi model giữa một run |
| Diagram | PlantUML **1.2026.9** candidate, Java Temurin **21 LTS**, Graphviz `dot` local; font Noto Sans có tiếng Việt | Tài liệu chính thức công bố PlantUML version và component/alias/interface. Chưa tải/kiểm patch Java, Graphviz, font hoặc tương thích; exact binaries/hash cần chốt và probe tại đợt 4 |
| Test | pytest 9.1.1 hiện có, multiprocessing/subprocess/SQLite tạm, codec hai backend | Tests S02 và regression S01 từ wheel đã cài, ngoài source; không sửa tests S01 để hợp S02 |

Tái dùng callable công khai `parse_json/serialize_json`, `check_envelope`, `Repository.verify/get_run/get_snapshot/get_source` và comparator khi cần đúng semantics S01. Viết adapter nhỏ chống đổi API; không tái dùng taxonomy lỗi/schema S01 cho model. Extension validator S02 nhận Decimal/int finite và phân biệt bool; required/null/enum/ID/cross-record refs kiểm riêng; không gọi regex `\S` mặc định để nới/siết W. Output LLM có fields lạ/duplicate/Unicode không biểu diễn được bị giữ raw và lỗi có kiểm soát, không trim hoặc tự sửa chuỗi.

So sánh: một framework agents/LangChain không cần thiết khi flow chín bước đã xác định; tăng state và retry khó audit. Model local loại bỏ gửi prompt ra dịch vụ nhưng cần phần cứng, chất lượng tiếng Việt/schema và chi phí vận hành chưa đo; giữ adapter để đánh giá riêng nếu yêu cầu không gửi tài liệu ra ngoài. Đề xuất cloud chỉ cho tài liệu/synthetic đã được phép dùng ở đợt LLM, **không đưa dữ liệu lịch hẹn thực lên API**. R5 ràng buộc ứng dụng đích; việc sử dụng tài liệu yêu cầu cho công cụ thiết kế cần chính sách riêng, không tự suy là được phép gửi mọi dữ liệu của dự án. Không có lời gọi mạng LLM trong lượt này.

### 2.1 Tài liệu chính thức đã kiểm và phần chưa xác minh

Ngày đọc 18/10/2026: dùng skill OpenAI Docs cho tra cứu API/model. Trang [models](https://developers.openai.com/api/docs/models) và [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) công bố Responses/structured outputs và reasoning medium; trang [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) là căn cứ đối chứng. Đây là khả năng công bố, không chứng minh tài khoản dự án có quyền truy cập hoặc chất lượng DACN.

[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) hỗ trợ JSON Schema subset. S02 dùng schema projection cho **candidate**, không bắt provider sinh metadata/review. Vẫn kiểm parse/ref/version/semantics phía local và xử lý refusal/incomplete trước lấy output. Không cắt schema S02 chỉ để vừa provider; nếu subset không biểu diễn invariant thì code kiểm thêm. Không để SDK tự parse snapshot numbers qua float. Nguồn snapshot được serialize exact thành chuỗi trong prompt; output model không thay thế snapshot authoritative. Thiếu context capacity thì báo lỗi/tách phạm vi explicit, không cắt đầu prompt âm thầm.

API config đề xuất `store=false`, không conversation/previous_response_id, tools rỗng và truncation disabled; mỗi lần nhận đầy đủ nguồn/phạm vi cần thiết. Đây không phải cam kết zero retention của provider. Model page hiện chỉ liệt kê snapshot ID cùng tên model; lưu requested/returned model, request/response và ngày dùng, không giả vờ có dated snapshot ổn định chưa được công bố. Khả năng model alias thay đổi và API retention phải kiểm lại trước thử thật.

Renderer: [PlantUML download](https://plantuml.com/download) công bố 1.2026.9; [component](https://plantuml.com/component-diagram), [command line](https://plantuml.com/command-line), [Graphviz](https://plantuml.com/graphviz-dot) hỗ trợ đường chuyển local; [security profile](https://plantuml.com/security) có SANDBOX cấm đọc file/URL từ diagram. Đề xuất SANDBOX, không include, và subprocess với stdin/stdout, không shell. Trang [Temurin releases](https://adoptium.net/temurin/releases/?version=21) xác nhận 21 LTS, chưa xác nhận artifact macOS/patch cụ thể. Chưa chạy `java`, `dot` hoặc PlantUML; chưa cam kết SVG ổn định byte-for-byte giữa OS/fonts/tool versions. Chính sách pin/probe là điều kiện trước đợt 4, không phụ thuộc việc cài ngay bây giờ.

## 3. Module và dữ liệu nội bộ dự kiến

Cây này chỉ trong tài liệu, chưa tạo file:

```text
src/dacn_s02/
  s01_adapter.py        # checked lookup + archive nguồn đã chọn
  codec_boundary.py    # dùng codec S01, type/representation failure
  schemas/             # schema S02 và candidate theo contract version
  validation.py        # schema, typed refs, mapping inventory, gates
  repository.py        # kho S02, records/blob/head, checked lookup
  revision.py          # base/impact/reuse/stale logic thuần
  orchestration.py     # work items theo scope, thứ tự bước và giới hạn
  llm.py               # request/response raw, retries, candidate, replay
  clarification.py     # questions/answers, handoff sửa input qua S01
  diagram.py           # view + converter grammar + fidelity
  renderer.py          # local process, timeout, bytes/logs
  review.py            # exact bundle, scope, conditions, handoff
  cli.py               # config/receipt/IO/exit, không duplicate business logic
tests/s02/{unit,contract,integration,e2e}/
evaluation/s02/        # manifest và rubric; dataset external, không copy toàn bộ
```

Không dùng abstraction kho/agents tổng quát. Pure functions nhận candidate + immutable context và trả decision/errors/impact; repository không diễn giải nghiệp vụ. LLM không có công cụ ghi DB/sửa snapshot/chấp nhận model. User commands không sửa JSON history trực tiếp; tạo records mới. Error từ lớp trước khiến bước phụ thuộc not_run, không sinh “reference missing” vì parse chưa có cây. Business issue khác code error: issue có thể nằm trong model hợp lệ về cấu trúc và chỉ chặn scope.

Candidate nội bộ gồm `{base_model_id,base_analysis_set_id,source_context_id,step,scope,proposed_elements,proposed_issues,rationale}` theo schema từng bước. Code cấp ID, gắn output tới attempt, validate rồi tạo model/hồ sơ. ID mới trong một candidate dùng local handles chỉ có nghĩa trong candidate; code chuyển toàn bộ handles sang ID chính thức trong một lượt, phát hiện trùng/missing thay vì vá. Existing IDs chỉ được tham chiếu từ allowlist base. Candidate không được cung cấp Record timestamps/revision/review/handoff; các trường này ngoài schema candidate.

## 4. Kho S02 và transaction/recovery

Kho S02 cấu hình ngoài dataset, tách cả directory với kho S01. Một `s02.sqlite3`, schema version đề xuất `1` cùng application_id riêng; không tự reset/migrate. DDL cuối cùng ở đợt 1 cần audit, mô hình thiết kế:

| Bảng | Cột chính / dữ liệu có thẩm quyền | Ràng buộc |
| --- | --- | --- |
| sessions | session_id PK, S01 spec_id, head_model_id/head_analysis_set_id nullable, sequence integer | Hai head cùng model/session; CAS cặp head. Sequence chỉ ordinal vận hành, không quyết định freshness |
| records | id PK, session_id FK, type, created_at, body_json TEXT | Immutable; body qua codec; unique `(session_id,id)`; metadata cột khớp JSON |
| analysis_sets | record_id PK/FK, model_id, revision, parent_set_id | unique(model,revision); set đầu cùng commit model; successor cùng model +1; selection theo key/type, không timestamp |
| active_reviews | bundle_id PK/FK, review_id FK | CAS review hiện hành của đúng bundle; không đổi analysis head |
| models | record_id PK/FK, session_id, revision, parent_id, source_context_id | unique(session,revision); parent cùng session, +1; model body chứa phần tử đầy đủ |
| links | owner_record_id FK, target_record_id FK, role | Immutable; references materialize từ JSON, không nhập tay; deferred FK chỉ cho records cùng commit; EventRef/StageRef có typed links riêng tới event/staging đã tồn tại hoặc cùng commit, không FK trỏ transaction tương lai |
| artifacts | record_id PK/FK, sha256, bytes BLOB | Hash/length match Artifact; schema/prompts/config/LLM/source/PUML/SVG đều trong DB |
| operations | command_id PK, session_id nullable, parent_command_id nullable, reserved_run_id unique, request_json TEXT | Intent bất biến; reserved_run_id chỉ định danh dự kiến, không FK tới Run chưa có. Outcome derive từ finalized event, không cột mutable nullable |
| operation_events | event_id PK, command_id FK, ordinal, kind, payload_json | Append-only typed payload theo contract §4.3–4.4; unique(command,ordinal); một finalized/command và một application_applied/answer |
| application_heads | answer_id PK/FK, active_command_id FK | CAS claim một application đang chạy/Answer; chuyển sang command tiếp nối tường minh, không thay Answer/events; applied duy nhất chặn dispatch lại |
| staged_blobs | (command_id,blob_id) PK, media_type/purpose/hash/length, bytes BLOB | FK operation đã có; immutable, chưa là Artifact; request/config/prompt/response/input sửa được lưu trước final Run |

Session sequence là ordinal vận hành; model revision là phiên bản model, AnalysisSet.revision là phiên bản tập hồ sơ trong cùng model. Chỉ model/set head pair quyết định freshness; log/review không làm set mới. Active review có CAS riêng. Kiểm cặp base và active review trong transaction khi công bố; không dùng sequence tăng vì log để reject candidate còn đúng context. Command đã biết `command_id` trước commit: receipt local tạo mới/flush trước chạy, lookup theo ID. Đây là thiết kế riêng S02, không sửa receipt S01 hoặc tuyên bố API idempotency. ID UUIDv4 + unique; collision trước publish được thử cấp lại hữu hạn 8 lần, sau publish không đổi ID/ghi đè. IDs logic model giữ qua revisions nhưng refs luôn kèm immutable model record ID.

JSON payload/response/request/body không đưa qua SQLite REAL/JSON numeric extraction; chỉ TEXT ASCII từ codec và bytes BLOB. Dữ liệu nguồn không coerce, missing khác null, true khác 1. Lưu archive envelope S01 một lần theo SourceContext; model chỉ trỏ, không lặp nguồn ở mọi stage. Hash nhận diện bytes; revision phân tích dựa dữ liệu exact/explicit operation, không dùng hash để suy nghiệp vụ. Timestamp UTC chỉ audit; clamp completion khi clock lùi, giữ duration monotonic riêng.

**Transaction tường minh**: sqlite autocommit=True, BEGIN IMMEDIATE/COMMIT/ROLLBACK, foreign_keys ON, journal DELETE, synchronous FULL; đọc lại PRAGMA và kiểm exact DDL. Parse/LLM/render ngoài write lock. Cơ chế chọn để sửa F02 là **staging, không tạo Artifact tham chiếu final Run trước khi Run tồn tại**:

1. T0 ghi operation/request (base model/set, scope, source), reserved_run_id, staged config/prompt/request bytes và prepared event. Receipt create-only biết command_id trước T0. Staging chỉ FK operation; metadata và BLOB kiểm hash/length, không đòi Run. Đối với config/prompt có Artifact cũ, reuse ID thật và producer gốc.
2. T1 ghi dispatch_intent, commit rồi mới send. Từ T1 thiếu response ⇒ dispatch_unknown, không chứng minh provider chưa nhận. Không giữ transaction qua mạng. Không event dispatch thì theo giao thức chưa gửi; resume explicit có thể tiếp tục từ prepared bytes.
3. T2 capture response BLOB và metadata vào staging + response_received cùng transaction; lưu bytes trước parse output. Nếu crash sau T2, lookup command nhìn captured; recovery parse lại bytes, không resend. HTTP invalid/refusal/incomplete vẫn có evidence; headers bỏ secret. Giá trị usage không đọc được giữ null, không mất bytes.
4. T3 đọc cặp head, kiểm expected model/set trước no-op; resolve refs/invariants. Promote các staged blobs dùng cho Run thành Artifact+BLOB, tạo Run/Attempt chính thức cùng transaction, ghi model/Change/AnalysisSet nếu hợp lệ, Validation/Bundle nếu đủ; materialize links, finalized event + promotion map, CAS heads. Cyclic refs Artifact↔Run chỉ deferred tới cuối **T3**. Không tạo head mới khi rejected/stale; vẫn finalize raw artifacts/attempt/outcome. Nếu cần ghi blocking Issue mới, công bố set và outcome cùng T3, không bỏ finding ngoài current set.

BLOB có thể copy bằng thao tác trong DB nhưng staging vẫn bất biến, không rename thành Artifact hoặc đổi producer. Một finalized/command, một promotion/blob/command, reserved_run_id duy nhất; collision lỗi có kiểm soát. Không INSERT OR REPLACE, trigger cấm update/delete history. Mutable chỉ head/operational sequence/active review pointer/application claim; mọi ý nghĩa hoặc kết quả là event/record append-only. Kiểm JSON↔cột/typed links, hash và commit completeness khi lookup.

**Recovery chọn một quy tắc:** show-command chỉ đọc; recovery command mới trỏ parent command gốc, nhưng áp dụng/finalize CAS đúng operation gốc/reserved_run_id, không coi là lần gửi mới. Prepared có thể tiếp tục explicit; captured dùng lại bytes; finalized trả đúng outcome; dispatch_unknown không auto-send. Nếu cần operator quyết định gọi lại provider sau đối soát, ghi command/attempt mới cùng budget lineage, không tự đổi unknown thành transport_failed. Không có transaction chung API/DB; lookup response thiếu không chứng minh chi phí=0. Commit không rõ mở connection mới lookup command/events/outcome; không overwrite completed bằng failed. Busy/IO là persistence error, không MODEL_CONFLICT/ANALYSIS_CONFLICT. Không có backfill FK sang transaction tương lai.

**F01:** Khi model giữ nguyên nhưng Scenario/Characteristic/Issue đổi, ghi successors và AnalysisSet mới rồi CAS head_analysis_set; bundle/validation/review cũ mất khả năng handoff. Lần công bố mới phải lựa chọn đủ records, kiểm refs tới current set; thất bại CAS giữ response stale. Handoff cũ chỉ lịch sử nếu issue đến sau nó; lookup/export lại kiểm cặp head. Bản đầu yêu cầu review gói mới, không carry approval cả khi ảnh hưởng nhỏ. Thêm log/event không đổi model/set, không invalidate. Review mới chỉ CAS active review của bundle hiện hành.

**F03:** Answer raw text bất biến; interpretation_selected/consent_recorded/s01_dispatch_intent/s01_result_observed/application_applied/recovery_observed là typed operation_events theo contract §4.4. Consent pin stage input SHA và S01 request base. Lưu S01 run ID/receipt trước submit; S01 committed mà S02 lỗi thì checked lookup cùng run, không submit lại. Source switch T3 ghi SourceContext archive, model/Change, AnalysisSet, issue successor resolved và application_applied nguyên tử; EventRef↔Change/Issue cùng transaction, không deferred ra sau. Reanalysis có thể pending nên resolved không tự eligible. Lookup application đã applied không tăng revision. User trả lời mới tạo Answer mới; recovery lời cũ không tạo Answer. Base S02 đổi: finalize command cũ stale rồi mở command tiếp nối cùng Answer, CAS application claim sang base mới sau impact review; dùng lại S01 dispatch/observation cũ, không submit nữa khi committed/unknown. Một application_applied/Answer; lời người dùng mới mới có Answer mới. Không cross-DB transaction, không nâng quyền adapter intake thành tự sửa S01.

Artifacts renderer cũng staging bytes rồi promote cùng final Run trong transaction sau render/check, không coi “ghi SVG xong” là commit bundle. Export review package ra directory tạo mới bằng temp/atomic publish + manifest, giữ DB làm nguồn authoritative; thất bại export tra lại command, không render lại tự động. Nếu cần publish nhiều file, chuẩn bị cùng directory rồi rename directory tạo mới đã kiểm, flush; DB và filesystem không atomic chung, receipt/manifest thể hiện trạng thái. Không ghi dataset/code/docs/examples khi chạy. Không prune tự động; quyền local owner, giữ raw input/output cần audit, secrets chỉ env không lưu. Backup/quotas production/mạng/Windows cần việc riêng.

Kho S01 có checked reads mode=rw để SQLite recovery, không phải immutable file open. S02 chỉ gọi API đọc, không init/submit từ ingestion. Khi tests kiểm “không đổi S01”, hash trong trạng thái quiescent/DB sạch; không gọi việc hot-journal recovery là sửa requirements. User-approved requirement update vẫn qua S01 service/CLI hiện có và receipt S01, tách rõ quyền thao tác khỏi adapter đọc.

## 5. Topology LLM, prompts và giới hạn

Một orchestrator, không nhiều agents tự trò chuyện. Gọi theo **đơn vị công việc** với base/source/scope cố định:

| Công việc | LLM đề xuất | Code / người dùng |
| --- | --- | --- |
| 1 | Issues có nguồn; phân biệt thiếu thật với bỏ sót nguồn | Code gom theo source/phạm vi, không gộp bằng text duy nhất; user trả lời. Không answer thì scope blocked |
| 2 | Actors/actions, workflows, read/write/rules | Code ref/type/version; user làm rõ quyền/actor, không tự đưa candidate vào S01 |
| 3 | Components/responsibilities và lý do nhóm/tách/phương án khác | Code liên kết operation/rules/requirements |
| 4 | Mapping từng requirement/criterion/portion/gap | Code inventory độc lập, semantic reviewer đối chiếu nghĩa vụ |
| 5 | Interface/dependency, scenario walkthrough và findings | Code endpoint/capability/model refs; nội dung dependency phải review |
| 6 | Characteristic goals/effects/options/tradeoffs/verification | Code hồ sơ đầy đủ; user quyết định mục tiêu thiếu; không patch model ở đây |
| 7 | Candidate thay đổi từ finding/review được chọn | Code CAS apply và invalidate; chạy lại 4/5/6 theo ảnh hưởng |
| 8 | Không gọi LLM cho converter/render | Code 8.1–8.5; người kiểm readability; lỗi nghĩa về bước tạo |
| 9 | Không dùng LLM thay người chấp nhận | User review chính xác bundle; code gate/scope/conditions |

Lần đầu khuyến nghị tách sáu calls bước 1…6 để dễ truy lỗi. Bước 7 chỉ gọi khi có change proposal được chọn. Có thể batch cùng bước nhiều phần độc lập nhưng mỗi batch có phạm vi và token budget rõ; không tạo parallelism trước có kiểm revision. Ngay cả khi cùng một response chứa nhiều nhóm, code phải validate gate giữa nhóm và không gắn “passed” cho nhóm phụ thuộc lỗi.

Prompts là artifacts bất biến có semantic version + SHA-256 bytes, gồm task instructions, output schema version, source refs/context và scoped model. Chưa viết prompt thực thi ở lượt này. Khi implement: phân tách instruction với requirement text; yêu cầu coi nội dung nguồn là dữ liệu; không cho tools/KB/web trong LLM call. Candidate chỉ reasoning ngắn gắn nguồn/options; không thu thập hidden chain-of-thought. Ghi cấu hình reasoning/model/sampling thực hỗ trợ; không giả định temperature/seed được mọi model hỗ trợ. Pin request bytes và raw response; replay đọc raw output đã archive, không gọi mạng, giữ `mode=replay` và run mới chứ không gán thành measured live.

### 5.1 Retry và vòng sửa đề xuất

| Loại | Giới hạn khuyến nghị | Hành vi và lý do |
| --- | --- | --- |
| Transport | Tối đa 2 retry sau lần đầu, chỉ lỗi connect trước gửi hoặc explicit 429 có Retry-After; tổng timeout mỗi attempt 180 giây | Backoff 1s/4s có jitter ghi log, tôn trọng Retry-After ≤30s; vượt thì dừng. Không retry unknown response sau gửi/5xx chưa rõ outcome; tránh nhân chi phí không kiểm soát |
| Content repair cùng work item | Tối đa 2 lần sửa sau candidate đầu | Lỗi parse/schema/ref hoặc omission có nguồn; gửi error set cụ thể, không hỏi nghiệp vụ thiếu để LLM tự đoán |
| Model restructure 7→5–6 | Tối đa 3 vòng trên một yêu cầu resume/source | Đủ thử một số phương án nhỏ, chặn lặp vô hạn; không phải ngưỡng chất lượng đã đo |
| Tổng calls/resume | 18 request attempts có gửi tới provider, tính cả repair/retry; output cap 12.000 tokens/call, input budget 24.000/call | Trần thử local; không hứa output dài luôn vừa. Incomplete được ghi, không chấp nhận JSON cắt cụt; muốn đổi limit cần config/version mới |
| Chi phí/resume | 5 USD cap, reserve upper bound trước call, không reset qua retry | Theo dự toán bên dưới, còn phải review; unknown usage giữ reservation tối đa, không tự coi chi phí 0 |
| Không tiến triển | Hai candidate liên tiếp cùng lỗi canonical + cùng tập nghĩa vụ/gaps/model content, hoặc lặp model content đã thấy trong 3 vòng | Dừng NO_PROGRESS, giữ unresolved; whitespace/reorder metadata không tính tiến triển. Error giảm nhưng cùng vấn đề ngữ nghĩa vẫn cần reviewer, không chỉ dựa count |

Giới hạn giữ cumulative trong lineage resume, không tự tạo run mới để reset ngân sách khi vẫn cùng yêu cầu. Người dùng có thể mở budget mới tường minh, lịch sử giữ lý do. Không trả lời/hết thời gian chờ không là review. `blocked` là kết quả theo phạm vi; orchestrator tiếp tục work items độc lập, không chạy task có unresolved blocking deps.

### 5.2 Chi phí, model đối chứng và mức chưa biết

[Giá OpenAI chính thức](https://developers.openai.com/api/docs/pricing) khi đọc: Standard short context, USD/1M tokens: Sol input **2**, cached input **0,10**, cache write **2,50**, output **10**; Astra tương ứng **10 / 1 / 12,50 / 50**. Context dài/tier khác có hệ số riêng; bản đề xuất input 24k dưới ngưỡng 272k trên model page. Giá có thể đổi: archive rate card/ngày/tier dùng thực tế trước live run; không hardcode giá như contract nghiệp vụ.

Ví dụ **dự toán, chưa đo**: 6 calls, mỗi call 8k input +4k output ⇒ Sol khoảng 0,336 USD nếu input uncached thường; Astra 1,68 USD. Reserve bảo thủ tính cache-write rate cho toàn input + output cap: 24k×2,5/1M +12k×10/1M =0,18 USD/call Sol; 18 calls ≤3,24 USD trước phí ngoài giả định. Nếu đổi Astra thì reserve 0,90 USD/call, cap5 USD dừng trước đủ18; không tự nâng cap. Billed reasoning/output, retries và usage thật phải theo response/billing; thời gian/chi phí unknown ghi null, không ước tính thành đo.

Khuyến nghị pilot so Sol và Astra trên cùng 6 case phát triển, 2 runs/model/case (24 runs), rubric người review như mục 8. Chọn model chính sau trade-off chất lượng/chi phí; không tự coi quảng bá “near-Astra” là kết quả DACN. Tài khoản, rate limits, effective model revision, schema support cho candidate thực, latency và giá cuối cùng đều chưa xác minh bằng live call. Nếu cloud không được phép, dừng phần LLM thật và review model local riêng; các đợt thuần code vẫn tiến được.

## 6. Cách chạy local và resume dự kiến

CLI **chưa tồn tại/chưa chạy**, ví dụ giao diện để audit:

```text
python -m dacn_s02 --config s02.toml init
python -m dacn_s02 --config s02.toml start --s01-run-id RUN --expect-snapshot SNAP --receipt NEW_PATH
python -m dacn_s02 --config s02.toml advance --session SESSION --base-model MODEL --base-analysis-set SET --steps 1-4 --receipt NEW_PATH
python -m dacn_s02 --config s02.toml answer --issue ISSUE_RECORD --input answer.json --base-model MODEL --base-analysis-set SET --receipt NEW_PATH
python -m dacn_s02 --config s02.toml apply-answer --answer ANSWER --interpretation interpretation.json --base-model MODEL --base-analysis-set SET --receipt NEW_PATH
python -m dacn_s02 --config s02.toml record-consent --application-command COMMAND --input consent.json --receipt NEW_PATH
python -m dacn_s02 --config s02.toml recover --command COMMAND --receipt NEW_PATH
python -m dacn_s02 --config s02.toml switch-source --session SESSION --base-model MODEL --base-analysis-set SET --s01-run-id RUN2 --application-command COMMAND --receipt NEW_PATH
python -m dacn_s02 --config s02.toml diagram --session SESSION --base-model MODEL --base-analysis-set SET --view VIEW --receipt NEW_PATH
python -m dacn_s02 --config s02.toml review --bundle BUNDLE --input decision.json --base-model MODEL --base-analysis-set SET --receipt NEW_PATH
python -m dacn_s02 --config s02.toml show-command --receipt PATH
python -m dacn_s02 --config s02.toml show-record --id RECORD
python -m dacn_s02 --config s02.toml export-bundle --id BUNDLE --directory NEW_DIRECTORY
```

Answer file lưu người trả lời/nội dung; máy local không cung cấp xác thực doanh nghiệp, reviewer identity là actor được operator ghi, không chữ ký số. User phải xem toàn input sửa, diff và request base trước update nghĩa qua S01; record-consent pin đúng interpretation/hash. apply-answer chỉ chuẩn bị proposal/event; chưa có consent thì không submit. Sau consent, application chuẩn bị receipt/run S01, lưu dispatch intent rồi mới submit bằng API S01 đã có. switch-source gắn application-command khi xuất phát từ Answer; chuyển nguồn độc lập không Answer vẫn dùng Change thông thường. Không tự đổi nguồn vì S01 head mới. `advance` tự chọn phần chưa xong trong steps đã xin, không vượt scope/budget; base stale bị từ chối. Diagrams/reviews cũ vẫn xem được nhưng bundle/review hết hiệu lực khi model **hoặc AnalysisSet** đã khác. review input phải có workflow_choices khi muốn thu hẹp nhánh; code dùng closure §9.1, không cho user bỏ prerequisite bằng chọn action tay.

TOML dự kiến gồm state_dir, s01_store_key/path, dataset_roots, busy_timeout_ms=5000, provider/model/reasoning/tier, budget limits, renderer java/jar/dot/fonts paths+hashes. Secret API key chỉ env; không xuất vào config archive/log. Paths explicit, relative config theo config parent; không default ngầm kho máy cá nhân. Config unknown fields/type sai báo lỗi; không ép string→number. Input/artifact export nằm ngoài state và dataset; create-only receipts, không overwrite. Không nhận SVG/PUML tự viết làm output tin cậy chỉ vì user import.

Stdout đúng một JSON result `{command_id,status,record_ids,errors}` (operational adapter, không thay Record contract); log stderr; exit đề xuất 0 completed/lookup, 2 rejected/stale, 3 failed, 4 lookup missing, 5 blocked, 64 usage. Completed command không đồng nghĩa S03 eligible. State bất biến trong DB; recovery tạo command con để đối soát cùng application/finalization gốc, không tạo lần gửi hoặc Answer mới. Resume công việc mới mới có operation/Run mới với base model/set hiện hành; lookup không tạo records. show-command trả committed events/staged refs/outcome và derived state prepared/dispatch_unknown/captured/finalized/interrupted; không trình planned IDs như records tồn tại. Receipt có command_id, resolved S02 store và version, không chứa token/input.

## 7. Converter, renderer và bằng chứng fidelity

8.1 validate toàn model/refs/mapping inventory + AnalysisSet đang head, pin set vào Validation; unknown nghiệp vụ được báo và scope đánh dấu. 8.2 chọn view components/interfaces/dependencies đóng dưới endpoints; inventory phần bị lược. 8.3 converter fixed grammar; alias từ ID, escaped label và thứ tự deterministic; định nghĩa ba nét dependency/required/provided theo contract. 8.4 render local + đối chiếu độc lập + người kiểm readability. 8.5 commit bundle đúng model/set, chưa review trước khi gate đủ.

Ưu tiên Graphviz dot cho component layout thay Smetana thử nghiệm; exact dot version lấy binary khả dụng được review tại đợt 4, không dùng danh sách version cũ trong docs làm bảo đảm bản mới. Pin jar 1.2026.9 candidate/hash, Java21 patch/hash, dot/hash, OS, fonts bytes/hash, locale, dimensions, converter/config version trong toolchain artifact. Không đổi tools giữa cùng phép tái lập; nếu probe thất bại thì ghi quyết định chọn version thay thế để audit, không sửa semantics model.

Chạy subprocess argv không shell, timeout60s, output SVG max10MiB, sandbox, không URLs/includes. Trần này là lỗi công cụ/resource, không input requirement invalid. Label Unicode/control được thể hiện hoặc báo lỗi đúng contract; test injection `@enduml`, quotes/newline/markup/URL. Không chỉ lọc chuỗi đen; generator grammar không cho label tạo token lệnh. SVG đọc như XML không thực thi, cấm external entity/script/external href trước xuất bundle. Escape profile thực phải được probe trên candidate jar trước chốt implementation.

Oracle fidelity: (1) model selection oracle độc lập tính tập cần hiển thị; (2) parse PUML grammar đã generate để lấy typed edges/endpoints; (3) extractor SVG của renderer version lấy node/edge IDs, endpoint/type/direction và text. Nếu SVG không cung cấp đầy đủ semantic markers, bổ sung đối chiếu geometry/arrow marker và golden fixtures đã review; không đánh passed chỉ bằng manifest generator. Quan sát label gốc vs hiển thị có escape kiểm rõ, không dùng ảnh hash duy nhất. Người xem diagram cạnh view inventory kiểm cắt chữ/khả năng đọc. Cùng model/view/config phải PUML byte-identical; SVG byte-identical chỉ yêu cầu cùng toolchain/profile sau khi loại metadata không ngữ nghĩa có quy tắc đã review; mặc định kiểm semantic graph, không hứa cross-platform bit-identical.

## 8. Kiểm thử code và đánh giá ngữ nghĩa — chưa thực thi

### 8.1 Code tests

Fixtures synthetic nhỏ và DB tạm riêng; không ghi dataset. Expected values/sets/state transitions viết độc lập với code dưới test; không tự gọi production resolver/comparator để tạo oracle. Ngưỡng đề xuất: mọi invariant bắt buộc phải đạt, không skipped test bắt buộc; báo từng lỗ hổng còn lại, không dùng số test hoặc coverage thay bằng chứng.

| Nhóm | Dữ liệu/tình huống | Oracle/kết quả mong đợi |
| --- | --- | --- |
| Unit | Duplicate keys, big Decimal, bool/number, missing/null, W29, Unicode unrepresentable trong source/diagnostic | Không đổi giá trị hoặc crash diagnostic; raw preserved; exact error |
| Unit | Typed source/criterion refs, ~0/~1, reorder, same criterion text, IDs xóa/tái xuất hiện | Resolve đúng snapshot/type; ref cũ không retarget |
| Unit | F04: A2→A1 bắt buộc, branch exclusive có choice/unknown, dependency nhiều tầng/SCC, Support theo action dùng chung, global parts chưa accepted | Oracle viết tay tập actions/parts và context: A2 chặn kéo A1 chặn; exclusive đã review có thể tách; unknown choice lỗi; SCC không bỏ prerequisite; không block toàn component; mọi system part vẫn cần review |
| Unit / contract (Đợt 1) | F04 bổ sung: seed P1={A1} phát hiện P12={A1,A2}, rồi P2={A2}; ba biến thể blocker, không blocker và tách P12 trước review | Oracle viết tay: hai biến thể đầu cần actions={A1,A2}, parts={P1,P12,P2}; Q2 chặn A2 ⇒ P1 bị chặn. Không blocker và đủ review ⇒ allowed giữ toàn bộ closure. Model mới tách P12 chỉ xét A1 độc lập sau review mới; kiểm hợp cuối không chứa part thiếu actions/phụ thuộc hoặc blocked qua seed khác. Không chỉ test parts một action |
| Contract | F05: OP02 unknown + actors[A01]; external + actors[A01] nhưng tự suy quyền hủy | Trường hợp đầu SCHEMA_INVARIANT/schema; trường hợp sau có thể qua structure nhưng Q-cancel vẫn chặn, semantic reviewer phải phát hiện |
| Contract | F01: B1 accepted rồi issue mới/characteristic successor cùng M1; log-only | Hai thay đổi đầu ANALYSIS_STALE, allowed rỗng; log giữ set và review. Mọi refs current-set, không carry approval |
| Contract | Toàn records, fields lạ/thiếu/null, invalid endpoints, thiếu mapping row/Part, goal thiếu | Structural reject đúng gate; unknown hợp lệ giữ issue, không tự đáp án |
| Contract | S01 failed/rejected/envelope giả; unchecked snapshot; unchanged run source khác origin | Chỉ checked lookup eligible mới intake; archive cả hai nguồn, snapshot giữ nguyên |
| Contract | Late response, stale model/view/diagram/review, sửa source/S01 spec khác, revoked review | Không apply cũ; bundle mới chưa accepted; false handoff không allowed scope |
| Integration | F02: crash trước dispatch, sau capture, invalid bytes, unknown provider outcome | FK hợp lệ tại từng commit; staging giữ raw, chưa Artifact/Attempt/Run đến T3; invalid vẫn có evidence; recover không resend |
| Integration | F03: Answer pending→consent→S01 committed→S02 fail→lookup cùng run→apply; lost acknowledgement; user answer mới | Text/hash/consent/request immutable; application một lần; run nguồn không nhân đôi; same answer recovery khác new answer; issue resolved không waive reanalysis |
| Integration | F01 race: issue publish vs review/handoff, hai set publishers cùng base, log cạnh tranh publish | IPC kiểm winner/head; stale set không eligible, log không false-conflict, lookup handoff cũ check freshness lại |
| Integration | Restart và lookup source/model/answer/run/artifact; mutate lịch sử, FK/unique/head cùng session | BLOB/TEXT exact, rollback và corruption detection, không tự repair |
| Integration | Hai processes, cùng DB, IPC barrier: proposals cùng base; source switch cạnh tranh response; review cạnh tranh model commit | Một CAS áp, bên kia stale; không overwrite/auto merge. Review lịch sử không trở thành approval mới |
| Integration | Fault trước/sau insert/commit, lock thật, kill đồng bộ trước/sau commit; crash sau request intent | Reopen kiểm records/head atomic; unknown external-call giữ nguyên, không tự gửi lại. Không lấy sleep/tuần tự làm bằng chứng race |
| Integration | Provider stub trả 429/refusal/incomplete/timeout sau gửi, bytes sai, usage thiếu, model khác, retry ngầm | Số attempts/cost reservation đúng; stop theo budget; không parsed candidate khi failed |
| Unit + renderer integration | Missing/extra nodes/edge, đảo hướng/type, wrong alias, label injection/Vietnamese/control, partial view | Oracle độc lập phát hiện fidelity; không “render được là đúng”. Render thực riêng với manifest tools |
| E2E | CLI stdout/stderr/exit, receipt trước effect, restart/export fail, paths alias/dataset roots, package installed ngoài source | Không đổi input/S01history; JSON sạch, lookup recovery, artifact gắn đúng revision |
| Regression | S01 toàn suite hai codec backends + installed/wheel/source | Baseline a6 không thay đổi; instrument backend, báo tests thực tế của đợt đó, không mượn kết quả cũ |

Giữ lịch IPC/lock/commit và DB cuối cho race; fault injection ghi riêng với lỗi lock thật/kill process. Không claim power-loss/disk-full/Windows/network FS nếu chưa chạy. Stub/replay test chỉ xác minh code, không bằng chứng semantic LLM hoặc network API thật. Kiểm bind run/source từ DB được chọn, không coi JSON minh họa hiện tại là persisted validated S01.

### 8.2 Thiết kế tập và rubric ngữ nghĩa

Đề xuất ban đầu **12 đặc tả phát triển + 12 đặc tả giữ riêng cuối**, mỗi đặc tả có các biến thể clarification/reorder/missing source/quality goal, tách theo đặc tả gốc và domain để không leak biến thể. 12 development gồm phòng khám minh họa và synthetic ở ít nhất ba domain; 12 final do audit/người hướng dẫn giữ, không dùng để chỉnh prompt. Không giả định dataset có sẵn: manifest case IDs, nguồn được phép dùng, split trước khi chạy là deliverable đợt 2. Nếu thiếu final set, báo thiếu, không tuyên bố generalization.

Pilot 6 development×2 models×2 runs =24 runs như mục 5.2, sau đó chọn model/prompt. Đánh giá cuối **12 case×3 runs =36 runs** cùng config đã freeze, kể cả failed/refused/blocked; không chọn best-of. Ghi mọi output/cost/time và tỷ lệ code-valid, hoàn thành theo scope, critical omissions, số lượt sửa/câu hỏi. 12 case nhỏ là kiểm chứng khả thi có kiểm soát, không đủ khẳng định phổ quát. Nếu output cuối được dùng chỉnh prompt, công khai contamination và tạo heldout mới trước kết luận độc lập.

Hai người chấm: agent audit/technical reviewer và người hiểu nghiệp vụ (người dùng hoặc người được chỉ định); Astra cung cấp evidence, không tự nghiệm thu. Chấm độc lập trước xem đánh giá của nhau. LLM có thể đề xuất finding nhưng không sole grader. Bất đồng ghi rubric item + nguồn + lý do; đối thoại đối chiếu hoặc người hướng dẫn thứ ba; không lấy trung bình để che lỗi quyền/nguồn nghiêm trọng. Người dùng quyết định facts nghiệp vụ chưa có; reviewer không tự điền.

| Chiều rubric | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Actors/actions/workflows/rules | Sai chủ thể/quyền hoặc nghĩa vụ chính | Có nhiều thiếu/nhánh quan trọng | Đủ chính, còn thiếu nhỏ có ghi | Đủ theo nguồn, ngoại lệ/unknown đúng, không bịa |
| Requirement/criterion coverage | Mất obligation bắt buộc | Có link nhưng không phân nghĩa vụ/gap | Phần lớn nghĩa vụ rõ, thiếu nhỏ có disclosure | Mọi nghĩa vụ đối chiếu được, gap/blocked minh bạch |
| Phân chia/trách nhiệm | Tùy tiện hoặc entity=component không lý do | Lý do chung chung/overlap lớn | Căn cứ operations/rules rõ, tradeoff còn yếu | Phương án hợp lý, trách nhiệm rõ, cân nhắc nhóm/tách và alternatives |
| Dependencies/tình huống | Sai hướng/quyền hoặc quan hệ vô nguồn | Chỉ cùng data/đứng cạnh workflow | Capability/consumer/provider có lý do, scenario còn hở | Phối hợp và nhánh thất bại được đối chiếu, assumptions rõ |
| Architectural characteristics | Bịa SLA/workload/claim runtime achieved | Kể tên quality nhưng không tác động model | Có nguồn/goal/scope/effects, tradeoff thiếu | So giữ/sửa ranh giới, ảnh hưởng chéo/constraints và verification rõ |
| Làm rõ/provenance/revision | Giả xác nhận hoặc reuse sai revision | Hỏi lại nguồn đã có/ảnh hưởng bỏ sót | Câu hỏi đúng, scope phần lớn đúng | Câu hỏi tối thiểu đủ quyết định, reuse/impact có căn cứ và unknown nguyên vẹn |

Ngưỡng **đề xuất cần duyệt trước chạy**: không lỗi critical trong các kết quả được đưa xin acceptance (bịa quyền, fabricated confirmation, retarget source/review, bỏ constraint bắt buộc, claim performance không đo); mỗi chiều ≥2 cho ít nhất 10/12 case, dùng điểm **thấp nhất trong 3 runs**/case để không che bất ổn; mọi case dưới2 có failure analysis. Rubric điểm không tự gate business acceptance; unknown được block đúng có thể đạt rubric nhưng chưa cho phép chuyển scope đó S03. Ngưỡng 10/12 là mốc pilot khả thi, không mức bảo đảm thống kê; audit có thể điều chỉnh trước freeze. Báo phân bố/critical counts và bất đồng, không chỉ mean score. Không dùng khớp tên/số lượng components hoặc một model đáp án duy nhất.

### 8.3 Đối chứng giá trị nâng cấp theo nguồn LaTeX

Nguồn hiện hành yêu cầu so sánh bốn cấu hình: baseline giản lược hai nâng cấp, chỉ thêm thao tác–dữ liệu, chỉ thêm kiểm tra dependency/tình huống, và kết hợp cả hai. Đề xuất giữ cùng requirements/model LLM/budget, step6 characteristics và converter profile; khác nhau đúng hai yếu tố phân tích cần đo. Baseline này phục vụ ablation, không tuyên bố tái hiện toàn bộ hành vi S02 cũ ngày12/10 hoặc đáp ứng contract production hiện tại. Mọi nhánh giản lược gắn nhãn nghiên cứu, không dùng để xuất handoff S03. Không biến experiment flags thành cách bỏ gate trong ứng dụng chính.

Trước heldout, hoàn thiện bốn prompt/config variants chỉ trên development, freeze hashes và rubric. Nếu audit duyệt đối chứng đầy đủ: cùng **12 heldout×3 runs×4 cấu hình =144 runs**, gồm36 full-S02 đã nêu ở8.2 và108 runs giản lược bổ sung; không phải180. Randomize thứ tự cấu hình, lưu assignment; người chấm không thấy tên cấu hình khi chấm nếu khả thi, nhưng không che dữ liệu/gap cần đánh giá. So paired theo case: obligation omissions, dependency/component thiếu căn cứ, thời gian và số sửa người review, mức bất đồng, latency/cost. Giữ cả failures, không chỉ chọn model có diagram đẹp. Ngân sách tổng và công sức chấm144 runs cần user/audit quyết định trước chạy; nếu chỉ thực hiện36 full-S02 thì báo rõ **chưa đánh giá được giá trị nâng cấp bằng đối chứng**. Không kết luận nâng cấp tốt hơn chỉ từ rubric tuyệt đối.

## 9. Các đợt implementation và bàn giao audit

Mỗi đợt chỉ triển khai khi được giao; audit trước mở rộng. Revision/làm rõ có schema và tests từ đợt 1, không thiết kế muộn ở đợt 5.

| Đợt | Phạm vi/dependencies | Deliverables dự kiến | Điều kiện hoàn thành / tests / bằng chứng audit |
| --- | --- | --- | --- |
| 1 Nền tảng + nối S01 | Contract/plan được review; wheel S01 a6 giữ nguyên | Namespace/locks S02 riêng; schemas, typed refs, SourceContext archive; repository model/AnalysisSet heads, staging/promotions/typed events, change/issues, scope closure thuần; CLI init/lookup/receipt tối thiểu | Unit/contract + real SQLite process races/rollback/reopen, fake envelope/unchanged/reorder, source/history hash; F01 current-set/log race, F02 FK tại T0–T3, F03 event identity, F04 fixed-point oracle gồm part nhiều actions được phát hiện giữa vòng lặp và tính đóng của hợp allowed_scope; ba biến thể file08 mới phải có oracle độc lập trước bàn giao Đợt 1. Bàn giao DDL, version manifest, command logs, installed-wheel/source hashes; chưa cần LLM |
| 2 Bước 1–4 | Đợt1; dataset split và quyền dùng dữ liệu/live budget được quyết định | LLM adapter/replay, prompt artifacts versioned; questions/answers bất biến + interpretation/consent/application recovery; actors/workflow/data/rules/components/mapping; source-switch qua S01 receipt | Stub tests khác live pilot; truthfulness/permission/coverage rubric trên development, logs prompt/request/response/cost/failures; chứng minh không tự trả lời, không float hóa; audit cả S01-committed/S02-failed recovery và same-answer apply exactly once trong S02, không tuyên bố exactly-once provider |
| 3 Bước 5–7 | Model/mapping foundation, feedback gates đã có | Interfaces/deps, scenarios, characteristics/options, changes/affected/reused/reevaluate, bounded loops | Scenario dependency có đủ đầu nhưng sai nghĩa, R3/R5 tradeoff, step6 không mutate, step7 invalidate, late responses, concurrent switch, no progress. Audit source→obligation→operation→responsibility chain và phạm vi độc lập |
| 4 Bước 8 | Hồ sơ current-model; pin/probe toolchain được review | View/converter/renderer/fidelity/validation/readability/package export | PlantUML thực chạy local với logs/tool hashes, independent graph oracle, adversarial labels, node/edge direction/type mutation, render timeout, wrong-revision bundle, repeat PUML/SVG. Chưa có user acceptance giả |
| 5 Bước 9 + toàn luồng | Đợt1–4; model/prompt/rubric frozen, heldout được giữ riêng | Review transitions/conditions/revocation/handoff, E2E resume, final evaluation report và hướng dẫn | Wrong bundle/version reject, conditional scope closure, change không tái dùng review, 36 full-S02 final runs và đối chứng144 runs tổng nếu được duyệt theo8.3; human scores/disagreements/costs, mọi lỗi công khai. Audit end-to-end package cùng phiên bản; không triển khai S03 |

Bàn giao từng đợt: phạm vi/version, code diff, source/protected hashes trước–sau, provenance dataset synthetic/development/final, reproduction từ package đã cài ngoài source, exact commands/exit/logs, raw failures và fixture expectations tách khỏi measurement, limitations và quyết định pending. Không xóa tests fail/skip để đạt gate. Phần mới không làm giảm phạm vi nghiệm thu S01 mà không có impact review.

## 10. Đối chiếu chín bước: contract – đợt – đánh giá

| Bước đã chốt | Record/điều khoản contract | Đợt | Bằng chứng code + đánh giá nghĩa |
| --- | --- | --- | --- |
| 1 Làm rõ | SourceContext/Issue/Answer, §3–4,7 | 1–2; resume xuyên suốt | Pin snapshot/answer history/source switch; hỏi đúng thiếu, không suy quyền hủy từ R4 |
| 2 Actors/workflows/operation–data–rule | Model Actor/Action/Workflow/Data/Rule, §5 | 2 | Typed refs/branches/unknowns; review ai làm gì, dữ liệu/quy tắc, không tự quyền |
| 3 Initial components | Component/Responsibility/Trace, §5 | 2 | ID/links; rationale nhóm/tách, không entity1:1 |
| 4 Mapping | Mapping/Part/Scope, §5.1 | 2; cập nhật3 | Inventory tất cả requirements/criteria; reviewer tìm omission lý do/người/thời điểm R2 |
| 5 Trách nhiệm/tương tác | Interface/Dependency/Scenario, §5–6 | 3 | Endpoint/type/hướng; lý do capability và walkthrough |
| 6 Characteristics | Characteristic/Option/Scenario, §6 | 3 | No mutation, source/goal/scope; tác động ranh giới/tradeoffs, không runtime claims |
| 7 Restructure | Change/Reuse/Task + model revision, §7 | 1 foundation,3 behavior | CAS/stale/impact/reuse; phân tích lại4/5/6 đúng scope |
| 8.1–8.5 Validate→view→PUML→SVG→package | Validation/View/Diagram/Artifact/Bundle, §8–9 | 4 | Independent graph oracle/render thật/readability/versions; hình không chứng nhận chất lượng |
| 9 Review | Review/Condition/Handoff, §9 | 1 state foundation,5 complete | Review exact bundle, closure/conditions/revoke; human acceptance và thiếu thông tin giữ blocked |

## 11. Quyết định cần audit và tiêu chí hoàn thành

1. **Contract**: mức chia Part/Scope; AnalysisSet/head và no approval carry khi đổi tập; workflow branch choices + Dependency.Support + Part.action_ids + closure/global policy; exact-version/one-spec-per-session; review theo head với bundle bất biến. Rủi ro chính: closure đủ refs nhưng còn thiếu phụ thuộc ngữ nghĩa, cần người review.
2. **Persistence/local interface**: DB S02 riêng, archive bytes trong DB, command intent/receipt, staging→Artifact/Run trong T3, typed application events/consent/recovery, transaction boundaries, export atomic directory; không cross-DB atomicity. Khuyến nghị không migrate S01. API/production auth chưa nằm trong phạm vi.
3. **LLM**: OpenAI Sol medium làm candidate, Astra pilot đối chứng, stdlib HTTP thay SDK; chốt dữ liệu được phép gửi, account/model availability, budget và response schema trước live. Chưa có số đo chứng minh model nào đủ tốt.
4. **Giới hạn**: retry2/repair2/restructure3/calls18/cap5USD, no-progress rule, input24k/output12k/timeout180s; cần calibrate trên development rồi freeze, không tune từ final set.
5. **Renderer**: jar candidate1.2026.9 + Java21 + dot/font pin; xác minh marker/type/direction/escape/control trên SVG. Nếu oracle không đủ thì chưa xong bước8, không hạ tiêu chí.
6. **Đánh giá**: 12+12 case, pilot24/final36; đối chứng bốn cấu hình cần144 runs tổng cho heldout nếu được duyệt; human rubric và proposed threshold10/12. Domain reviewer, holdout manifest, quyền dùng dữ liệu và ngân sách chấm còn cần quyết định. Không có phương án chia component duy nhất.

S02 chỉ đề nghị nghiệm thu kỹ thuật sau khi các đợt được giao hoàn thành, code invariants/gates có bằng chứng, LLM/renderer thực chạy được phân biệt với stub/replay, mọi gap/unknown được báo, review version/conditional scope được kiểm, semantic evaluation được người review xem xét và giới hạn công khai. Người dùng xác nhận nghiệp vụ/model theo gói riêng; chưa có việc này trong lượt chuẩn bị.

### Kiểm tra artifacts draft.3

Kết quả kiểm tra tĩnh và inventory/hash mới được ghi trong [S02_DRAFT3_AUDIT_RESPONSE.md](S02_DRAFT3_AUDIT_RESPONSE.md). [File08](examples/s02/08-scope-closure.json) thêm ba biến thể tại `/scenarios/7`, `/scenarios/8`, `/scenarios/9` cho Part nhiều actions; giữ nguyên bảy graph và expected outcomes cũ. Bảy JSON còn lại chỉ đổi contract_version để đồng bộ draft.3; F01/F02/F03/F05 không đổi quy tắc/ví dụ. [Báo cáo draft.2](S02_DRAFT2_AUDIT_RESPONSE.md) và bằng chứng cũ giữ nguyên như lịch sử, không cập nhật số liệu của chúng thành kết quả lượt này.

Không tạo S02 code/schema/DDL runtime, scripts/tests, config/dependencies; không chạy suite S01/S02, LLM, renderer hoặc đánh giá dataset. Các bảng §8 là kế hoạch kiểm thử khi được giao implementation, không kết quả đã chạy. Baseline S01 giữ nguyên. **Draft.3 vẫn proposed, đang chờ audit lại; chưa implement S02.**
