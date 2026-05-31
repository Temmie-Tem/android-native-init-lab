# Native Init V1335 Early-CNSS WLFW Parity Observer

## Summary

- Cycle: `V1335`
- Type: bounded live observer
- Decision: `v1335-native-early-cnss-no-wlfw-observe-only`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1334-execns-helper-v277-deploy/manifest.json`
  - `tmp/wifi/v1335-early-cnss-wlfw-parity-observer-live/manifest.json`
  - `tmp/wifi/v1335-early-cnss-wlfw-parity-observer-live/summary.md`
- Helper: `a90_android_execns_probe v277`
- Helper SHA256: `3a61125bd3e2bad9cda8dcac2df75184c3df369ada4a9a0010681c49788a6fd9`
- Script: `scripts/revalidation/native_wifi_early_cnss_wlfw_parity_observer_live_v1335.py`

V1334 deployed helper `v277` to `/cache/bin/a90_android_execns_probe`.
V1335 then ran the early-CNSS observer with `--subsys-trigger-gate
observe-only`, so `/dev/subsys_esoc0` was forbidden even if a WLFW precondition
appeared.

## Key Evidence

| item | value |
| --- | --- |
| observe_only_gate | `1` |
| cnss_diag_started | `1` |
| cnss_daemon_started | `1` |
| mdm_helper_esoc0_fd_seen | `1` |
| surface_poll_count | `32` |
| wlfw_precondition_observed | `0` |
| wlfw_trigger_ready | `0` |
| subsys_esoc0_open_attempted | `0` |
| subsys_trigger.started | `0` |
| all_postflight_safe | `1` |
| post_selftest | `pass=11 warn=1 fail=0` |

The native runtime could start `pm-service`, `mdm_helper`, `cnss_diag`, and
`cnss-daemon -n -l` in the expected private runtime context. `mdm_helper`
reached `/dev/esoc-0`, but CNSS still did not emit the early WLFW precondition
that Android showed before the captured `__subsystem_get(esoc0)` timestamp.

## Decision

This closes the immediate V1332 question: the gap is not just that native opens
`/dev/subsys_esoc0` too early or too late. With `/dev/subsys_esoc0` held closed,
native `cnss-daemon` still does not reach Android's early WLFW userspace state.

Next work should classify the Android-only input/provider that enables early
WLFW state before eSoC power-up. Good candidates are Android `cnss-daemon`
property/runtime deltas, service-manager/binder provider deltas that do not
start Wi-Fi HAL, or vendor init side effects visible before the Android
`wlfw_start` timestamp.

## Safety

Allowed live actions were limited to selinuxfs mount/cleanup, private property
shim, `/vendor/bin/pm-service`, `/vendor/bin/mdm_helper`, `/vendor/bin/cnss_diag`,
and `/vendor/bin/cnss-daemon -n -l`. No `/dev/subsys_esoc0` open, eSoC
controller ioctl/notify, BOOT_DONE spoof, PMIC/GPIO write, service-manager
start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external
ping, flash, boot image write, or partition write occurred.
