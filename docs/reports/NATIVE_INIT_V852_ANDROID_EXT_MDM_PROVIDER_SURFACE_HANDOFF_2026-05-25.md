# Native Init V852 Android ext-mdm Provider Surface Handoff Report

## Result

- decision: `v852-android-mdm3-online-provider-surface-captured`
- pass: `true`
- handoff runner: `scripts/revalidation/android_ext_mdm_provider_surface_handoff_v852.py`
- Android collector: `scripts/revalidation/native_wifi_android_ext_mdm_provider_surface_sample_v852.py`
- evidence: `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/`
- inner evidence:
  `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/`

## Scope

V852 temporarily flashed a known Android boot image, ran an Android read-only
provider-surface collector, then restored native v724. The Android collector did
not enable Wi-Fi, scan/connect, use credentials, run DHCP, change routes, ping
externally, write provider sysfs/debugfs, export/write GPIOs, load/unload
modules, or start services directly. Rollback restored native v724 with
`BOOT OK` and selftest `fail=0`.

## Key Signals

| Signal | Android V852 | Native V851 |
| --- | --- | --- |
| mdm3 state | `ONLINE` | `OFFLINING` |
| mss state | `ONLINE` | not active in idle surface |
| `/dev/esoc*` node | `/dev/esoc-0` present | absent |
| `/dev/subsys_esoc0` node | present | absent until manual mknod |
| GPIO debug | readable | not readable |
| pinctrl debug | present/readable | not present/readable |
| MDM2AP status IRQ | `mdm status` on GPIO 142, count `1` | not observable |
| MHI IRQs | present with nonzero counts | absent |
| WLAN-PD indication | present | absent |
| BDF downloads | `regdb.bin`, `bdwlan.bin` | absent |
| `wlan0` | present in dmesg | absent |

## Android Readiness Timeline

Important Android dmesg markers captured by V852:

- `qrtr: Modem QMI Readiness RX`
- `sysmon-qmi ... modem's SSCTL service`
- `service-notifier ... 180 service`
- `service-notifier ... 74 service`
- `cnss-daemon wlfw_start: Starting`
- `root_service_service_ind_cb ... msm/modem/wlan_pd`
- `wlfw_send_bdf_download_req: BDF file : regdb.bin`
- `wlfw_send_bdf_download_req: BDF file : bdwlan.bin`
- `sysmon-qmi ... esoc0's SSCTL service`
- `dev : wlan0`

The dmesg search also counts strings such as mount option `errors=panic` and
driver build marker `PANIC_ON_BUG`; these are not interpreted as a live kernel
panic. The rollback health check is the authoritative safety signal.

## Interpretation

V852 confirms that the same stock kernel and hardware path can bring mdm3,
WLAN-PD, BDF download, and `wlan0` up under Android. This closes the question of
whether the hardware/stock kernel can reach the target lower Wi-Fi state. The
native blocker is now narrower: native lacks the Android userspace/device-node
and provider activation context that makes mdm3 transition from `OFFLINING` to
`ONLINE`.

The most useful next discriminator is not a direct GPIO write. Android has
actual `/dev/esoc-0` and `/dev/subsys_esoc0` nodes plus ueventd/init context;
native only proved manual `/dev/subsys_esoc0` mknod/open blocks in
`mdm_subsys_powerup`. V853 should classify the Android actor and open/holder
surface for `/dev/esoc-0` and `/dev/subsys_esoc0`: process FDs, SELinux context,
init/ueventd rules, and service ordering. That should happen before any native
GPIO/eSoC write attempt.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_ext_mdm_provider_surface_sample_v852.py \
  scripts/revalidation/android_ext_mdm_provider_surface_handoff_v852.py
python3 scripts/revalidation/android_ext_mdm_provider_surface_handoff_v852.py \
  --out-dir tmp/wifi/v852-handoff-dryrun \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run
python3 scripts/revalidation/android_ext_mdm_provider_surface_handoff_v852.py \
  --out-dir tmp/wifi/v852-android-ext-mdm-provider-surface-handoff \
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
```

Result:

```text
decision: v852-android-mdm3-online-provider-surface-captured
pass: True
device_commands_executed: True
device_mutations: True
wifi_bringup_executed: False
external_ping_executed: False
```

Post-rollback:

```text
BOOT OK
selftest fail=0
```

## Next Gate

V853 should be an Android actor/FD/ueventd classifier for the mdm3/eSoC provider
path. It should capture read-only Android evidence for which process, if any,
holds `/dev/esoc-0` or `/dev/subsys_esoc0`, which SELinux domains are involved,
and which init/ueventd rules create the device nodes. This should be classified
host-side before any native raw eSoC ioctl, GPIO write, subsystem write, HAL
start, scan/connect, DHCP/routes, external ping, or boot-image change.
