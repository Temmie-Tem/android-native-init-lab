# V1158 Android `mdm_helper` Extended Strace Capture

## Summary

V1158 extended the Android handoff capture until the Wi-Fi lower stack reached
FW-ready/`wlan0`, then pulled the Magisk `mdm_helper` strace plus process
snapshots before native rollback.

Result: **PASS**.

Evidence directory:

```text
tmp/wifi/v1158-extended-strace-live-20260527-185829
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

## Key Findings

### Android Wi-Fi lower stack reached FW-ready

The extended capture waited until Android exposed `wlan0`:

```text
wifi_ready=1
wifi_ready_reason=wlan0-netdev
wifi_ready_wait_sec=0
```

The captured Android dmesg includes:

```text
icnss: WLAN FW is ready: 0xd87
wma_wait_for_ready_event: FW ready event received
dev : wlan0 : event : 16
dev : swlan0 : event : 16
dev : p2p0 : event : 16
dev : wifi-aware0 : event : 16
```

### `mdm_helper` does not expose a post-wakelock image transfer path

The strace still stops at the same coarse boundary as V1157:

```text
openat(..., "/dev/esoc-0", O_RDONLY|O_NONBLOCK) = 5
ioctl(5, _IOC(_IOC_NONE, 0xcc, 0x7, 0), 0x800) = 0
ioctl(5, _IOC(_IOC_READ, 0xcc, 0x2, 0x4), ...) = 4
openat(..., "/sys/power/wake_lock", O_WRONLY|O_APPEND) = 6
write(6, "mdm_helper\0", 11) = 11
```

Classifier values:

```text
strace_has_cmd_engine_register = true
strace_has_wait_for_req        = true
strace_has_wakelock            = true
strace_has_ks                  = false
strace_has_mhi_pipe            = false
strace_line_count              = 270
```

This disproves the narrow hypothesis that the missing post-wakelock sequence was
only a too-short host capture window. At FW-ready time, `mdm_helper.real` was
still alive but sleeping:

```text
cmdline: /vendor/bin/mdm_helper.real
wchan:   SyS_nanosleep
fd 5:    /dev/esoc-0
```

The `a90_strace` parent was waiting on the traced child:

```text
cmdline: /vendor/bin/a90_strace ... /vendor/bin/mdm_helper.real
wchan:   do_wait
```

### `pm-service` remains the stronger trigger candidate

At Android FW-ready time, process snapshots show:

```text
pm-service fd 9:       /dev/subsys_modem
pm_proxy_helper fd 3:  /dev/subsys_modem
mdm_helper.real fd 5:  /dev/esoc-0
```

The same Android dmesg shows a `pm-service` Binder thread triggering the eSoC
subsystem path:

```text
[   8.812849] Binder:915_2: __subsystem_get: modem count:1
[   9.142107] init: starting service 'vendor.mdm_helper'
[   9.404287] Binder:915_2: __subsystem_get: esoc0 count:0
[  10.200441] icnss_qmi: QMI Server Connected: state: 0x980
[  10.282887] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin
[  10.302448] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin
[  15.189406] icnss: WLAN FW is ready: 0xd87
```

This shifts the next native repair target back toward the PM actor contract:
`pm-service`/`pm_proxy_helper` must remain alive in the correct runtime domain
and drive the `esoc0` subsystem get path. `mdm_helper` appears to be the eSoC
command-engine participant, not the sole lower trigger.

## Code Changes

- `scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py`
  - bumps the generated Magisk module to V1158;
  - waits passively for FW-ready/`wlan0` before process snapshot;
  - captures `/proc/<pid>/syscall`, `/proc/<pid>/stack`, and `a90_strace` /
    `mdm_helper.real` process directories.
- `scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py`
  - adds `android-wifi-fw-ready-wait`;
  - adds `--capture-wifi-ready-timeout` and `--capture-wifi-ready-poll`;
  - enriches trace classification with FW-ready, `wlan0`, ioctl, wakelock,
    `ks`, MHI pipe, and process snapshot markers.

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
  --out-dir tmp/wifi/v1158-extended-strace-dryrun \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run

python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1158-extended-strace-live-20260527-185829 \
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

V1159 should target `pm-service`/`pm_proxy_helper`, not another blind
`mdm_helper` hold:

1. Capture Android `pm-service` Binder/eSoC thread contract with strace or
   process/thread snapshots.
2. Include `/proc/<pid>/task/*/{wchan,syscall,stack}` to identify the thread
   that issues `__subsystem_get: esoc0`.
3. Compare that contract with native `pm-service exit 255` and current
   `per_mgr_subsys_modem_seen=0` evidence.
4. Keep the same guardrails: no Wi-Fi scan/connect, no DHCP/routes, no external
   ping, no native `/dev/subsys_esoc0` retry.
