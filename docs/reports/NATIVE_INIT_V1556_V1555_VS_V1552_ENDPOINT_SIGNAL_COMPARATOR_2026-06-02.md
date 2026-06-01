# V1556 V1555-vs-V1552 Endpoint Signal Comparator

- generated: `2026-06-01T19:26:49.501646+00:00`
- command: `run`
- decision: `v1556-stable-gap-android-endpoint-signals-native-zero`
- pass: `True`
- reason: host-only comparison fixes the stable delta: Android-good has wake/status endpoint signals while native V1552 remains endpoint-silent after AP-side power/refclk/PERST
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1556-v1555-vs-v1552-endpoint-signal-comparator`

## Inputs

| input | decision | pass | path |
| --- | --- | --- | --- |
| native_v1552 | v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0 | True | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json |
| android_v1555 | v1555-android-good-minimal-trace-reference-pass | True | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v1555-android-good-minimal-trace-reference/manifest.json |

## Comparison

| signal | native_v1552 | android_v1555 | interpretation |
| --- | --- | --- | --- |
| AP-side pcie1 power/refclk/PERST | True | not traced in V1555 minimal set | native preconditions are already proven by V1552 |
| GPIO135/AP2MDM | 0 | 6 | Android-good has AP2MDM activity; V1552 sysfs-enumerate window does not |
| GPIO102/PERST | 2/1 | 21 | both paths can toggle PERST-like GPIO102 |
| GPIO104/pcie wake | 0 | 12 | positive Android endpoint wake signal is absent in native |
| IRQ252/msm_pcie_wake | 0 | 12 | native wake IRQ delta stays zero |
| GPIO142/MDM2AP | 0 | 7 | positive Android mdm status level is absent in native |
| IRQ290/mdm status | 0 | 7 | native mdm status IRQ delta stays zero |
| L0/MHI/lower Wi-Fi | False/False/False | 248.811581/49.775275 | Android lower path is proven; late L0 timing needs caution |

## Interpretation

V1556 fixes the stable signal delta without running the device.  V1552 already proves native AP-side pcie1 GDSC/refclk/pipe-clock/PERST activity, but endpoint response remains zero: no GPIO104/pcie wake, no GPIO142/MDM2AP, no mdm status IRQ, and no L0.  V1555 preserves Android lower Wi-Fi under a lower-impact observer and shows the missing positive endpoint signals: GPIO104/IRQ252 and GPIO142/IRQ290.

The Android timing still has a caveat: retained RC1 L0/MHI excerpts appear after the first WLFW/BDF/FW-ready/`wlan0` lines.  Therefore the next gate should compare stable signal presence/absence, not claim the late L0 excerpt is the first enabling L0.

## Next

- V1557 should either run a native provider+minimal endpoint hold aligned to V1555's positive signals, or first perform a dmesg-only Android timing clarifier if first-L0 ordering is needed.
- Keep firmware/MHI/WLFW/connect work parked until native RC1 L0 and PCI enumeration exist.

## Safety

Host-only classifier. No device command, tracefs/debugfs/sysfs write, reboot, flash, partition write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, direct PMIC/GPIO/GDSC write, eSoC notify, PCI rescan, or platform bind/unbind is performed.
