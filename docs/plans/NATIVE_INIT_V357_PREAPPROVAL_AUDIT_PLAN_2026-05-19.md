# v357 계획: V317 Pre-Approval Audit

## Summary

- v357은 native init/boot image 변경 없이 host-only gate를 한 번 더 묶는 검증 단계다.
- 목표는 V317 live proof 직전 상태가 “정확한 승인 문구만 남은 상태”인지 자동 확인하는 것이다.
- live proof, cleanup, daemon start, scan/connect/link-up, helper deploy 같은 device mutation은 실행하지 않는다.

## Key Changes

- `scripts/revalidation/wifi_v317_preapproval_audit.py`를 추가한다.
- `scripts/revalidation/wifi_v317_live_executor.py`는 V351 `plan`/approval-required manifest에 `remaining_blockers`를 명시한다.
- audit 대상은 다음 네 도구다.
  - V349 final readiness: `wifi_v317_final_readiness.py`
  - V350 operator checklist: `wifi_v317_operator_checklist.py`
  - V351 live executor `plan`: `wifi_v317_live_executor.py plan`
  - V352/V354/V355/V356 executor regression: `wifi_v317_live_executor_regression.py run`
- 성공 조건은 다음으로 고정한다.
  - 각 manifest decision이 기대값과 일치한다.
  - 각 manifest `pass=true`, `git_dirty=false`, current HEAD와 일치한다.
  - `device_commands_executed=false`, `device_mutations=false`다.
  - remaining blocker는 `exact-v317-approval-phrase` 하나뿐이다.
  - V350 preferred command는 V351 executor를 사용한다.
  - V351 plan은 `live_execution_approved=false`다.
  - V352 regression matrix는 no/partial/wrong phrase cases를 모두 PASS로 포함한다.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_preapproval_audit.py
python3 scripts/revalidation/wifi_v317_preapproval_audit.py \
  --out-dir tmp/wifi/v357-v317-preapproval-audit \
  check
```

## Expected Result

- dirty tree pre-commit에서는 clean-head 조건 때문에 blocked가 정상이다.
- clean HEAD post-commit에서는 `v317-preapproval-audit-awaiting-approval`가 기대값이다.
- 이 단계가 PASS해도 V317 live proof는 여전히 exact approval phrase 전까지 실행하지 않는다.

## Assumptions

- 최신 승인 전 기준은 V356 `Record V356 wrong phrase validation`이다.
- V317 live proof는 다음 exact phrase 없이는 실행하지 않는다.
  - `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up`
- v357은 host tooling 안전성 강화이며 native init version을 올리지 않는다.
