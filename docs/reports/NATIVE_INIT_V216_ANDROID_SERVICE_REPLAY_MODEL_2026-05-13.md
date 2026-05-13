# v216 Android Service Replay Model

## Summary

v216 adds a manifest-only Android service replay model for the ICNSS/CNSS/Wi-Fi
service chain. It does not change the native init boot image and does not run
any service.

Result: PASS.

Final decision: `replay-model-ready`.

Reason: first-class Android Wi-Fi/CNSS services are modeled without execution
approval.

## Changes

- Added `scripts/revalidation/wifi_service_replay_model.py`.
- Added v216 plan:
  `docs/plans/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_PLAN_2026-05-13.md`.

## Scope

The modeler consumes v206/v215 manifests and reconstructs a service graph from
captured Android init rc evidence. It writes:

- `tmp/wifi/v216-service-replay-model/manifest.json`
- `tmp/wifi/v216-service-replay-model/service-graph.json`
- `tmp/wifi/v216-service-replay-model/summary.md`

## Static Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_service_replay_model.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_service_replay_model
wifi_service_replay_model.validate_no_active_commands()
print('v216 command guard PASS')
PY
```

Result:

```text
v216 command guard PASS
```

```bash
git diff --check
```

Result: PASS.

## Model Run

Command:

```bash
python3 scripts/revalidation/wifi_service_replay_model.py \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --v215-manifest tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json \
  --v215-native-manifest tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json \
  --out-dir tmp/wifi/v216-service-replay-model
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v216-service-replay-model decision=replay-model-ready reason=first-class Android Wi-Fi/CNSS services are modeled without execution approval
```

## Service Graph

| service | Android state | executable | native availability | risk | blocker |
| --- | --- | --- | --- | --- | --- |
| `cnss-daemon` | running | `/system/vendor/bin/cnss-daemon` | requires vendor/system path alias | kernel-lifecycle-high | ICNSS/CNSS recovery model required |
| `cnss_diag` | running | `/system/vendor/bin/cnss_diag` | requires vendor/system path alias | kernel-lifecycle-high | ICNSS/CNSS recovery model required |
| `vendor.wifi_hal_legacy` | running | `/vendor/bin/hw/android.hardware.wifi@1.0-service` | requires temporary vendor mount | android-hal-high | `SYS_MODULE` capability policy review |
| `vendor.wifi_hal_ext` | running | `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service` | requires temporary vendor mount | android-hal-high | `SYS_MODULE` capability policy review |
| `wificond` | running | `/system/bin/wificond` | requires mounted system | framework-medium | none |
| `wpa_supplicant` | running | `/vendor/bin/hw/wpa_supplicant` | requires temporary vendor mount | active-network-high | scan/connect gate required |
| `hostapd` | seen | `/vendor/bin/hw/hostapd` | requires temporary vendor mount | active-network-high | scan/connect gate required |

Replay order model:

1. `cnss-daemon`
2. `cnss_diag`
3. `vendor.wifi_hal_legacy`
4. `vendor.wifi_hal_ext`
5. `wificond`
6. `wpa_supplicant`
7. `hostapd`

## Guardrails

- No live device commands.
- No service start.
- No `ctl.start` or `ctl.restart`.
- No `class_start`.
- No ICNSS bind/unbind.
- No Wi-Fi enablement.
- No rfkill write.
- No link-up.
- No scan/connect.

## Hashes

```text
50556bb6e5747fae5570720b23005305e1703c9e9c6dae677008eed0d202e5dd  scripts/revalidation/wifi_service_replay_model.py
320c5a1da3d8984ea47ae35057218137674b0397d4eda2d9042f4ade3b5fb6f6  docs/plans/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_PLAN_2026-05-13.md
aa12b46644343065bf9b8712e4a46893e87a508fdc3411fe75eec31f4ba2b671  tmp/wifi/v216-service-replay-model/manifest.json
4218bb9fad86dbbdd2d2f3e31a449975341b060314c228fb777256ac1529ffa5  tmp/wifi/v216-service-replay-model/service-graph.json
f54e724850ca8e8e4931374c7a3dfc95895706954747d46f005049c8b541b1ba  tmp/wifi/v216-service-replay-model/summary.md
```

## Decision

v216 proves that the first-class Android Wi-Fi/CNSS service chain is now mapped
well enough for the next read-only step.

This still does not approve execution. `cnss-daemon` and `cnss_diag` remain
blocked until ICNSS debug/recovery controls are inventoried. Wi-Fi HAL,
`wificond`, supplicant, hostapd, scan, and connect remain blocked by later
gates.

## Next

Plan v217 as ICNSS debug/recovery inventory. The goal is to identify read-only
debugfs/sysfs/ramdump/recovery controls and classify which controls are safe,
dangerous, or unknown before any CNSS execution experiment.
