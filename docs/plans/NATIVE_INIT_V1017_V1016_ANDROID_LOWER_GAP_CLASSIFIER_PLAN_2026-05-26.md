# V1017 V1016 Android Lower Gap Classifier Plan

- date: `2026-05-26`
- type: host-only classifier
- selected after: V1016 after-fd Wi-Fi surface matrix live
- target: choose the next safe live gate toward WLFW/BDF/`wlan0`

## Objective

Compare V1016 native evidence against existing Android-positive dmesg evidence
to decide whether the current WLFW-precondition gate is circular.

V1016 proved:

- `mdm_helper` reached `/dev/esoc-0` fd-positive state
- service-manager, Wi-Fi HAL legacy/ext, `wificond`, `cnss_diag`, and
  `cnss-daemon` all started
- WLFW precondition remained absent
- the WLFW-gated `/dev/subsys_esoc0` child did not open

The classifier answers whether the next gate should be Android read-only
recapture/Magisk sampling, or a scoped native `/dev/subsys_esoc0` window after
fd-positive upper-surface parity.

## Inputs

- V1016 live manifest:
  `tmp/wifi/v1016-after-fd-wifi-surface-matrix-live/manifest.json`
- V1000 Android dmesg:
  `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/v913-android-esoc-gpio-timeline-run/android/commands/dmesg-full.txt`
- V1000 Android manifest:
  `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/v913-android-esoc-gpio-timeline-run/manifest.json`
- V968 Android dmesg timing manifest:
  `tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json`
- V1016/V968 reports for interpretation guards

## Method

Add:

```text
scripts/revalidation/native_wifi_v1016_android_lower_gap_classifier_v1017.py
```

The script is host-only and must not contact the device. It extracts:

- V1016 fd/upper-surface/no-WLFW contract
- Android `vendor.mdm_helper`, `cnss-daemon`, `/dev/subsys_esoc0`,
  `wlfw_start`, WLAN-PD, ICNSS QMI ordering
- V968 full Android-positive WLFW/BDF/FW-ready/`wlan0` chain
- whether GPIO transition timing is still secondary or immediately blocking

## Success Criteria

Return:

```text
v1017-select-after-fd-upper-surface-subsys-window
```

only if:

- V1016 proves fd-positive upper-surface parity
- V1016 confirms WLFW missing while `/dev/subsys_esoc0` was not opened
- Android dmesg places `/dev/subsys_esoc0` get in the same narrow window as
  `cnss-daemon wlfw_start`
- Android-positive evidence proves WLFW/BDF/FW-ready/`wlan0`
- GPIO transition timing remains a secondary question, not a blocker for the
  next scoped service-window gate

## Hard Gates

- no device command
- no ADB command
- no boot handoff
- no service/daemon start
- no `/dev/esoc-0` or `/dev/subsys_esoc0` open
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no GPIO/sysfs/debugfs write

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1016_android_lower_gap_classifier_v1017.py
python3 scripts/revalidation/native_wifi_v1016_android_lower_gap_classifier_v1017.py
git diff --check
```
