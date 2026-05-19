# V377 Service-Manager Start-Only Result Router Report

## Result

- regression decision: `service-manager-start-only-router-regression-pass`
- current route decision: `service-manager-start-only-router-awaiting-approval`
- pass: `true`
- device_commands_executed: `false`
- device_mutations: `false`
- evidence:
  - `tmp/wifi/v377-service-manager-start-only-router-regression-20260520-022406/`
  - `tmp/wifi/v377-service-manager-start-only-router-route-20260520-022406/`

## Verified

- Python compile PASS for `scripts/revalidation/wifi_service_manager_start_only_result_router.py`.
- Regression covers missing manifest, preflight-ready, approval-required, blocked, clean pass, runtime-gap, Wi-Fi scope violation, and unexpected decisions.
- Current latest V376 manifest routes to `service-manager-start-only-router-awaiting-approval`.
- Current route reason: `V376 is ready but live start is not approved: decision=service-manager-start-only-live-preflight-ready`.
- Router did not open the bridge and did not mutate device state.

## Current Gate

V376 live start still requires this exact phrase with `--apply --assume-yes`:

```text
approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

- Run V376 approved live only after the exact phrase is provided.
- After approved V376 evidence exists, rerun V377 route.
- If V377 returns `service-manager-start-only-router-hal-readiness-next-ready`, create a separate HAL start-only readiness/approval packet.
- If V377 returns `service-manager-start-only-router-runtime-gap`, classify runtime gaps before HAL work.
