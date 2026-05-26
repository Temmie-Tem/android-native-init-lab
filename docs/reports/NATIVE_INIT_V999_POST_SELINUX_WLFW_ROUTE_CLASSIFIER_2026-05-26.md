# V999 Post-SELinux WLFW Route Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only route classifier | `tmp/wifi/v999-post-selinux-wlfw-route-classifier/manifest.json` | `v999-select-android-dmesg-gpio-recapture-before-lower-trigger` |

V999 accepts the Android dmesg/eSoC/GPIO recapture direction, but updates the
version flow: V896 already exists, so the post-V998 routing decision is V999 and
the next capture unit should be V1000.

## Findings

- V998 materially changed the state:
  - service-manager trio, Wi-Fi HAL legacy/ext actors, `wificond`,
    `mdm_helper`, and `cnss-daemon` are observable;
  - `wificond` now execs as `u:r:wificond:s0`;
  - postflight is safe;
  - WLFW precondition is still missing.
- V966 still matters:
  - Android emits `cnss-daemon wlfw_start` before `/dev/subsys_esoc0`
    `__subsystem_get`;
  - direct `/dev/subsys_esoc0` is not the observed cause of `wlfw_start`.
- V968's fallback condition is now active:
  - exact GPIO135/AP2MDM, PMIC GPIO9, and GPIO142/MDM2AP transition timing is
    still unresolved;
  - after a clean service-window retry still failed to produce WLFW, Android
    read-only recapture is justified.
- V918/V923/V924/V965 still demote blind lower retries:
  - repeated `/dev/subsys_esoc0` can stall in `sdx50m_toggle_soft_reset`;
  - stale `qcwlanstate` and `IWifi.start` retries remain lower-confidence
    until the Android-positive lower timing gap is narrowed.

## Decision

The next useful unit is not a Magisk module first. The next useful unit is an
Android-positive, read-only ADB recapture focused on eSoC/GPIO/PMIC/PCIe timing.

If immediate Android ADB evidence still lacks transition timing, then a bounded
Magisk early sampler can be planned as a separate fallback.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_selinux_wlfw_route_classifier_v999.py
python3 scripts/revalidation/native_wifi_post_selinux_wlfw_route_classifier_v999.py
```

Result:

```text
decision: v999-select-android-dmesg-gpio-recapture-before-lower-trigger
pass: True
route: android-positive-control-gpio-esoc-recapture-first
```

## Guardrails

- Host-only classifier.
- No Android boot, ADB command, Magisk module, serial command, actor start,
  service-manager start, Wi-Fi HAL start, scan/connect, credentials, DHCP,
  route, external ping, eSoC ioctl, `/dev/subsys_esoc0` open, GPIO/sysfs/debugfs
  write, boot image write, or partition write occurred in V999.

## Next

Plan V1000 as a temporary Android boot plus read-only ADB capture:

```bash
adb shell dmesg | grep -E "mdm|esoc|gpio|ap2mdm|mdm2ap|pmic|pm8150|pcie|mhi|cnss|wlfw"
```

The capture should also collect full `dmesg`, focused `/proc/interrupts`
samples, `/sys/kernel/debug/gpio` if readable, `subsys9/state`, and eSoC sysfs
read-only state.
