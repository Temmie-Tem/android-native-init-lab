# Native Init V702 cnss2 Focus Surface Classifier Plan

- date: `2026-05-24 KST`
- cycle: `v702`
- type: host-only classifier over V700 live evidence

## Goal

V701 classified the remaining blocker as a pre-WLFW kernel/platform
progression gap. V700 helper v119 already emitted read-only cnss2/icnss/QCA
focus capture during the provider-first retry window. V702 structures that
capture and answers:

- whether the `icnss` platform driver is bound;
- whether the `qca6390` platform node is visible;
- whether `qca6390` has a driver link;
- whether `wlan0` or debug ICNSS surfaces exist;
- whether the evidence still blocks Wi-Fi HAL/scan/connect.

## Inputs

- `tmp/wifi/v700-provider-first-cnss-orchestrated-run/manifest.json`
- `tmp/wifi/v701-pre-wlfw-trigger-classifier/manifest.json`
- `tmp/wifi/v700-provider-first-cnss-orchestrated-run/arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt`
- `tmp/wifi/v700-provider-first-cnss-orchestrated-run/arm-v700-v119-provider-first-cnss/live/native/dmesg-delta.txt`

## Guardrails

V702 must not:

- contact the device;
- mount or bind mount filesystems;
- start daemons or service managers;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan, connect, link up, use credentials, DHCP, route changes, or external
  ping;
- write sysfs/debugfs, boot images, or partitions.

## Implementation

Add `scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py`.

The classifier parses:

- V700 and V701 manifests;
- V700 helper key/value output;
- `A90_EXECNS_DIR_*` focus blocks;
- `A90_EXECNS_PATH_*` focus blocks;
- V700 dmesg marker absence.

## Decision Criteria

`v702-qca6390-platform-binding-gap-classified` requires:

- V700 provider-first retry and V701 pre-WLFW classifier are ready;
- focus capture is complete for `service74_open` and `window`;
- `/sys/bus/platform/drivers/icnss` is bound to `18800000.qcom,icnss`;
- `/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390` is visible;
- the `qca6390` node has no `driver` symlink in the captured window;
- `wlan0` and `/sys/kernel/debug/icnss` are absent;
- WLFW/BDF/`wlan0` dmesg markers remain zero.

## Validation Plan

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py

python3 scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py \
  --out-dir tmp/wifi/v702-cnss2-focus-surface-plan-check plan

python3 scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py \
  --out-dir tmp/wifi/v702-cnss2-focus-surface-classifier run
```

## Next Gate

If V702 classifies the binding gap, plan V703 as Android-vs-native qca6390 and
icnss binding reference comparison. Do not write `bind`/`unbind`, start Wi-Fi
HAL, scan/connect, DHCP, credentials, or external ping until the Android/native
delta is known.
