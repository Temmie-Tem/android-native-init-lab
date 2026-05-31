# V1245 PMIC/GDSC Reachability Classifier

- report: `docs/reports/NATIVE_INIT_V1245_PMIC_GDSC_REACHABILITY_CLASSIFIER_2026-05-31.md`
- classifier: `scripts/revalidation/native_wifi_pmic_gdsc_reachability_classifier_v1245.py`
- evidence: `tmp/wifi/v1245-pmic-gdsc-reachability-classifier/manifest.json`
- result: `v1245-soft-reset-reached-pmic-gdsc-not-applied`
- pass: `true`

## Scope

V1245 is host-only. It connects existing V918, V1243, and V1244 evidence to
answer the immediate reachability question before another live `esoc0` trigger.
No device command or mutation is executed.

## Evidence

| Surface | Evidence |
| --- | --- |
| Native soft-reset stack | V918 reports `sdx50m_toggle_soft_reset -> mdm4x_do_first_power_on -> mdm_cmd_exe -> mdm_subsys_powerup -> __subsystem_get -> subsys_device_open` |
| Current native esoc0 path | V1243 reports `pm-service` reaching `/dev/subsys_esoc0` with 14 response samples |
| Current native PMIC state | PM8150L soft-reset line remains `pin 7 (gpio9): (MUX UNCLAIMED)` |
| Current native GDSC state | `pcie_1_gdsc` and `pcie_0_gdsc` remain `0mV` |
| Current native downstream response | GPIO142 `[0]`, PCI `[0]`, MHI `[0]`, `wlan0` `[0]` |
| Android-positive contrast | PM8150L `gpio9` is claimed as output and Android reaches PCIe RC1/WLAN-PD/ICNSS-QMI/FW-ready/`wlan0` |

## Interpretation

V1245 answers the first half of the V1244 next step:

- Native can reach the proprietary SDX50M soft-reset stack.
- Current native evidence does not show Android-equivalent PM8150L pinctrl
  ownership or PCIe GDSC enablement.
- Therefore the blocker is not simply above `mdm_subsys_powerup`; it is inside
  or immediately after the proprietary soft-reset/power path, before the PMIC
  soft-reset/GDSC/GPIO142/PCIe response becomes visible.

The next useful gate is V1246: either capture the soft-reset stack and PMIC/GDSC
response in the same bounded live run, or reproduce Android's PM8150L pinctrl
setup before another bounded `esoc0` trigger.

## Validation

| Command | Result |
| --- | --- |
| `python3 -m py_compile scripts/revalidation/native_wifi_pmic_gdsc_reachability_classifier_v1245.py` | pass |
| `python3 scripts/revalidation/native_wifi_pmic_gdsc_reachability_classifier_v1245.py run` | pass |

## Safety

- host-only classifier; no device command or mutation executed
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, Wi-Fi bring-up, flash, boot image write, or partition write
