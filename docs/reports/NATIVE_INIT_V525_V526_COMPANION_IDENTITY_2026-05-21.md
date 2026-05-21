# Native Init V525/V526 Companion Identity

## Summary

- target: capture exact Android identity contract before native companion start-only work
- collector: `scripts/revalidation/native_wifi_android_companion_identity_v525.py`
- handoff runner: `scripts/revalidation/android_companion_identity_handoff_v526.py`
- V526 handoff decision: `v526-handoff-pass`
- V525 collector decision: `v525-companion-identity-captured`
- Wi-Fi bring-up: not executed

V523/V524 proved that the missing native Wi-Fi path is likely the Android
companion-service set around QRTR, RMT storage, TFTP, PD mapping, CNSS diag,
and CNSS daemon. Directly starting those binaries in native init would be a
weak proof without Android's observed users, groups, SELinux domains, and
capability state. V525 therefore captures the Android service identity contract
read-only, and V526 performs the approved Android boot handoff plus native
rollback automatically.

## Evidence

Evidence roots:

```text
tmp/wifi/v526-android-companion-identity-handoff-run/
tmp/wifi/v526-android-companion-identity-handoff-run/v525-android-companion-identity-run/
```

V526 live handoff result:

```text
decision: v526-handoff-pass
pass: True
reason: Android handoff, V525 identity recapture, and native rollback completed
boot_partition_write_executed: True
wifi_bringup_executed: False
```

V525 Android collector result:

```text
decision: v525-companion-identity-captured
pass: True
reason: service blocks and process identities captured for required companion set
device_mutations: False
wifi_bringup_executed: False
```

## Native Rollback State

Post-handoff live native status:

```text
init: A90 Linux init 0.9.61 (v319)
boot: BOOT OK shell 4.1s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
adbd: stopped
netservice: disabled tcpctl=stopped
```

## Android Service Contract

| service | init path | command | init user | init group/caps |
| --- | --- | --- | --- | --- |
| `vendor.qrtr-ns` | `/vendor/etc/init/hw/init.qcom.rc` | `/vendor/bin/qrtr-ns -f` | `vendor_qrtr` | `vendor_qrtr`, `NET_BIND_SERVICE` |
| `vendor.rmt_storage` | `/vendor/etc/init/vendor.qti.rmt_storage.rc` | `/vendor/bin/rmt_storage` | `root` | not declared, `shutdown critical`, `ioprio rt 0` |
| `vendor.tftp_server` | `/vendor/etc/init/vendor.qti.tftp.rc` | `/vendor/bin/tftp_server` | `root` | not declared |
| `vendor.pd_mapper` | `/vendor/etc/init/hw/init.target.rc` | `/vendor/bin/pd-mapper` | `system` | `system` |
| `cnss_diag` | `/vendor/etc/init/hw/init.target.rc` | `/system/vendor/bin/cnss_diag -q -f -t HELIUM` | `system` | `system wifi inet sdcard_rw media_rw diag` |
| `cnss-daemon` | `/vendor/etc/init/hw/init.qcom.rc` | `/system/vendor/bin/cnss-daemon -n -l` | `system` | `system inet net_admin wifi`, `NET_ADMIN` |

## Android Runtime Identity

| process | uid | gid | groups | SELinux domain | effective caps |
| --- | --- | --- | --- | --- | --- |
| `qrtr-ns` | `2906` | `2906` | none | `u:r:vendor_qrtr:s0` | `0000000000000400` |
| `rmt_storage` | `9999` | `1000` | `1000 3010` | `u:r:vendor_rmt_storage:s0` | `0000001000000400` |
| `tftp_server` | `2903` | `2903` | `1000 2903 2904 3010` | `u:r:vendor_rfs_access:s0` | `0000001000000400` |
| `pd-mapper` | `1000` | `1000` | none | `u:r:vendor_pd_mapper:s0` | `0000000000000400` |
| `cnss_diag` | `1000` | `1000` | `1010 1015 1023 2002 3003` | `u:r:vendor_wcnss_service:s0` | `0000000000000000` |
| `cnss-daemon` | `1000` | `1000` | `1010 3003 3005` | `u:r:vendor_wcnss_service:s0` | `0000000000001000` |

Captured Android service-state properties:

```text
[init.svc.vendor.qrtr-ns]: [running]
[init.svc.vendor.rmt_storage]: [running]
[init.svc.vendor.tftp_server]: [running]
[init.svc.vendor.pd_mapper]: [running]
[init.svc.cnss_diag]: [running]
[init.svc.cnss-daemon]: [running]
```

Captured binary labels:

```text
/vendor/bin/qrtr-ns: u:object_r:vendor_qrtr_exec:s0
/vendor/bin/rmt_storage: u:object_r:vendor_rmt_storage_exec:s0
/vendor/bin/tftp_server: u:object_r:vendor_rfs_access_exec:s0
/vendor/bin/pd-mapper: u:object_r:vendor_pd_mapper_exec:s0
/vendor/bin/cnss_diag: u:object_r:vendor_wcnss_service_exec:s0
/vendor/bin/cnss-daemon: u:object_r:vendor_wcnss_service_exec:s0
```

## Interpretation

- The direct TWRP/Android handoff approach is valid and now automated for
  identity capture.
- `rmt_storage` and `tftp_server` are declared as root-started services but run
  under constrained Android runtime identities, so native start-only must not
  approximate them as generic root daemons.
- The next native proof should reproduce process order and observable runtime
  surface first, then compare QRTR/QMI/WLFW/BDF markers before any Wi-Fi HAL
  start or Wi-Fi connect attempt.
- `rmt_storage` remains the highest-risk companion in the set because it is
  part of modem storage access; the next helper must use a bounded start-only
  window, explicit cleanup, and no persistence writes.

## Guardrails

- V526 `run` required `--allow-android-boot-flash`,
  `--i-understand-native-rollback`, and `--assume-yes`.
- V525 executed Android ADB read-only commands only.
- No daemon was started by the host collector.
- No Wi-Fi HAL start, `qcwlanstate`, scan, credential, DHCP, route, or
  external ping was executed.
- Native rollback to `A90 Linux init 0.9.61 (v319)` was verified after the
  Android capture.

## Validation

Commands run:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_companion_identity_v525.py \
  scripts/revalidation/android_companion_identity_handoff_v526.py

python3 scripts/revalidation/native_wifi_android_companion_identity_v525.py plan
python3 scripts/revalidation/native_wifi_android_companion_identity_v525.py preflight

python3 scripts/revalidation/android_companion_identity_handoff_v526.py \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  plan

python3 scripts/revalidation/android_companion_identity_handoff_v526.py \
  --out-dir tmp/wifi/v526-android-companion-identity-handoff-dryrun \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run

python3 scripts/revalidation/android_companion_identity_handoff_v526.py \
  --out-dir tmp/wifi/v526-android-companion-identity-handoff-run \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run

python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
```

## Next Gate

Recommended V527:

1. implement a bounded `wifi-companion-start-only` native helper mode using the
   V525 identity contract;
2. start `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`, `cnss_diag`, and
   `cnss-daemon` in the Android-observed order;
3. capture process identity, logs, `/proc/net/qrtr`, QMI/WLFW/BDF markers, and
   cleanup proof;
4. keep scan/connect/link-up, DHCP, routing, and external ping blocked until
   the companion layer shows Android-like readiness markers.
