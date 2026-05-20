# Native Init V438 Android Wi-Fi Re-enable Observation Report

Date: 2026-05-20

## Summary

V438 added and ran a bounded Android Wi-Fi re-enable observation gate.  The live
handoff passed with:

```text
decision: v438-android-wifi-reenable-enabled-contained-pass
pass: True
reason: Wi-Fi re-enable completed, but route/DNS/connectivity exposure was not observed
wifi_enable_executed: True
wifi_bringup_executed: True
```

This is a controlled Wi-Fi bring-up observation, not a scan/connect or server
exposure approval.  Android accepted `cmd wifi set-wifi-enabled enabled`, but
the observation window did not show `wlan0` IP, `wlan0` default-route candidate,
route-get via `wlan0`, active validated Wi-Fi connectivity, DNS surface, or
global listening sockets.  Native v319 rollback was verified afterward.

## Implementation

- `scripts/revalidation/wifi_android_reenable_observation_v438.py`
  - performs the bounded pre/enable/post Android observation;
  - allows only `cmd wifi set-wifi-enabled enabled` as the Wi-Fi mutation;
  - rejects scan/connect, credential, server, packet-probe, routing, sysfs,
    rfkill, module, property, and direct daemon-start patterns;
  - records pre/post state and redacted evidence summaries.
- `scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py`
  - boots Android through the known baseline boot image;
  - waits for boot-complete;
  - runs the V438 collector;
  - restores native v319.

## Static Validation

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_reenable_observation_v438.py \
  scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py

git diff --check
```

Both checks passed.

Plan and dry-run evidence:

```text
tmp/wifi/v438-android-wifi-reenable-plan-20260520-165336/
tmp/wifi/v438-android-wifi-reenable-handoff-plan-20260520-165336/
tmp/wifi/v438-android-wifi-reenable-handoff-dryrun-20260520-165336/
```

## Live Evidence

Live evidence:

```text
tmp/wifi/v438-android-wifi-reenable-handoff-live-20260520-165358/
tmp/wifi/v438-android-wifi-reenable-handoff-live-20260520-165358/v438-android-wifi-reenable-observation-run/
```

State markers:

| Item | Pre | Post |
| --- | --- | --- |
| `enabled_by_status` | `False` | `True` |
| `disabled_by_status` | `True` | `False` |
| `wifi_connected` | `False` | `False` |
| `android_auto_connect_observed` | `True` | `True` |
| `wlan0_has_ip` | `False` | `False` |
| `default_route_wlan` | `False` | `False` |
| `route_get_wlan` | `False` | `False` |
| `connectivity_validated_wifi` | `False` | `False` |
| `dns_surface_wlan` | `False` | `False` |
| `global_listener_observed` | `False` | `False` |

Other classification markers:

| Item | Value |
| --- | --- |
| `pre_contained` | `True` |
| `post_exposure` | `False` |
| `listener_safe` | `True` |
| `next_gate` | `V439 decide cleanup or longer enabled observation` |

The `android_auto_connect_observed=True` marker means Android Wi-Fi framework
policy/log evidence still contains autojoin/connectivity-selection clues.  It
did not become an active connection in this run because `wifi_connected`,
`wlan0_has_ip`, route, DNS, and validated connectivity remained false.

## Rollback Verification

Post-live native checks:

```text
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json selftest
python3 scripts/revalidation/a90ctl.py --json status
```

Results:

```text
A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

Redaction scan over the live evidence passed for Wi-Fi credential, SSID/BSSID,
connection-name, and network-type patterns.

## Interpretation

V438 proves the framework re-enable command itself is bounded and observable.
The result is safer than V432/V433 auto-connect exposure because the re-enable
did not produce route/DNS/connectivity surface within the V438 window.

However, Android framework Wi-Fi has now been intentionally set to enabled.
That state may persist into a later Android boot, even though the current boot
image was rolled back to native v319 and the native status is contained.  The
next step should not proceed directly to server exposure or credentials.

## Next

Recommended next cycle: V439 post-reenable persistence and containment decision.

Two safe branches are available:

- run a longer read-only Android enabled observation to see whether delayed
  auto-connect appears without scan/connect or external probes;
- disable Wi-Fi again as cleanup if the project wants to return to the V436
  contained baseline before native-side work.

Do not start Wi-Fi server exposure, credential work, or explicit scan/connect
until V439 resolves this post-reenable state.
