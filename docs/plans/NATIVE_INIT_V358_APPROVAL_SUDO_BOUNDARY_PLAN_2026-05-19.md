# v358 계획: V317 Approval/Sudo Boundary Matrix

## Summary

- v358은 native init/boot image 변경 없이 V317 live 직전 운영 경계를 문서화하는 host-only 작업이다.
- 목표는 “어떤 작업은 그냥 실행 가능하고, 어떤 작업은 host `sudo`가 필요하며, 어떤 작업은 사용자 승인 없이는 금지인지”를 한 문서에 고정하는 것이다.
- V317 live proof, cleanup, daemon start, scan/connect/link-up, helper deploy, reboot/flash는 실행하지 않는다.

## Key Changes

- `docs/operations/WIFI_V317_APPROVAL_AND_SUDO_MATRIX.md`를 추가한다.
- 문서는 다음 범주를 분리한다.
  - host-only/no-sudo: plan, audit, checklist, regression, manifest inspection, static checks
  - host-sudo: serial bridge open/restart, `/dev/ttyACM0` access, NCM host IP assignment
  - exact approval required: V351 executor `run`/`cleanup`
  - separate approval required: boot partition write, reboot/rollback, Wi-Fi scan/connect/link-up, global namespace/property changes
- V357 PASS 상태와 exact V317 approval phrase를 기준으로 연결한다.

## Validation

```bash
git diff --check
rg -n "V358|Approval/Sudo|exact V317|sudo|WIFI_V317_APPROVAL" \
  docs/operations docs/plans docs/reports
python3 scripts/revalidation/wifi_v317_preapproval_audit.py \
  --out-dir tmp/wifi/v357-v317-preapproval-audit \
  check
```

## Expected Result

- V358은 문서 작업만 수행한다.
- V357 audit는 계속 `v317-preapproval-audit-awaiting-approval`이어야 한다.
- live execution은 여전히 exact approval phrase 전까지 blocked다.

## Assumptions

- 최신 host-only gate는 V357 PASS 상태다.
- 현재 Codex 실행 환경에서는 `sudo`를 자동 승인 요청 없이 직접 사용할 수 없거나, 사용자가 직접 실행해야 하는 작업으로 취급한다.
- exact approval phrase는 live mutation 승인 전용이며, broad approval이나 일반 동의 문장으로 대체하지 않는다.
