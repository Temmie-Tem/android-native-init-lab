# Native Init V853 Android eSoC Actor Handoff Report

## Result

- decision: `v853-android-esoc-actor-surface-captured`
- pass: `true`
- handoff runner: `scripts/revalidation/android_esoc_actor_handoff_v853.py`
- Android collector: `scripts/revalidation/native_wifi_android_esoc_actor_sample_v853.py`
- evidence: `tmp/wifi/v853-android-esoc-actor-handoff/`
- inner evidence:
  `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/`

## Scope

V853 temporarily flashed a known Android boot image, ran an Android read-only
actor/device-node collector, then restored native v724. The Android collector
did not directly open or ioctl eSoC/subsys nodes, enable Wi-Fi, scan/connect,
use credentials, run DHCP, change routes, ping externally, write provider
sysfs/debugfs, export/write GPIOs, load/unload modules, or start services
directly. Rollback restored native v724 with `BOOT OK` and selftest `fail=0`.

## Key Signals

| Signal | Android V853 |
| --- | --- |
| `/dev/esoc-0` | present, char `484:0`, `0660 root:radio`, `vendor_esoc_device` |
| `/dev/subsys_esoc0` | present, char `236:9`, `0640 system:system`, `vendor_ssr_device` |
| `/dev/subsys_modem` | present, char `236:0`, `0640 system:system`, `vendor_ssr_device` |
| `/dev/wlan` | present, char `478:0`, `0660 wifi:wifi`, `vendor_wlan_device` |
| `/dev/qcwlanstate` | absent as a device node |
| `/proc/devices` | `subsys`, `mhi_uci`, `mhi_qdss`, `qcwlanstate`, `esoc`, `diag` |
| FD holders | `mdm_helper`, child `ks`, and `pm-service` |
| Android boot | `sys.boot_completed=1` captured |

## Actor Findings

V853 found three relevant Android userspace holders:

| Process | SELinux domain | Held node | Interpretation |
| --- | --- | --- | --- |
| `/vendor/bin/mdm_helper` | `u:r:vendor_mdm_helper:s0` | `/dev/esoc-0` | primary eSoC actor |
| `/vendor/bin/ks ... -g mdm1` | `u:r:vendor_mdm_helper:s0` | `/dev/esoc-0` | child spawned by `mdm_helper`, uses MHI pipe and modem EFS path |
| `/vendor/bin/pm-service` | `u:r:vendor_per_mgr:s0` | `/dev/subsys_esoc0`, `/dev/subsys_modem` | PeripheralManager owns subsystem references |

This is the important delta from native: native manually materialized only
`/dev/subsys_esoc0`, then blocked in `mdm_subsys_powerup`; Android has both
the real eSoC char node and the PeripheralManager/subsystem actor already
running in their vendor SELinux domains.

## Android Rules

Relevant ueventd rules captured by V853:

```text
/dev/wlan                 0660   wifi       wifi
/dev/subsys_*             0640   system     system
/dev/esoc-0               0660   root       radio
```

Relevant SELinux file contexts:

```text
/dev/esoc.*               u:object_r:vendor_esoc_device:s0
/dev/subsys_.*            u:object_r:vendor_ssr_device:s0
/dev/wlan                 u:object_r:vendor_wlan_device:s0
/vendor/bin/mdm_helper    u:object_r:vendor_mdm_helper_exec:s0
/vendor/bin/ks            u:object_r:vendor_mdm_helper_exec:s0
/vendor/bin/pm-service    u:object_r:vendor_per_mgr_exec:s0
```

Relevant init ordering fragments:

```text
start rmt_storage
service vendor.per_mgr /vendor/bin/pm-service
on property:init.svc.vendor.per_mgr=running
service vendor.mdm_helper /vendor/bin/mdm_helper
start cnss_diag
service cnss_diag /system/vendor/bin/cnss_diag -q -f -t HELIUM
service cnss-daemon /system/vendor/bin/cnss-daemon -n -l
```

## Interpretation

V853 narrows the next native prerequisite. Repeating a manual
`/dev/subsys_esoc0` open is no longer the best test because Android does not
only rely on that single node. Android has:

1. ueventd-created `/dev/esoc-0` with `root:radio` ownership and
   `vendor_esoc_device` label,
2. ueventd-created `/dev/subsys_*` nodes with `system:system` ownership and
   `vendor_ssr_device` label,
3. `pm-service` holding both modem and eSoC subsystem nodes,
4. `mdm_helper` holding `/dev/esoc-0` and spawning `ks` for the MHI/modem EFS
   path.

The next gate should classify the smallest safe native equivalent of this
contract before attempting raw eSoC ioctl, GPIO write, subsystem state write,
HAL start, scan/connect, DHCP/routes, external ping, or boot-image changes.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_esoc_actor_sample_v853.py \
  scripts/revalidation/android_esoc_actor_handoff_v853.py
python3 scripts/revalidation/native_wifi_android_esoc_actor_sample_v853.py \
  --out-dir tmp/wifi/v853-actor-plan-current plan
python3 scripts/revalidation/android_esoc_actor_handoff_v853.py \
  --out-dir tmp/wifi/v853-handoff-plan-current \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  plan
python3 scripts/revalidation/android_esoc_actor_handoff_v853.py \
  --out-dir tmp/wifi/v853-handoff-dryrun-current \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run
python3 scripts/revalidation/android_esoc_actor_handoff_v853.py \
  --out-dir tmp/wifi/v853-android-esoc-actor-handoff \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  --timeout 45 \
  --recovery-timeout 240 \
  --android-timeout 360 \
  --boot-complete-timeout 360 \
  run
git diff --check
```

Result:

```text
decision: v853-android-esoc-actor-surface-captured
pass: True
device_commands_executed: True
device_mutations: True
raw_esoc_open_executed: False
subsys_char_open_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

Post-rollback:

```text
BOOT OK
selftest fail=0
```

## Next Gate

V854 should be a host-only native parity classifier using V853 evidence. It
should decide whether the next safe live step is:

1. ueventd/device-node parity only,
2. `pm-service`/PeripheralManager start-only below HAL/connect,
3. `mdm_helper` plus `/dev/esoc-0` contract classification,
4. or a stricter Android init-order replay.

V854 should not perform raw eSoC ioctl, GPIO/sysfs/debugfs write, subsystem
state write, HAL start, scan/connect, DHCP/routes, external ping, or boot-image
changes.
