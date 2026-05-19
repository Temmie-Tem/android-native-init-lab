# V384 Preflight Ready State

## Summary

- Current next execution item remains V384 helper v15 deploy followed by service-manager ptrace-lite crash capture.
- No V384 live/deploy action has been executed from this report.
- Wi-Fi HAL/start/scan/connect/link-up remains blocked.

## Evidence Sources

- Deploy preflight manifest: `tmp/wifi/v384-v15-deploy-preflight-current/manifest.json`
- Live preflight manifest: `tmp/wifi/v384-live-preflight-current/manifest.json`
- Executor plan regression: `tmp/wifi/v384-executor-plan-regression/manifest.json`
- Executor no-approval regression: `tmp/wifi/v384-executor-full-noapproval-regression/manifest.json`

## Current Deploy Preflight

```text
decision=execns-helper-v15-deploy-blocked
pass=False
reason=blocked before deploy by remote-helper-v15
next_step=resolve blockers before deploy
device_mutations=False
daemon_start_executed=False
wifi_bringup_executed=False
```

Non-pass checks:

- `remote-helper-v15`: `needs-deploy`; remote helper is not v15 yet.
- `approval-gate`: `needs-operator`; exact V384 deploy approval not supplied.
- `ncm-host-reachable`: warning only; serial fallback remains available.

## Current Live Preflight

```text
decision=service-manager-start-only-live-blocked
pass=False
reason=blocked before live run by helper-v15
next_step=resolve blockers before approval
daemon_start_executed=False
wifi_bringup_executed=False
```

Non-pass checks:

- `helper-v15`: blocker; V384 helper v15 must be deployed first.
- `approval-gate`: needs operator; exact V384 ptrace live approval not supplied.

Pass conditions already satisfied:

- native version/selftest baseline is usable
- service-manager and hwservicemanager binaries are visible
- real linker config and apex libraries are visible
- private property root is visible
- process surface is clean
- Wi-Fi link surface is clean
- temporary binder nodes are not present before helper-owned setup

## Executor Regression

Plan mode:

```text
decision=v384-deploy-live-executor-plan-ready
pass=True
device_commands_executed=False
device_mutations=False
daemon_start_executed=False
wifi_bringup_executed=False
```

No-approval `full` mode:

```text
decision=v384-deploy-live-executor-approval-required
pass=True
device_commands_executed=False
device_mutations=False
daemon_start_executed=False
wifi_bringup_executed=False
remaining_blockers=[exact-v384-deploy-approval-phrase, exact-v384-ptrace-live-approval-phrase]
```

## Required Next Approval

Deploy helper v15:

```text
approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up
```

Live ptrace-lite crash capture:

```text
approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Command

After both approvals are supplied, run:

```bash
python3 scripts/revalidation/wifi_v384_deploy_live_executor.py \
  --out-dir tmp/wifi/v384-executor-full-$(date +%Y%m%d-%H%M%S) \
  --deploy-approval-phrase "approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up" \
  --live-approval-phrase "approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  full
```

Expected allowed effects:

- `/cache/bin/a90_android_execns_probe` is replaced with v15.
- Bounded service-manager start-only ptrace-lite capture runs.
- Runtime-gap classifier runs if live result is a runtime gap.

Expected forbidden effects:

- no Wi-Fi HAL start
- no CNSS/diag start
- no wificond/supplicant/hostapd start
- no scan/connect/link-up/credential/DHCP/routing
- no Android partition write
