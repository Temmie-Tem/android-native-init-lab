# Native Init V434 Android Wi-Fi Auto-connect Policy Report

Date: 2026-05-20

## Summary

V434 added a host-side Android Wi-Fi auto-connect policy selector and a wrapper
that refreshes V433 containment evidence before selecting policy.  The live
handoff passed with:

```text
decision: v434-android-wifi-policy-contain-first-pass
pass: True
policy: contain-first
reason: V433 mapped stable Wi-Fi auto-connect with route/DNS exposure; choose containment before serverization
wifi_bringup_executed: False
```

The run temporarily booted Android through the nested V433 handoff, collected
fresh read-only containment evidence, selected the `contain-first` policy, and
restored native init `A90 Linux init 0.9.61 (v319)`.  V434 did not add Wi-Fi
enable/disable, scan/connect, credential, DHCP/routing mutation, external
packet-probe, or server-exposure steps.

## Implementation

- `scripts/revalidation/wifi_android_autoconnect_policy_v434.py`
  - consumes latest or explicit V433 containment manifest;
  - maps stable route/DNS exposure to `contain-first`;
  - records blocked actions and allowed next actions.
- `scripts/revalidation/android_wifi_autoconnect_policy_handoff_v434.py`
  - reruns the V433 read-only containment handoff;
  - restores native init through the inherited V433 rollback path;
  - runs V434 policy selection against the fresh V433 manifest.

## Static Validation

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_autoconnect_policy_v434.py \
  scripts/revalidation/android_wifi_autoconnect_policy_handoff_v434.py

git diff --check
```

Both checks passed.

Plan, host-run, and dry-run evidence:

```text
tmp/wifi/v434-android-autoconnect-policy-plan-20260520-161113/
tmp/wifi/v434-android-autoconnect-policy-hostrun-20260520-161113/
tmp/wifi/v434-android-autoconnect-policy-handoff-plan-20260520-161113/
tmp/wifi/v434-android-autoconnect-policy-handoff-dryrun-20260520-161113/
```

## Live Evidence

Corrected live handoff:

```text
tmp/wifi/v434-android-autoconnect-policy-handoff-live-20260520-161134/
decision: v434-android-wifi-policy-contain-first-pass
pass: True
device_commands_executed: True
device_mutations: True
wifi_bringup_executed: False
```

Nested fresh V433 evidence:

```text
tmp/wifi/v434-android-autoconnect-policy-handoff-live-20260520-161134/v433-containment-handoff/
decision: v433-android-wifi-autoconnect-exposure-mapped
pass: True
```

Policy evidence:

```text
tmp/wifi/v434-android-autoconnect-policy-handoff-live-20260520-161134/v434-policy/
decision: v434-android-wifi-policy-contain-first-pass
policy: contain-first
next_gate: V435 bounded auto-connect disable/containment proof; no scan/connect/server exposure
```

Rollback/postflight:

```text
version: A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
status: rc=0 status=ok
```

Redaction scan on live evidence:

```text
WPA_PSK: none
targetConfigKey=": none
BSSID=<raw-mac>: none
SSID=": none
Wifi is connected to "<raw>": none
networkType=TYPE_*: none
```

## Policy Findings

Fresh V433 evidence used by V434:

| Item | Value |
| --- | --- |
| `wifi_connected` | `True` |
| `wifi_connected_stable` | `True` |
| `wlan0_has_ip` | `True` |
| `default_route_wlan` | `True` |
| `route_get_wlan` | `True` |
| `route_stable` | `True` |
| `connectivity_validated_wifi` | `True` |
| `dns_surface_wlan` | `True` |
| `global_listener_observed` | `False` |

Selected policy:

```text
policy: contain-first
blocked:
  - server exposure
  - explicit scan/connect
  - credential operations
  - DHCP or routing mutation
  - external packet probes
  - new listeners on Wi-Fi-facing routes
allowed next:
  - bounded Wi-Fi disable/containment proof
  - post-cleanup route/DNS/listener verification
  - native rollback verification
  - documentation of lab auto-connect policy
```

## Interpretation

V434 makes the next step explicit.  Android-managed Wi-Fi is usable, but it is
already externally routed through saved auto-connect state at boot-complete.
That is not a good point to expose services or run explicit scan/connect tests.

The safe next step is not more bring-up.  It is containment:

- prove an intentional disable/containment action can stop auto-connect for lab
  runs;
- verify route, DNS, validated-network, and listener surfaces after cleanup;
- keep native rollback clean;
- only then decide whether serverization can proceed in a controlled network
  state.

## Next

Recommended next cycle: V435 bounded Android Wi-Fi auto-connect containment
proof.

V435 may use a mutating cleanup action only inside a bounded gate.  It should
still forbid scan/connect, credentials, server exposure, and external probes.
