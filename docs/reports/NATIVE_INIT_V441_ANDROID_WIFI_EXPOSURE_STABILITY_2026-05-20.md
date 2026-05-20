# Native Init V441 Android Wi-Fi Exposure-aware Stability Report

Date: 2026-05-20

## Summary

V441 added and ran a bounded Android-managed Wi-Fi exposure-aware stability
cycle.  The live run passed with:

```text
decision: v441-android-wifi-exposure-stability-cleanup-pass
pass: True
reason: Android-managed Wi-Fi stayed connected/exposed across all samples and cleanup containment passed
wifi_enable_executed: True
wifi_disable_executed: True
wifi_bringup_executed: True
```

V441 used the existing V438 enable handoff and V439 observation/cleanup handoff.
It did not issue explicit scan/connect, credentials, external probes, server
exposure, routing mutation, sysfs/rfkill writes, module operations, `setprop`,
or direct daemon starts.

## Implementation

- `scripts/revalidation/wifi_android_exposure_stability_v441.py`
  - orchestrates V438 controlled enable;
  - orchestrates V439 exposure-aware observation and cleanup disable;
  - classifies sample stability, listener safety, and cleanup containment from
    nested manifests.

## Static Validation

```text
python3 -m py_compile scripts/revalidation/wifi_android_exposure_stability_v441.py

git diff --check
```

Both checks passed.

Plan and dry-run evidence:

```text
tmp/wifi/v441-android-wifi-exposure-stability-plan-20260520-172418/
tmp/wifi/v441-android-wifi-exposure-stability-dryrun-20260520-172418/
```

## Live Evidence

Live evidence:

```text
tmp/wifi/v441-android-wifi-exposure-stability-live-20260520-172446/
tmp/wifi/v441-android-wifi-exposure-stability-live-20260520-172446/v438-enable-handoff/
tmp/wifi/v441-android-wifi-exposure-stability-live-20260520-172446/v439-stability-handoff/
```

Top-level classification:

| Item | Value |
| --- | --- |
| `sample_count` | `11` |
| `exposure_sample_count` | `11` |
| `stable_all_samples` | `True` |
| `cleanup_contained` | `True` |
| `listener_safe` | `True` |
| `v438_decision` | `v438-android-wifi-reenable-enabled-contained-pass` |
| `v439_decision` | `v439-android-wifi-post-reenable-exposure-observed-cleanup-pass` |

Nested V439 sample summary:

| Item | Value |
| --- | --- |
| `sample_count` | `11` |
| `enabled_seen` | `True` |
| `disabled_seen` | `False` |
| `wifi_connected_seen` | `True` |
| `exposure_seen` | `True` |
| `first_exposure_phase` | `sample-000` |
| `listener_safe` | `True` |

Sample edge checks:

| Phase | Elapsed | Wi-Fi Connected | WLAN IP | Default Route | Route-get | Validated | DNS | Global Listener |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `sample-000` | `0.0s` | `True` | `True` | `True` | `True` | `True` | `True` | `False` |
| `sample-010` | `300.0s` | `True` | `True` | `True` | `True` | `True` | `True` | `False` |

Cleanup state from nested V439:

| Item | Value |
| --- | --- |
| `cleanup_ok` | `True` |
| `cleanup_contained` | `True` |
| `cleanup.enabled_by_status` | `False` |
| `cleanup.disabled_by_status` | `True` |
| `cleanup.wlan0_has_ip` | `False` |
| `cleanup.default_route_wlan` | `False` |
| `cleanup.route_get_wlan` | `False` |
| `cleanup.connectivity_validated_wifi` | `False` |
| `cleanup.dns_surface_wlan` | `False` |
| `cleanup.global_listener_observed` | `False` |

As in V439, historical `dumpsys wifi` log lines can keep a parser-level
`wifi_connected` marker true after cleanup.  Active exposure is judged by the
direct IP, route, route-get, DNS, validated connectivity, and listener markers,
all of which were contained after cleanup.

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

V441 proves Android-managed Wi-Fi is not merely reachable; it stays connected,
routed, DNS-enabled, and Android-validated for the full 5-minute bounded sample
window.  No global listener exposure was observed, and cleanup disable restored
the contained lab state.

This is enough to treat Android-managed Wi-Fi as functionally available for
bounded tests.  It is not enough to expose native services over Wi-Fi or perform
credential-changing scan/connect flows.

## Next

Recommended next cycle: V442 credential/target allowlist design.

Rationale:

- V441 already gives a stable 5-minute Android-managed Wi-Fi proof.
- The next risky boundary is not basic connectivity; it is explicit
  scan/connect and credential handling.
- Server exposure remains blocked until listener binding, ACL, authentication,
  and network-scope policy are explicit.
