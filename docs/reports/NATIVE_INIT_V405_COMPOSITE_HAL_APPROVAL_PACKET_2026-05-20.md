# Native Init v405 Composite Wi-Fi HAL Approval Packet

## Summary

V405 completed as a non-mutating approval packet and helper/runner implementation stage.

Helper v23 was built locally with `wifi-hal-composite-start-only` support. The deploy wrapper and composite HAL runner both fail closed without exact approval. No helper deploy, service-manager start, Wi-Fi HAL start, scan/connect/link-up, or Wi-Fi bring-up was executed.

## Evidence

- V405 approval packet: `tmp/wifi/v405-composite-hal-approval-packet-final-20260520-092442/`
- V405 approval manifest: `tmp/wifi/v405-composite-hal-approval-packet-final-20260520-092442/manifest.json`
- V405 approval summary: `tmp/wifi/v405-composite-hal-approval-packet-final-20260520-092442/summary.md`
- helper v23 artifact: `tmp/wifi/v405-a90_android_execns_probe-v23/a90_android_execns_probe`
- runner plan evidence: `tmp/wifi/v405-composite-hal-runner-plan-final-20260520-092442/`
- runner no-approval evidence: `tmp/wifi/v405-composite-hal-runner-noapproval-final-20260520-092442/`

Result:

```text
decision: v405-composite-hal-approval-packet-ready
pass: True
reason: approval packet ready; deploy and HAL start-only still require separate exact approvals
next_step: operator may approve V405 helper v23 deploy first
helper_sha256: 64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520
live_execution_approved: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

## Helper v23

Built artifact:

```text
tmp/wifi/v405-a90_android_execns_probe-v23/a90_android_execns_probe
sha256 64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520
```

Required strings were present:

- `a90_android_execns_probe v23`
- `wifi-hal-composite-start-only`
- `vendor-wifi-hal-ext`
- `vendor-wifi-hal-legacy`
- `--allow-wifi-hal-start-only`
- `wifi_hal_composite_start.scan_connect_linkup=0`

## Guard Results

| step | decision | status |
| --- | --- | --- |
| deploy plan | `execns-helper-v23-deploy-plan-ready` | pass |
| deploy preflight | `execns-helper-v23-deploy-preflight-ready-needs-deploy` | pass |
| deploy run without approval | `execns-helper-v23-deploy-approval-required` | pass |
| HAL runner plan | `composite-hal-start-only-plan-ready` | pass |
| HAL runner run without approval | `composite-hal-start-only-approval-required` | pass |

The deploy preflight correctly reports `ready-needs-deploy` because the device still has helper v22. That is expected and is not a V405 packet blocker.

## Approval Phrases

Deploy helper v23 only:

```text
approve v405 deploy execns helper v23 only; no daemon start and no Wi-Fi bring-up
```

Composite HAL start-only smoke:

```text
approve v405 composite Wi-Fi HAL start-only smoke only; no scan/connect/link-up and no Wi-Fi bring-up
```

The deploy approval must be used first. The HAL approval should only be considered after helper v23 deploy and V405 runner preflight pass.

## Scope

V405 implemented the path required by V404: one helper-owned private namespace can supervise the service-manager pair and first HAL candidate together.

Still not executed:

- helper v23 deployment.
- `servicemanager`, `hwservicemanager`, or Wi-Fi HAL live start.
- `wificond`, supplicant, hostapd, CNSS/diag.
- scan/connect/link-up, credentials, DHCP, routing.
- rfkill, ICNSS bind/unbind, module load/unload, firmware mutation.
- persistence or boot/autostart changes.

## Next Target

Proceed only after explicit approval:

1. Deploy helper v23 with the V405 deploy phrase.
2. Run V405 composite HAL runner preflight.
3. If preflight passes, request a separate explicit decision before HAL start-only smoke.
