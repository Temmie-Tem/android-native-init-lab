# Native Init V436 Android Wi-Fi Disabled Persistence Report

Date: 2026-05-20

## Summary

V436 added a read-only Android Wi-Fi disabled persistence checker and Android
handoff wrapper.  The live handoff passed with:

```text
decision: v436-android-wifi-disabled-persistence-pass
pass: True
reason: Wi-Fi remained disabled after fresh Android boot and exposure stayed absent
wifi_disable_executed: False
wifi_bringup_executed: False
```

The run temporarily booted Android after V435 had disabled Wi-Fi, collected
read-only persistence evidence without issuing another disable command, and
restored native init `A90 Linux init 0.9.61 (v319)`.

## Implementation

- `scripts/revalidation/wifi_android_disabled_persistence_v436.py`
  - reuses V435's read-only capture list and active-connectivity parser;
  - verifies disabled Wi-Fi status, no `wlan0` IP, no `wlan0` route candidate,
    no active validated Wi-Fi connectivity, no active DNS surface, and no global
    listeners;
  - records `wifi_disable_executed=False`.
- `scripts/revalidation/android_wifi_disabled_persistence_handoff_v436.py`
  - boots Android, runs V436 after boot-complete settle, and restores native
    init v319 through rollback;
  - blocks Wi-Fi enable/disable, scan/connect, server/probe, credential, and
    routing-mutation command patterns from the handoff plan.

## Static Validation

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_disabled_persistence_v436.py \
  scripts/revalidation/android_wifi_disabled_persistence_handoff_v436.py

git diff --check
```

Both checks passed.

Plan and dry-run evidence:

```text
tmp/wifi/v436-android-wifi-disabled-persistence-plan-20260520-164016/
tmp/wifi/v436-android-wifi-disabled-persistence-handoff-plan-20260520-164016/
tmp/wifi/v436-android-wifi-disabled-persistence-handoff-dryrun-20260520-164016/
```

## Live Evidence

Live handoff:

```text
tmp/wifi/v436-android-wifi-disabled-persistence-handoff-live-20260520-164037/
decision: v436-android-wifi-disabled-persistence-pass
pass: True
device_commands_executed: True
device_mutations: True
wifi_disable_executed: False
wifi_bringup_executed: False
```

Collector evidence:

```text
tmp/wifi/v436-android-wifi-disabled-persistence-handoff-live-20260520-164037/v436-android-wifi-disabled-persistence-run/
decision: v436-android-wifi-disabled-persistence-pass
pass: True
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

## Persistence Findings

Live sample state:

| Item | Value |
| --- | --- |
| `enabled_by_status` | `False` |
| `disabled_by_status` | `True` |
| `wlan0_has_ip` | `False` |
| `default_route_wlan` | `False` |
| `route_get_wlan` | `False` |
| `connectivity_validated_wifi` | `False` |
| `dns_surface_wlan` | `False` |
| `global_listener_observed` | `False` |

Derived checks:

```text
disabled: True
no_wlan_ip: True
route_absent: True
connectivity_absent: True
listener_safe: True
```

## Interpretation

V436 proves that V435's Android Wi-Fi containment survives at least one fresh
Android boot-complete handoff.  This is the baseline needed before making a
controlled re-enable decision or returning to native-side Wi-Fi work.

The current state is intentionally contained, not brought up:

- Android Wi-Fi remains disabled;
- no `wlan0` IP or route candidate is present;
- active Wi-Fi connectivity/DNS exposure is absent;
- global listener exposure was not observed;
- native rollback remains clean.

## Next

Recommended next cycle: V437 controlled Android Wi-Fi branch decision.

V437 should choose and document one path:

- controlled Android Wi-Fi re-enable observation, still no scan/connect,
  credentials, server exposure, or external probes; or
- return to native-side Wi-Fi integration while preserving Android disabled
  containment as the safe lab baseline.
