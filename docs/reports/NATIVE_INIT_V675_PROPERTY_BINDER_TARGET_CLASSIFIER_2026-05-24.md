# Native Init V675 Property/Binder Target Classifier Report

## Summary

- script: `scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py`
- plan evidence: `tmp/wifi/v675-property-binder-targets-plan/`
- run evidence: `tmp/wifi/v675-property-binder-targets/`
- decision: `v675-property-binder-targets-classified`
- pass: `true`
- device commands: `false`
- Wi-Fi HAL start: `false`
- scan/connect/link-up: `false`
- external ping: `false`

V675 is a host-only classifier for the V674 post-HAL/`wificond` blocker. It
uses existing evidence only and does not contact the device.

## Result

| Check | Result |
| --- | --- |
| V674 input ready | pass |
| Android full getprop input | pass, `935` properties |
| property-context rule input | pass, `1264` rules |
| denied property contexts known | pass, `24/24` keys mapped |
| runtime property values known | pass |
| Binder failures targeted | finding, `5` failures |

The denied-property side is now concrete enough for a minimal repair target.
All `24` denied keys map to captured Android property contexts, and the
runtime-required values are available from the Android full getprop capture.

## Property Targets

| Category | Count |
| --- | ---: |
| `log_default` | `11` |
| `linker_debug_default` | `2` |
| `runtime_debug_default` | `8` |
| `runtime_required` | `3` |

Runtime-required targets:

| Property | Context | Type |
| --- | --- | --- |
| `ro.vendor.redirect_socket_calls` | `u:object_r:vendor_socket_hook_prop:s0` | `bool` |
| `ro.debuggable` | `u:object_r:build_prop:s0` | `bool` |
| `ro.vndk.version` | `u:object_r:vndk_prop:s0` | `string` |

The remaining property lookups are log/debug/defaultable categories. They still
need `property_info` coverage so bionic/liblog/linker lookups stop failing, but
most do not need hard-coded values when Android also omits them.

## Binder Target

V675 keeps Binder as a separate target from property-info completeness:

| Actor | Failures |
| --- | ---: |
| `servicemanager` | `1` |
| `hwservicemanager` | `1` |
| `wificond` | `2` |
| `cnss-daemon` | `1` |

The Binder failures remain important, but V675 shows they should not be mixed
with property-context repair. The next live gate should first provide the
missing property-info/value surface, then capture Binder registration and
transaction behavior in a bounded run.

## Interpretation

V674's property failures are not evidence for a broad SELinux-policy blocker.
They are specific property-info/property-area completeness failures:

```text
private property_info/seed incomplete
  -> log/debug/runtime property lookups fail
    -> Android userspace starts but runs with degraded runtime assumptions
      -> Binder registration/transaction failures remain visible
        -> WLFW/BDF/wlan0 still do not advance
```

The next shortest path toward native Wi-Fi is V676:

1. expand the private property-info package for the `24` V675 keys;
2. seed the three runtime-required values from Android capture;
3. keep defaultable log/debug keys as property-info-covered default lookups;
4. rerun a bounded post-HAL/`wificond` capture;
5. inspect Binder registration/transaction behavior before any supplicant,
   scan/connect, DHCP, or external ping attempt.

## Validation

```sh
python3 -m py_compile scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py
python3 scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py --out-dir tmp/wifi/v675-property-binder-targets-plan plan
python3 scripts/revalidation/native_wifi_property_binder_target_classifier_v675.py --out-dir tmp/wifi/v675-property-binder-targets run
```

All validation commands passed. The V675 run produced
`v675-property-binder-targets-classified` and confirmed that no device command,
Wi-Fi HAL start, scan/connect, Wi-Fi bring-up, or external ping was executed.
