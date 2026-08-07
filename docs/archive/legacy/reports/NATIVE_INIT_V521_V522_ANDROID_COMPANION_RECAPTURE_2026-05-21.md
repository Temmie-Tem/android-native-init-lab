# Native Init V521/V522 Android Companion Recapture

## Summary

- target: Android boot handoff, read-only companion recapture, and native rollback
- V521 runner: `scripts/revalidation/native_wifi_android_companion_recapture_v521.py`
- V522 runner: `scripts/revalidation/android_companion_recapture_handoff_v522.py`
- V522 decision: `v522-handoff-pass`
- V521 decision: `v521-companion-startables-captured`
- pass: `true`
- device mutations: V522 boot partition handoff and rollback only
- Wi-Fi bring-up: not executed

V521/V522 closes the V520 recapture gap. The device was moved from native init
to TWRP, temporarily flashed with the Android baseline boot image, booted into
Android, captured companion-service state over ADB, then rolled back to the
native init boot image. The live run completed and native init was verified
after rollback.

## Evidence

Evidence roots:

```text
tmp/wifi/v522-android-companion-recapture-handoff/
tmp/wifi/v522-android-companion-recapture-handoff/v521-android-companion-recapture-run/
```

Key V522 result:

```text
decision: v522-handoff-pass
pass: True
reason: Android handoff, V521 recapture, and native rollback completed
boot_partition_write_executed: True
device_mutations: True
wifi_bringup_executed: False
```

Key V521 result:

```text
decision: v521-companion-startables-captured
pass: True
reason: Android companion binary candidates were captured
next: export candidates and design bounded native companion start-only proof
device_commands_executed: True
device_mutations: False
wifi_bringup_executed: False
```

## Handoff Steps

| step | result |
| --- | --- |
| native precheck | `A90 Linux init 0.9.61 (v319)` and status OK |
| recovery transition | native `recovery` command succeeded |
| Android boot flash | baseline Android boot image `c15ce425abb8da41...` written and read back |
| Android boot | ADB reported `DEVICE-A90-01 device`; `sys.boot_completed=1` observed |
| Android recapture | V521 completed in read-only mode |
| rollback | native boot image `98cc57153bcc4c23...` restored |
| post-rollback verify | `cmdv1 version` and `cmdv1 status` passed |

Post-rollback live status:

```text
init: A90 Linux init 0.9.61 (v319)
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
adbd: stopped
netservice: disabled tcpctl=stopped
```

## Android Companion Findings

| item | result |
| --- | --- |
| `vendor.qrtr-ns` | running as `qrtr-ns -f` |
| `vendor.pd_mapper` | running as `/vendor/bin/pd-mapper` |
| `cnss_diag` | running as `cnss_diag -q -f -t HELIUM` |
| `cnss-daemon` | running as `cnss-daemon -n -l` |
| service managers | `servicemanager`, `hwservicemanager`, and `vndservicemanager` running |
| Wi-Fi HALs | Android and Samsung vendor Wi-Fi HAL services running |
| QMI support | `sysmon-qmi` and `service-notifier` connection lines present |
| direct mainline set | `rmtfs` and `tqftpserv` not captured as startable binaries |

Captured startable binary and init candidates:

```text
/vendor/etc/init/hw/init.qcom.rc:service qmiproxy /system/bin/qmiproxy
/vendor/etc/init/hw/init.target.rc:service vendor.pd_mapper /vendor/bin/pd-mapper
/vendor/bin/cnss-daemon
/vendor/bin/cnss_diag
/vendor/bin/pd-mapper
/vendor/bin/qrtr-ns
```

Captured process contracts:

```text
qrtr-ns -f
pd-mapper
cnss_diag -q -f -t HELIUM
cnss-daemon -n -l
android.hardware.wifi@1.0-service
vendor.samsung.hardware.wifi@2.0-service
wificond
```

Captured QRTR/QMI readiness lines:

```text
qrtr: Modem QMI Readiness RX cmd:0x2 node[0x0]
qrtr: Modem QMI Readiness TX cmd:0x2 node[0x1]
sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service
sysmon-qmi: ssctl_new_server: Connection established between QMI handle and slpi's SSCTL service
service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service
service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service
```

## Interpretation

- The strong next native candidate is not another `qcwlanstate` retry.
- Android proves `qrtr-ns`, `pd-mapper`, `cnss_diag`, `cnss-daemon`, service
  managers, and Wi-Fi HAL processes are active before a full Wi-Fi stack is
  usable.
- The local Android recapture did not capture `rmtfs` or `tqftpserv` as direct
  startable binaries, so the native path should first try Android-proven vendor
  equivalents instead of assuming the mainline SDM845 service names exist.
- V521 did not execute scan, connect, DHCP, routing, external ping, driver-state
  writes, HAL start, or daemon start from native. It is evidence collection,
  not Wi-Fi bring-up.

## Next Gate

Recommended V523:

1. export the proven Android service contracts for `qrtr-ns`, `pd-mapper`,
   `cnss_diag`, and `cnss-daemon`;
2. verify `qmiproxy` path handling because Android init references
   `/system/bin/qmiproxy`;
3. design a bounded native start-only proof that starts companion services in
   Android-observed order, still with no scan/connect/link-up;
4. observe for native QRTR/QMI/WLFW/BDF markers before allowing any
   `qcwlanstate`, Wi-Fi HAL, scan, credential, DHCP, or external ping step.

## Validation

Commands run:

```bash
python3 scripts/revalidation/android_companion_recapture_handoff_v522.py \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run

python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json status
```

Result:

```text
V522 handoff passed.
V521 companion startables were captured.
Native init v319 was restored and verified after rollback.
```
