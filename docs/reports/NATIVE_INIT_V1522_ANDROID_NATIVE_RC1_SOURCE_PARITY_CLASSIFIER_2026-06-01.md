# Native Init V1522 Android/Native RC1 Source Parity Classifier

## Summary

- Cycle: `V1522`
- Type: host-only classifier over V1521 Android-good and V1518/V1517 native-fail evidence
- Decision: `v1522-sampled-sources-nondiscriminating-msm-pcie-static-needed`
- Result: PASS
- Reason: V1521 Android-good and V1518/V1517 native-fail share the same sampled GPIO/GDSC low/off snapshots, so the next useful branch is msm_pcie TEST:11 vs normal-path semantics

## Inputs

| input | path |
| --- | --- |
| v1521 | tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/manifest.json |
| v1518 | tmp/wifi/v1518-wifi-critical-source-timing-classifier/manifest.json |
| v1517_rc1 | tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-rc1-window-result.stdout.txt |

## Checks

| check | status | detail |
| --- | --- | --- |
| android-good-pre-post-lower-window | pass | V1521 brackets WLFW/BDF/wlan0 with post-fs-data samples and rolls back to native v724 |
| native-source-exact-no-l0-window | pass | V1518/V1517 preserve rc1-ltssm-link-failed-no-l0 with selected sources before link fail |
| sampled-debugfs-sources-nondiscriminating | pass | Android-good and native-fail both show low GPIO135/GPIO142 and 0mV pcie1 GDSC in the sampled windows |
| pcie-l0-marker-still-needs-better-source | pass | V1521 confirms lower Wi-Fi success but does not expose a PCIe L0 dmesg timestamp in this capture |

## Android-Good Window

- WLFW/BDF/wlan0: `8.585121/9.673077/14.843021`
- PCIe L0 dmesg timestamp in V1521: `None`

| sample | uptime | GPIO135 | GPIO142 | GPIO142 IRQ zero | pcie1 GDSC |
| --- | --- | --- | --- | --- | --- |
| first | 5.72 | gpio135 : out 0 16mA no pull | gpio142 : in  0 8mA no pull | True | pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV |
| before_lower | 8.13 | gpio135 : out 0 16mA no pull | gpio142 : in  0 8mA no pull | True | pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV |
| after_lower | 8.74 | gpio135 : out 0 16mA no pull | gpio142 : in  0 8mA no pull | True |  |
| last | 21.74 | gpio135 : out 0 16mA no pull | gpio142 : in  0 8mA no pull | True |  |

## Native-Fail Window

- Decision: `rc1-ltssm-link-failed-no-l0`
- link failed after TEST:11 case: `114.851` ms
- selected source max end: `30` ms

| source | value |
| --- | --- |
| GPIO135 | sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull |
| GPIO142 | sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull |
| GPIO142 IRQ | sample=case_aligned_micro_after_case_0ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status |
| pcie1 GDSC | sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV |

## Interpretation

V1521 captured the Android-good pre/post lower window early enough, but the sampled debugfs/interrupt/regulator sources still look like the native-fail pre-L0 window: GPIO135/GPIO142 low, GPIO142 IRQ count zero, and `pcie_1_gdsc` 0mV. These sources therefore cannot by themselves explain native `POLL_COMPLIANCE -> link failed -> no L0`.

The next useful branch is `msm_pcie` path semantics: classify the corrected debugfs `TEST:11` path against Android's normal RC1 bring-up path and identify operations TEST:11 does not perform. Firmware/MHI/WLFW/scan/connect remain downstream until native RC1 reaches L0 and PCI enumeration.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.

## Next

- V1523 should build the `msm_pcie` TEST:11 vs normal-path static/callgraph classifier.
- Keep firmware/MHI/WLFW/scan/connect parked until native RC1 L0 and PCI enumeration exist.
