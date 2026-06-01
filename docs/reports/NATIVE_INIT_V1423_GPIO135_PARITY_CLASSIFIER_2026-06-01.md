# Native Init V1423 GPIO135 Parity Classifier

## Summary

- Cycle: `V1423`
- Type: host-only/read-only classifier over existing evidence
- Decision: `v1423-gpio135-low-is-not-actionable-by-itself`
- Result: PASS
- Inputs:
  - `docs/reports/NATIVE_INIT_V1422_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER_HANDOFF_2026-06-01.md`
  - `tmp/wifi/v1422-wifi-test-boot-rc1-window-sampler-handoff/test-rc1-window-result.stdout.txt`
  - `tmp/wifi/v1422-wifi-test-boot-rc1-window-sampler-handoff/test-v1393-dmesg.stdout.txt`
  - `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/gpio-pinctrl-surface.txt`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/interrupts-focus.txt`
  - `tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/v1022-late-android-pm-esoc-timing/android/commands/gpio.txt`

## Evidence

| Signal | Native V1422 | Android reference |
| --- | --- | --- |
| GPIO135/AP2MDM steady debugfs value | `gpio135 : out 0 16mA no pull` in all 5 RC1-window samples | also `gpio135 : out 0 16mA no pull` in V852/V1022/V1158/V1159 snapshots |
| GPIO142/MDM2AP steady debugfs value | `gpio142 : in 0 8mA no pull` in all 5 RC1-window samples | also `gpio142 : in 0/ 0 8mA no pull` in Android snapshots |
| `mdm status` IRQ | count `0` in all V1422 samples | V852 positive capture has count `1` |
| MHI IRQs | absent / `0` | V852 positive capture has MHI IRQs with nonzero counts |
| RC1 result | PHY ready, reset/release path, LTSSM polling, no L0 | Android reaches L0/GEN2 in earlier positive reference |
| WLAN result | no MHI/WLFW/BDF/FW-ready/`wlan0` | Android reaches BDF/FW-ready/`wlan0` |

## Interpretation

V1422 correctly shows GPIO135/AP2MDM low throughout the sampled native
RC1-window. However, existing Android-positive evidence also shows the same
steady-state GPIO135 low value after Android has reached the working Wi-Fi lower
state. Therefore GPIO135 low is not sufficient by itself to prove that native
failed to assert AP2MDM.

The stronger discriminator remains downstream response:

- Android has at least one `mdm status` IRQ and MHI IRQ activity.
- Native V1422 has no `mdm status` IRQ, no L0, no MHI, no WLFW/BDF, and no
  `wlan0`.

The current gap is therefore not "GPIO135 observed low" alone. It is either:

1. AP2MDM is active-low or a short pulse and the current sampler only sees idle
   low; or
2. native is missing an earlier power/refclk/PERST/PMIC prerequisite that lets
   SDX50M respond with GPIO142/PCIe L0 after the corrected RC1 path.

## Decision

Treat GPIO135 low as non-actionable without a higher-frequency transition
capture or an Android-matched time window. The actionable V1422 result is:

- corrected RC1 timing and reset/release path are present;
- endpoint response is absent;
- GPIO142/MDM2AP IRQ and PCIe L0 remain the next proof points.

## Next

V1424 should remain below connect and should choose one of two safe directions:

1. host-only: compare Android positive dmesg timing against V1422 to determine
   whether RC1 is being triggered before or after the expected MDM2AP transition;
2. source/build-only: prepare a higher-frequency read-only RC1/interrupt sampler
   focused on `mdm status` IRQ and LTSSM timing, without adding any PMIC/GPIO
   write or Wi-Fi scan/connect path.

Do not proceed to credentials, scan/connect, DHCP/routes, external ping, direct
PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan,
or platform bind/unbind from this evidence.
