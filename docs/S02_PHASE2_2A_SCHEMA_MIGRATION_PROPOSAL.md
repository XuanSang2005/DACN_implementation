# S02 2A — đề xuất schema profile, compatibility và migration

**Trạng thái: proposed — đã phản hồi S02-2A-01/02, chờ audit lại; chưa được duyệt implementation.**

Phiên bản tài liệu `s02-2a-storage-plan/0.1.0-draft.2`, ngày 22/10/2026. Đây là gói kỹ thuật cần review trước persistence/carry 2A, không phải implementation hoặc migration đã chạy. [Audit plan draft.3/addendum draft.2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft3-2026-10-21/AUDIT_REPORT.md) đóng S02-P2-01, S02-P2-02/A2-R1/R2 **ở mức thiết kế**; G2 giữ kết luận đã rõ. Semantics A1 và DIRECT/CARRY/REPLACEMENT trong [addendum](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md) giữ nguyên. Không suy ra đã nghiệm thu code, schema mới, migration, whole S02 hay cấp quyền live.

Draft.2 chỉ phản hồi [audit storage draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-2a-storage-draft1-2026-10-21/AUDIT_REPORT.md): nguồn chỉ đọc từ lần mở đầu (§6.2), identity receipt/manifest/activation (§5.1, §6.3–6.4) và các ca dự kiến (§7.1). L1/E1 và các lựa chọn version ở §2–3 giữ nguyên. Xem [phản hồi từng finding](S02_PHASE2_2A_DRAFT2_AUDIT_RESPONSE.md); hai finding vẫn chờ auditor xác nhận, không tự đóng.

## 1. Căn cứ thực tế và phạm vi quyết định

| Căn cứ đọc, không thực thi | Hiện trạng và hệ quả |
| --- | --- |
| [storage_schema.py](../packages/s02/src/dacn_s02/storage_schema.py), [repository.py](../packages/s02/src/dacn_s02/repository.py) | application_id `0x44414332`, DB_VERSION=1, STRICT tables, journal DELETE; exact DDL so trên mỗi connection. Records/operations/events chứa JSON TEXT + SHA-256; artifacts/stages có BLOB. Chưa có profile ID |
| [validation.py](../packages/s02/src/dacn_s02/validation.py), [events.py](../packages/s02/src/dacn_s02/events.py) | Một SCHEMA global; shape, walk_schema, fields, typed links và graph checks dùng chung. Không thể chỉ thêm schema thứ hai mà không truyền profile xuyên các bước này |
| [contract.json](../packages/s02/src/dacn_s02/schemas/contract.json) | `$id=urn:dacn:s02:0.1.0-draft.3`; SHA-256 `dd32824ab03c5e4d5faae3eb3888bdea3cacd5ba4735a4a5df19416b024f70b7`. Record `{type,id,created_at,body}` đóng; không có version trong từng record. Export hiện có contract_version=draft.3 |
| Repository._check/_links/_check_heads | Whole-store checked read, SHA/columns/FK/typed-link inventory, snapshot archive, record và operation invariants, paired heads, claims, promotions. Phải giữ mọi lớp kiểm và dispatch theo owner profile |
| [local_io.py](../packages/s02/src/dacn_s02/local_io.py) | Receipt `s02/1` ghim command_id + state_dir. Copy DB sang đường dẫn mới không tự chuyển receipt; read_receipt hiện từ chối state_dir khác |
| [tests repository](../packages/s02/tests/test_repository.py), [schema artifacts](../packages/s02/tests/test_contract_artifacts.py) và [bàn giao a3](../reports/s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md) | Có oracle cho immutable/FK/unknown DB version, rollback/ACK/lock và shape cũ. Chưa có kiểm thử migration hoặc mixed profiles. Không chạy lại suite trong lượt tài liệu |

Giữ Python/runtime/dependencies hiện có, S01 a6 không thay đổi. Không tạo common package, ledger, capture protocol mới, CLI phân tích, LLM hoặc renderer. Lượt này chỉ cập nhật trạng thái phản hồi trong AGENTS/tài liệu này, ví dụ JSON, báo cáo phản hồi và manifest tĩnh mới. Hash nguồn được lấy trước sửa; không tạo schema thực thi hoặc DB. Manifest/báo cáo cũ giữ nguyên.

## 2. Khuyến nghị version và profile

Các tên/giá trị **đề xuất**, chưa phát hành hoặc sửa file version:

| Lớp | Legacy | Đề xuất cho gói 2A có persistence |
| --- | --- | --- |
| Package | dacn-s02 `0.1.0a3` nghiệm thu Đợt 1 | `0.2.0a1`, dự kiến để biểu thị thay đổi storage/reader; chốt khi giao code, không nâng dependencies |
| Contract document / schema semantics | `s02/0.1.0-draft.3` | `s02/0.1.0-draft.4`: bản materialize draft.3 + addendum A1/A2 đã audit, không gồm G3/G4/G5 mới. Tạo file mới sau khi duyệt, không sửa draft.3 |
| Profile ID | `s02-profile/legacy-a3` (L1) | `s02-profile/a1a2-v1` (E1) |
| Schema resource tương lai | Bản schema a3 nguyên byte, hash như §1 | Resource mới `$id=urn:dacn:s02:0.1.0-draft.4`; hash **chưa có**, chỉ tính từ bytes thực sau materialize/review |
| Semantic rules ID | `s02-rules/legacy-a3` | `s02-rules/a1a2-v1`; label gắn code/bằng chứng version, không phải chứng minh thuật toán đúng |
| DB structure | `user_version=1` | `user_version=2`, giữ application_id; exact DDL riêng, không dùng PRAGMA schema_version làm version ứng dụng |
| Model/set/spec revisions | Các số và ID đã lưu | Không tăng khi migration, không đồng nhất với profile/version DB |

**Chọn một profile E1 đủ A1+A2 ở lớp schema/validator/repository**, để không phát hành reader chỉ hiểu một phần amendments. E1 có `observed_source_context_id`, cả hai nullable Issue fields và các status/method đã audit. Vì vậy phạm vi kỹ thuật 2A đề xuất cần cả checker A1 ở mức thấp, dù orchestration consent/S01 update vẫn thuộc 2C và chưa được giao. Đây là **lựa chọn cần duyệt về batch**, không ngầm cấp quyền code hoặc dời toàn 2C vào 2A. Oracle A1 low-level phải chạy trước công bố E1; nếu chưa làm được thì 2A chỉ pure handlers, không tuyên bố E1 persistence hoàn thành.

Phương án khác: profile A2-only rồi profile A1+A2 tại 2C. Giảm checker cần làm ngay, nhưng thêm format/event compatibility matrix và migration/profile edge; dễ tạo kho E1 tự nhận hỗ trợ A1 nhưng không verify được. Không khuyến nghị. Không chọn shape union “thử L1 rồi E1”, suy profile từ field thiếu/null, hay tự điền null vào JSON lịch sử.

Capability là danh sách cố định trong descriptor đã review: L1=`foundation-draft3`; E1=`foundation-draft3`, `observed-s01-context-v1`, `issue-carry-v1`, `issue-replacement-v1`, `typed-history-refs-v1`. Đây là yêu cầu reader phải hiểu, **không phải feature flags để caller tắt validator**. G3 capture/G4 ledger không có trong tập này. Unknown profile, descriptor/hash/rules ID hoặc capability ⇒ từ chối mở kho, không bỏ qua record chưa đọc tới.

## 3. Binding profile và schema cụ thể

### 3.1 Profile nằm ngoài bytes người dùng/lịch sử

DB2 thêm cột `profile_id TEXT NOT NULL` với FK registry vào **records** và **operations**. Không thêm vào `record_json`, `request_json`, `payload_json` hoặc input S01. Events và StagedBlob **kế thừa profile từ operation sở hữu**, không có override theo event. Artifacts là records có profile; BLOB không tự mang profile của nội dung tùy ý. SourceContext.schema_artifact_id vẫn chỉ schema input S01; registry S02 không thay thế nó.

- Migration gán L1 cho mọi record/operation được copy sau khi chúng vượt toàn kiểm a3. Đây là metadata storage mới, không phải backfill field trong lịch sử.
- Mọi record/operation mới sau activation nhận E1 do repository cấp. Caller/LLM không chọn profile. Reuse record cũ giữ L1, không copy thành E1 chỉ để đủ field.
- Legacy operations đã migrated chỉ đọc, kể cả append log; không tiếp tục một command dưới schema khác. Command mới E1 có thể parent tới command L1 finalized/stale nếu protocol claim hiện có cho phép, nhưng không sửa parent hoặc re-dispatch S01 của tổ tiên.
- Trong T3 của command E1, các records **mới** cùng E1; tham chiếu records/StageRef cũ vẫn có thể L1 theo rules. Run/Attempt/config/prompt pins của từng command giữ nguyên; config mới có profile/contract/rules IDs, config cũ không bị thay.
- Record/operation profile thiếu hoặc không được registry cho phép ⇒ corruption. Không suy L1 do field mới vắng; chỉ DB1 đã verified có profile L1 ngầm theo version kho.

### 3.2 Materialize resources và API nội bộ dự kiến

Giữ `schemas/contract.json` hiện hành nguyên byte làm L1 để tests/callers cũ còn đối chiếu được. E1 ở file mới dự kiến `schemas/profiles/a1a2-v1/contract.json`; descriptor registry mới dự kiến `schemas/profiles/registry.json`. Packaging phải include resources đệ quy và đối chiếu wheel→installed, không chỉ glob `schemas/*.json` như hiện tại. Không tạo các file này ở lượt đề xuất.

Materialize E1 từ schema L1 đã pin bằng thay đổi tường minh, không merge patch ở runtime: thêm defs Carry/Replacement/evaluation/obligation checks theo addendum; thêm hai required nullable fields vào Issue; oneOf các nhánh DIRECT/CARRY/REPLACEMENT với status/assessment đúng; thêm required nullable observed_source_context_id vào application event; annotations typed links cho các field mới. Các objects đều đóng, lists/refs theo contract; mọi required/nullability phải có bảng diff schema review được. `$defs.Export` legacy không trở thành export mixed bằng cách đổi const version; 2A không công bố mixed export (xem §5).

Interfaces dự kiến nhận profile qua keyword-only: shape(value, name, profile), walk_schema(value, spec, profile), fields(record, profile), validate_record(..., owner_profile, profile_map), validate_operations(..., operation_profile_map, record_profile_map). Repository lấy maps từ metadata đã verify, không từ candidate. Có thể giữ `SCHEMA` alias L1 và default L1 cho helper shape/fields legacy để không phá tests Đợt 1; **mọi đường repository E1 phải truyền profile tường minh**, instrumentation bắt fallback vào alias. Không thay global SCHEMA theo lần gọi vì sẽ sai khi concurrent hoặc mixed graph. Runtime đọc descriptor trong DB chỉ so với allowlist packaged, không tải module/schema theo đường dẫn trong dữ liệu.

### 3.3 Shape, graph invariants và lịch sử mixed-profile

Shape registry immutable ánh xạ ID → schema bytes + semantic rules đã đóng gói. Resource schema chỉ local refs; không tải `$ref` từ mạng/kho. Các entry trong DB phải khớp bytes/hash/descriptor được reader hỗ trợ, không thực thi schema tùy ý do DB cung cấp.

| Owner E1 | Schema / kiểm theo addendum; không thay semantics |
| --- | --- |
| Issue DIRECT | Có `resolution_carry=null`, `resolution_replacement=null`; status cũ. Nếu resolved bằng Answer: root event chính Issue/model, applied/backlinks/current selection như trước |
| Issue CARRY | Carry non-null, replacement null; assessment applicable ↔ resolved; undetermined/not_applicable ↔ resolution_pending_revalidation. Bảng method structural_check/human_review giữ đúng A2-R1 |
| Issue REPLACEMENT | Carry null, replacement non-null; complete ↔ resolution_replaced; incomplete ↔ resolution_pending_revalidation. Complete/target/coverage/tasks/review/re-hold đúng A2-R2 |
| application_applied | Field observed_source_context_id bắt buộc; null ở existing-source, non-null ở changes_requirements. So snapshot Cmodel/Cobserved sau base CAS. Không nới Change requirements_switch/analysis_edit |
| Các loại khác | Shape chỉ thay annotations/refs/gates cần thiết để dùng Issue mới. Không thêm enum/event capture, Usage hoặc ledger chưa duyệt |

E1 Issue thiếu một trong hai nullable fields là invalid; null không bằng missing. Cả hai non-null là invalid. L1 Issue có bất kỳ field/status mới là invalid. Field `structural_reuse` không hợp E1. Chỉ chọn đúng branch khi shape đã đạt; lỗi shape không chuyển thành undetermined.

Checked read/write thứ tự đề xuất:

1. Kiểm DB identity/version/exact DDL, registry/store metadata; kiểm owner profile, hash/raw columns và FK/inventory trước xử lý graph.
2. Decode qua codec exact, shape theo **profile owner**, không deserialize JSON numeric thành SQL REAL/Python float. Bytes không representable phải lỗi có kiểm soát; không normalize hoặc sửa diagnostic từ dữ liệu nguy hiểm.
3. Walk schema bằng profile owner để tạo/đối chiếu đúng path-role typed links. Không dùng SCHEMA global E1 để walk record L1.
4. Resolve target theo type/session + **profile của target**. Root L1 được validate nguyên gốc L1, successor E1 kiểm thêm lineage/impact/current-target. Cả nguồn/traces/basis refs đều kiểm snapshot và model tương ứng; không nới mọi SourceRef.
5. Graph checker E1 thực thi các ngoại lệ typed-history đúng trường. Các path `/body/resolution_carry/{origin_issue_id,from_issue_id,base_analysis_set_id}` và old sides của source/scope checks kiểm lịch sử; replacement thêm origin/obsolete/from/base và old_ref. `replacement_issue_id` luôn current trong result set/cùng Model. Current issue refs thông thường và các new-side refs vẫn current. Root events không retarget, Check Change.application_event_refs của carry/replacement thuần không thêm app cũ.
6. Kiểm whole-store operation chain, one_applied toàn kho, active claim/review, promotions, revision/index/head pair. Kiểm trước và sau mutation trong transaction. Checked reads không tạo Run, cập nhật hash/timestamps hoặc chọn lại source head.

L1 validator ở reader mới phải đóng băng **rules của a3 đã sửa findings**, không phải phục hồi các lỗi a1/a2. Refactor bỏ globals được phép ở lượt code sau nhưng cần differential tests trên valid/invalid corpus a3. Không gọi nguyên hàm a3 trên cả graph E1 khiến shape cũ veto hợp lệ mới; ngược lại không dùng rules E1 nới root L1. Lookup root/history dùng immutable node + pinned base/result set của operation đó, không bắt history thuộc head hiện tại.

## 4. DB2 đề xuất và commit boundary

Đây là **thiết kế bảng**, chưa tạo DDL thực thi. Bản DDL exact và hashes chỉ chốt cùng implementation được duyệt.

| Thành phần | Cột/ràng buộc đề xuất và mục đích |
| --- | --- |
| records, operations | Thêm profile_id NOT NULL FK schema_profiles; giữ toàn bộ cột/FK/unique hiện có, immutable UPDATE/DELETE. Không default L1 hoặc E1 trong DDL |
| schema_profiles | `profile_id TEXT PRIMARY KEY`, `schema_bytes BLOB`, `schema_sha256 TEXT`, `descriptor_bytes BLOB`, `descriptor_sha256 TEXT`, tất cả NOT NULL; immutable. Descriptor exact JSON gồm profile_id/contract_version/rules_id/required_capabilities/schema_sha256. Hai rows L1/E1 đều phải match packaged registry |
| store_metadata | Singleton `slot=1`, `store_id TEXT UNIQUE NOT NULL`, `write_profile_id TEXT NOT NULL FK schema_profiles`, `origin_kind fresh|migration`, `migration_id TEXT UNIQUE nullable`, `migration_manifest BLOB nullable`, `manifest_sha256 TEXT nullable`; immutable. Fresh: ba migration fields null; migration: đều non-null. Manifest chứa source inventory, profile allocation và công cụ migration; không chứa secret |
| store_activation | Singleton `slot=1 FK store_metadata(slot)`, `activation_id TEXT UNIQUE`, `store_id TEXT`, `profile_id TEXT`, `basis_sha256 TEXT`, `operator TEXT`, `activated_at TEXT`, NOT NULL; immutable. FK store/profile, cross-check với metadata; một row mới cho phép normal writes. basis là manifest hash khi migrated, init descriptor hash khi fresh. Với migration, activation_id phải bằng receipt và manifest; migration_id được lấy qua chính singleton store_metadata, không suy từ ID do caller gửi (chi tiết §6.3) |
| Tất cả bảng cũ còn lại | Giữ meanings/indexes/trigger protections; event profile kế thừa operations. one_applied/one_finalized không partition theo profile. Head/claim vẫn CAS, không reset sequence hoặc selection |

Tất cả bảng mới STRICT; thêm immutable triggers, FK/deferred FK để profile/record/event cyclic references cùng T3 hợp lệ. Hash/descriptor equality và singleton inventory được verify trong repository; SQL constraint không thay graph validator. Không dùng INSERT OR REPLACE. L1 allocation chỉ được migration builder thực hiện; normal writer chỉ E1. Legacy profile column không thể sửa sau commit.

Một DB2 chưa có activation chỉ cho inspect/verify/reconcile/migration-activate; normal prepare/append/finalize/init không tự activation. Mọi write đọc activation và registry lại trong transaction. Fresh init tạo registry/metadata/activation trong một transaction khi path mới/DB rỗng hợp lệ. DB1 hoặc DB2 không đúng dạng không được initialize như DB mới. Đây là cơ chế tránh bản copy dở dang bị dùng nhầm, không phải authorization doanh nghiệp.

Version check trước khi parse payload. a3 kiểm user_version==1 và exact DDL1 nên sẽ từ chối DB2; hạ mỗi PRAGMA về 1 cũng không hợp DDL1. Đây là suy luận từ code, **chưa chạy old-reader test**. DB2 không downgrade tự động; reader mới từ chối DB3/unknown capability thay vì cố đọc phần biết.

## 5. Compatibility, lookup, export và receipts

| Reader / kho | Hành vi đề xuất |
| --- | --- |
| a3 / DB1 | Baseline không đổi; không patch a3 |
| a3 / DB2 | Từ chối trước payload; không reset, không migrate |
| Reader mới / DB1 hợp lệ | Checked read L1 qua connection mode=ro; initialize/write trả migration_required. Không mở rw chỉ để đặt pragmas rồi gọi đó là read-only |
| Reader mới / DB2 L1+E1 đủ profiles | Decode từng owner, checked whole store; normal write chỉ sau activation và chỉ E1 |
| Reader mới / DB2 shape giống legacy nhưng gắn E1 thiếu fields | Từ chối; không fallback L1 |
| Reader mới / DB2 unknown profile, rules, hash, DDL hoặc thiếu activation | Unknown/corrupt từ chối toàn kho; riêng kho verified chưa activated được inspect nhưng không write |
| Lịch sử invalid / missing evidence | Từ chối migration/checked read; không repair, bỏ row hoặc backfill approval |

**Lookup:** API nội bộ mới cần trả hoặc mang kèm authoritative profile metadata; không suy từ bare dict. Giữ raw-record lookup để audit bytes, thêm wrapper metadata `{profile_id, record}` cho interface mới và operation tương tự. Event/stage wrapper ghi profile kế thừa command. Metadata này không được ghi vào JSON gốc. Legacy methods trong implementation cần được rà mọi call site, không chỉ đổi signature shape().

**Export:** không dán contract_version=draft.3 lên gói mixed. Đề xuất export mới riêng `s02-export/2`: store_id, supported profile descriptors/hash, records kèm profile IDs, operations kèm profile IDs, events/stages cùng owning command và blob manifest. Chỉ export khi checked; lookup/export không trở thành trusted import endpoint. **Khuyến nghị 2A chưa implement export v2**: từ chối export mixed qua interface cũ, vẫn cho lookup riêng; không silently strip fields. Export legacy lịch sử có thể trả raw bytes nguyên dạng nhưng phải ghi rõ không phải gói current toàn store.

**Receipt/path:** giữ receipt `s02/1` nguyên bytes. Source/destination state_dir khác nhau, nên receipt cũ vẫn chỉ source cũ. Không sửa read_receipt để bỏ binding, không symlink/rename đè thư mục cũ để giả cùng store. Đề xuất receipt mới `s02/2` cho command mới ghim command_id/state_dir/store_id; receipt migration riêng `s02-migration/1` theo §5.1. S01 receipts/store không thay đổi.

Đối soát lệnh cũ ở destination phải là thao tác explicit `lookup-migrated` dự kiến: nhận **cả** receipt cũ và migration receipt, kiểm source path, command thuộc inventory copy, destination store_id/migration_id/activation_id/root hash đúng theo §6.3; rồi checked lookup đúng command ID. Không chuyển lookup thành submit, không phát receipt command ID mới, không tự sửa config. Tên CLI/API là đề xuất chưa tồn tại; cần test adapter trước phát hành công cụ migration.

### 5.1 Receipt migration: identity bền vững trước effects (S02-2A-02)

`s02-migration/1` là object đóng, mọi field dưới đây **bắt buộc và không null**; kiểm duplicate JSON keys và codec exact như dữ liệu khác. Chưa có file receipt thực hoặc schema thực thi trong lượt này.

| Field | Kiểu / quy tắc | Có trước copy |
| --- | --- | --- |
| receipt_version | String const `s02-migration/1` | Có |
| migration_id, target_store_id, activation_id | Ba string UUIDv4 dạng canonical lowercase, cấp một lần; không chấp nhận missing/null/blank/sai dạng, không tự sửa ID | Có, lưu cả ba trong receipt |
| source_state_dir, destination_state_dir | Absolute path string đã resolve/check guards; hai nơi khác nhau, không alias nhau hoặc vùng cấm | Có |
| plan_version | String const `s02-2a-storage-plan/0.1.0-draft.2` cho quy trình này; không ngầm nâng receipt draft.1 | Có |
| source_inventory_sha256 | String 64 hex lowercase, root inventory L1 đã verify trong read transaction nguồn; dùng lại khi resume để phát hiện nguồn đổi kể cả copy chưa bắt đầu | Có; đây **không phải hash manifest** |

Root nguồn đã biết được pin thêm trong receipt để crash sau receipt không làm mất mốc so sánh nguồn. Không ghi hash manifest, copy counts hoặc thời điểm activation vào receipt trước effects: các giá trị ấy chỉ biết ở các bước sau. Receipt bất biến, không append hash manifest vào nó sau copy. Format này chưa từng phát hành; receipt draft.1 thiếu activation_id không được coi là receipt đầy đủ hoặc tự backfill.

Ghi receipt theo create-only: serialize exact bytes, ghi file tạm cùng filesystem, flush/fsync file, publish vào tên receipt bằng primitive không overwrite rồi fsync thư mục; xác nhận bytes/shape/path/IDs đọc lại **trước tạo destination, reserve file DB hoặc transaction đích**. Đây là quy tắc dự kiến dựa trên cơ chế local_io, chưa phải chứng minh durability mới. Nếu receipt đã tồn tại, không replace; chỉ đường resume tường minh mới được dùng receipt đã kiểm. Lỗi/ACK chưa rõ ở ghi/fsync receipt ⇒ dừng trước effects; resume kiểm bytes và hoàn tất xác nhận độ bền của cùng file trước khi tiếp tục, không cấp bộ ID khác. Không bảo đảm mất điện khi chưa có bằng chứng filesystem/hardware.

Resume lấy **cả migration_id, target_store_id, activation_id từ receipt đã kiểm tra**, không lấy ID kỳ vọng từ row đích và không gọi UUID generator thay thế. Receipt thiếu/sai field, version không hỗ trợ, source/destination path sai ⇒ `MIGRATION_RECEIPT_INVALID` (mã đề xuất), không mở đích theo chế độ tạo/ghi. Mất receipt không được khôi phục tự động từ manifest/activation; giữ nguyên đích để audit, đối soát thủ công là công việc riêng. Receipt hợp dạng nhưng identity/path/inventory khác manifest/metadata đích ⇒ `MIGRATION_IDENTITY_CONFLICT`, không sửa receipt/đích. Collision sau khi receipt bền vững là conflict, không cấp lại UUID.

## 6. Migration offline DB1 → DB2 mới

### 6.1 Điều kiện và những trường hợp không hỗ trợ ban đầu

Chọn **offline copy có kiểm**, không ALTER/UPDATE DB1 tại chỗ, không cp file đang mở, không biến migration thành event nghiệp vụ/Run mới. Nguồn là kho S02 operational hợp lệ, không dataset. Đích và receipt ngoài checkout/dataset/kho S01 và không alias/symlink/hardlink với nguồn. Đích mới hoàn toàn, đủ dung lượng cho DB/rollback journal; không tự ghi đè hoặc xóa file không thuộc migration_id.

Bản đầu chỉ migrate khi tất cả operations đã finalized hợp lệ và không còn dispatch thiếu kết quả có thể gây side effect: S01 dispatch chưa có observation đối soát, dispatch không response, Attempt unknown_outcome đều **chặn migration**, kể cả Run đã finalized. Lock timeout là persistence/busy, không MODEL_CONFLICT. Active claim của command finalized/stale vẫn copy nguyên và unique; migration không release claim hoặc đánh Answer applied. Không dựa số tiền null để coi chi phí bằng 0.

Đánh đổi: read compatibility rộng hơn migration eligibility. DB1 hợp schema có command chưa kết thúc vẫn đọc được, nhưng phải hoàn tất/đối soát theo protocol cũ bằng công việc được cấp quyền riêng trước migration. Tool không tự finalize interrupted/stale, dựng observation hoặc gọi provider/S01. Nếu không đủ bằng chứng để giải quyết command cũ, dừng migration; không trình bày archive copy như kho có thể tiếp tục workflow. Hỗ trợ chuyển command đang chạy là phạm vi migration riêng về sau.

Operator phải dừng toàn bộ writer cũ trước khi bắt đầu và duy trì source đóng băng khi chuyển cấu hình. SQLite lock chỉ bảo vệ trong lúc giữ connection, không làm a3 vĩnh viễn biết kho đã chuyển. Không tự tuyên bố đã fencing mọi process sau khi thả lock; nếu không bảo đảm vận hành offline thì không activate destination. Môi trường ban đầu chỉ local filesystem đã audit, chưa hỗ trợ online rollout/network FS.

### 6.2 Thứ tự và atomicity

**Quy tắc chung S02-2A-01:** mọi connection SQLite **tới nguồn migration** phải mở URI `mode=ro` ngay từ lần mở đầu, trước mọi PRAGMA/SELECT/inspect. Áp dụng cho inspect/preflight, đọc copy, copy verification, mở lại sau lỗi, resume và reconcile, kể cả helper/nested connection. Không mở `rw` rồi đặt query_only, không fallback `rw`/`rwc`, không dùng `immutable=1` để bỏ qua journal hoặc locking, không ATTACH nguồn bằng đường mặc định có quyền ghi. Không chạy DML/DDL, đổi journal mode hoặc PRAGMA có tác dụng ghi nguồn. L1 checks dùng connection chỉ đọc do caller cấp; helper không được tự mở connection a3.

Không gọi public `Repository.verify()`/`a3.verify()` trên nguồn: public API đó mở `mode=rw`. Được tái sử dụng **logic validation L1 đã đóng băng**, tách khỏi factory mở kho a3; vẫn phải kiểm đầy đủ identity/application_id/version/exact DDL, settings thực, FK/integrity, bytes/hash/inventory, profiles L1 ngầm, archive/typed links và toàn record/operation/head/claim/graph. Không thay full verification bằng đọc user_version hoặc một hash. Unknown/busy/read-only lỗi khác giữ diagnostic riêng; chỉ kết luận cần recovery khi có bằng chứng tương ứng, ví dụ `SQLITE_READONLY_ROLLBACK`.

Nếu nguồn cần hot-journal/crash recovery: dừng `SOURCE_RECOVERY_REQUIRED` (mã đề xuất), giữ nguyên bytes DB/journal và báo path/stage/SQLite error; không retry bằng quyền ghi, xóa journal, checkpoint hoặc tự recovery. **Trước mọi tạo/ghi đích khi resume cũng phải qua gate này.** Đích đã có được giữ nguyên, không tạo đích khác. Recovery nguồn là công việc riêng do operator quyết định và cấp quyền; sau recovery phải inspect/verify đầy đủ lại từ đầu. Nếu có receipt, root nguồn phải còn bằng root đã pin; khác ⇒ từ chối resume, không sửa receipt hoặc merge dữ liệu.

1. **Inspect, không mutate:** từ connection `mode=ro` bắt đầu read transaction và đọc nguồn, giữ snapshot trong các bước sau; xác minh source path/version/application_id/exact DDL1/journal DELETE, FK + integrity và toàn L1 graph/hash; inventory tất cả cột/bảng/blob/link/head/claims. Gate commands ở §6.1. Resume trước hết đọc/kiểm receipt như §5.1 rồi inspect nguồn theo cùng quy tắc chỉ đọc; so root với receipt trước khi truy cập đích theo chế độ ghi/tạo. Một báo cáo inspect cũ không thay lần kiểm này.
2. **Cấp identity và receipt:** lần mới cấp UUIDv4 migration_id/target_store_id/activation_id, ghi **cả ba** cùng root nguồn đã kiểm vào receipt §5.1, fsync/đọc lại trước mọi effects đích. Resume chỉ đọc lại ba ID từ receipt, không sinh ID. Manifest input pin source path/inventory, target, profiles/resource hashes/tool version. Chưa có manifest hash ở bước này. Không timestamp nào thay timestamps records/events lịch sử.
3. **Giữ snapshot nguồn:** tiếp tục giữ connection **mode=ro** và read transaction (`BEGIN` rồi SELECT) từ bước 1 tới hết đối soát/activation trong journal DELETE. Read lock này chặn commit của writer khác, không khẳng định ngăn writer lấy RESERVED lock hoặc tạo journal. Vì vậy vẫn bắt buộc offline operator gate; không đổi sang mode=rw hoặc BEGIN IMMEDIATE chỉ để khóa một nguồn chỉ đọc. Tính lại source inventory và eligibility trong snapshot đang giữ, so với receipt; khác ⇒ abort/review lại, không copy head khác âm thầm. Mất connection thì quay lại gate chỉ đọc bước 1, không tiếp tục dùng báo cáo cũ.
4. **Transaction đích:** tạo DB2 ở path mới đã reserve, đọc lại foreign_keys=ON, synchronous=FULL, journal_mode=DELETE. Trong một `BEGIN IMMEDIATE` đích: tạo toàn DDL2 + registry + metadata; copy tất cả rows/cột legacy với parameter binding, thêm profile L1 cho records/operations; copy BLOB/typed links/index metadata đúng; ghi migration manifest có source inventory và kết quả byte comparisons, set user_version=2/application_id. Không có activation row. Do FK deferred, copy order phải được xác định trước, không tắt FK để vượt lỗi. Không INSERT OR REPLACE.
5. **Kiểm trước COMMIT:** verify profiles + toàn graph bằng L1, compare tất cả old columns/JSON strings/raw BLOB/IDs/hashes/timestamps/heads/sequence/claims/promotions/typed links, `foreign_key_check` và `integrity_check`. Không rebuild link rows của lịch sử để che drift. Không cần record E1 nghiệp vụ nào xuất hiện chỉ vì migrate. COMMIT chỉ ở đích; source không thay đổi, không có cross-DB atomicity được hứa.
6. **Mở lại đích bằng connection mới:** kiểm metadata/manifest và bộ ba ID với receipt, root hash/schema/profile/graph và inventory bằng cơ chế checked read; đối chiếu source vẫn locked/unchanged qua connection chỉ đọc. Destination bây giờ verified nhưng chưa được normal writer dùng. Lỗi/commit chưa rõ theo §6.4; không tạo target mới tự động.
7. **Activation explicit:** khi operator đã giữ source offline, kiểm root source một lần nữa trong lock; nhận xác nhận chuyển nơi ghi với bộ ba ID/profile/manifest đúng. Trong transaction riêng ở đích, kiểm lại identity và CAS activation-absent → một row store_activation, không sửa session/head. Reopen đối soát đầy đủ §6.3; cùng identity đã commit trả row/kết quả đã lưu, khác identity conflict. Sau thành công mới chuyển config sang destination; giữ source như archive chỉ đọc ở vận hành. Tool không tự sửa config/old receipt. Release source bằng ROLLBACK (không ghi dữ liệu). Hai store không bao giờ được tuyên bố writable đồng thời.

Một transaction đích đem lại all-or-none cho copy, còn activation là bước riêng có kiểm; không dựa vào “file đã ghi xong”. Đích dở dang hoặc version0 sau lỗi không được runtime initialize/reset. Migration recovery chỉ inspect, xác định đúng identity rồi yêu cầu cleanup/restart có chủ đích nếu chưa commit. Nếu process chết trước khi thả source read lock, OS/SQLite giải phóng lock; operator vẫn phải giữ writer cũ dừng trước resume/activation. Chính sách offline này không phải distributed fencing.

### 6.3 Exact preservation và manifest

Copy record_json/request_json/payload_json **nguyên ASCII strings đang lưu**; không decode→encode để ghi lại, không trim Unicode hoặc chuẩn hóa số. BLOB byte-for-byte. Dùng codec exact chỉ để validate và tạo metadata mới; SQL numbers chỉ các cột integer metadata có sẵn, không đưa số nghiệp vụ JSON vào REAL. Không áp null defaults A2 vào L1, không thêm application, không tăng Model/set revisions hoặc sequence do migration.

Manifest (`s02-migration-manifest/1`) ghi **migration_id, target_store_id, activation_id**, source_state_dir/destination_state_dir/plan_version/source_inventory_sha256 đúng receipt; source application_id/user_version, source inventory counts, target version/write profile, L1/E1 schema/descriptor hashes, tool/package/rules versions, table copy counts và before/after hashes của cột legacy, exclusions duy nhất là hai cột profile thêm + registry/store metadata/activation mới. Ba IDs đã có trước copy; manifest chỉ trở thành evidence bền vững cùng COMMIT copy. Không sinh activation_id khi tạo manifest. Hash toàn file SQLite **không được kỳ vọng bằng nhau** vì pages/schema/row layout khác.

Inventory định nghĩa để tái lập: table names và column order theo manifest DDL1; rows sắp theo declared PK với BINARY ordering. Hash mỗi row bằng length-prefixed typed cells: type tag N/I/T/B; N payload rỗng; I ASCII decimal canonical metadata integer; T UTF-8 của giá trị TEXT (JSON columns phải ASCII); B raw bytes; mỗi cell gồm tag + 8-byte unsigned big-endian length + payload. Row digest SHA-256, table digest trên table name/column names length-prefixed + row digests theo thứ tự; store root trên bảng/count/digests và DDL1 hash/version. Không float, không locale sorting, không hash lại dict để thay bytes JSON. Manifest bytes encode bằng codec exact, hash lưu riêng; hash không bao gồm chính nó. Định nghĩa framing là đề xuất cần review/test oracle độc lập; không nói hash chứng minh ý nghĩa nghiệp vụ.

| Thời điểm | Evidence có thể tồn tại bền vững | Phép đối chiếu bắt buộc |
| --- | --- | --- |
| Sau receipt, trước tạo/copy đích | Receipt chứa ba IDs, paths, plan và root nguồn; chưa có metadata/manifest/activation | Resume không cấp ID; inspect nguồn `mode=ro`, root bằng receipt, destination vẫn phải vắng để bắt đầu copy |
| Copy commit, chưa activation | Receipt cũ; store_metadata + manifest chứa ba IDs; manifest_sha256 biết **sau** tạo bytes manifest; chưa có store_activation | metadata.migration_id = receipt.migration_id = manifest.migration_id; metadata.store_id = receipt.target_store_id = manifest.target_store_id; manifest.activation_id = receipt.activation_id; paths/plan/root bằng receipt; SHA-256 raw manifest bytes = metadata.manifest_sha256 |
| Activation commit | Thêm row store_activation; receipt và manifest không thay | activation.activation_id = receipt.activation_id = manifest.activation_id; activation.store_id = metadata.store_id = receipt.target_store_id; activation.profile_id = metadata.write_profile_id = manifest.write_profile_id; activation.basis_sha256 = metadata.manifest_sha256; slot=1 trỏ chính metadata mang migration_id đã so ở trên |

Không thêm migration_id trùng lặp vào row activation: lấy qua singleton metadata đã kiểm cùng transaction/checked read, do đó bộ ba identity vẫn đối chiếu đầy đủ. Không chỉ so activation_id hoặc chỉ so store_id. Các mismatch trong metadata/manifest/hash/profile là corruption/conflict, không coi là retry thành công. Cùng bộ ba IDs nhưng basis/profile khác cũng từ chối. Receipt thiếu/sai identity bị từ chối **trước** khi lấy ID ở đích; có activation ở đích không làm receipt sai trở thành hợp lệ. Khác identity không thể cập nhật manifest hoặc activation cũ để “khớp lại”.

Hai activation cùng identity và basis: một transaction insert, bên còn lại kiểm lại sau khi giành lock rồi đọc row đã commit, trả **cùng kết quả cũ**, giữ operator/activated_at cũ, không tạo activation thứ hai. Hai yêu cầu khác identity: identity được manifest pin từ copy; yêu cầu không khớp bị conflict dù tới trước hoặc sau yêu cầu đúng. Chỉ yêu cầu khớp manifest mới có thể CAS. Nếu row đã có nhưng khác identity thì conflict; không replace. Busy/timeout vẫn là persistence error, không tự gán identity conflict. Cùng receipt chưa phải đã có consent activation: resume trước activation vẫn cần quyết định operator §6.2 bước 7; chỉ retry sau activation commit mới trả kết quả cũ.

### 6.4 Lỗi, recovery, rollback

| Điểm lỗi | Kết quả/đối soát bắt buộc |
| --- | --- |
| Source invalid, profile/DDL unknown, unresolved commands, alias path | Không tạo DB đích; có thể chỉ receipt/diagnostics nếu đã cấp; không sửa source |
| Nguồn cần recovery tại preflight/resume/reconcile | Chỉ `mode=ro`; dừng SOURCE_RECOVERY_REQUIRED, DB/journal nguyên byte; không tạo DB đích mới, không mutate/activate đích đã có. Recovery nguồn tách riêng rồi inspect lại |
| Receipt thiếu/sai identity hoặc ACK độ bền receipt chưa rõ | Không tạo/ghi đích; đọc lại cùng file và kiểm đầy đủ §5.1. Không overwrite receipt, không thay ID; thiếu/sai receipt ⇒ từ chối, không dựng receipt từ manifest |
| Busy trước source/target transaction | Deadline hữu hạn, lỗi busy/persistence; không giả revision conflict hoặc retry submit |
| Lỗi trước COMMIT đích | Rollback đích; source không đổi, không activation. Giữ diagnostics/receipt, không xóa artifact chưa xác định quyền sở hữu |
| COMMIT đích mất ACK | Dùng receipt đã kiểm, gate nguồn `mode=ro` trước resume; connection đích mới mở **existing-only**, đối chiếu cả ba IDs và manifest §6.3, verify toàn kho. Khớp ⇒ copy committed; không tồn tại/partial/corrupt ⇒ phân biệt chưa commit/unknown, không đánh success hoặc overwrite |
| Copy verified nhưng chưa activate, hoặc source đổi sau mất lock | Chỉ inspect/reconcile. Source fingerprint khác ⇒ cấm activate; không append missing rows hoặc merge hai nhánh |
| Activation mất ACK | Reconcile đọc receipt và kiểm chuỗi metadata/manifest/activation §6.3 bằng connection đích mới, không sinh IDs. Đã có đúng identity/basis/profile ⇒ trả row/kết quả cũ, không đổi timestamps/operator hoặc phát consent mới; khác ⇒ conflict. Mọi connection nguồn trong reconcile vẫn mode=ro |
| Sau activate, chưa có E1 writes | Chỉ rollback vận hành bằng quyết định operator, đóng băng đích và chứng minh không new records/operations/heads/claims so với migration manifest. Không downgrade DB2 tại chỗ |
| Sau E1 writes | Không trỏ lại DB1 như “rollback không mất dữ liệu”. Giữ cả hai để audit, sửa forward hoặc thiết kế migration ngược riêng; không tự drop E1 fields |

Manifest và activation row cùng hashes/receipt đủ đối soát local; chưa phải chữ ký xác thực doanh nghiệp. Không bảo đảm chống operator cố ý chạy a3 tiếp trên archive sau cutover. Không tự retry copy sang path mới khi outcome chưa rõ.

## 7. Changes dự kiến và nghĩa vụ kiểm thử trước bàn giao

Không tạo các files dưới đây trong lượt này. Phân rã đề xuất để audit từng phần:

| Tiểu đợt 2A | Phạm vi code dự kiến | Điều kiện/bằng chứng |
| --- | --- | --- |
| 2A-P1 profiles | profiles.py/resources mới; validation.py/events.py nhận explicit owner profile; L1 corpus freeze; E1 DIRECT/CARRY/REPLACEMENT và A1 checker | Hash schema cũ nguyên; profile/schema/rules registry audited; differential L1 + E1 positive/negative, cả codec backends, installed wheel ngoài source |
| 2A-P2 storage | storage_schema.py DB2, repository.py profile columns/typed links/checks/activation; lookup metadata | Mixed graph root L1→E1 successor đúng; legacy rows nguyên byte; FK/unique/CAS/immutability; old-reader reject, no missing-profile fallback |
| 2A-P3 migration local | migration.py; minimal receipt/inspect/copy/activate/reconcile adapter; test helpers/process_worker phù hợp | Offline copy full DB1, no mutate source; exact inventories/reopen/unknown commit; command eligibility/cutover/receipt path binding; chưa CLI phân tích hoặc source update orchestration |
| 2A còn lại | Pure handlers/candidates/bootstrap/admission theo plan | Chỉ công bố persisted carry khi P1/P2/P3 thuộc phạm vi đã audit; profile không thay chứng minh chất lượng ngữ nghĩa hoặc G1 inventory |

Các tests dưới đây **dự kiến, chưa viết/chạy**. Fixtures synthetic nhỏ, DB temp riêng; không dùng dataset hay projections docs làm export canonical được tin cậy.

| Nhóm / oracle độc lập | Ca bắt buộc và kết quả mong đợi |
| --- | --- |
| Profile dispatch | L1/E1 với field thiếu/null/lạ, unknown ID/hash/capability/rules, E1→L1 downgrade label, event override profile, schema resource bị đổi; reject trước mutation. Đúng legacy root giữ invariant a3; không thử union schemas |
| A1 low-level | Cùng snapshot/archive mới, unchanged nhưng snapshot S02 cũ, consent/run/raw mismatch, stale pair; branch/evidence đúng. Không coi đó là đã có 2C orchestration |
| A2 root/carry | DIRECT root L1 và E1, không clone event target; CARRY same/changed snapshot, method matrix, pending→applicable không app mới; refs lịch sử đúng trường, unrelated refs vẫn current; negative key/lineage/cycle/wrong event/prepared |
| A2 replacement | JSON 07 chuyển thành fixtures canonical riêng: old/new key đủ, application_new trước review vẫn block; complete với evidence/tasks/current target; source-only/removal/future target-invalid; root not_applicable giữ, mỗi Answer tối đa một app; prose-only/scope thiếu/old target/review giả reject |
| Mixed links/gates | Materialized role inventory theo owner schema, không rebuild chữa lịch sử; scopes/Parts mở mọi action fixed point, target REPLACEMENT/cycle reject; task attestation không mutate Change; all current keys và paired CAS |
| Numeric/raw | Huge int, Decimal, bool/number, null/missing, W29/Unicode boundary, invalid JSON staged bytes, consent source hashes; copy ASCII/BLOB exact. Oracle bytes độc lập với encode của writer; phép hash framing có vectors cho N/I/T/B và PK composite |
| Migration golden | DB1 tạo từ wheel a3 sạch; tất cả bảng có rows gồm finalized/stale/failed và claims, promotions/stages, source archive, legacy review; compare toàn old columns và lookup outputs before/after. Empty DB, fresh DB2, DB1 read-only writes refused |
| Eligibility | Prepared/unfinalized, dispatch thiếu observation, unknown_outcome kể cả finalized ⇒ refuse migration; không tự finalize/release claim. Finalized stale đã đối soát hợp lệ migrate được, successor vẫn phải claim/CAS |
| Old-reader | Cài a3 wheel cũ ở môi trường riêng: DB1 vẫn đọc; DB2 exact hoặc chỉ sửa user_version=1 vẫn reject, source/target hashes không thay bởi thao tác từ chối. Không nới expectations suite cũ để đạt |
| Fault/recovery thật | Inject trước/sau từng table insert, trước COMMIT/activation; lost ACK sau commit; hai process giữ SQLite lock; kill bằng IPC tại copy trước/sau commit và activation. Reopen connection mới kiểm IDs/rows/activation; không sleep làm bằng chứng race |
| Races | Hai activation cùng identity/basis: một insert, bên còn lại trả row cũ; khác identity: bên không khớp manifest conflict, chỉ bên đúng có thể insert. Source writer có thể bắt đầu nhưng COMMIT bị chặn khi read lock đang giữ; source đổi sau crash/release ⇒ activation refused; hai mixed-profile app cùng Answer và hai publishers model/set như baseline, unique toàn kho |
| Receipts/rollback | Wrong source path/store_id/migration_id/hash/command, existing destination, aliases/links, forbidden roots; old receipt không tự route; lookup-migrated exact. Có E1 writes ⇒ rollback về DB1 bị từ chối, không xóa lịch sử |

**Cách giữ oracle Đợt 1 khi đổi storage/API:** không thể hứa mọi fixture a3 chạy nguyên xi trên E1: Issue E1 bắt buộc hai nullable fields, application E1 có field mới, DB thêm cột và DB1 không còn writable bằng reader mới. Giữ lane đối chứng wheel a3 + suite a3 nguyên bản ngoài source; lane package mới dùng fixtures khai báo E1 tường minh và tests L1 read/legacy shape riêng. Adapter test chỉ thêm fields/profile bắt buộc hoặc chọn fixture DB2, không runtime-auto-upgrade payload legacy, không skip case hoặc nới các assertions identity/negative/preservation. Mọi expectation đổi vì đặc tả storage/API có chủ đích phải có mapping case cũ→oracle mới và được audit; không báo “suite cũ nguyên vẹn pass trên E1” nếu đã dùng adapter. S01 suite giữ nguyên trên a6; instrumentation backend vẫn bắt buộc ở cả lanes.

Bàn giao tương lai gồm version/hash runtime/schema/rules/wheel và source–installed–wheel; baseline/protected inventories; commands/exit/logs thực; timeline process/locks/fault points; copied-column comparisons; a3 differential/old-reader evidence; mọi trạng thái chưa chạy. Full S01/S02 regression hai backends giữ instrumentation, không skip/nới test cũ. Tách tests code với ngữ nghĩa human_review; metadata người review hợp shape chưa chứng minh người dùng thật đã đồng ý.

### 7.1 Các ca bổ sung riêng S02-2A-01/02 — dự kiến, chưa thực thi

| ID | Dữ liệu / checkpoint | Kỳ vọng và bằng chứng cần có khi implementation được giao |
| --- | --- | --- |
| RO01 | DB1 sạch, finalized/known outcomes; inspect → copy verification → resume/reconcile | Instrument **mọi** source open là URI mode=ro ngay từ đầu, không immutable/rw/public a3.verify; full L1 checks và inventory đạt; hash DB/sidecars trước–sau giữ nguyên. Một DB1 sạch về journal nhưng sai DDL/hash/graph phải reject, chứng minh không bỏ validation |
| RO02 | Hot journal ở preflight, DB đích chưa có | SOURCE_RECOVERY_REQUIRED, ghi SQLite extended error; DB/journal cùng hash/length/existence, không DB đích mới. Oracle file bytes độc lập, không gọi a3.verify để kiểm sau vì chính nó có thể recovery |
| RO03 | Receipt đã bền vững, crash rồi nguồn có hot journal; resume với đích vắng **và** với copy đã commit | Cùng refusal như RO02; ID/receipt nguyên, không tạo DB đích mới; đích có sẵn không đổi bytes/activation. Mỗi variant dùng fixture riêng. Sau recovery nguồn được cấp quyền riêng phải inspect đầy đủ; root khác receipt ⇒ refuse |
| ID01 | Crash sau fsync receipt, trước reserve/copy | Resume đọc lại đúng ba UUID; root nguồn đúng thì copy bằng cùng identity; UUID generator không được gọi. Chưa yêu cầu manifest hash; trước receipt durable không có destination |
| ID02 | Copy commit rồi crash trước activation | Manifest/metadata khớp receipt; source gate đạt; không copy lại. Sau operator xác nhận, insert activation_id từ receipt; vẫn không có normal writes trước activation |
| ID03 | Activation commit nhưng ACK mất | Mở lại connection đích, đọc và verify cùng identity/basis/profile; trả đúng row cũ (kể cả operator/time), một row duy nhất; không cập nhật receipt/manifest hoặc cấp UUID/consent mới |
| ID04 | Receipt thiếu/null/blank/UUID sai activation_id, wrong version/path; receipt mất; hoặc durable write/ACK lỗi | Từ chối trước tạo/ghi đích, không lấy ID từ manifest để bù. Ghi receipt lỗi không dẫn tới copy; receipt hiện có không overwrite. Trường hợp fsync ACK chưa rõ chỉ tiếp tục sau xác minh độ bền của cùng file |
| ID05 | Receipt hợp dạng nhưng một trong ba IDs khác đích; manifest đổi ID; activation có ID đúng nhưng basis/profile sai | MIGRATION_IDENTITY_CONFLICT hoặc corruption đúng lớp; không đổi đích/receipt/head, không báo retry success. Các biến thể mutation kiểm từng field, không chỉ activation_id |
| ID06 | Hai process/two connections cùng đích, cùng receipt/identity/basis | IPC barrier trước transaction + deadline; một insert, bên kia re-check rồi cùng kết quả; log thứ tự và DB reopen có đúng một activation. Busy tách khỏi conflict |
| ID07 | Hai process cùng đích với hai receipt có activation_id khác (đúng UUID), các fields khác bằng nhau; đổi thứ tự đến bằng IPC | Chỉ receipt khớp manifest được insert/return; bên kia conflict kể cả tới trước. Nếu activation đã có khác ID cũng conflict. Không replace, không sinh ID thứ ba; giữ byte evidence sau reopen |
| ID08 | File receipt tồn tại, target một migration khác, copy/activation ACK chưa rõ, source root đổi sau crash | Không overwrite/recopy/auto-retry dưới identity hoặc path mới. Existing-only reconcile; root mismatch hoặc identity mismatch dừng rõ; không coi file tồn tại là đã commit |

RO02/RO03 cần fixture hot-journal tạo bằng process bị kill/exit sau spill có đồng bộ và kiểm header; RO01 có negative fixtures cấu trúc/hash/graph. ID01–03 dùng crash/IPC ở đúng checkpoint; fault injection riêng cho fsync/ACK, không gọi mô phỏng đó là mất điện thực. ID06–07 bắt buộc hai process, hai connection, một DB và event/deadline; không dùng chạy tuần tự/sleep làm bằng chứng race. Chưa viết hoặc chạy bất kỳ ca nào ở đây.

## 8. Tài liệu chính thức đã đối chiếu và phần chưa xác minh

Ngày kiểm 21/10/2026, chỉ đọc web:

- SQLite cho phép một writer đồng thời; read transaction giữ snapshot, BEGIN IMMEDIATE/COMMIT có thể busy. Đó là căn cứ giữ read transaction nguồn và write transaction đích riêng. Thiết kế offline/cutover là đề xuất DACN. [SQLite Transactions](https://www.sqlite.org/lang_transaction.html).
- user_version/application_id là metadata ứng dụng; read-back pragmas cần thiết vì pragma không biết có thể bị bỏ qua. Không dùng schema_version nội bộ làm format version. [SQLite PRAGMA](https://www.sqlite.org/pragma.html).
- Commit rollback-journal và durability phụ thuộc cơ chế flush/filesystem/hardware. Thiết kế dùng transaction đích, verify/reopen và activation riêng; chưa có bằng chứng mất điện hoặc disk-full thực. [Atomic Commit in SQLite](https://www.sqlite.org/atomiccommit.html).

**Bằng chứng bổ sung đã có, không chạy lại trong lượt này:** [preflight-probe.json của auditor](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-2a-storage-draft1-2026-10-21/preflight-probe.json), CPython 3.13.16/SQLite 3.53.1/package a3 trên **kho tạm**: mode=ro trả SQLITE_READONLY_ROLLBACK và giữ DB/journal; public a3.verify thành công nhưng đổi DB 1.662.976 → 217.088 bytes, xóa journal. Probe xác nhận vì sao phải cấm public verify trên nguồn migration; không phải bug baseline a3, không phải migration mới đã chạy, không phải full suite hoặc kiểm mất điện. Không truy cập operational store trong probe.

Chưa có implementation migration mới, schema E1 hash hoặc exact DDL2 để kiểm. Không cài dependencies, mở DB, chạy application tests/migration/LLM/renderer trong lượt này. Xem [ví dụ metadata và cases](examples/s02-phase2-2a/01-profile-and-migration.json), [receipt/manifest/activation và checkpoints](examples/s02-phase2-2a/02-readonly-preflight-and-activation-recovery.json), [kiểm tĩnh draft.2](examples/s02-phase2-2a/STATIC_CHECKS_DRAFT2.json). [STATIC_CHECKS.json draft.1](examples/s02-phase2-2a/STATIC_CHECKS.json) giữ nguyên như bằng chứng lịch sử; không dùng nó để chứng nhận artifacts draft.2. Chỉ kiểm tĩnh tài liệu, không gọi đó là application tests.

## 9. Quyết định cần chốt trước code

1. Chấp thuận profile E1 gộp A1+A2 ở low-level 2A; 2C vẫn sở hữu orchestration. Nếu chọn A2-only phải audit profile khác trước code.
2. Chốt các ID/version đề xuất và cách materialize contract draft.4/schema resources mới, exact DDL2/registry, package target. Hash E1 chỉ chốt sau khi có artifact thực; không dùng placeholder trong runtime.
3. Chấp thuận giới hạn offline/quiescent migration, legacy commands đọc-only, activation riêng và trách nhiệm ngừng writer a3. Không hỗ trợ chuyển command đang chạy hoặc tự repair.
4. Chốt lookup metadata/export refusal hoặc export v2, receipt s02/2 + migration receipt/lookup-migrated; không bỏ binding path/ID để tiện cutover.
5. Giao rõ P1/P2/P3 hoặc pure handlers độc lập, yêu cầu audit theo bảng §7. Chưa có quyết định triển khai do audit thiết kế A2 tự cấp.

**proposed — đã phản hồi S02-2A-01/02, chờ audit lại; chưa được duyệt implementation.** Dừng để auditor review; A2-R1/R2 vẫn đóng ở mức thiết kế, chưa sửa thêm semantics, chưa implement persistence/carry hoặc chạy migration.
