# V999 Post-SELinux WLFW Route Classifier Plan

## Goal

Decide the next safe route after V998 proved the Android service-window actors
can run under the repaired SELinux context, but WLFW still does not appear.

This is a host-only routing step. It does not boot Android, run ADB, install a
Magisk module, start daemons, open `/dev/subsys_esoc0`, or attempt Wi-Fi
scan/connect.

## Inputs

- V998 post-SELinux service-window result:
  `docs/reports/NATIVE_INIT_V998_ANDROID_SERVICE_WINDOW_POST_SELINUX_2026-05-26.md`
- V966 Android `wlfw_start` attribution:
  `docs/reports/NATIVE_INIT_V966_ANDROID_WLFW_START_ATTRIBUTION_2026-05-26.md`
- V968 Android dmesg/eSoC/GPIO timing classifier:
  `docs/reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md`
- V918 `/dev/subsys_esoc0` soft-reset stall:
  `docs/reports/NATIVE_INIT_V918_MDM_HELPER_SUBSYS_TRIGGER_WAIT_LIVE_2026-05-26.md`
- V923/V924/V965 route guardrails around CNSS, WLFW, and stale
  `qcwlanstate`/`IWifi.start` retries.

## Method

1. Confirm V998 has a clean service-window runtime:
   - all expected actors observed;
   - `wificond` post-exec context is `u:r:wificond:s0`;
   - postflight cleanup is safe.
2. Confirm V998 still has no WLFW precondition and did not execute lower
   triggers such as `qcwlanstate`, `IWifi.start`, eSoC ioctl, or
   `/dev/subsys_esoc0` open.
3. Reuse V966 to preserve the Android-positive ordering:
   - `cnss-daemon wlfw_start`;
   - then `/dev/subsys_esoc0` `__subsystem_get`;
   - then WLAN-PD, ICNSS QMI, BDF, FW-ready, and `wlan0`.
4. Reuse V968 to decide whether the unresolved GPIO transition timing question
   is now relevant.
5. Reject repeated blind native lower triggers if V918/V923/V924/V965 still
   demote them.

## Decision Criteria

Select Android-positive eSoC/GPIO recapture first if all are true:

- V998 service-window actors are clean after SELinux repair.
- V998 still has no WLFW precondition.
- V966 proves Android emits `wlfw_start` before `/dev/subsys_esoc0` get.
- V968 says exact GPIO135/PMIC9/GPIO142 transition timing is not yet captured.
- V918/V923/V924/V965 still reject blind `/dev/subsys_esoc0`,
  `qcwlanstate`, and stale `IWifi.start` retries.

## Next Unit

If V999 passes, V1000 should temporarily boot Android and run a read-only ADB
recapture focused on:

- full `dmesg`;
- focused `dmesg | grep -E "mdm|esoc|gpio|ap2mdm|mdm2ap|pmic|pm8150|pcie|mhi|cnss|wlfw"`;
- `/proc/interrupts` focused samples;
- `/sys/kernel/debug/gpio` if readable;
- `/sys/bus/msm_subsys/devices/subsys9/state`;
- `/sys/bus/esoc/devices/esoc0` read-only surface.

Magisk early sampling remains a fallback only if immediate Android ADB evidence
still cannot capture GPIO135/AP2MDM, PMIC GPIO9, or GPIO142/MDM2AP transition
timing.

## Guardrails

- No Android boot in V999.
- No ADB command in V999.
- No Magisk module in V999.
- No serial device command in V999.
- No service-manager, Wi-Fi HAL, `cnss-daemon`, `mdm_helper`, or `wificond`
  start in V999.
- No scan/connect, credentials, DHCP, routes, or external ping.
- No eSoC ioctl or `/dev/subsys_esoc0` open.
- No GPIO/sysfs/debugfs write.
- No boot image or partition write.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_selinux_wlfw_route_classifier_v999.py
python3 scripts/revalidation/native_wifi_post_selinux_wlfw_route_classifier_v999.py
```
