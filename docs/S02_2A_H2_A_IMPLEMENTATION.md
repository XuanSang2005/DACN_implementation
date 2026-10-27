# H2-A — pure scope policy

`dacn-s02 0.6.0a2` · **Đã được người dùng nghiệm thu kỹ thuật pure policy local/synthetic ngày 26/10/2026.** [Audit độc lập](acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/README.md) đóng S02-2A-H2-A-01/02/03; [biên bản](acceptance/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/S02_2A_H2_A_ACCEPTANCE.json) ghi riêng quyết định người dùng sau audit. [Phản hồi/bằng chứng lịch sử](../reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/FINDINGS_RESPONSE.md). Người dùng chấp thuận D1–D4 của [draft.2](S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md); [audit thiết kế](acceptance/s02-2a-h2-design-draft2-2026-10-25/README.md) đóng D01/D02 design-only. Proposal đã audit giữ nguyên byte. [Wheel/evidence gốc](../reports/s02-phase2/2a-h2-a-fixes-0.6.0a2-round1-2026-10-25/START_HERE.md). H2-B/C/H3 và pipeline H2 chưa nghiệm thu; H2-B cần giao việc riêng.

Phạm vi thực thi là các hàm thuần trên projection synthetic của cùng checked snapshot/SourceContext, fresh E1, bước 1–4. Không có command scoped, provider đọc file, bootstrap/handlers/writer H2 hoặc checkpoint H2. Không dùng kết quả này như nghiệm thu pipeline, xác nhận nghiệp vụ hay accepted_scope. H1 a2 và cơ chế DB2 không đổi.

## API và thứ tự caller phải tuân thủ

| Module mới | Trách nhiệm |
| --- | --- |
| `h2_limits` | Budget chung invocation, lexical/structure/occurrence/byte bounds, deadline cooperative; không I/O |
| `h2_contracts` | SourceInventory requirement family + mọi criterion FR/NFR/constraint; HoldSelector; BindingRequest; AnalysisEvidence; typed external AuthorityContext/Grant; ConstructionPermit |
| `h2_graph` | ModelContext detached; context identity Part + toàn mapping row chứa nó; closure, reverse_impact và impact trên base/candidate |
| `h2_candidates` | Projection candidate đóng/typed handles/read allowlist/sources/full inventory; không cấp IDs hay dựng Model |
| `h2_policy` | materialize selector, admit trước/sau Parts và assess_union của full built candidate; trả Admission, không sửa Records |

Caller tạo **một Budget** và dùng chung SourceInventory/ModelContext/contracts/candidate/policy. Checked S01 lookup, E1 owner/history/Run/Change/AS lineage phải do verifier hiện có kiểm trước; shape/local refs ở đây không thay checked lookup hoặc whole-graph verification. Context giữ bản copy để tách khỏi input ban đầu; caller không được sửa index/body hoặc Budget nội bộ giữa các lần kiểm.

Trình tự dự kiến cho caller H2-B: checked lookup → inventory/current Model+AS+Issues → selectors code-owned → closed candidate và analysis → exact binding + authority bên ngoài → `admit` → builder giữ raw-to-result fidelity → `assess_union` → whole graph + publication/CAS. H2-A kiểm các hàm thuần trong chuỗi này; builder/publisher chưa có. `admit` riêng không phải validator candidate, `parse_candidate` riêng không phải authority hoặc admission. Composite test ghim cùng exact raw bytes qua cả ba phép kiểm, nhưng built Model vẫn là fixture độc lập, không phải handler H2 đã chạy.

Private versions theo draft.2: `s02-h2-work`, `s02-h2-hold`, `s02-h2-analysis`, `s02-h2-candidate`, `s02-h2-scope-rules`, `s02-h2-local-limits` cùng hậu tố `/0.1.0-draft.2`. Không đăng ký schema canonical mới. Admission/Footprint là kết quả Python; AdmissionManifest/progress/config/plan persistence thuộc H2-B. Candidate request hash bỏ bốn raw hash/length slots để tránh vòng self-hash; BindingRequest đầy đủ vẫn pin cả candidate lẫn analysis raw.

## Invariants được kiểm thuần

- Unit là requirement family với toàn criteria, dùng snapshot+pointer; full inventory giữ cả constraint/NFR/unknowns. Không chia Part/action để né blocker.
- Selector logic tồn tại cả khi graph rỗng và materialize lại khi graph lớn. Unknown impact dùng all_source_uses. Current Issue ID/key và AS phải khớp; không thu nhỏ canonical blocking/source refs.
- Mỗi Part phát hiện mở **mọi action_ids**, lặp qua mappings/workflow mọi nhánh reachable/Support tới fixed point. Support chưa rõ hoặc branch chưa xác định giữ undetermined. Dùng chung component/responsibility/data/actor chưa tự kéo mọi actions; blocker explicit trên context đó vẫn áp dụng.
- Part semantic context bao gồm row ID/source_ref/assessment/issue links/membership. Swap nguồn, chuyển Part, thay membership/removed relationship được xét trên cả hai graph. Revision pin và set order không tự thành đổi nghĩa; giữ thứ tự criteria/workflow như draft.2.
- Evidence usable phải inspected, có basis, không missing facts; disjoint scope cần independence pair với hold và inventory đầy đủ. Grant allow chỉ cấp quyền dùng evidence synthetic, không tự chứng minh independence.
- Không nhận trusted=true/authority trong candidate/analysis. AuthorityGrant và AuthorityContext là input caller tin cậy riêng; binding pin Model+AS/source/units/selectors/progress/retained basis/raw/policy/control hash. Unavailable/deny/mismatch giữ blocked hoặc từ chối contract.
- ConstructionPermit là projection provenance **caller đã kiểm**, không suy từ role/pending-mapping hoặc Issue cũ. Chỉ đúng verification task/key/origin command/target/unit mới được dựng task đó. Không resolve Issue, miễn business/gap holds hay tự tạo review.
- Responsibility coverage, initiator unknown, existing Part gap và final mapping coverage giữ gate. AS-only/Issue-ID rebinding chưa được publish ở A.
- Trước build, reclose hợp units đã qua gate riêng để không lan lỗi U sang V; footprint vẫn giữ toàn request. Hợp kết quả được closure lại từ source seeds, không cộng pass flags. Meaningful impact trên cả base/candidate phải nằm trong quyền causal của base, không dùng Part/workflow mới để tự mở quyền; membership Responsibility thay đổi mở các actions được assign trong reverse impact, context dùng chung không đổi vẫn không kéo mọi actions. Candidate append-only; row proposed cũ/nguồn/kết quả cũ không được sửa. Một selected unit fail sau ghép ⇒ `guard_required`, không cắt candidate lấy phần pass. Guard chỉ là outcome cần caller B xử lý; A không tạo guard AS.

## Limits và lỗi

Draft.2 caps: candidate+analysis raw tổng 1 MiB; authority raw 1 MiB; serialized config 2 MiB; plan 16 MiB; depth 64; values 100.000; UTF-8/string 64 KiB; references **50.000 occurrences**; obligations 1.000; entities/nodes 2.000; edges/Parts 4.000; findings 500; Issues 2.000; compute 30 giây mỗi invocation. Có thể hạ caps để thử boundary, không tăng. Cap kết quả kiểm toàn candidate Model + current Issues trước union success, ngoài input totals và footprint bounds; không reset Budget hoặc truncate. `Budget.serialized` kiểm config/plan khi caller cung cấp; A không tạo chúng. Authority byte bound là primitive, chưa chứng minh file read/provider lifecycle.

Input slot có tên cho cùng request/analysis/candidate/selector chỉ tính một lần khi cùng bytes; đổi bytes trong slot bị từ chối. Anonymous inputs vẫn cộng dồn từng occurrence. Parse khác Budget không né aggregate check của policy. Cache không reset deadline. Deadline cooperative kiểm trong traversal, không hard timeout I/O; invocation resume mới có budget mới nhưng A chưa triển khai resume/sealed plan.

Contract/limits sai trả S02Error `H2_CONTRACT_INVALID` / `H2_LOCAL_LIMIT`. Admission có allowed/blocked units, materialized holds, footprint, reason_codes và global_blocked. Footprint vẫn mô tả toàn request, gồm units bị chặn, nên không là quyền ghi chúng. Pre-build có thể chọn lại chỉ V bằng work tuple/analysis/grant ghim đúng unit set mới; không cắt candidate U+V đã dựng hoặc dùng binding U+V như binding V. Caller/pipeline thực hiện việc này thuộc B. Stale/authority thiếu thường trả blocked để caller giữ hold; shape/refs/schema sai bị reject. Không CLI/exit code H2 trong A.

## Phần chưa chứng minh

Chưa có provider file matching/cấp lại ở process mới; finalized provenance lookup cho ConstructionPermit; raw-to-builder fidelity/ID allocation; current Issue successor rebinding; scoped bootstrap/receipt/seal/progress/revalidation guard lifecycle; CAS/concurrency/crash/lost ACK/stale pipeline H2. H1 regression chỉ bảo toàn baseline, không chứng minh chúng cho H2. Các phần này thuộc H2-B được giao riêng; stress H2-C không thay correctness gate writer đầu tiên. Không H3, Answer/A2 history, LLM, renderer, operational store hoặc live.

Auditor đã chốt [erratum oracle limits](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-a-0.6.0a2-round1-2026-10-26/ORACLE_ERRATUM.md): file gốc dùng `.value.code`, trong khi error API đã pin là `.value.error["code"]`. Corrected oracle chỉ đổi accessor, đạt 4/4 cases mỗi backend trên a2; a1 vẫn 2 fail + 2 pass. Source/error API, oracle gốc và raw failures a2 (2 accessor fail + 2 pass/backend) giữ nguyên; kết quả corrected là kiểm độc lập do auditor chạy, không phải diagnostic replay của implementation hay application tests mới trong lượt tài liệu này.
