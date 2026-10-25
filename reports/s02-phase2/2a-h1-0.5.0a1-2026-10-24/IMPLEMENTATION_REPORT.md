# 2A-H1 0.5.0a1 — triển khai để audit độc lập

Ngày bàn giao: 24/10/2026. **Đã triển khai, chờ audit độc lập**. Không tự ghi nghiệm thu H1 hoặc toàn 2A. Phạm vi được người dùng giao riêng: fresh E1/full scope, S01 test store → bốn mock qua handlers thật → draft Model/mapping/Issues; checkpoint/reopen/resume/blocked và toàn safety §7.1.

## Căn cứ và trạng thái ban đầu

- [Proposal draft.2](../../../docs/S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md), SHA-256 `28a43ae1bea4cf6b0106537293472a82fc4de9867f144c6c97e10b165f863e3b`.
- [Audit thiết kế 24/10/2026](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-design-draft2-2026-10-24/AUDIT_REPORT.md): D01/D02 đóng ở mức thiết kế; mọi gate §7.1 thuộc H1.
- HEAD trước sửa `4c7e69719dbd1a6e4215cfd01764c6750962ee7f`; index trống. Đã có docs/README sửa và proposal/handoff draft.2 chưa track: giữ đúng bytes công việc này, chỉ cập nhật dòng navigation hiện hành sau implementation.
- Inventory trước sửa: **13.105 files, 2.262.866.069 bytes** gồm tracked inputs và toàn evidence reports hiện có. Không suy inventory này thành kiểm toàn filesystem/cache.
- Bootstrap trước sửa trên source P3 a3 đối chiếu S01 20 entries và S02 30 entries bằng accepted wheels. Môi trường baseline riêng, không lấy source H1 làm baseline L1.

## Delta implementation

| Vị trí | Thay đổi / điều kiện kiểm |
| --- | --- |
| `h1_candidates.py:35`, `:80`, `:133` | Schema candidate đóng, detached E1 projection; required/nested typed refs, exact codec, inventory/source pointers; unique handles, allowlist có kiểu; không ID canonical, Review/Answer/consent hoặc sửa actor supplied |
| `h1_builders.py:43`, `:59`, `:144–180` | Bootstrap và bốn handlers riêng; giữ SourceContext/snapshot, actors supplied, unknowns/criteria; mapping requirement/criterion; Model+Change+AS hoặc AS-only; Issue lineage/current scopes, code-owned mapping task và full-scope holds |
| `h1_store.py:188` | Prepare kiểm absent/existing/intent+insert trong cùng checked BEGIN IMMEDIATE; raw/config T0 trước parse, một reserved Run; cùng intent idempotent/khác intent reject; lost-ACK probe đối soát cả pins và bytes |
| `h1_store.py:116`, `:257` | Private plan strict envelope/bindings/allocation/promotions, whole-graph preflight; seal đếm 0/1/nhiều và kiểm finalized ngay transaction; không repair/chọn timestamp/thêm plan mù |
| `h1_service.py:52`, `:104` | Parse/link/build/validate/seal/finalize; canonical validators/CAS nguyên; rejection giữ raw; blocked giữ hold; stale không domain publication; finalized outcome từ Run/event, progress tách current/result pair |
| `h1_cli.py:13`, `cli.py` | Bootstrap/analyze-step/prepare-work/resume/progress; receipt-first, raw bound+hash, explicit receipt-only policy; CLI cũ không đổi dispatch/API |
| `h1_limits.py` | Defaults/version đã audit, lexical bounds trước tree, total result limits, monotonic cooperative deadline; giữ exact Decimal/Unicode oracle; không áp lên legacy validators |
| `h1_recovery.py:16` | Receipt/store-ID-bound H1-only rollback hot journal qua SQLite, checked fresh DB2+registry+reservation gates; không sửa row/DDL/activation |
| `pyproject.toml`, `__init__.py` | Version `0.5.0a1`, mô tả H1; build requirements/dependencies/locks không đổi |

Code tại [packages/s02/src/dacn_s02](../../../packages/s02/src/dacn_s02/). Chỉ thêm bảy module H1 và nhánh CLI; repository, validators/profiles, canonical schemas/registry/DDL, S01 nguyên byte. Không import test helpers vào production; AST import inventory lưu ngoài repo. Không thêm framework/tables/claims/settings keys. Canonical E1/L1 profile/contract/rules IDs giữ nguyên; candidate/config/plan/limits là blobs/private projection có version theo thiết kế.

Alias long-handle dùng namespace `stepN-long.<SHA256(handle)>` nếu prefix thường vượt 128 ký tự, không trim/coerce hoặc nối bằng tên. CLI trả allowlist có kiểu cho bước kế. Technical mapping task chỉ kết thúc khi mọi row có Parts/assessment proposed; không chứng minh nghĩa vụ được đáp ứng. Unknown initiator giữ analysis_omission để đọc nguồn trước khi hỏi nghiệp vụ. Null covered_portion và gaps vẫn giữ hold.

## Mốc CLI và gate §7.1

Hai demo mới `m1-final-c/`, `m1-final-python/` có S01 input/envelope/store, raw bốn mock, receipts, stdout từng CLI, Model/mappings/Issues/AnalysisSet, progress và SUMMARY. Mỗi checkpoint chạy bằng process mới; raw file được chuyển vào mock-archive trước resume để chứng minh không reread. S01 store hash trước/sau bằng nhau. Hai actions, một component, sáu mapping rows; trạng thái `synthetic_draft_not_reviewed`. Session riêng nhận inspection held trả blocked/2, reopen/resume giữ đúng holds. Fixtures/mocks là synthetic test tooling; không dùng canonical import thay handlers.

| Gate | Tests H1 trong full lane |
| --- | --- |
| Receipt trước/sau kill; checked absence/5 và explicit prepare | `test_crash_receipt_creation_and_explicit_prepare`, CLI receipt-only/prepare-work/conflict |
| T0/seal/T3 trước COMMIT, sau COMMIT kill, sau COMMIT lost ACK, sau COMMIT unknown | `test_commit_crash_lost_ack_unknown_reopen` — 3×4 cases, process/connection riêng; raw/plan/run/head/IDs/times được đối soát |
| Hai resumers trước/sau seal | `test_two_resumers_before_and_after_seal` — 2 cases, barriers, một plan và finalized event |
| Hai preparers cùng/khác intent | `test_two_preparers_same_receipt_compare_intent` — 2 cases, một T0/raw/config/reserved Run |
| AS-only stale và Model stale riêng | `test_stale_as_head_and_model_head_are_separate` — không publication planned IDs, head thắng không đổi |
| Version/bindings/hash/type/nhiều plan/unknown marker | `test_h1_integrity.py`; không rebuild/repair; finalized Run authoritative kể cả unpromoted future stage |
| Candidate/ref/unknown/criterion/system/multi-action/boundaries | `test_h1_candidates.py`, `test_h1_limits.py`; bộ limits có inclusive/+1, lexer UTF/depth/values/string, findings500/501, obligations1000/1001, total graph caps và fake monotonic clock |
| Cache spill thực với hot journal | `test_default_cache_spill_crash_seal_recovery`; wrong store ID, progress read-only và migration reservation từ chối trước recovery, DB/journal bytes không đổi; CLI resume đúng receipt hoàn tất |

Raw parse/schema/ref failures là rejected evidence, không sửa candidate để qua gate. Candidate thiếu thông tin là blocked draft, không rejected để đoán đáp án. H1 không partial-continue qua holds; lịch sử Answer/CARRY/REPLACEMENT/Review ngoài entry mới bị từ chối tường minh, capability validators cũ giữ nguyên.

## Hot journal: lý do bổ sung và giới hạn

Trong development, kill trước seal COMMIT với plan lớn làm SQLite default cache spill tạo hot rollback journal thật. Reader `mode=ro` không thể tự rollback, nên resume cũ dừng trước khi đọc checkpoint. Log `commands/spill-before-recovery.log` và JUnit trial01 giữ phản chứng. Đây là lỗi phát hiện trong triển khai §7.1, không thay thiết kế/schema DB2 đã nghiệm thu.

H1 recovery kiểm receipt trước, đọc immutable view chỉ cho exact DDL/identity/registry/fresh activation, đối soát store ID và migration reservation trước khi mở writable connection cho engine rollback. Sau đó full checked graph dưới lock, không có SQL sửa dữ liệu logic. Không dùng Records/heads/eligibility từ immutable view, không tự init/activate. Read-only progress/DB1/shared readers giữ hành vi cũ. Evidence kiểm trên filesystem local ổn định/caller hợp tác; chưa chứng minh chống adversarial namespace replacement hoặc power loss thật. Không gọi đây là general repair API.

## Bảo toàn, oracle và đóng gói

[START_HERE](START_HERE.md) trỏ kết quả đo và wheel duy nhất. `implementation.diff.patch` so đúng inventory đầu task, không lấy Git HEAD trống làm baseline cho docs đã sửa trước đó. `protected-verification.json` kiểm toàn original inventory; `final-git-state.json` ghi index/HEAD thực, không stage/commit/push.

Full lane giữ adapter E1 đã có, hashes và mọi diff setup trong ADAPTER.json. Test H1 mới và conftest giữ byte trong copy. Oracle ngoài chạy trực tiếp file gốc, hash trước/sau do runner kiểm; không assertions/skip/xfail mới. Helpers từ bundle pin SHA-256, không sửa helper để đổi oracle.

Ba oracle P2 gốc có **16 pass + 1 failure harness/backend**: checked `heads()` từ chối ngay sau selection corruption ngoài pytest.raises. [Audit P2 a2 §oracle lịch sử](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p2-0.3.0a2-2026-10-23-015238/AUDIT_REPORT.md) đã xác nhận lỗi setup này; không làm yếu checked read để qua file cũ. Oracle v2 do auditor cung cấp và boundaries chạy riêng. Không sử dụng file persistence không hậu tố v2 có sai API.

Build hai copies sạch ngoài source; S01 toàn 20 entries bằng accepted, S02 toàn 37 entries giữa rebuilds (kể cả METADATA/WHEEL/RECORD). Cài locks require-hashes từ wheel S01 lịch sử trước, rồi thay S01 rebuild chỉ sau proof equality; S02 H1 non-editable mới. Collector source=wheel=installed, pip check, direct URL và import paths có evidence riêng. Không ép wheel ZIP khác version bằng P3, không sửa locks/cache wheel bàn giao cũ. Driver tái lập offline đã được chạy lại vào output mới và đối chiếu payload với wheel bàn giao.

## Development logs và phần chưa chứng minh

Giữ mọi trial failures: lần log diagnostic dùng json.dumps(Decimal) sai; thử gọi test trong repo qua external-audit adapter gây double conftest; cache-spill recovery chưa có; positive fixture từng gán actions vào system constraint Part bị validator từ chối đúng, sửa own fixture chọn FR row; demo driver trial01 đọc nhầm key analysis_set (API chỉ có result_pair), sửa driver lấy show-record. Không thay oracle/validator để xử lý các lỗi harness này. Kết quả cuối dùng wheel release và final logs/JUnit riêng, không tái dùng số cũ.

Chưa chạy LLM, renderer, operational migration/live, semantic heldout evaluation, stress ngoài matrix H1, hardware power loss, network/filesystem khác, real disk-full hoặc cumulative runtime ledger. Không chứng nhận requirements đủ rõ, mapping đúng nghiệp vụ, performance/SLA hay user review. H2 partial G2, H3 và các bước5–9 không thuộc đợt này. Handoff này chưa được auditor kiểm độc lập.
