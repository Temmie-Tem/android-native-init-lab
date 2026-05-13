# v216 Plan: Android Service Replay Model

## Summary

v216 follows v215 `lifecycle-map-ready`. The goal is to transform Android
ICNSS/CNSS/Wi-Fi service evidence into a native replay model without starting
any service.

This is still read-only planning/modeling work. It must not execute
`cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd, rfkill,
link-up, scan, or connect.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v215 PASS, `lifecycle-map-ready`
- modeler: `scripts/revalidation/wifi_service_replay_model.py`
- evidence input:
  - `tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json`
  - `tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json`
  - `tmp/wifi/v206-android-icnss-cnss-map/manifest.json`
- evidence output: `tmp/wifi/v216-service-replay-model`
- report after execution:
  `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`

## Reference Notes

- Android init service definitions include executable path, class, user/group,
  capabilities, disabled/oneshot flags, interfaces, sockets, and property
  triggers. Native init must model these dependencies before attempting service
  execution:
  <https://chromium.googlesource.com/aosp/platform/system/core/+/master/init/README.md>
- v214 showed that driver sysfs reprobe is not a safe substitute for the
  Android userspace lifecycle:
  <https://docs.kernel.org/6.7/driver-api/driver-model/driver.html>

## Inputs

Required:

- v206 Android ICNSS/CNSS map
- v215 lifecycle map

Optional:

- v204 Android/TWRP baseline
- v214 safety-stop manifest
- raw captured init rc command files from v206/v215 evidence directories

## Model Scope

The modeler should classify:

- service name
- executable path
- init rc source file
- class names
- user/group
- capabilities
- interfaces
- disabled/oneshot flags
- property trigger hints
- required firmware evidence
- required runtime evidence
- native availability status
- risk category

Initial first-class services:

- `cnss-daemon`
- `cnss_diag`
- `vendor.wifi_hal_legacy`
- `vendor.wifi_hal_ext`
- `wificond`
- `wpa_supplicant`
- `hostapd`

## Forbidden

- service start
- `ctl.start`, `ctl.restart`, `class_start`
- `svc wifi`
- `cmd wifi set-wifi-enabled`
- Wi-Fi scan/connect
- rfkill writes
- link-up
- module load/unload
- `firmware_class.path` writes
- ICNSS bind/unbind

## Decision Model

- `replay-model-ready`
  - required service graph is extracted and all high-level dependencies are
    classified.
- `replay-model-partial`
  - enough evidence exists for some services, but important service metadata or
    native availability is missing.
- `missing-android-runtime`
  - model shows required Android property/socket/SELinux/framework support is
    too broad for a near-term native replay.
- `manual-review-required`
  - evidence is missing or inconsistent.

## Validation

Static:

```sh
python3 -m py_compile scripts/revalidation/wifi_service_replay_model.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_service_replay_model
wifi_service_replay_model.validate_no_active_commands()
print('v216 command guard PASS')
PY
```

Model run:

```sh
python3 scripts/revalidation/wifi_service_replay_model.py \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --v215-manifest tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json \
  --v215-native-manifest tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json \
  --out-dir tmp/wifi/v216-service-replay-model
```

## Acceptance

- The modeler writes `manifest.json`, `summary.md`, and `service-graph.json`.
- The output names every first-class service and its evidence status.
- The modeler performs no live device command by default.
- The modeler has an active-command guard even though it is currently
  manifest-only.
- The decision explicitly states whether v217 can search for recovery/debug
  controls or whether v216 needs more Android evidence.

## Next Step

If v216 returns `replay-model-ready`, v217 should perform read-only ICNSS
debug/recovery inventory with the service graph as context. If v216 returns
`missing-android-runtime`, pause native replay and reassess whether Wi-Fi
bring-up requires a larger Android compatibility layer.
