# H3-B 0.10.0a1 — candidate chờ audit runtime

B-P01 đã được người dùng chấp thuận theo [audit/quyết định](acceptance/s02-2a-h3-b-contract-draft1-2026-10-31/README.md). Chỉ checked adoption/revalidation AS-only/API, chưa nghiệm thu runtime B. Proposal [H3 draft.2](S02_2A_H3_E1_HISTORY_DESIGN_PROPOSAL.md) và [B-P01 snapshot](S02_2A_H3_B_CHECKPOINT_CONTRACT_DELTA_PROPOSAL.md) giữ byte. H3-A a2 pure semantics/checkers và evidence nguyên trạng.

## Frozen dispatch và hash domains

| Lane | Marker/version được nhận | Semantics |
| --- | --- | --- |
| A input projection | Config/Plan/Admission draft.2, A policy/work/authority draft.2 | Existing pure checkers nguyên byte; không dùng cho B result |
| H2 historical publisher | H2 config/plan draft.2 và handler H2 version gốc | Chỉ đọc actual promoted provenance; không gọi H2 context để giả graph không có A2 |
| B checkpoint | Config/Plan/Admission draft.3; handler `s02-2a-h3-b/0.10.0a1` | New result/config/publisher pure checks và AS-only writer |
| B semantic work | policy `s02-h3-history-policy/0.1.0-draft.3`, work `s02-h3-work/0.1.0-draft.3`, authority `s02-h3-local-authority/0.1.0-draft.3`, analysis `s02-h3-analysis/0.1.0-draft.3` | Exact B tuple only; A approvals/mixed versions reject; purpose vẫn synthetic_test_only |
| Historical reviews | `s02-h3-historical-reviews/0.1.0-draft.1` | Original external invoker tuple trước checked read, all-store R cố định; không semantic authority |

Field sets của B Config/Plan/Admission giữ A shapes; version constants tách theo B-P01/G2. Canonical E1/L1 schemas/registry/DB2/receipt s02/2 và numeric ceilings giữ byte. B chỉ adopt/revalidate, candidate=null; step adopt=0, revalidate=1..4. Unknown/mixed versions không dispatch ngầm. Pure validators giữ cùng mode/goal/stage gates với API: adopt goal=admission; retained_output cần requested stage thật trong checked parent; own operation request exact scope/config_artifact_id=null.

## Pure checks — cụ thể hóa G1–G3 trước writer

`h3_checkpoint_contracts` trả schema copies và validate private draft.3. `h3_checkpoint_checks` tách checked stage provenance khỏi result assessment. No-anchor stage0 giữ actual outputs/needs_revalidation; full H2 anchor kiểm actual H2 publisher và A original checker ở lane không nested aliases, typed adapter riêng cho workflow members. Revalidate giữ toàn stage/output refs từ checked B parent; không dùng assessment để cấp stage mới.

`CheckpointVerifier.published` đọc actual config/plan Artifact bytes, prepared/log/finalized events, input/plan promotions và exact batch Records. Walk parent chain oldest-first với visited/depth/shared Budget; parent capability được kiểm lại từ actual publication, dataclass/dict tự khai không đủ. Result checks full old keys, Model/source nguyên byte, adopt giữ current Issues; revalidate chỉ DIRECT technical guard successors với origin H2 đã kiểm, không human decision/A2 release mới. Không sửa completed output hoặc rebind Model để nhận AS-only.

Source/context/diff/closure/proof/parent hashes theo B-P01 §2.1, từ actual result graph/analysis/config frozen. `Progress.assessment` luôn khác null ở B result, latest pair/hashes thật; input stage projection A vẫn null. Revalidate Config parent_metadata bằng promoted parent Admission hoàn chỉnh, không projection bị xóa assessments.

T0 history binding giữ **toàn** Record/event/snapshot và owner/profile inventory của checked store lúc prepare. Sau đó `dependencies` kiểm từng pinned Record/event ID/hash, snapshot/archive, owner/profile maps và current-key selection của base. Operations pin qua toàn prepared-event inventory của T0; không bỏ ancestors/session khác. Whole current store vẫn canonical-check với registry riêng. Own prepared/staged/sealed/finalized facts kiểm exact command/phase/stage/payload/promotions; unrelated canonical appends có thể tồn tại nhưng không được refresh history/intent pin. Live external B binding pin original history SHA; historical registry R thay đổi vẫn fail closed.

Admission giữ typed TaskOrigin H2 từ actual introducing plan/root/predicate/unit/target-step với current Issue ID và origin plan SHA; selectors giữ đúng target_step/role đã chứng minh. Adopt kiểm ở bước1, task của bước sau không bị đổi thành blocker bước1; tại target step B không miễn task để build. Metadata không cấp B construction permit. Unknown verification Issue không được nhận làm code task từ kind/prefix.

Guard revalidate dùng structured full inspections/independence với full source basis, canonical surviving holds và actual H2 guard lineage. Không parse prose thành approval; thiếu proof giữ open/full hold. Không nhận business Issue/A2 proof là technical guard, không auto-resolve Answer hoặc REPLACEMENT/CARRY. Unknown impact giữ global selector. No-anchor existing outputs vẫn held kể cả một lần technical assessment đạt; domain repair/build thuộc scope riêng.

## API local/synthetic và transport

`HistoryService(settings, historical_reviews=ReviewTrustContext(...), authority=LocalSyntheticCheckpointAuthority(...))` nhận settings hiện hành và hai trust lanes riêng. Các methods `inspect`, `prepare`, `resume`, `report`, `adopt`, `revalidate` là API Python; không có product CLI mới. `prepare(command,parent,receipt=...,expected_pair=...,analysis=bytes,mode=...,step=...,unit_ids=...,goal=...,anchor=...)` pin input trước T0. `resume(command,receipt=...)` luôn tiếp đúng command/plan; `report(command)` đọc pending/finalized mà không tạo effects. `adopt/revalidate` ghép prepare và resume, không cung cấp implicit retry/rebase.

Loader đọc tối đa cap+1 bytes, đối chiếu external tuple/hash rồi dựng Repository với review map trước reconciliation/checked read. Mỗi invocation giữ một shared Budget; mỗi transaction rehash original registry và external B authority trước commit. Registry file locator có thể khác nếu original bytes/tuple identity giữ nguyên; registry ID/SHA/R/pins không được thay khi pending. Finalized report/replay không cần authority hoặc analysis file ngoài DB nhưng vẫn kiểm original historical registry.

B anchor được đọc bằng dispatch B, actual promoted parent/result assessments và full correspondence trên AS-only path. Model/source giữ nguyên; false/prefix/omitted stage proof không cấp completed progress. H2 publisher luôn qua actual H2 config/plan/raw projection reader; lane không có nested aliases dùng thêm A original anchor checker. H2 `Node`/`Edge` locators được chuẩn hóa riêng thành typed `WorkflowNode`/`WorkflowEdge` trong private B transport sau khi kiểm ID/membership với actual workflow/raw origin; không sửa canonical/H2 bytes. Current Issue aliases được rebind qua immutable issue_key; snapshots trong historical output refs vẫn giữ origin/root/from/obsolete/target đúng vai trò.

T0 receipt s02/2 đi trước persistence. T0 chỉ cấp reserved Run/start/raw/config một lần; seal chọn đúng một plan chứa toàn allocations/times/IDs. T3 dùng unchanged paired CAS của Repository. Witness của losing plan giữ toàn immutable T0 dependencies và own phases, trong khi whole current store/registry vẫn checked riêng. AS-only hoặc Model+AS rival làm loser stale, không publish planned AS/Issue Records. Sau seal không rebuild/rebase ngầm; COMMIT probe/explicit same-command resume đọc lại winning identity.

## Verification và trạng thái

G1–G3 phải đạt trên installed wheel với real projected graph round-trip trước writer. Sau đó writer/runtime B phải có toàn S1–S6/E18/HR-P/E20/E21 theo H3 §7.1, C rồi Python tuần tự, OS-process concurrency bên trong tests. Không nhận H2 fixture publications/pure projection là runtime B safety; không hoãn sang D. Handoff cuối sẽ ghi commands/JUnit/DB/readbacks/failures và wheel/seal; chưa được gắn B đã audit hoặc người dùng nghiệm thu.

[Bàn giao candidate](../reports/s02-phase2/2a-h3-b-0.10.0a1-2026-10-31/START_HERE.md) ghi measurements mới, failures/limits, wheel và integrity marker. B-P01 đạt thiết kế; runtime B chờ auditor độc lập và người dùng nghiệm thu.
