# Native Init v403 Service-Manager Start-Only Retry Approval Packet

## Summary

V403 prepares the next bounded step after the V402 private SELinux proof pass.

The V403 runner and approval packet are ready. No live service-manager start was executed in this packet. Wi-Fi HAL/start/scan/connect remains blocked.

## Evidence

Primary evidence:

- approval packet evidence: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/`
- approval packet manifest: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/manifest.json`
- runner plan manifest: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/runner-plan/manifest.json`
- runner preflight manifest: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/runner-preflight/manifest.json`
- runner no-approval manifest: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/runner-noapproval-run/manifest.json`

Approval packet result:

```text
decision: v403-service-manager-start-only-retry-approval-packet-ready
pass: True
reason: approval packet ready; live start-only still requires separate exact approval
live_execution_approved: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

V403 runner preflight:

```text
decision: service-manager-start-only-live-preflight-ready
pass: True
reason: read-only preflight is ready; live run still needs approval
daemon_start_executed: False
wifi_bringup_executed: False
```

No-approval refusal:

```text
decision: service-manager-start-only-live-approval-required
pass: True
reason: exact approval phrase required; no mutation executed
daemon_start_executed: False
wifi_bringup_executed: False
```

## Key Checks

| check | status | detail |
| --- | --- | --- |
| `v402-helper-v22-deploy-pass` | `pass` | `decision=execns-helper-v22-deploy-pass pass=True` |
| `v402-private-selinux-proof-pass` | `pass` | `decision=private-selinux-surface-proof-pass pass=True` |
| `v402-no-daemon-no-wifi` | `pass` | V402 evidence has no daemon or Wi-Fi execution |
| `v402-postflight-ready` | `pass` | `decision=private-selinux-surface-proof-preflight-ready pass=True` |
| `v403-runner-plan-ready` | `pass` | `service-manager-start-only-live-plan-ready` |
| `v403-runner-preflight-ready` | `pass` | `service-manager-start-only-live-preflight-ready` |
| `v403-runner-noapproval-refuses` | `pass` | `service-manager-start-only-live-approval-required` |

Runner preflight confirmed:

- native version/status/selftest are clean.
- helper v22 is deployed and exposes service-manager start-only mode.
- `servicemanager` and `hwservicemanager` binaries are visible.
- linkerconfig/APEX/vendor block inputs are visible.
- private property root is visible.
- no service-manager process is already running.
- no Wi-Fi link surface is active.
- temporary Binder nodes are absent before the helper owns lifecycle setup.

## Approval Phrase

Required future approval:

```text
approve v403 service-manager start-only retry only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Scope After Approval

The phrase above would approve only:

- bounded `servicemanager` and `hwservicemanager` start-only retry.
- helper v22 private namespace with SELinuxfs, Binder, linkerconfig, APEX, and property runtime materialization.
- ptrace-lite crash/runtime-gap capture.
- bounded timeout, termination, reap, and postflight cleanliness checks.

It would still not approve:

- Wi-Fi HAL service start.
- `wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag` start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- rfkill writes, ICNSS bind/unbind, firmware mutation, Android partition writes.
- unbounded daemon persistence or boot autostart changes.

## Validation

Commands run:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_start_only_live_runner.py scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py scripts/revalidation/wifi_service_manager_start_only_v403_approval_packet.py

python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py --out-dir tmp/wifi/v403-live-runner-plan-20260520-085342 plan
python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py --out-dir tmp/wifi/v403-live-runner-preflight-20260520-085342 preflight
python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py --out-dir tmp/wifi/v403-live-runner-noapproval-20260520-085350 run

python3 scripts/revalidation/wifi_service_manager_start_only_v403_approval_packet.py --out-dir tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357 run

git diff --check
```

## Next Target

Next live step, if approved, is the V403 bounded start-only retry. Its result must be routed before any Wi-Fi HAL/start/scan/connect approval packet is considered.
