# V377 Service-Manager Start-Only Result Router Plan

## Summary

- 목표는 V376 live runner 결과를 host-only로 해석해 다음 안전 단계를 결정하는 router를 추가하는 것이다.
- V377은 device bridge를 열지 않고 manifest만 읽는다.
- 현재 V376 approved live start는 exact phrase 대기 상태이므로, 기본 route 결과는 approval 대기여야 한다.
- Wi-Fi HAL, scan/connect/link-up, credential, DHCP, routing은 계속 금지한다.

## Implementation

- 새 host-only router: `scripts/revalidation/wifi_service_manager_start_only_result_router.py`
- 입력 기본값:
  - 최신 `tmp/wifi/v376-*/manifest.json`
- 명령:
  - `route`: 현재 V376 manifest를 읽어 다음 action을 추천한다.
  - `regression`: synthetic V376 cases로 router decision matrix를 검증한다.

## Decision Model

- V376 manifest 없음: `service-manager-start-only-router-awaiting-v376`
- V376 preflight/no-approval: `service-manager-start-only-router-awaiting-approval`
- V376 blocked: `service-manager-start-only-router-blocked`
- V376 pass + clean postflight: `service-manager-start-only-router-hal-readiness-next-ready`
- V376 runtime-gap + clean postflight: `service-manager-start-only-router-runtime-gap`
- Wi-Fi bring-up marker present: `service-manager-start-only-router-scope-violation`
- unexpected result: `service-manager-start-only-router-manual-review`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_service_manager_start_only_result_router.py

python3 scripts/revalidation/wifi_service_manager_start_only_result_router.py \
  --out-dir tmp/wifi/v377-service-manager-start-only-router-regression-$(date +%Y%m%d-%H%M%S) \
  regression

python3 scripts/revalidation/wifi_service_manager_start_only_result_router.py \
  --out-dir tmp/wifi/v377-service-manager-start-only-router-route-$(date +%Y%m%d-%H%M%S) \
  route
```

## Acceptance

- Regression passes without device commands.
- Current route returns approval waiting state, not HAL readiness.
- Recommended command includes V376 exact phrase gate.
- `device_commands_executed=false` and `device_mutations=false` for every router output.
