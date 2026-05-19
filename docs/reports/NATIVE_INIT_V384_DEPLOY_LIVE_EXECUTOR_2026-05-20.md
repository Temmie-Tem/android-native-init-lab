# V384 Deploy/Live Executor

## Summary

- Added `scripts/revalidation/wifi_v384_deploy_live_executor.py` as a fail-closed V384 sequencer.
- It sequences helper v15 deploy, service-manager ptrace-lite live capture, and runtime-gap classification.
- No approval regression proves `full` without exact V384 phrases executes no bridge/device command, no mutation, no daemon start, and no Wi-Fi bring-up.

## Approval Boundary

Required deploy phrase:

```text
approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up
```

Required live phrase:

```text
approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Older V382/V373 phrases are intentionally insufficient for this executor.

## Validation

```text
$ python3 -m py_compile scripts/revalidation/wifi_v384_deploy_live_executor.py
PASS

$ python3 scripts/revalidation/wifi_v384_deploy_live_executor.py --out-dir tmp/wifi/v384-executor-plan-regression plan
decision: v384-deploy-live-executor-plan-ready
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False

$ python3 scripts/revalidation/wifi_v384_deploy_live_executor.py --out-dir tmp/wifi/v384-executor-full-noapproval-regression full
decision: v384-deploy-live-executor-approval-required
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Current Preflight State

- `tmp/wifi/v384-v15-deploy-preflight-current`: deploy preflight blocked by `remote-helper-v15`; local v15 artifact is ready.
- `tmp/wifi/v384-live-preflight-current`: live preflight blocked by `helper-v15`; service-manager binaries, runtime material, private property root, process surface, and Wi-Fi link surface are otherwise clean.
- NCM host ping was warning-only in deploy preflight; serial fallback remains available for deploy.

## Next

1. Optional host NCM setup if using NCM transfer instead of serial fallback.
2. Execute V384 deploy with the exact deploy phrase.
3. Execute V384 ptrace-lite live capture with the exact live phrase.
4. Classify captured evidence and choose the next repair target.
