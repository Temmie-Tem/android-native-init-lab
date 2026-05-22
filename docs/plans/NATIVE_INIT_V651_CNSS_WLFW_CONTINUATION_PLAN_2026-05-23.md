# Native Init V651 CNSS/WLFW Continuation Plan

- date: `2026-05-23 KST`
- cycle: `v651`
- scope: host-only classifier
- target: classify why native V644 reaches service `74` and CNSS netlink but
  does not continue into WLFW/WLAN-PD/QMI/BDF/`wlan0`

## Background

V650 proved the ASoC duplicate `pm_qos` warning is not a native-only final stop
condition. Android V649 and native V644 both continue through sound-card
registration after the warning. The next gap is therefore after the warning and
inside CNSS/WLFW continuation.

## Guardrails

V651 must not:

- contact the device;
- write sysfs or DSP boot nodes;
- start companion daemons, CNSS, service-manager, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V650 manifest:
  `tmp/wifi/v650-post-warning-continuation/manifest.json`
- Android V649 read-only dmesg:
  `tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt`
- Native V644 live dmesg delta:
  `tmp/wifi/v644-live-20260523-071610/native/dmesg-delta.txt`

## Checks

1. Confirm V650 passed before using its post-warning conclusion.
2. Compare Android/native CNSS markers:
   - `cnss_diag` netlink;
   - `cnss-daemon` netlink;
   - `cld80211` lookup;
   - genl failure;
   - binder `ioctl`/transaction failures.
3. Compare WLFW continuation:
   - `wlfw_start`;
   - `wlfw_service_request`;
   - WLAN-PD;
   - QMI server connected;
   - BDF `regdb.bin`/`bdwlan.bin`;
   - WLAN firmware ready;
   - `wlan0`.
4. Treat Android `cnss-daemon Failed to init genl ... continue` as non-fatal
   only if WLFW follows in the same dmesg.
5. Treat native binder `-22` as the next blocker only if native reaches
   CNSS netlink/`cld80211` but never reaches WLFW.

## Success Criteria

V651 passes if it classifies one of:

- `v651-cnss-daemon-binder-blocks-wlfw-continuation`
- `v651-cnss-wlfw-review-required`

A passing classification does not authorize Wi-Fi HAL, scan/connect,
credentials, DHCP, route changes, or external ping. It can only select the next
bounded live gate.

## Expected Next Gate

If native binder failures are confirmed, V652 should be a bounded
service-manager/binder-runtime parity proof around `cnss-daemon` in the existing
service `74`-positive path. The V652 target is WLFW marker movement only, not
Wi-Fi HAL or network association.
