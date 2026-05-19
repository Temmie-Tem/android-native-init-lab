# Native Init v287 Wi-Fi Service-Order Replay Model Plan

- date: `2026-05-19`
- scope: host-side Wi-Fi service-order replay modeling
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_service_order_replay_model.py`

## Summary

v283-v285 proved that bounded `cnss-daemon -n -l` start-only runs are safe and
cleanly reaped, but they do not produce ICNSS/QCA6390 readiness deltas. v286
then mapped the Android/native gap: Android enters a Wi-Fi service ordering
chain around `7s..15s`, while native boot-window evidence has no matching
`android_wifi_action`, HAL, `cnss_diag`, `wificond`, `cnss-daemon`, WLFW/QMI, or
`wlan0` readiness sequence.

v287 does not execute any Android Wi-Fi daemon. It builds a deterministic
service-order replay model by merging:

- v216 Android service graph;
- v228 controlled `cnss-daemon`/`cnss_diag` start plan;
- v286 Android/TWRP/native timing comparison.

The output should decide which service boundary is the next safe investigation
target and which services remain blocked.

## Reference Notes

- Android init service declarations include executable, args, class, user,
  group, capabilities, and interface metadata:
  https://android.googlesource.com/platform/system/core/+/c5c532fc312c9e5a2f2b8fecbfc535af4ffcd245/init/README.md
- Android init can associate services with HIDL/AIDL interfaces, so HAL daemons
  are not just ordinary binaries; service discovery and hwservicemanager/binder
  context matter:
  https://android.googlesource.com/platform/system/core/+/c5c532fc312c9e5a2f2b8fecbfc535af4ffcd245/init/README.md
- HIDL HALs are IPC services between framework and vendor components, so
  starting a Wi-Fi HAL outside Android init needs binder/hwbinder and interface
  registration context:
  https://source.android.com/docs/core/architecture/hidl?hl=en
- HIDL service discovery uses registered named services and can race if the
  server registers after the client request, which is relevant when replaying
  partial Android service ordering:
  https://source.android.com/docs/core/architecture/hidl/services?hl=en

## Inputs

Default inputs:

- `tmp/wifi/v216-service-replay-model/manifest.json`
- `tmp/wifi/v228-controlled-cnss-start-plan/manifest.json`
- `tmp/wifi/v286-icnss-boot-timing-native-20260519-133421/manifest.json`

Required source decisions:

- v216: `replay-model-ready`
- v228: `cnss-start-plan-ready`
- v286: `icnss-boot-timing-gap-mapped`

## Model Design

The model maps v286 Android events onto known Android services:

| Android event | service boundary | v287 policy |
| --- | --- | --- |
| `android_wifi_action` | `vendor.wifi_hal_ext` | model-only |
| `wifi_hal_start` | `vendor.wifi_hal_ext`, with legacy HAL as sibling candidate | blocked |
| `cnss_diag_start` | `cnss_diag` | blocked diagnostic |
| `wificond_start` | `wificond` | model-only |
| `cnss_daemon_start` | `cnss-daemon` | bounded start-only candidate, not executed by v287 |
| `wlfw_start` | readiness checkpoint | observe-only |
| `qmi_server_connected` | readiness checkpoint | observe-only; no QMI payload |
| `bdf_download` | firmware/data checkpoint | observe-only |
| `wlan_fw_ready` | kernel readiness checkpoint | observe-only |
| `firmware_load` | firmware loader checkpoint | observe-only |
| `wlan_driver_log` | driver checkpoint | observe-only |
| `fw_ready_event` | driver checkpoint | observe-only |
| `wlan_netdev` | network device checkpoint | observe-only; no link-up |
| `wiphy_rfkill` | cfg80211/rfkill checkpoint | observe-only; no rfkill write |

## Guardrails

- No live service execution.
- No `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No QMI payload.
- No QRTR nameservice packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind or `driver_override`.
- No firmware path mutation.
- No reboot/recovery/poweroff.
- No Android partition write.

## Expected Decision

PASS:

- `wifi-service-order-replay-model-ready`

FAIL/BLOCKED:

- `wifi-service-order-input-missing`
- `wifi-service-order-input-incomplete`
- `wifi-service-order-unsafe-policy`

The model is considered ready if the three input manifests are present and PASS,
the Android timing chain is mapped to explicit service/checkpoint stages, and no
HAL/supplicant/hostapd service is marked executable in the current phase.

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_service_order_replay_model.py \
  scripts/revalidation/wifi_icnss_boot_timing_compare.py \
  scripts/revalidation/wifi_service_replay_model.py
git diff --check
```

Model run:

```bash
python3 scripts/revalidation/wifi_service_order_replay_model.py \
  --out-dir tmp/wifi/v287-wifi-service-order-replay-model
```

Expected output:

- decision: `wifi-service-order-replay-model-ready`
- no device command execution
- `service-order.json`, `replay-stages.json`, `summary.md`, and `manifest.json`

## Acceptance

- The model identifies `vendor.wifi_hal_ext` as the first Android service-order
  boundary missing from native boot-window evidence.
- `cnss-daemon` is classified as the only already-proven bounded start-only
  service candidate, but v287 still does not execute it.
- Wi-Fi HALs, `wificond`, `wpa_supplicant`, and `hostapd` remain blocked pending
  separate binder/hwbinder/framework/scan-connect gates.
- The next recommendation is not another blind `cnss-daemon` start-only repeat.

## Next

If v287 passes, v288 should inventory HAL/framework service dependencies needed
before any Wi-Fi HAL or `wificond` execution attempt. That means binder,
hwbinder, hwservicemanager, VINTF/interface declarations, property service,
socket paths, SELinux/domain assumptions, user/group/capabilities, and vendor
library namespace requirements.
