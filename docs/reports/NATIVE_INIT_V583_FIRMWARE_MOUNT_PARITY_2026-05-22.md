# Native Init V583 Firmware Mount Parity Classifier

- date: `2026-05-22 KST`
- objective: compare Android firmware/modem mount parity against current native global mount namespace before any qcwlanstate or `IWifi.start()` retry
- status: `classified`; Wi-Fi external ping is **not** complete

## Scope

- Android reference:
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt`
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/mounts-core.txt`
- Native read-only captures:
  - `/proc/mounts`
  - `/proc/partitions`
  - `/vendor`
  - `/vendor/firmware_mnt`
  - `/vendor/firmware-modem`
  - `/firmware`
  - `/bt_firmware`
  - ICNSS uevent
  - remoteproc/rpmsg surfaces
- Context:
  - `tmp/wifi/v582-modem-companion-classifier/manifest.json`

## Guardrails

- No mount or unmount.
- No daemon start.
- No sysfs or qcwlanstate write.
- No Wi-Fi HAL or `IWifi.start()` retry.
- No scan/connect/link-up/DHCP/routing.
- No external ping.

## Implementation

- `scripts/revalidation/native_wifi_firmware_mount_parity_v583.py`
  - parses Android firmware/modem mount evidence
  - captures native current mount namespace and targeted firmware path existence
  - verifies native health and ICNSS/partition visibility
  - classifies whether firmware/modem mount parity is missing before the QRTR readiness layer

## V583 Result

Command result:

```text
decision: v583-native-firmware-modem-mount-parity-gap-classified
pass: True
reason: Android mounts /vendor/firmware_mnt and /vendor/firmware-modem before QRTR modem readiness, while native currently has no global firmware/modem mount parity
next: plan V584 bounded firmware/modem mount-parity proof before qcwlanstate/IWifi retry; keep scan/connect blocked
```

Evidence:

- `tmp/wifi/v583-firmware-mount-parity/`

## Android Reference

Android reference has:

```text
vendor_firmware_mnt=True
vendor_firmware_modem=True
firmware_alias=True
bt_firmware_alias=True
```

The key Android dmesg sequence is:

```text
mount source=/dev/block/bootdevice/by-name/apnhlos target=/vendor/firmware_mnt type=vfat = Success
mount source=/dev/block/bootdevice/by-name/modem target=/vendor/firmware-modem type=vfat = Success
qrtr: Modem QMI Readiness RX
qrtr: Modem QMI Readiness TX
sysmon-qmi ready
service-notifier ready
```

## Native Surface

Native current mount namespace:

```text
/system=True
/mnt/system=True
/vendor=False
/system/vendor=False
/vendor/firmware_mnt=False
/vendor/firmware-modem=False
/firmware=False
/bt_firmware=False
```

Other read-only facts:

```text
native_healthy=True
sda28_present=True
sda29_present=True
icnss_uevent_present=True
remoteproc_present=False
rpmsg_present=True
```

## Interpretation

- V582 classified `sysmon-qmi` / `service-notifier` / WLAN-PD as kernel/QMI readiness evidence, not missing startable userspace daemons.
- V583 adds the missing earlier Android precondition: Android mounts firmware/modem partitions before QRTR modem readiness.
- Native currently has only system mounts in the global namespace and no firmware/modem mount parity.
- The next useful live gate is not qcwlanstate or `IWifi.start()`. It is a bounded mount-parity proof that recreates Android's firmware/modem read-only mount surface, then observes whether QRTR modem readiness markers appear.

## Next Gate

Recommended V584:

1. Plan a bounded, cleanup-safe firmware/modem mount parity proof:
   - create private or controlled mount targets
   - mount `apnhlos` read-only at `/vendor/firmware_mnt`
   - mount `modem` read-only at `/vendor/firmware-modem`
   - provide `/firmware` and `/bt_firmware` aliases if needed
2. Observe QRTR/service-notifier/sysmon markers only.
3. Keep qcwlanstate retry, `IWifi.start()`, scan, connect, and external ping blocked until the lower QRTR/modem readiness surface changes.
