# Đáp ứng audit S02 draft.1 → draft.2

**proposed — chưa audit lại/chưa được duyệt** · Astra · 18/10/2026.

Đã sửa proposal theo F01–F05, chưa implement S02. Contract hiện là `s02/0.1.0-draft.2`, kế hoạch `s02-plan/0.1.0-draft.2`. Đây là báo cáo của bên biên soạn, **không phải kết luận auditor đã đóng finding** hoặc nghiệm thu S02.

## 1. Căn cứ và giới hạn

Đã đọc [audit draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft1-2026-10-18/AUDIT_REPORT.md), `static-checks.json`, `counterexample-traces.json`, `audit-evidence.json` cùng thư mục; AGENTS, hai proposal và bốn ví dụ cũ. Hash bảy đầu vào được audit (AGENTS, hai proposal, bốn JSON) khớp bằng chứng audit tại đầu lượt sửa. Không ghi đè một phiên bản khác chưa hiểu.

Giữ flow chín bước; bước 6 vẫn phân tích characteristics/đề xuất, bước 7 mới áp dụng; bước 8 giữ 8.1–8.5; không mở rộng S03. Baseline S01 `0.1.0a6`, schema `1.0.0`, output `0.1.0-draft.2`, DB structure `1` không đổi. Không sửa AGENTS, implementation, tests, dependencies, tài liệu S01, dataset, LaTeX/PDF hoặc audit/report nguồn.

Các quyết định dưới đây là **phương án Astra đã chọn để đưa audit lại**, không để implementation tùy chọn giữa nhiều ngữ nghĩa. Model/API/giá/toolchain giữ căn cứ tra cứu lịch sử của draft.1; lượt này không tra cứu mới hoặc thử khả năng dịch vụ.

## 2. Finding → quyết định → minh họa

| Finding | Quyết định sửa và trade-off | File/vị trí | Ví dụ / expected outcome |
| --- | --- | --- | --- |
| F01 | AnalysisSet bất biến, head và revision riêng; Scenario/Characteristic có analysis_key/supersedes, Issue giữ issue_key. Validation/Bundle pin set; CAS cặp model/set. Mọi đổi set làm gói cũ stale; log/review không đổi set. Bản đầu yêu cầu review mới, **không carry approval một phần**; đổi lại có thể phải review nhiều hơn. | [Contract §6.1](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:175), §8–9; [plan §4](/Users/macbookpro/Documents/DACN_implementation/docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md:71), §6,8–9 | [File05](examples/s02/05-analysis-freshness.json), `/scenarios/1` issue mới và `/scenarios/2` characteristic successor: M1 giữ nguyên nhưng handoff B1 `ANALYSIS_STALE`, allowed rỗng. `/scenarios/3` log-only: không invalidate. `/scenarios/4` nêu thứ tự publish/handoff/CAS, chưa chạy concurrency. |
| F02 | Staging BLOB theo operation đã commit; chưa là Artifact. T0 prepare → T1 dispatch intent → T2 capture → T3 promote Artifact/Run/Attempt cùng transaction. Giữ producer_run_id invariant, không nullable workaround/FK xuyên transaction; giữ staging để audit nên tốn thêm lưu trữ. | [Contract §4.3](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:91), §4.1; plan §4,6,8 | [File06](examples/s02/06-artifact-lifecycle.json), `/scenarios/0` đến `/scenarios/3`: prepared chưa dispatch, captured chưa final, invalid response vẫn giữ bytes, dispatch_unknown không tự resend. Planned IDs không được coi là FK tới record đã commit. |
| F03 | Answer giữ nguyên text/interpretation lúc nhận; bỏ hai nullable result links khỏi Answer. Typed operation events nối diễn giải được chọn, consent exact input/hash/request, S01 run đã biết, quan sát kết quả và application_applied. CAS claim một application/Answer, tối đa một applied/Answer; recovery không tạo câu trả lời mới. Command tiếp nối giữ lineage, S01 outcome và không resend khi committed/unknown. | [Contract §4.4](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:108), §7; plan §4,6,8–9 | [File07](examples/s02/07-answer-application.json), `/scenarios/1/timeline`: Answer pending → consent **giả định** → S01 run-demo-006 commit → S02 crash → lookup đúng run → source switch/Change/Issue successor/event cùng commit. Answer vẫn needs_interpretation ban đầu; effective interpretation qua event. Chỉ Q-priority giả định resolved; Q-cancel vẫn chưa rõ, reanalysis còn pending, handoff false. |
| F04 | Part.action_ids; Workflow.branch_points và review workflow_choices; Dependency.Support theo action với prerequisite IDs/null. Closure duyệt workflow từ entry, prerequisites và dependencies đến fixed point; unknown không được chọn hẹp; chu trình không bị bỏ. Mọi part system phải review cho slice. Không kéo mọi action của shared component/interface. Bản đầu bảo thủ khi chưa chứng minh độc lập. | [Contract §5](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:127), [§9.1](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:236); plan §6,8–10 | [File08](examples/s02/08-scope-closure.json), `/scenarios/0` đến `/scenarios/6`: A2 trước A1 kéo A1 blocked; exclusive đã review cho phép nhánh độc lập; unknown choice lỗi; nhiều tầng/SCC giữ blocker; shared use A2 không chặn use A1 nhưng whole-interface issue chặn cả hai; global nghĩa vụ chưa review chặn functional slice. |
| F05 | Quy tắc actor/initiator rõ: unknown/internal + actors rỗng; external + actors không rỗng. Vi phạm dùng `SCHEMA_INVARIANT/schema`, details.invariant=`action_initiator_actors`. ID hợp lệ và initiator nhất quán không chứng minh quyền. | Contract §5,11; plan §8.1; [file04](examples/s02/04-review-and-rejection-scenarios.json) | `/scenarios/2/cases/6`: unknown + [A01] bị chặn cấu trúc. `/scenarios/2/cases/7`: external + [A01] có thể qua cấu trúc nhưng suy quyền hủy vô nguồn; semantic review phải phát hiện, Q-cancel vẫn open và OP02 chưa được phép handoff. |

Các scenario là diễn biến và **kết quả mong đợi**, không log ứng dụng. File07 không ghi nhận người dùng thật đã trả lời/duyệt priority. Biến thể priority chỉ đối chiếu JSON S01 minh họa đã có. File08 là graph projections synthetic để diễn đạt closure, thiếu các trường không liên quan có chủ đích; không phải Model export production có thể import.

## 3. Files thay đổi và thêm

| File | Thay đổi |
| --- | --- |
| [S02_OUTPUT_CONTRACT_PROPOSAL.md](S02_OUTPUT_CONTRACT_PROPOSAL.md) | Draft.2: fields, identity/current set, staging/applications, closure/gates, errors, lifecycle và links ví dụ đồng bộ. |
| [S02_IMPLEMENTATION_PLAN_PROPOSAL.md](S02_IMPLEMENTATION_PLAN_PROPOSAL.md) | Draft.2: bảng lưu trữ thiết kế, transaction/recovery, CLI dự kiến, kế hoạch kiểm thử/phases phù hợp F01–F05. Không tạo DDL/code. |
| [01-source-and-model.json](examples/s02/01-source-and-model.json) | Version, Run context/operation, Part.action_ids, Dependency.Support, branch_points, Issue result links và initial AnalysisSet. Giữ input nghiệp vụ/unknowns. |
| [02-analysis-and-review-package.json](examples/s02/02-analysis-and-review-package.json) | Analysis keys/supersession, current AnalysisSet, Validation/Bundle/Handoff pin set; vẫn preparing/not_run. |
| [03-revision-scenarios.json](examples/s02/03-revision-scenarios.json) | Version/base set, Change event refs; định nghĩa ID tương lai bằng descriptors/hypothetical snapshot, không giả làm commit thật. |
| [04-review-and-rejection-scenarios.json](examples/s02/04-review-and-rejection-scenarios.json) | Version, set/branch choices, preconditions closure, định nghĩa review/bundle giả định và tách F05. |
| [05-analysis-freshness.json](examples/s02/05-analysis-freshness.json) | Mới: freshness cùng model, successor và log-only, thứ tự cạnh tranh dự kiến. |
| [06-artifact-lifecycle.json](examples/s02/06-artifact-lifecycle.json) | Mới: commit boundaries, exact staged bytes/hash, dữ liệu chưa commit và external unknown. |
| [07-answer-application.json](examples/s02/07-answer-application.json) | Mới: lời/consent giả định và chuỗi application/recovery/issue resolution bất biến. |
| [08-scope-closure.json](examples/s02/08-scope-closure.json) | Mới: bảy graph projections synthetic, expected required/allowed/blocked scope. |
| [S02_DRAFT2_AUDIT_RESPONSE.md](S02_DRAFT2_AUDIT_RESPONSE.md) | Báo cáo này. |
| [S02_DRAFT2_STATIC_CHECKS.json](S02_DRAFT2_STATIC_CHECKS.json) | Mới: bằng chứng kiểm tra tài liệu, hash deliverables và inventory 179 file bảo vệ với before/after; không phải config/schema/test script thực thi. |

## 4. Kiểm tra tĩnh đã thực hiện

Dùng Python stdlib ở chế độ `-B`, qua các đoạn kiểm tra ad hoc trong phiên, chỉ đọc JSON/Markdown và đối chiếu đường dẫn/IDs/hash. Không import/chạy service, validator hoặc tests S01/S02. Không lưu một script kiểm thử trong codebase.

| Kiểm tra | Kết quả thực của artifacts |
| --- | --- |
| JSON parse + duplicate-key rejection + version/nhãn minh họa | 8/8 JSON đọc được, không key trùng, exact `s02/0.1.0-draft.2`. |
| Field inventory của full Record definitions | 33 định nghĩa đúng tập fields được kiểm, gồm 17 top-level records và 16 định nghĩa trong scenario; không phải 33 records đã commit. |
| Bindings file/JSON Pointer | 105 resolve; gồm references tới descriptors giả định được ghi type riêng, không coi chúng là production records. |
| SourceRef / AnswerRef / ElementRef | 93 / 1 / 8 resolve; refs của model tương lai đối chiếu base descriptor, chưa chứng minh model tương lai đã materialize hợp lệ. |
| EventRef / StageRef / staged bytes | 20 / 21 resolve; 15 staged payloads có byte length và SHA-256 đúng bytes minh họa. |
| Mutation pointers / scenario pointer | 10 / 1 resolve tới vị trí gốc. Giá trị C-missing, source index99 và phiên bản lệch là **negative variants có chủ đích**, không được báo như output hợp lệ. |
| AnalysisSet / Bundle pin | 7 set definitions kiểm model/revision/parent/key-selection; Bundle chuẩn bị pin đúng set/Validation/lists. Expected stale/log-only phù hợp quy tắc đã chọn. |
| Scope trong full records | 40 Scope objects resolve đúng model/part IDs. Đây không phải phép chứng minh độc lập ngữ nghĩa. |
| Clinic mapping/model | 15 rows = 5 requirements + 10 criteria; 16 parts có action scope; 24 nhóm typed refs, 2 Support entries và 4 workflows kiểm liên kết. |
| Synthetic graph links | 7 graphs kiểm node/edge/entry/action/part/component/interface/Support và các ID trong expected scope; allowed/blocked parts không giao nhau. Đối chiếu diễn biến dự kiến với §9.1, chưa chạy thuật toán S02. |
| F05 | Hai biến thể có kỳ vọng tách biệt; Q-cancel trong record minh họa vẫn open. |

Các phép kiểm kết thúc thành công được ghi trong JSON bằng chứng. Một truy vấn chẩn đoán ban đầu dùng selector quá rộng gặp Binding có type=issue nhưng không có body; đã sửa selector chỉ xét Record. Đây là lỗi của truy vấn kiểm tài liệu, không phải lỗi S02 hoặc lý do sửa nội dung nghiệp vụ. Không dùng số lượng các checks làm bằng chứng chất lượng thiết kế hoặc nghĩa vụ nghiệp vụ.

**Chưa thực hiện:** implementation, runtime schema/DDL, tests ứng dụng/concurrency/fault/DB thật, tạo DB/source/snapshot thực, cài deps, gọi LLM, renderer, benchmark/evaluation dataset, hoặc Git. Chưa xác minh live API/model/toolchain. Những bảng kiểm thử trong plan vẫn là kế hoạch; các lịch crash/race là minh họa. Chưa có auditor độc lập review draft.2.

## 5. Inventory và bảo vệ trước–sau

Baseline mới được lấy **đầu lượt này, trước sửa**, lúc `2026-10-18T13:55:14.139610+00:00`; đối chiếu sau lúc `2026-10-18T14:12:44.033836+00:00`. **179/179 file cùng inventory và cùng SHA-256; không thêm/mất file trong tập chọn.** Xem đầy đủ từng đường dẫn tuyệt đối + before/after hash trong [JSON bằng chứng](S02_DRAFT2_STATIC_CHECKS.json), trường `protected_files`.

| Tập kiểm thực tế | Số file |
| --- | ---: |
| Root regular files (gồm AGENTS, pyproject, version/locks/in/gitignore) | 9 |
| src (package S01 và metadata egg-info; không cache) | 21 |
| tests (không cache) / tools | 20 / 12 |
| reports S01 / dist wheels S01 | 84 / 6 |
| docs S01 và ví dụ S01, không S02 | 10 |
| External output/pdf / outputs/system-input-v1 | 7 / 5 |
| Bốn file audit S02 draft.1 / S01_ACCEPTANCE.json | 4 / 1 |
| Tổng | **179** |

Quy tắc chọn: root files trực tiếp; toàn regular files trong src/tests/tools/reports/dist trừ __pycache__/.pytest_cache; docs trừ tên `S02*` và thư mục `s02`; regular files trong ba thư mục external đã nêu và S01_ACCEPTANCE. Inventory cụ thể mới là tập có bằng chứng, không tuyên bố mọi file trên máy được hash. Không quét venv/runtime/tool downloads/caches hoặc toàn dataset ngoài các tài liệu tham chiếu kể trên. Không dùng lại con số187 của lượt trước.

## 6. Điểm cần audit lại và quyết định còn mở

- Review F01: chấp nhận chính sách toàn gói stale khi đổi AnalysisSet; phân biệt set/model/sequence và checked handoff sau công bố mới. Reuse phân tích độc lập không đồng nghĩa carry approval.
- Review F02/F03: các typed refs/FK tại mỗi commit, staging promotion, recovery command lineage, application claim/unique-applied và consent exact bytes; kiểm eventual implementation không tạo Run/Artifact giả sớm hoặc gửi S01/LLM lặp khi outcome unknown.
- Review F04/F05: độ đủ của Part.action_ids, branch choices và Support; tính bảo thủ của mọi system parts; structural actor invariant không thay semantic review quyền. Không để nguồn nghĩa vụ thiếu bị “sửa” bằng suy luận cho graph dễ vượt gate.
- Những quyết định kỹ thuật/ngân sách còn chờ từ draft.1: exact toolchain/escape/fidelity probe; quyền dữ liệu/API và model pilot; budget/giới hạn; tập phát triển/heldout, rubric/người chấm và số runs. Không coi các đề xuất này đã được duyệt qua việc sửa F01–F05.
- AGENTS hiện giữ đúng flow và trạng thái proposal chi tiết chưa chốt; **không cần sửa để thực hiện lượt tài liệu này**. Sau khi draft được duyệt, đề nghị đồng bộ tham chiếu version contract/plan và quy tắc set/application/closure có hiệu lực trong một lượt được giao; chưa áp dụng thay đổi đó.

**Draft.2 vẫn proposed, đang chờ audit lại; chưa implement S02.**
