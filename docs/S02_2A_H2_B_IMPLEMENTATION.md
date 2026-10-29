# H2-B — scoped checkpoints local/synthetic

`dacn-s02 0.7.0a1`, handler `s02-2a-h2-b/0.7.0a1`. Implementation theo H2 draft.2, D1–D4 đã chốt. **Chờ audit độc lập và người dùng nghiệm thu**; không đổi trạng thái nghiệm thu H1/H2-A. [Bàn giao](../reports/s02-phase2/2a-h2-b-0.7.0a1-2026-10-27/START_HERE.md) ghi wheel, kiểm thực chạy và giới hạn.

Chỉ fresh E1, cùng checked snapshot/SourceContext, requirement family giữ toàn criteria, bước 1–4, mock local. Không H1 bridge, H2-C/H3, sửa output đã hoàn tất, Answer/A2, LLM, renderer, operational migration hoặc live. Không đổi canonical schemas, registry, DB2, locks hoặc handlers H1. Settings của store giữ nguyên.

## API và lifecycle

- `h2_authority.LocalSyntheticAuthority(path, expected_sha256)` nhận trust context trực tiếp từ invoker. File approvals đóng theo §3.1; exact tuple, không wildcard/default allow. File được đọc/hash lại ở prepare/resume, seal và bên trong transaction trước publication. Stored context không thay external authority.
- `h2_service.H2Service(repo, authority=...)`: `intent` chỉ xuất metadata/binding skeleton read-only; `prepare` tạo/so toàn intent tại T0; `resume` dùng raw đã pin và duy nhất một sealed plan; `report(progress=True)` đọc lịch sử và không cấp eligibility.
- `h2_store.ScopeStore` dùng transaction, whole-graph verifier và pair CAS hiện có. T0 lưu một primary config và raw candidate/analysis riêng; plan chỉ append sau T0. Không rebuild sealed plan hoặc tự rebase/resubmit. Finalized history chỉ dùng plan Artifact đã promote trong event finalized; log/stage thêm sau đó không sửa outcome.
- `h2_builders.ScopedBuilder` áp projection đóng vào full Model; `h2_candidates`/`h2_policy` kiểm inventory, quyền ghi, union và meaningful impact trước rebind. Issue successors dùng cùng key; code kiểm raw→IDs, refs và correspondence Model+AS/progress. Source rows ngoài scope giữ nguyên.
- `h2_checkpoint` giữ selectors, tasks có origin, progress và hashes. Origin plan được kiểm và cache chỉ trong invocation; Budget/deadline không reset.

Authority binding bao gồm full source/base Model+AS, selectors, progress và retained assessment hashes, raw hashes/lengths, read/write intent, policy/limits. Hash intent bao gồm bảng alias để cùng raw không bị diễn giải thành IDs khác khi restart. Candidate/analysis không cấp authority và không import canonical Records.

Một Budget H2 được dùng xuyên suốt mỗi invocation; caps draft.2 giữ nguyên, occurrences không deduplicate. Deadline cooperative, không hard timeout I/O/SQLite. Test workers có process/connection riêng; không đổi timeout/assertions của oracle lịch sử.

## Commands

```text
dacn-s02 --config local.toml scoped-bootstrap \
  --from-receipt intake.json --receipt bootstrap.json

dacn-s02 --config local.toml \
  --h2-authority-file approvals-v1.json --expect-h2-authority-sha256 SHA \
  scoped-step --from-receipt current.json \
  --expect-model MODEL --expect-analysis-set AS --step 2 --unit UNIT \
  --mock-response candidate.json --expect-sha256 CANDIDATE_SHA \
  --analysis analysis.json --expect-analysis-sha256 ANALYSIS_SHA \
  --receipt new-work.json

dacn-s02 --config local.toml \
  --h2-authority-file approvals-v1.json --expect-h2-authority-sha256 SHA \
  scoped-resume --receipt new-work.json

dacn-s02 --config local.toml scoped-progress --receipt new-work.json
```

`scope-plan --from-receipt ... --step ... --unit ...` là preview read-only của current checkpoint; không authorize tuple mới. `prepare-scope-work --receipt existing.json --mode bootstrap|step|revalidate` nhận full original intent của mode; chỉ prepare T0. Receipt hợp lệ nhưng chưa có operation trả 5; không tự cấp identity khác. Mọi create command cần receipt mới; authority allow phải có trước receipt/T0 của semantic work.

`scoped-revalidate` nhận parent/current pair, `--goal admission|retained_output`, step, units, `--guard-key` lặp và analysis/hash; không nhận candidate. Resume chỉ receipt cùng global authority flags, không nhận raw/units mới. Hai authority flags phải cùng có hoặc cùng vắng; pending semantic work thiếu cả hai trả 3. Bootstrap không dùng provider. Finalized progress/resume không đòi provider cũ.

Codes: 0 đọc/progress/prepared/completed; 2 blocked/rejected/denied/stale/conflict; 3 failure/unknown/unsupported/integrity/provider unavailable; 4 input/receipt not found; 5 checked not prepared; 64 sai flags/cú pháp. Authority file không đọc được là 3. Run toàn cục có thể blocked/2 khi V vừa hoàn thành stage còn U/global tasks open.

## Guard, retained output và giới hạn

Candidate không đủ union/impact proof không được publish Model; code tạo guard AS-only với root key hash origin command, source selectors và provenance của failed raw/context. Guard không đi vào Model/mapping/Part aliases. Current selection giữ cả key resolved. Guard-only không tăng completed work và không cắt candidate lấy phần pass.

Revalidation dùng command mới và current pair. P_guard kiểm origin/lineage, full inventory, disposition của từng family/use, failure context, nguồn và retained outputs. Thiếu proof tạo open successor; đủ proof tạo resolved successor. Business/gap/global tasks trên cùng Model giữ chính IDs/bytes. Chỉ code builder đúng predicate được resolve construction task; global mapping task cần toàn inventory proposed. Revalidate không tăng stage hoặc công bố candidate từng bị chặn. Command mới mới được thử output tiếp theo.

`retained_output` chỉ đánh giá output đã tồn tại. Đòi domain edit được giữ `terminal_out_of_scope`, guard open; không sửa action/rule/responsibility/Part/source hoặc build lại cặp đã hoàn tất. Metadata giữ lịch sử output/IDs, from/to pair, parent assessment, diff/context hashes và result hashes. `eligibility_authorized_in_process=false` luôn hiện trong read-only report.

Ranh giới tin cậy là caller hợp tác, synthetic store và filesystem local ổn định; không xác minh danh tính người thật/nghiệp vụ hay chống thay namespace ác ý đồng thời/power loss thật. Approvals là test control, không Review/consent hoặc chứng nhận independence ngữ nghĩa. Bằng chứng kiểm phần mềm được ghi riêng với mock; không dùng test pass để tự tuyên bố nghiệm thu.
