# Native Init v405 Composite Wi-Fi HAL Approval Packet Plan

## Goal

Prepare the first bounded composite Wi-Fi HAL start-only path after V404.

V405 is an approval packet and helper/runner implementation stage. It does not deploy the helper, start service-manager, start Wi-Fi HAL, or bring up Wi-Fi unless later exact approval phrases are provided.

## Starting Evidence

- V404 readiness report: `docs/reports/NATIVE_INIT_V404_PRIVATE_COMPOSITE_HAL_READINESS_PACKET_2026-05-20.md`
- V404 packet evidence: `tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/`

V404 proved:

```text
decision: v404-private-composite-hal-readiness-packet-ready
first_hal_candidate: vendor.wifi_hal_ext
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Implementation

Update `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper v23:

- add `wifi-hal-composite-start-only` mode.
- add `vendor-wifi-hal-ext` and `vendor-wifi-hal-legacy` target profiles.
- add explicit `--allow-wifi-hal-start-only` gate.
- require `--allow-service-manager-start-only` together with HAL approval.
- keep scan/connect/link-up, `wificond`, supplicant, hostapd, CNSS/diag, DHCP, routing, rfkill, firmware mutation, and persistence outside the mode.
- supervise `servicemanager`, `hwservicemanager`, and one Wi-Fi HAL candidate in one helper-owned private namespace.

Add host tooling:

- `scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py`
  - fail-closed runner for plan/preflight/run.
  - `run` without exact approval executes no device command.
  - approved run targets only composite HAL start-only.
- `scripts/revalidation/wifi_execns_helper_v23_deploy_preflight.py`
  - deploy wrapper for `/cache/bin/a90_android_execns_probe` helper v23.
  - exact deploy approval required.
- `scripts/revalidation/wifi_composite_hal_v405_approval_packet.py`
  - builds/audits helper v23 locally.
  - verifies V404 readiness.
  - verifies deploy and HAL runner fail-closed behavior.
  - records exact future approval phrases.

## Approval Boundaries

Deploy approval phrase:

```text
approve v405 deploy execns helper v23 only; no daemon start and no Wi-Fi bring-up
```

This approves only `/cache/bin/a90_android_execns_probe` helper v23 install/verification.

HAL start-only approval phrase:

```text
approve v405 composite Wi-Fi HAL start-only smoke only; no scan/connect/link-up and no Wi-Fi bring-up
```

This approves only a bounded helper-owned private namespace that supervises:

- `servicemanager`
- `hwservicemanager`
- `vendor.wifi_hal_ext`

Still not approved:

- `wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag`.
- Wi-Fi scan/connect/link-up, credentials, DHCP, routing.
- rfkill writes, ICNSS bind/unbind, module load/unload, firmware mutation.
- Android partition writes.
- unbounded daemon persistence or boot autostart.

## Validation Plan

Static/build checks:

```text
python3 -m py_compile \
  scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py \
  scripts/revalidation/wifi_execns_helper_v23_deploy_preflight.py \
  scripts/revalidation/wifi_composite_hal_v405_approval_packet.py

bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v405-a90_android_execns_probe-v23/a90_android_execns_probe

git diff --check
```

Guard checks:

```text
python3 scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py \
  --out-dir tmp/wifi/v405-composite-hal-runner-plan-$(date +%Y%m%d-%H%M%S) \
  plan

python3 scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py \
  --out-dir tmp/wifi/v405-composite-hal-runner-noapproval-$(date +%Y%m%d-%H%M%S) \
  --helper-sha256 64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520 \
  run
```

Expected:

```text
plan: composite-hal-start-only-plan-ready
no-approval run: composite-hal-start-only-approval-required
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Approval packet:

```text
python3 scripts/revalidation/wifi_composite_hal_v405_approval_packet.py \
  --out-dir tmp/wifi/v405-composite-hal-approval-packet-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected:

```text
decision: v405-composite-hal-approval-packet-ready
pass: True
live_execution_approved: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

## Next Step

If the operator provides the exact V405 deploy phrase, deploy helper v23 only. After deploy, run the V405 composite HAL runner preflight before considering the separate HAL start-only approval phrase.
