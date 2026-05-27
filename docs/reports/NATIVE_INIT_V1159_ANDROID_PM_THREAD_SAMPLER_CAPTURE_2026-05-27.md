# V1159 Android PM Thread Sampler Capture

## Summary

V1159 added an early Magisk `post-fs-data` background sampler for Android PM
actors and reused the Android handoff flow to capture `pm-service`,
`pm_proxy_helper`, `mdm_helper.real`, and `cnss-daemon` thread state through
FW-ready/`wlan0`.

Result: **PASS**.

Evidence directory:

```text
tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019
```

Decision:

```text
v1149-android-mdm-helper-strace-captured-rollback-complete
```

Native rollback:

```text
A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
```

## Key Finding

Android `pm-service`, not `mdm_helper`, owns the lower `esoc0` power-up wait.

The sampler caught this exact PM Binder thread:

```text
label=pm-service
pid=1554
tid=1620
comm=Binder:1554_2
wchan=mdm_subsys_powerup
syscall=56 ...
```

The matching kernel stack:

```text
mdm_subsys_powerup
__subsystem_get
subsys_device_open
chrdev_open
do_dentry_open
vfs_open
path_openat
do_filp_open
do_sys_open
SyS_openat
```

The thread was in uninterruptible sleep:

```text
State: D (disk sleep)
fd 9: /dev/subsys_modem
```

The same Android dmesg lines identify the target subsystem:

```text
[    8.854707] Binder:1554_2: __subsystem_get: modem count:1
[    9.491382] Binder:1554_2: __subsystem_get: esoc0 count:0
[    9.491393] Binder:1554_2: Changing subsys fw_name to esoc0
[   10.263706] icnss_qmi: QMI Server Connected: state: 0x980
[   10.333750] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin
[   10.347832] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin
[   15.344607] wma_wait_for_ready_event: FW ready event received
[   15.784281] dev : wlan0 : event : 16
```

## Interpretation

V1158 showed `mdm_helper.real` stays in `SyS_nanosleep` after
`ESOC_WAIT_FOR_REQ`; V1159 now shows the lower SDX50M/eSoC power-up path is
driven by `pm-service` Binder thread `Binder:1554_2` entering `openat` on a
subsystem char device and blocking in `mdm_subsys_powerup`.

This reconciles the recent PM evidence:

- native V1139/V1140 proved upper PM provider/CNSS connect can be alive;
- Android V1159 proves an additional PM-service Binder action opens the `esoc0`
  subsystem path;
- native still lacks `/dev/subsys_esoc0`, MHI, `ks`, WLFW service `69`, and
  `wlan0`.

So the next native gate should not blindly hold `mdm_helper` longer. It should
reproduce or observe the PM-service Binder request that causes the Android
`pm-service` thread to enter:

```text
openat -> subsys_device_open -> __subsystem_get(esoc0) -> mdm_subsys_powerup
```

## Code Changes

- `scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py`
  - bumps generated module metadata to V1159;
  - clears stale `/data/local/tmp/a90-wifi` before capture;
  - starts an early `post-fs-data` PM thread sampler;
  - stores `pm_thread_samples.txt`, `pm_thread_interesting.txt`,
    `pm_thread_summary.txt`, and per-thread snapshots.
- `scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py`
  - surfaces PM thread sampler files in `android-trace-surface`;
  - classifies PM sample counts, Binder threads, `mdm_subsys_powerup`, and
    dmesg `esoc0` subsystem-get markers.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py \
  scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py

python3 scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py \
  --strace-binary external_tools/userland/bin/strace-aarch64-static-7.0 \
  --wrapper-binary external_tools/userland/bin/a90_mdm_helper_strace_wrapper-aarch64-static

python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1159-pm-thread-sampler-dryrun \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --capture-wifi-ready-timeout 240 \
  --capture-wifi-ready-poll 2 \
  --capture-settle-sleep 15 \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run

python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019 \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --capture-wifi-ready-timeout 240 \
  --capture-wifi-ready-poll 2 \
  --capture-settle-sleep 15 \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run

python3 scripts/revalidation/a90ctl.py --timeout 10 version
python3 scripts/revalidation/a90ctl.py --timeout 20 selftest
```

## Guardrails

- Magisk module only; no direct vendor partition mutation.
- Temporary Android handoff only, with native v724 rollback.
- No native `/dev/subsys_esoc0` retry.
- No native eSoC ioctl.
- No Wi-Fi credentials, scan/connect, DHCP/routes, or external ping.

## Next

V1160 should be host-only/source-first:

1. identify which userspace call into `pm-service` triggers the
   `Binder:1554_2` `openat` path;
2. map the native helper sequence that starts PM actors but misses this Binder
   request;
3. only then add a bounded native gate that reproduces the PM-service request
   without scan/connect/DHCP/external ping.
