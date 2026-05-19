# V382 Deploy Live Executor

## Summary

- Added `scripts/revalidation/wifi_v382_deploy_live_executor.py` as a fail-closed wrapper for the V382 handoff.
- The executor sequences final readiness, helper v14 deploy, live preflight, bounded service-manager start-only live smoke, result routing, and runtime-gap classification.
- Deploy and live remain separately gated by exact approval phrases and explicit `--apply --assume-yes` flags.
- No Wi-Fi HAL, CNSS/diag, wificond, supplicant, scan, connect, link-up, DHCP, routing, firmware mutation, or Android partition write is approved by this executor.

## Executor Commands

Plan-only readiness:

```bash
python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-plan \
  plan
```

Deploy-only after exact deploy approval:

```bash
python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-deploy \
  --deploy-approval-phrase "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  deploy
```

Live-only after exact live approval and v14 remote helper deployment:

```bash
python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-live \
  --live-approval-phrase "approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  live
```

Full approved handoff:

```bash
python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-full \
  --deploy-approval-phrase "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up" \
  --live-approval-phrase "approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  full
```

## No-Approval Regression

Ran local no-approval regression before live use:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_v382_deploy_live_executor.py \
  scripts/revalidation/wifi_v382_final_readiness.py \
  scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py \
  scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py \
  scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py

python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-deploy-noapproval deploy
python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-live-noapproval live
python3 scripts/revalidation/wifi_v382_deploy_live_executor.py \
  --out-dir tmp/wifi/v382-executor-full-noapproval full
```

Observed for all no-approval modes:

- decision: `v382-deploy-live-executor-approval-required`
- pass: `true`
- `device_commands_executed=false`
- `device_mutations=false`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`

## Static Validation

- `python3 -m py_compile` passed for the executor and dependent V382 scripts.
- `git diff --check` passed.
- Executor default timeout was raised to `1800s` because serial fallback transfer of the 903KB static helper can exceed 360s when NCM is unavailable.

## Safety Notes

- `live` does not rerun pre-deploy final readiness after helper deployment; it runs the V382 live preflight instead.
- `full` runs final readiness before deploy, deploys v14, then runs live preflight before any bounded service-manager start.
- The executor is intended to reduce operator sequencing errors, not to broaden the approved scope.
