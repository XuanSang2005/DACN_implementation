# H3-B checkpoint result assessment — delta đề nghị draft.1

Trạng thái: **PROPOSED, chờ audit trước writer phụ thuộc**. Không sửa contracts/code A a2 hoặc proposal H3 draft.2 đã audit. Căn cứ: [H3 §2.2/§5/§7.1](S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md), [delta A a2](../reports/s02-phase2/2a-h3-a-fixes-0.9.0a2-2026-10-30/CONTRACT_DELTA.md), [nghiệm thu A](acceptance/s02-2a-h3-a-0.9.0a2-2026-10-31/README.md). Người dùng giao B ngày31/10 và yêu cầu trình delta để audit trước khi dùng trong writer nếu contract cần đổi.

## 1. Vấn đề được tái lập trên a2 nguyên byte

`check_admission` dùng `_checked_progress` rồi đòi **toàn** `progress_by_unit` bằng projection đó. No-anchor trả `unassessed_progress`; anchor hợp lệ cũng trả stage/output projection với `assessment=None`, `latest_checked_pair=None`. Đây là nguyên tắc A chống tự khai completed stage đã được nghiệm thu.

Ngược lại, `_published_data` kiểm **mọi** progress row có assessment khác null, result pair/hashes/state/output refs đúng actual promoted publication; reader này được `check_anchor` gọi. Một H3 AS-only plan đạt `check_plan` không thể được reader ấy nhận làm publisher: `publisher_assessment`. Chỉ điền assessment cho checkpoint mới, không tăng stage hoặc thêm output, lại bị `admission_progress_provenance`. Do đó không thể dùng nguyên cả hai checks để xây chuỗi prepare→seal→report/anchor→revalidate theo §2.2/§5.

Vị trí trên source đã audit:

- [h3_bindings.py](../packages/s02/src/dacn_s02/h3_bindings.py): `_published_data`, `check_anchor`, `_checked_progress`, `check_admission`, `check_plan`.
- [h3_policy.py](../packages/s02/src/dacn_s02/h3_policy.py): `unassessed_progress`.
- [positive projection A](../packages/s02/tests/test_h3_a_contracts.py): `test_positive_pure_plan_projection_and_exact_reserved_pins`, fixture projection đã có; không phải runtime writer B.

[Diagnostics và logs](../reports/s02-phase2/2a-h3-b-contract-review-2026-10-31/START_HERE.md) thực chạy mới trên fresh venv/non-editable a2: 3/3 mỗi backend C rồi Python, 0 failures/errors/skips. Các tests **xác nhận mismatch mong đợi**, không chứng minh H3-B đạt safety. Existing H2 stage2 publisher/full anchor là positive control. Không sửa original test/oracle để có kết quả này.

## 2. Delta tối thiểu đề nghị

Tách hai capability bằng API/checker có tên và version riêng; shape validation không cấp capability nào:

| Capability | Nguồn bằng chứng | Quyền được kiểm |
| --- | --- | --- |
| Stage/output provenance | Full anchor + actual promoted origin/raw/config/plan + transitions theo A a2 | Chỉ `work_completed_through`, ordered output refs, actual output inventory và correspondence; không tự cấp current assessment |
| Checkpoint result assessment | Config/analysis/authority đã pin + checked base/result graph + exact sealed plan | Được tạo assessment kỹ thuật mới cho result pair, giữ stage/output provenance và holds; không tạo completed work hoặc human decision |

Giữ pure A `check_admission/check_plan` nguyên hành vi cho callers/fixtures cũ. Thêm versioned pure B checker đề nghị:

```text
check_checkpoint_result(config, plan, base_view, result_view,
                        *, stage_evidence, checked_parent_plan) -> checked result
```

Đây là chữ ký đề nghị để audit, chưa code/public API. `stage_evidence` phải được tái kiểm từ bytes anchor trên base view; không nhận dataclass hoặc completed map tự khai. `checked_parent_plan` chỉ được tạo từ actual finalized/promoted bytes; caller dict không đủ. Checker kiểm projected Run/finalized event/whole graph như A, rồi kiểm result metadata bằng các quy tắc dưới đây. Không dùng `progress=...` tự khai để vượt `_checked_progress`.

### 2.1 Quy tắc AS-only result bắt buộc

1. Model/current source giữ nguyên ID/bytes. Adopt giữ mọi current Issue ID/bytes và selection. Revalidate chỉ successor/guard được thiết kế hỗ trợ; không Model/Change, Answer/application hoặc human_review mới. Mọi old key giữ trong result selection.
2. Với từng unit, result completed stage và ordered output refs **bằng đúng** stage evidence đã chứng minh ở base; no-anchor luôn stage0/outputs rỗng, giữ actual output IDs và `needs_revalidation` cho existing outputs. Không bỏ nguyên unit/outputs để giải hold. Revalidate không tăng stage và không làm output chưa có proof trở thành overwriteable.
3. Result `latest_checked_pair` bằng actual result pair. `assessment` khác null, `from_pair` bằng config base pair, `result_pair` bằng batch head, result Model/AS SHA bằng actual Records. `output_refs` bằng đúng retained output refs; `state` bằng assessment_state. New assessment chỉ mô tả lần kiểm kỹ thuật, không là bằng chứng stage.
4. Assessment hashes do code recompute bằng exact codec `digest` hiện hành. Đề nghị payload cố định: `source_sha256=digest({source_context_id,snapshot_id,archive_sha256,obligations})`, obligations là SourceRefs đầy đủ sorted theo input_pointer; `context_sha256=digest(result Model Record)` giữ row/Part/Issue associations; `diff_sha256=digest({elements,parts,rows,source_changed})` từ `impact(base,result)` như anchor a2; `closure_sha256=digest({before:delta.before.scope(),after:delta.after.scope()})`. `proof_sha256=digest({history_sha256,analysis_sha256,authority_binding_sha256,historical_reviews_pin,anchor_sha256,issue_roles,transitions,full_hold_reasons,stage_inventory})`, stage_inventory gồm sorted unit→`{work_completed_through,outputs,actual_output_ids}` đã được chứng minh. Không hash chính assessment/plan vào proof để tránh cycle. Không lấy hash shape đúng từ analysis/progress caller; AS-only diff rỗng vẫn tính từ hai contexts thực.
5. Adopt bắt đầu assessment chain H3: `parent_assessment_sha256=None` vì Config adopt bắt buộc parent_metadata null. Anchor provenance được pin riêng, không chuyển null đó thành thiếu stage proof. Revalidate parent_metadata bằng **actual promoted parent Admission**, parent assessment SHA mỗi unit bằng digest assessment của unit trong Admission ấy; không bằng một projection đã xóa assessments. Giữ parent chain để đọc lại mà không cần semantic authority.
6. Unresolved keys và full holds được tính lại từ canonical current Issues/typed selectors/unknown materialization và analysis đầy đủ. Result current/assessed_held chỉ khi có kiểm tương ứng; no-anchor existing-output vẫn needs_revalidation. `current` không thay semantic eligibility hoặc xác nhận người dùng. Không dùng null assessment để che một kiểm còn thiếu.

### 2.2 Config, reader và version dispatch

Config input checker cho B nhận parent_metadata có result assessments **chỉ sau khi** đối chiếu exact promoted parent plan qua checker B tương ứng. Binding `progress_before_sha256` pin full verified parent progress, gồm assessment hashes; retained-assessment hashes lấy từ cùng verified map. Anchor vẫn cần để chứng minh stage/output origin nếu chưa có verified H3 chain; metadata tự nhận current không đủ.

Reader B phân biệt input projection A với result Admission B; không chạy input-only equality trên newly assessed result, cũng không nới `_published_data` để nhận result có assessment null. Publisher checks actual config/raw/plan/Run/Records/events trước khi cấp transport capability. Revalidate/restart/finalized report đều theo cùng dispatch; chain phải có visited/cycle/depth checks trong shared Budget, không recursion không chặn.

Đề nghị bump **private Config/Plan/Admission semantics sang draft.3 cho B**, handler/package B riêng; field sets hiện có đủ diễn tả, không thêm canonical fields. Không diễn giải marker draft.2 thành semantics B. Giữ reader A/H2 lịch sử theo version gốc; unsupported marker fail closed. Exact marker/API choices này **chưa được chấp thuận** và không được dùng để viết plan/writer trước audit. Canonical E1/L1 registry/schema/A2/DB2 và receipt s02/2 giữ nguyên; registry protocol draft.1 và numeric caps giữ nguyên.

## 3. Không thay trust hoặc scope

Registry vẫn do invoker cấp trusted tuple ngoài DB trước mọi checked read; all-store R fixed, includes ancestors/other sessions; raw/hash/pins original trong T0 và seal. Assessment kỹ thuật mới không cấp historical HumanReviewEvidence. Finalized replay/report vẫn cần original registry, không semantic authority hoặc input files cũ, không ghi effects. Missing/tampered/superset registry fail closed, khôi phục original mới resume cùng identity; không upgrade registry pending.

T0 config/history snapshot được kiểm so với graph tại prepare. Lần load sau phải kiểm cả whole current store và exact immutable dependency slice đã pin tại T0, phân biệt chính prepared/log/finalized events của command mới với dependencies của intent; không refresh history pin theo head mới. Chi tiết thuật toán slice/correspondence phải có tests trước writer, không coi toàn current store tự bằng T0 sau khi append event.

## 4. Controls và gate audit đề nghị

| Control trước writer | Kỳ vọng độc lập |
| --- | --- |
| No-anchor existing outputs → adopt → finalized report → revalidate | Stage0 và same actual IDs xuyên chuỗi, held; mỗi checkpoint có actual result assessment/parent hash đúng, không build hoặc completed increment |
| Full H2 stage2 anchor → adopt → restart → revalidate | Stage2/outputs/aliases/raw refs nguyên; đúng result pair/hashes, assessment chain mới; bước2 vẫn không được chạy lại, bước3 chỉ thuộc C khi được giao |
| Missing/tampered/subset anchor hoặc omitted unit | Reject sai proof; thiếu proof giữ toàn outputs/unassessed/holds, không cấp stage mới |
| Forged result/current state, false assessment hashes, wrong parent assessment/base/result | Reject; summary/hash không thay canonical graph hoặc actual publication |
| Guard success/failure trên supported existing provenance | Chỉ AS/Issue được phép đổi; actual blockers giữ đúng, old A2 roots/obsolete/from/target và application counts không thay |
| Plan qua B checker → promoted publisher reader → Config revalidate checker | Round-trip được, không cần tự nới input checks A hoặc bỏ assessment requirement; exact bytes/pins/replay cùng identity |
| A2 original13/focused129/supplement8 | Giữ bytes/assertions; A2 acceptance không bị làm yếu để nhận B metadata |

Sau audit delta mới triển khai writer B và chạy **toàn S1–S6/E18/HR-P/E20/E21 theo §7.1**, cả AS-only and valid Model+AS opponents, OS-process races, T0/seal/T3 rollback/kill/lost ACK/unknown và registry restart. Matrix/fault gates không hoãn D. Lượt diagnostic này chưa có B writer, chưa các safety cases đó, chưa wheel/version B hoặc nghiệm thu B.

## 5. Quyết định cần auditor/người dùng chốt

**B-P01:** chấp thuận tách stage provenance khỏi result assessment; versioned pure B checker và parent chain semantics §2.1–2.2, field sets giữ và marker draft.3. Auditor kiểm invariants/compatibility cùng reproducible diagnostics; người dùng chốt delta sau audit. Nếu giữ API/semantics A a2 nguyên trạng cho mọi result, cần một phương án khác chứng minh được round-trip nêu trên trước writer, không bỏ kiểm hoặc âm thầm thay nghĩa.

H3-A a2 vẫn đã nghiệm thu đúng pure scope; đây là khoảng trống cho runtime B, không tự mở lại ba findings A đã đóng. D1–D5 và D01/D02 design-only, proposal/handoffs/seals lịch sử giữ byte. H3-C/D/CLI/live ngoài phạm vi.
