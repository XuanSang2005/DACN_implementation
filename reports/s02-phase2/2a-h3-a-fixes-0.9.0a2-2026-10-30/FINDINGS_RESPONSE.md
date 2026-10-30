# Phản hồi ba findings — implementer, chưa tự đóng

Vị trí source: [h3_bindings](../../../packages/s02/src/dacn_s02/h3_bindings.py), [h3_policy](../../../packages/s02/src/dacn_s02/h3_policy.py), [h3_limits](../../../packages/s02/src/dacn_s02/h3_limits.py), [controls mới](../../../packages/s02/tests/test_h3_a_fixes.py), [Plan fixture/negative](../../../packages/s02/tests/test_h3_a_contracts.py).

Căn cứ audit a1: focused99 pass/backend nhưng oracle độc lập13 có8 fail/5 pass/backend C/Python; không harness error. A1 supporting full1076/986 của implementer giữ lịch sử. Oracles/replay/fixtures/assertions tại audit a1 giữ nguyên byte và chỉ replay vào output mới.

| Finding (vẫn OPEN chờ auditor) | Sửa và vị trí | Controls mới / hồi quy |
| --- | --- | --- |
| S02-2A-H3-A-01 | `h3_bindings._published/_output_origin/check_anchor/_checked_progress/check_admission/check_config/check_plan`: finalized/promoted provenance, complete output inventory, actual assessment chain; `h3_policy.admit`: no-anchor existing-output build hold | `test_h3_a_fixes`: valid full stage2 anchor, step2 không được làm lại/step3 được phép; raw/origin/prefix/duplicate negative; Config inspect được nhưng build held; unit không output bước1 được phép; actual AS-only guard transition với base/result hashes đúng được transport stage2 nhưng vẫn needs_revalidation/held, hash sai reject. Hai oracle progress/anchor giữ nguyên |
| S02-2A-H3-A-02 | `h3_bindings.check_admission/check_plan`: Plan base pair phải bằng actual operation/Run base và Admission.from_pair bằng base ấy; branch/assessment derivation từ canonical current Issue/proof; current key/changed inventory/uniqueness và origins map correspondence | DIRECT null, CARRY applicable/undetermined, REPLACEMENT complete/incomplete đúng vẫn nhận; sai branch/assessment, duplicate summary bị reject; oracle false summary nguyên bản |
| S02-2A-H3-A-03 | `h3_limits.references`: named typed Pair occurrences, unresolved/store/dispatch/analysis keys, Workflow Edge endpoints và StageRef atomic; caps/one-invocation slots giữ | Exact pair counts, under/exact/over reduced cap, repeat same slot không cộng lặp, different raw cùng slot reject; registry/history/config/plan/authority aggregate; prose/atomic refs negative; hai oracle counts nguyên bản; typed schema catalogue exhaustive và mixed boundary 8 refs (cap7/8/9), prose guard/from/to negative |

## Điều chỉnh source tests sai expectation E06

`test_h3_a_policy.test_resolved_history_positive_admission_is_still_not_business_acceptance` a1 có existing domain outputs/no anchor nhưng expect build step1 allowed, trái draft.2 §2.2/E06/D3. A2 đổi tên/expect thành giữ toàn selected units blocked với `PROGRESS_PROOF_REQUIRED`; vẫn stage0/needs_revalidation và giữ IDs. Snapshot/patch/source tests a1 trong evidence cũ không sửa.

`test_h3_a_controls.test_direct_answer_history_and_independent_output_with_u_hold` đổi lời gọi sang **revalidate/admission thuần**, vì có outputs độc lập sẵn không cấp quyền build lại step1. V vẫn inspect/admission được, U vẫn held và outputs/application count giữ. Thêm positive unit thực sự chưa có output bước1 và full-anchor unfinished-stage control, không dùng always-reject.

Hai negative controls so exact reason tuples (unknown hold/semantic authority) được bổ sung `PROGRESS_PROOF_REQUIRED` do cùng fixture cũng có output chưa anchor; các lý do cũ vẫn phải có. Không nới production caps/timeout hoặc sửa tests/conftest H1/H2/S01, canonical validators hay oracle auditor. Diff chính xác nằm trong bàn giao; kết quả mới/failures chỉ ghi theo logs/JUnit a2.

Reason-code text và full-hold reason text chỉ là diagnostics được giữ, không diễn giải là verified facts/authority; không dùng list rỗng để suy no blockers. Branch/assessment/current IDs/SHA/inventory được đối chiếu riêng với canonical data, holds vẫn do policy kiểm.

## Điều chỉnh fixture Plan/from_pair trong finding02

Positive Plan fixture a1 tạo Admission bằng helper read-only có from_pair=result_pair, dù operation/Run thực dùng base pair trước publication. A2 sửa fixture pin actual base pair, giữ nguyên positive assertions, và thêm tham số negative dựng **coherent sealed Plan có Artifact/SHA thật** nhưng from_pair=result_pair: phải bị từ chối. Không chỉ mutate payload rồi để outer hash gate bắt lỗi thay correspondence. Mã check_plan đối chiếu cả Run/operation base, không cho metadata chọn from pair để lách changed-key summary inventory. Đây là sửa đúng nghĩa field đã có, không mới writer/contract field.

Full provisional environment-v2/delivery đã dừng SIGINT để rebuild correction này. Partial JUnit C1049 cases không fail nhưng không là full pass; Python full chưa chạy. Logs/DB/ZIP giữ nguyên, PROVISIONAL_V2_ABORTED/RESULT ghi disposition. Fresh environment-v3, focused126/oracle13 và delivery-final là gates cuối, không dùng số provisional thay số mới.

## Điểm dừng

Không human decisions, Answer/application/source switch/completed-output edits, H3-B/C/D/I/O/CLI/writer/live/operational. Private API/counting delta tại CONTRACT_DELTA; chờ auditor kiểm độc lập và người dùng nghiệm thu cuối, không tự CLOSED findings.

## Hoàn tất schema field catalogue trong finding03

Catalogue quét cả nested event payload, aliases/nullable definitions, typed ID arrays/maps/Pairs từ shipped definitions; không lấy expected counts từ references(). Nó phát hiện thêm unresolved_keys, store_key, analysis_key, Edge.from/to và nested s01_store_key. REFERENCE_FIELD_AUDIT.json giữ attempt bị chặn vì còn s01_store_key; REFERENCE_FIELD_AUDIT_FINAL.json của fresh environment-v5 phải không còn unclassified field trước full. Runtime mixed boundary dùng expected8 viết tay và refs cap7/8/9, cùng atomic/prose/aggregate controls; không generic count mọi strings hoặc double-count SourceRef/StageRef.

Full provisional environment-v3/delivery-final cũng dừng SIGINT, partial C675/0 fail-error-skip không là full pass; Python full chưa chạy. Fresh environment-v5, focused129/oracle13 và delivery-release là authoritative gates cuối. Mọi old wheels/failed attempts/source copies/JUnit/DBs/dispositions giữ byte, không dùng count provisional cho bản cuối.
