# Native Init V433 Android Wi-Fi Auto-connect Containment Report

Date: 2026-05-20

## Summary

V433 added a read-only Android Wi-Fi auto-connect containment sampler and a
boot-complete handoff wrapper.  The corrected live handoff passed with:

```text
decision: v433-android-wifi-autoconnect-exposure-mapped
pass: True
reason: Android Wi-Fi auto-connect is active and route/connectivity evidence shows possible external exposure
wifi_bringup_executed: False
```

The run temporarily booted Android, collected three read-only containment
samples, then restored native init `A90 Linux init 0.9.61 (v319)`.  V433 did not
issue Wi-Fi enable, scan, connect, credentials, DHCP/routing changes, external
packet probes, rfkill/sysfs writes, module operations, `setprop`, or direct
daemon starts.

## Implementation

- `scripts/revalidation/wifi_android_autoconnect_containment_v433.py`
  - records one-shot settings/service/process/socket state;
  - samples `cmd wifi status`, route tables, local `ip route get`, `wlan0`
    state, filtered connectivity state, and filtered Wi-Fi dumpsys state;
  - blocks mutating Wi-Fi commands and external packet-probe commands;
  - classifies stable connection, route/DNS/default-network exposure, and
    listener presence.
- `scripts/revalidation/android_wifi_autoconnect_containment_handoff_v433.py`
  - reuses Android boot-complete handoff and native rollback primitives;
  - runs V433 after Android boot-complete settle;
  - preserves `wifi_bringup_executed=False`.
- `scripts/revalidation/wifi_android_control_gate_v432.py`
  - redaction was tightened so future V432/V433-derived evidence removes
    Wi-Fi security-type suffixes and `networkType=TYPE_*` tokens from redacted
    saved-network lines.

## Static Validation

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_control_gate_v432.py \
  scripts/revalidation/wifi_android_autoconnect_containment_v433.py \
  scripts/revalidation/android_wifi_autoconnect_containment_handoff_v433.py

git diff --check
```

Both checks passed.

Plan and dry-run evidence:

```text
tmp/wifi/v433-android-autoconnect-containment-plan-20260520-155327/
tmp/wifi/v433-android-autoconnect-containment-handoff-plan-20260520-155327/
tmp/wifi/v433-android-autoconnect-containment-handoff-dryrun-20260520-155334/
```

## Live Evidence

Corrected live handoff:

```text
tmp/wifi/v433-android-autoconnect-containment-handoff-live-redactfix2-20260520-160156/
decision: v433-android-wifi-autoconnect-exposure-mapped
pass: True
device_commands_executed: True
device_mutations: True
wifi_bringup_executed: False
```

Collector evidence:

```text
tmp/wifi/v433-android-autoconnect-containment-handoff-live-redactfix2-20260520-160156/v433-android-wifi-autoconnect-containment-run/
decision: v433-android-wifi-autoconnect-exposure-mapped
pass: True
```

Superseded live attempts:

```text
tmp/wifi/v433-android-autoconnect-containment-handoff-live-20260520-155350/
  PASS, but redaction was later tightened for Wi-Fi security-type suffixes.

tmp/wifi/v433-android-autoconnect-containment-handoff-live-redactfix-20260520-155803/
  PASS, but Android dumpsys escaped quotes left `WPA_PSK` suffixes visible.
```

Rollback/postflight after corrected live:

```text
version: A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
status: rc=0 status=ok
```

Redaction scan on corrected evidence:

```text
WPA_PSK: none
targetConfigKey=": none
BSSID=<raw-mac>: none
SSID=": none
Wifi is connected to "<raw>": none
networkType=TYPE_*: none
```

## Containment Findings

V433 observed this stable state across the corrected live samples:

| Item | Value |
| --- | --- |
| `wifi_connected` | `True` |
| `wifi_connected_stable` | `True` |
| `wlan0_has_ip` | `True` |
| `wlan0_ip_stable` | `True` |
| `default_route_wlan` | `True` |
| `route_get_wlan` | `True` |
| `route_stable` | `True` |
| `connectivity_validated_wifi` | `True` |
| `dns_surface_wlan` | `True` |
| `global_listener_observed` | `False` |

The result is a containment warning, not a failure: Android auto-connect is
stable and functional, but the device has validated Wi-Fi connectivity, DNS
surface, and default-route/local-route evidence over `wlan0` before any explicit
test-initiated scan/connect.

## Interpretation

V433 confirms the V432 concern.  Android-managed Wi-Fi is not merely enabled or
HAL-ready; it becomes a validated network with route and DNS exposure through
saved framework state.  The current test did not create that state, but it
proves that serverization or wider network work must treat Android boot as
potentially externally connected unless explicitly contained.

The strongest current conclusions are:

- Wi-Fi auto-connect is stable across the V433 sample window;
- `wlan0` has an IP and is a default-route/local-route candidate;
- Android connectivity considers the Wi-Fi network validated;
- no global listening sockets were observed in the sampled socket surface;
- native rollback remains clean after the Android handoff.

## Next

Recommended next cycle: V434 Android Wi-Fi auto-connect policy gate.

V434 should choose one of two explicit policies before any server exposure:

- disable or contain Android auto-connect for lab runs, then verify cleanup and
  rollback behavior;
- or accept auto-connect as expected and run a longer read-only stability window
  that tracks route/DNS/default-network changes without external probes.
