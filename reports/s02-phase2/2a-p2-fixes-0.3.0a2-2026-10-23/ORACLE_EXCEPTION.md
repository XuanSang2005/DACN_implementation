# Một oracle từ chối sớm hơn vị trí pytest.raises

Giữ nguyên byte `test_independent_p2.py` từ audit a1. Sau sửa, **8 passed / 1 failed mỗi backend**, không gọi là toàn bộ oracle đạt. Ca còn lại là `test_writer_refuses_review_fork_after_selection_loss`; xem [JUnit C](audit-p2/checks/audit-1-c.xml), [log C](audit-p2/checks/audit-1-c.log), [JUnit Python](audit-p2/checks/audit-1-python.xml), [log Python](audit-p2/checks/audit-1-python.log).

## Phản chứng cụ thể

Oracle xóa `active_reviews`, sau đó thực hiện dòng sau **trước** `with pytest.raises(S02Error)`:

```python
op=operation(meta['session'],meta['context'],repo.heads(meta['session']))
```

`Repository.heads()` vốn là checked read: gọi `_check()` trước khi trả cặp head. Bản sửa `_check()` phát hiện `active_review_inventory` thiếu selection và từ chối ngay tại dòng trên. Trace có nguyên nhân `SCHEMA_INVARIANT: active_review_inventory`, được read boundary bọc thành `PERSISTENCE_FAILED`. Không có `prepare`/`finalize` được gọi, không có fork được commit. Đây là khác biệt với a1: a1 lọt checked heads rồi không raise cả trong prepare/finalize.

Yêu cầu sửa của người dùng: “Checked read và kiểm trước/sau mutation đều từ chối trạng thái sai.” Audit FINDINGS.md cũng yêu cầu “Missing/stale selection phải làm checked read/write từ chối”. Contract §9 yêu cầu một active review/bundle và CAS; storage draft.2 §3 yêu cầu whole-store review check. Cho `heads()` bỏ qua integrity để đi đến khối raises phía sau sẽ trái các yêu cầu này và làm yếu API hiện hành.

## Bằng chứng bổ sung, không thay oracle

File regression mới `packages/s02/tests/test_review_integrity.py` tách hai ranh giới:

1. Lấy request/head pins lúc kho còn hợp lệ, rồi làm hỏng selection bằng SQL fixture. Checked verify/heads/get_record/check_freshness và prepare đều phải raise; so nguyên DB bytes sau mỗi lời gọi (`test_bad_selection_refused_at_reads_and_before_write`).
2. Khi selection hợp lệ, thử root thứ hai hoặc successor dùng parent cũ: CAS từ chối, toàn T3 rollback và command vẫn prepared (`test_review_cas_rejects_divergent_publication`).
3. Hook fault injection hỗ trợ sẵn làm hỏng selection sau mutation, trước `_check` lần hai: transaction rollback nguyên bytes, reopen giữ root cũ (`test_post_mutation_check_rolls_back_selection_damage`). Không monkeypatch production validator để qua oracle.

Các ca chạy trên cả fresh E1 và mixed L1→E1, với controls request_changes/revoked. [34 regressions mới](focused-review-02/checks/commands.json) đạt cả hai backend; full suite chạy lại cùng file nguồn hiện hành. Bản sao test input và hashes ở evidence; original audit assertions không đổi, không skip/xfail.

Đề nghị auditor điều chỉnh fixture trong **một phiên bản oracle mới**: lấy head pins trước khi xóa selection; hoặc đặt checked heads trong raises riêng rồi dùng pins đã giữ để kiểm prepare/finalize. Không sửa file audit đã niêm phong trong lượt implementation này. Auditor quyết định tính hợp lệ của phản chứng và đóng findings sau khi kiểm lại. Finding 01/02 vẫn chưa được tự đóng.
