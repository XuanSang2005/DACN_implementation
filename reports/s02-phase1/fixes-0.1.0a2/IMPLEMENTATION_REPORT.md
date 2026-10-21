# Sửa audit S02 Đợt 1 — 0.1.0a2

Ngày 19/10/2026. **Bản sửa chờ audit lại; chưa nghiệm thu Đợt 1, chưa chuyển Đợt 2.** S01 `0.1.0a6` giữ nguyên trạng thái nghiệm thu kỹ thuật đã có. Báo cáo này xử lý riêng S02-01–S02-04 của [audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a1-2026-10-19/AUDIT_REPORT.md); không tự đóng findings thay agent audit.

## Căn cứ và kiểm baseline

Đã đọc `AGENTS.md`, contract/plan S02 draft.3, code/tests nền tảng, báo cáo bàn giao a1, audit và bảy tests tái hiện. Contract áp dụng vẫn **s02/0.1.0-draft.3**, DB structure **1**; không sửa tài liệu contract, schema input S01, AGENTS hoặc dataset.

[Baseline đầu lượt](baseline.json) xác nhận package cài S02 a1 khớp source/wheel **14 file**, S01 a6 khớp **16 file**. CPython **3.13.16 GIL**, SQLite **3.53.1**, simplejson **4.2.0**, jsonschema **4.26.0**, pytest **9.1.1**; không đổi dependencies/runtime. 198 file của inventory trước vẫn khớp. Inventory bảo vệ **mới** gồm 3.492 file được liệt kê, mở rộng cả báo cáo/wheel cũ, tài liệu và artifacts audit được đọc, kể cả các file môi trường audit có trong thư mục đó. Đây không phải tuyên bố kiểm toàn filesystem/dataset.

Bảy ca audit chạy lại trên package a1 đã cài, từ ngoài checkout: **7 failed/backend C và Python**, exit 1 do assertions đúng các findings, không setup error. Xem [lệnh trước sửa](before/audit-commands.json), [C](before/audit-c.log), [Python](before/audit-python.log), JUnit cùng thư mục. Khi chạy này source bắt đầu sửa nhưng production import vẫn từ wheel a1 đã cài; tests không đưa source vào PYTHONPATH.

## Sửa từng finding

| Finding | Thay đổi và invariant được thực thi | Bằng chứng chính |
| --- | --- | --- |
| S02-01 | EventRef của record phải thuộc cùng session. Issue resolved có Answer chỉ nhận `application_applied`, đúng `resolved_issue_id`, Answer cùng issue lineage, Change backlink/model; Answer được áp dụng phải có trong `answer_ids`. Resolved không Answer giữ nhánh source-only: SourceRefs + resolution, events rỗng. | Ca audit prepared; regression sai Issue/Answer/backlink/session; positive source-only và application thực sự commit |
| S02-02 | Application đọc **base AnalysisSet đã pin**, tìm đúng một Issue theo request.issue_key. Issue kết quả cùng key, supersedes đúng phiên bản đang chọn (open/pending). Answer.issue_id phải là chính phiên bản đó hoặc tổ tiên qua supersedes; không nối bằng text/key đơn thuần. Change giữ current Issue trong nguồn; Run.result_analysis_set_id phải chọn resolved Issue của đúng model kết quả. | Sai key, không được chọn, sai parent/nhánh; pending successor của Issue lúc nhận Answer; lịch sử vẫn verify sau khi AnalysisSet mới hơn xuất hiện |
| S02-03 | Trước xét functional seeds, gate từ chối cấp phạm vi nếu **bất kỳ mapping row** thiếu Parts hoặc còn `not_assessed`, gồm requirement và criterion của FR/NFR/constraint. Reason `MAPPING_NOT_ASSESSED`, `NO_ALLOWED_FUNCTIONAL_SCOPE`; allowed rỗng, blocked liệt kê actions/Parts thực có. Không tạo Part giả hoặc diễn giải Scope rỗng là global. | Sáu tổ hợp FR/NFR/constraint × requirement/criterion, checked store vẫn hợp lệ; audit constraint empty-parts bị chặn; toàn bộ positive closure/global/partial-scope cũ giữ nguyên |
| S02-04 | T3 chỉ ghi đúng một Attempt cho một dispatch của command; ID trùng T0, transport trùng T1. Prompt/request trỏ chính Artifact promote từ StageRef đã pin (hoặc prompt reuse có pin T0). Response trỏ Artifact từ capture; requested/returned model, provider_response_id, usage và elapsed_ms phải bằng T2, kể cả null. Không thay metadata sau capture bằng suy đoán/parser chưa kiểm. Không dispatch thì không có Attempt; không capture thì response/returned metadata/usage phải null và trạng thái phù hợp unknown/transport/stale. | Ba ca audit; từng metadata field riêng; Artifact khác ID dù cùng purpose/bytes bị từ chối; inventory Attempt; completed/refused/invalid/incomplete/stale synthetic, unknown/transport outcome, prompt reuse |

Các kiểm này chạy trong `_check` trước commit **và** checked reads. Không chỉ lọc lúc submit rồi tin dữ liệu đã lưu. Với application, “current” là selection của base/result đúng lần áp dụng, không dùng head mới nhất để vô hiệu lịch sử đúng đã commit.

## Transaction, lưu trữ và tương thích

Không đổi DDL, CAS head/claim, unique applied, immutable triggers, staging/BLOB, rollback hoặc quy tắc đối soát commit. `_check` sau insert và trước COMMIT thấy đủ vòng refs event–Issue–Change–Run–AnalysisSet; vi phạm phát sinh `SCHEMA_INVARIANT / schema` có invariant cụ thể và rollback toàn batch. Checked read một lịch sử sai trả `PERSISTENCE_FAILED`, không reset hoặc sửa nó. Không công bố Model/AnalysisSet/Issue/applied event/Run thành công từ batch lỗi.

S02-04 thêm **chi tiết giao thức nội bộ** `prepare(..., reused_artifact_ids=())`: khi cần reuse prompt/config đã tồn tại, T0 ghi danh sách ID trong payload `prepared`. Field optional, thiếu nghĩa không có pin reuse; a1 histories không phải thêm field. IDs được kiểm loại/purpose/session, typed links và immutable Artifact trước khi T0 commit. Prompt mới/request mới vẫn staging; T3 không được tự chọn Artifact cùng purpose thay pin. Config có pin trong prepared/request cũng phải khớp Run. Record/Attempt, input S01 và contract văn bản không đổi.

Đây là cách hiện thực reuse được §4.3 cho phép, cần audit cả schema materialized, typed links và API nội bộ mới. DDL version không tăng vì không đổi bảng/index/triggers. Reader a2 đọc được lịch sử a1 hợp lệ; **không cam kết downgrade** a1 đọc payload mới có reuse pin. Không tự migrate các DB sai do a1 đã tạo; giữ kho gốc làm bằng chứng, không khẳng định cách khôi phục nghiệp vụ ngoài phạm vi sửa này.

Gate nhận Model đã qua kiểm cấu trúc/inventory với snapshot: thiếu toàn bộ row vẫn là lỗi của validator Model. Model trung gian có row nhưng thiếu Parts vẫn được lưu; chỉ bị chặn khi xin scope. Applicability chưa biết không được coi là miễn nghĩa vụ. Mã reason không tự thêm ID mới vào Scope; muốn thấy nghĩa vụ chưa phân tích thì tra các Mapping rows của model đã pin.

## Files thay đổi

[code-changes.json](code-changes.json) ghi hashes trước/sau của **12 file** (10 sửa, 2 mới):

- `s02/src/dacn_s02/validation.py`: kiểm resolution evidence và cùng session.
- `events.py`: kiểm current Issue/lineage/result selection; bind Attempt với T0/T1/T2 và pin config.
- `repository.py`: truyền commands cùng session khi kiểm record; lưu reuse pin tại T0.
- `scope.py`: chặn readiness của mapping chưa đánh giá.
- `schemas/contract.json`, `s02/tools/materialize_schema.py`: trường reuse optional của prepared, không đổi schema nghiệp vụ Record/Attempt.
- `s02/pyproject.toml`, `s02/src/dacn_s02/__init__.py`: version `0.1.0a2`.
- `s02/tests/test_audit_regressions.py`: bảy ca audit chuyển thành regression portable; thêm oracle rollback logical DB image.
- `s02/tests/test_audit_guards.py`: 41 ca bổ sung cho negative/positive/checked-read và requirement/criterion readiness.
- `s02/tools/run_checks.py`, `collect_evidence.py`: bắt buộc chỉ rõ thư mục báo cáo để không ghi đè a1; JUnit, chạy audit ngoài, chọn wheel version và đối chiếu đầy đủ inventory package cài.

Không sửa/xóa/skip/nới kỳ vọng các tests S01 hoặc 141 tests S02 cũ. Báo cáo và wheel a1 giữ nguyên; report mới nằm trong thư mục này, wheel mới nằm ở `s02/dist/`.

## Kiểm thử và bằng chứng

Kết quả cuối từ wheel cài vào **venv mới**, ngoài checkout, ghi ở [TEST_RESULTS.md](TEST_RESULTS.md), [execution-summary.json](execution-summary.json). [Hướng dẫn tái lập](REPRODUCE.md) kèm lệnh chính xác, exit code, JUnit, instrumentation C/Python và logs. Tests mới dùng synthetic fixtures, không dữ liệu nghiệp vụ/dataset cuối; không gọi LLM/provider thật.

- Bảy regression gốc cộng kiểm negative mới so sánh logical DB image trước/sau lỗi bằng SQLite dump, sau đó checked verify qua Repository mới. Không chỉ assert “có exception”.
- Sáu ca fault injection tạo lịch sử sai bằng cách tạm vô hiệu **chỉ validator trong fixture**, khôi phục trước reopen; checked read phải từ chối. Đây là mô phỏng corrupted/unchecked history, không phải báo API sản phẩm đã chấp nhận dữ liệu đó.
- [legacy-store-results.json](legacy-store-results.json): chạy reader a2 trên **bản sao tạm** DB a1 thật trong audit. 12 lịch sử sai bị từ chối; hai model intermediate của finding 03 vẫn verify nhưng gate từ chối; 18 DB race/kill hợp lệ của a1 còn đọc được. Nguồn audit không bị thay đổi. [Probe thực chạy](check_legacy_stores.py).
- Các lịch CAS/cạnh tranh/real-lock/kill/recovery nằm trong full suite cũ, chạy lại từ wheel a2; logs và DB race/kill mới nằm ở `process-artifacts/`. Không thay các lịch đó bằng tuần tự hoặc sleep.
- Lượt phát triển đầu có **188 passed, 1 failed/backend** do fixture mới import nhầm `S01Adapter` không tồn tại; đã sửa fixture sang `Service.start` thật, giữ log `development/`. Đây không phải kết quả đạt. Lượt targeted sau sửa **48 passed** C; full suites cuối mới là bằng chứng bàn giao.

## Giới hạn và nội dung cần audit lại

1. Bốn finding cần agent audit xác nhận trên đúng wheel a2; implementation không tự ghi trạng thái closed/accepted.
2. Review tính đầy đủ của Issue–Answer–Change–event–selected AnalysisSet, gồm successor qua pending và historical lookup sau head tiến lên; kiểm rollback và từ chối DB sai khi reopen.
3. Review readiness bảo thủ của mọi requirement/criterion chưa có Parts; vẫn cho lưu phân tích dở dang, không biến scope rỗng thành global hoặc tự miễn constraint.
4. Review pin reuse T0 và ràng buộc từng capture field. Không có post-capture enrichment; null giữ null. `provider`, `step`, `repair_round` là khai báo của code gọi nội bộ, không có fact tương ứng trong event T2 hiện hành để đối chiếu; các tests replay không chứng minh đã gọi provider. Khi làm adapter Đợt 2 cần cung cấp các khai báo này từ cấu hình/dispatcher đáng tin cậy, không từ output LLM. Bản sửa này không thêm provider parser hoặc suy metadata từ raw response.
5. Không chạy LLM, full clarification/S01 update, renderer, full review/handoff workflow, KB/S03, đánh giá ngữ nghĩa hoặc benchmark. Không thêm bằng chứng durability mất điện/disk-full. Races, kill và fault injection không chứng minh các tình huống đó.

**S02 Đợt 1 — bản sửa 0.1.0a2 đã implement và kiểm thử, chờ audit lại; chưa nghiệm thu S02 và chưa chuyển Đợt 2.**
