# Native Init V913 Android eSoC GPIO Timeline Plan

## Goal

Capture or classify the Android positive boot timeline for the external MDM3 /
SDX50M eSoC path before executing the V912 native `/dev/subsys_esoc0` trigger
gate.

V913 is read-only. It exists to reduce uncertainty around the next risky native
trigger, not to start Wi-Fi in native init.

## Why This Reopens The Android Capture Question

V896 and V905 correctly concluded that a broad Android dmesg/Magisk recapture
was not the immediate blocker at that time. Since then V911 moved the native
boundary forward: `mdm_helper` now owns `/dev/esoc-0` and its worker blocks in
`ESOC_WAIT_FOR_REQ`.

That changes the question. The useful Android evidence is no longer generic
Wi-Fi readiness; it is the exact eSoC boot timeline around:

- AP-to-MDM status assertion, expected GPIO135;
- PMIC reset/deassert activity, expected PMIC GPIO9;
- MDM-to-AP status IRQ, expected GPIO142;
- PCIe RC1/link initialization;
- `mdm3` state transition to `ONLINE`;
- `mdm_helper` / `ks` / MHI pipe appearance;
- WLFW/BDF/`wlan0` positive markers.

## Preferred Method

Use Android normal boot plus immediate ADB read-only capture. A Magisk module is
not required for the first pass because dmesg should retain the boot history
needed for after-the-fact analysis.

Suggested read-only surfaces:

```text
adb shell dmesg
adb shell cat /proc/interrupts
adb shell cat /sys/bus/msm_subsys/devices/subsys9/state
adb shell cat /sys/kernel/debug/gpio
adb shell ps -A -Z
bounded fd summary for mdm_helper/ks only
```

The implementation should use a bounded host script that limits output size and
search scope. Do not run broad recursive scans or unbounded `/proc` dumps.

## Optional Magisk Module Path

Only use a Magisk module if ADB-after-boot dmesg proves too late or incomplete.
If used, keep scripts short and bounded:

- `post-fs-data.sh`: copy dmesg and one interrupt snapshot;
- `service.sh`: take a small number of timed `/proc/interrupts` and
  `subsys9/state` samples;
- no long sleeps that delay Android boot;
- no writes to GPIO, sysfs, debugfs, Wi-Fi, firmware, or boot partitions.

## Classification Questions

1. When does Android assert AP2MDM status relative to `mdm_helper`,
   `/dev/subsys_esoc0`, and `ESOC_WAIT_FOR_REQ`?
2. Does GPIO142 increment before or after `ks` and the MHI pipe appear?
3. Does PCIe RC1/link initialization precede `mdm3=ONLINE`, WLFW, and BDF?
4. Are PMIC reset/deassert markers visible in dmesg or debugfs?
5. Which exact Android-positive markers should the V912-derived native trigger
   observe before it is considered safe to proceed?

## Hard Guardrails

- No native Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
- No native `/dev/subsys_esoc0` trigger in V913.
- No eSoC ioctl, GPIO write, sysfs write, debugfs write, module load/unload,
  firmware mutation, boot image write, or partition write.
- No secret capture; redact Wi-Fi SSIDs, credentials, tokens, serial numbers,
  and unrelated account identifiers from reports.
- Keep evidence private under `tmp/wifi/`; commit only scripts and summaries.

## Success Criteria

- Produce a private evidence bundle with Android dmesg, interrupts,
  `subsys9/state`, GPIO surface if readable, and process/fd summaries.
- Produce a timestamped classifier summary that orders GPIO135, PMIC GPIO9,
  GPIO142, PCIe RC1/link, `mdm3=ONLINE`, `ks`, MHI, WLFW, BDF, and `wlan0`
  markers when present.
- Update the V912 follow-up decision:
  - proceed to V914 source/build-only trigger helper if Android timing supports
    the `mdm_helper`-held `/dev/subsys_esoc0` trigger;
  - otherwise adjust the trigger model before any live native subsystem open.

## Next

If V913 confirms the Android-positive order, V914 should implement the
source/build-only helper support for
`wifi-companion-mdm-helper-runtime-subsys-trigger-capture`. The first native
live trigger remains a separate bounded diagnostic gate with cleanup/reboot
handling.
