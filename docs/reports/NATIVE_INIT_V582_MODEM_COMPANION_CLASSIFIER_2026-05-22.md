# Native Init V582 Modem Companion Classifier

- date: `2026-05-22 KST`
- objective: classify the missing V581 `sysmon-qmi` / `service-notifier` / WLAN-PD readiness path before any more live Wi-Fi retry
- status: `classified`; Wi-Fi external ping is **not** complete

## Scope

- Android evidence:
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt`
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/processes-wifi.txt`
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/initrc-wifi-files.txt`
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/initrc-wifi-grep.txt`
  - `tmp/wifi/v206-android-icnss-cnss-map/android/commands/logcat-wifi-cnss-tail.txt`
- Native read-only surface:
  - `status`
  - `selftest`
  - `/sys/module`
  - `/proc/modules`
  - `/sys/kernel/debug`
  - `/proc/net/protocols`
  - `/proc/net/qrtr`
- Context:
  - `tmp/wifi/v581-icnss-order-gap/manifest.json`

## Guardrails

- No daemon start.
- No sysfs or qcwlanstate write.
- No Wi-Fi HAL or `IWifi.start()` retry.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No partition write.

## Implementation

- `scripts/revalidation/native_wifi_modem_companion_classifier_v582.py`
  - parses Android dmesg/process/init/logcat evidence
  - scans extracted roots for startable companion binaries
  - captures native read-only kernel/module/debug/protocol surfaces
  - classifies whether the V581 gap is a missing userspace daemon or kernel/QRTR readiness path

## V582 Result

Command result:

```text
decision: v582-kernel-modem-companion-readiness-gap-classified
pass: True
reason: sysmon-qmi/service-notifier/WLAN-PD are kernel/QMI readiness evidence, not missing startable userspace daemons; native must trigger the modem QRTR readiness path before qcwlanstate/IWifi retry
next: plan V583 around firmware/modem mounts, QRTR modem readiness trigger, and service-notifier/sysmon kernel surface; keep scan/connect blocked
```

Evidence:

- `tmp/wifi/v582-modem-companion-classifier/`

## Android Evidence

Android dmesg markers:

```text
sysmon-qmi=5
service-notifier=4
wlan_pd=2
qrtr_modem_readiness=2
qrtr-ns=1
cnss_diag=12
cnss-daemon=27
```

Android process evidence:

```text
sysmon-qmi=0
service-notifier=0
qrtr-ns=1
cnss_diag=1
cnss-daemon=1
```

Android init evidence:

```text
sysmon-qmi=0
service-notifier=0
cnss_diag=1
cnss-daemon=1
rmt_storage=1
```

This means Android exposes `sysmon-qmi` and `service-notifier` as kernel/QMI log markers, not as normal Android init services in the captured service list.

## Native Surface

Native read-only state:

```text
native_healthy=True
qipcrtr_protocol_present=True
proc_net_qrtr_present=False
sysmon module/debug hits=0
service-notifier module/debug hits=0
```

The current native kernel has the `QIPCRTR` protocol registered, but still has no `/proc/net/qrtr` surface and no observed `sysmon-qmi` / `service-notifier` / WLAN-PD readiness marker.

## Binary Scan

Extracted root scan:

```text
sysmon-qmi=False
service-notifier=False
service_notifier=False
cnss-daemon=True
cnss_diag=True
```

The local extracted roots do not provide startable `sysmon-qmi` or `service-notifier` binaries. Starting another userspace companion daemon is therefore not the next justified gate.

## Interpretation

- V579 already modeled the startable native companion stack: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `cnss_diag`, and `cnss-daemon`.
- V581 showed Android reaches QRTR modem readiness, `sysmon-qmi`, `service-notifier`, WLAN-PD, WLFW, QMI, and BDF/FW-ready, while native does not.
- V582 classifies `sysmon-qmi` and `service-notifier` as kernel/QMI readiness evidence rather than missing Android init daemons.
- The next live-changing work should not be another qcwlanstate or `IWifi.start()` retry. The next gate should explain why native does not trigger the QRTR modem readiness path that Android reaches at about 6–7 seconds after boot.

## Source References

Qualcomm kernel sources provide the relevant component class:

- `service-notifier.c`: https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/drivers/soc/qcom/service-notifier.c
- `sysmon-qmi.c`: https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/drivers/soc/qcom/sysmon-qmi.c
- `qrtr.c`: https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/net/qrtr/qrtr.c

## Next Gate

Recommended V583:

1. Classify firmware/modem mount parity in native against Android:
   - `/vendor/firmware_mnt`
   - `/vendor/firmware-modem`
   - `/firmware`
   - `/bt_firmware`
2. Inspect read-only QRTR/modem trigger surfaces:
   - remoteproc/subsys nodes
   - rpmsg/glink nodes
   - service locator strings
   - modem readiness dmesg deltas
3. Keep qcwlanstate retry, `IWifi.start()`, scan, connect, and external ping blocked until a lower QRTR/modem readiness input changes.
