# Native Init v403 Service-Manager Start-Only Retry Plan

## Goal

Prepare a bounded `servicemanager`/`hwservicemanager` start-only retry after V402 removed the private namespace SELinux surface blocker.

V403 is an approval packet and fail-closed runner stage. It does not run the live start-only attempt unless the exact V403 approval phrase is supplied with `--apply --assume-yes`.

## Starting Evidence

- V402 live report: `docs/reports/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_LIVE_2026-05-20.md`
- V402 helper deploy evidence: `tmp/wifi/v402-execns-helper-v22-deploy-live-20260520-084231/`
- V402 private proof evidence: `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/`
- V402 postflight evidence: `tmp/wifi/v402-private-proof-postflight-20260520-084853/`

V402 proved:

```text
decision: private-selinux-surface-proof-pass
private_selinux_proof.exec_attempted=0
private_selinux_proof.daemon_start_executed=0
private_selinux_proof.wifi_bringup_executed=0
```

## Implementation

Add a V403 live runner wrapper:

- `scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py`
  - reuses the guarded `wifi_service_manager_start_only_live_runner.py` body.
  - fixes helper SHA to v22: `55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6`.
  - uses V317 private property root.
  - uses `ptrace-lite` capture.
  - keeps Wi-Fi HAL/start/scan/connect outside scope.

Add a V403 approval packet generator:

- `scripts/revalidation/wifi_service_manager_start_only_v403_approval_packet.py`
  - checks V402 deploy/proof/postflight manifests.
  - runs the V403 runner in `plan`, `preflight`, and no-approval `run` modes.
  - emits the exact future approval phrase.
  - records that live execution remains unapproved.

Also make the shared runner preflight next-step text generic so wrapper reports do not incorrectly mention V373-specific approval.

## Approval Boundary

Required future live approval phrase:

```text
approve v403 service-manager start-only retry only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Approved after that phrase only:

- bounded `servicemanager` and `hwservicemanager` start-only retry.
- helper v22 private namespace with SELinuxfs, Binder, linkerconfig, APEX, and property runtime materialization.
- ptrace-lite capture for crash/runtime-gap evidence.
- bounded timeout, termination, reap, and postflight process/Wi-Fi cleanliness checks.

Still not approved:

- Wi-Fi HAL service start.
- `wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag` start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- rfkill writes, ICNSS bind/unbind, firmware mutation, Android partition writes.
- unbounded daemon persistence or boot autostart changes.

## Validation Plan

Static checks:

```text
python3 -m py_compile \
  scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py \
  scripts/revalidation/wifi_service_manager_start_only_v403_approval_packet.py

git diff --check
```

Runner guard checks:

```text
python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py \
  --out-dir tmp/wifi/v403-live-runner-plan-$(date +%Y%m%d-%H%M%S) \
  plan

python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py \
  --out-dir tmp/wifi/v403-live-runner-preflight-$(date +%Y%m%d-%H%M%S) \
  preflight

python3 scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py \
  --out-dir tmp/wifi/v403-live-runner-noapproval-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected:

```text
plan: service-manager-start-only-live-plan-ready
preflight: service-manager-start-only-live-preflight-ready
no-approval run: service-manager-start-only-live-approval-required
daemon_start_executed: False
wifi_bringup_executed: False
```

Approval packet:

```text
python3 scripts/revalidation/wifi_service_manager_start_only_v403_approval_packet.py \
  --out-dir tmp/wifi/v403-service-manager-start-only-retry-approval-packet-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected:

```text
decision: v403-service-manager-start-only-retry-approval-packet-ready
pass: True
live_execution_approved: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Step

If the operator provides the exact V403 approval phrase, run only the V403 live runner. After that, route the result before considering any Wi-Fi HAL/start/scan/connect packet.
