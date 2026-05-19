# V382 Service-Manager Property Runtime Result Router Report

## Result

- decision: `v382-result-router-ready`
- scope: host-only result routing
- device commands executed: `false`
- device mutations: `false`
- Wi-Fi bring-up: `false`

## What Changed

- `scripts/revalidation/wifi_service_manager_start_only_result_router.py`
  - generalized live label and recommended live command constants
  - preserves V377/V376 default behavior
- `scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py`
  - points recommended live command at `wifi_service_manager_start_only_v382_live_runner.py`
  - uses V382 evidence glob by default
  - keeps host-only routing semantics

## Evidence

| phase | path | result |
| --- | --- | --- |
| V377 regression | `tmp/wifi/v377-router-regression-after-v382-wrapper/manifest.json` | PASS |
| V382 regression | `tmp/wifi/v382-router-regression/manifest.json` | PASS |
| V382 route no-approval | `tmp/wifi/v382-router-route-noapproval/manifest.json` | awaiting approval |

## V382 Route

Input:

- `tmp/wifi/v382-live-noapproval-regression/manifest.json`

Output:

- decision: `service-manager-start-only-router-awaiting-approval`
- pass: `true`
- reason: `V382 is ready but live start is not approved`
- remaining blocker: `exact-v373-service-manager-approval-phrase`
- recommended command uses:
  - `scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py`
  - output prefix `tmp/wifi/v382-approved-live-...`

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_service_manager_start_only_result_router.py \
  scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py

python3 scripts/revalidation/wifi_service_manager_start_only_result_router.py \
  --out-dir tmp/wifi/v377-router-regression-after-v382-wrapper \
  regression

python3 scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py \
  --out-dir tmp/wifi/v382-router-regression \
  regression

python3 scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py \
  --out-dir tmp/wifi/v382-router-route-noapproval \
  --v376-manifest tmp/wifi/v382-live-noapproval-regression/manifest.json \
  route
```

## Next

- V382 helper deploy still requires:
  - `approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up`
- V382 live start-only still requires:
  - `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
- After approved V382 live, route the manifest through:
  - `scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py`
