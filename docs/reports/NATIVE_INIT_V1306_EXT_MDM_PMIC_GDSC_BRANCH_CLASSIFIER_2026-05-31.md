# Native Init V1306 ext-mdm PMIC/GDSC Branch Classifier

## Summary

- Cycle: `V1306`
- Type: host-only classifier
- Decision: `v1306-pmic-gdsc-prereq-gap-classified`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1306-ext-mdm-pmic-gdsc-branch-classifier/manifest.json`
  - `tmp/wifi/v1306-ext-mdm-pmic-gdsc-branch-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_ext_mdm_pmic_gdsc_branch_classifier_v1306.py`

V1306 compares the extended V1305 native `mdm_subsys_powerup` window against the Android-positive PMIC/PCIe power surface from V1244.

## Key Results

| field | value |
| --- | --- |
| V1305 decision | `v1305-ap2mdm-low-through-extended-powerup-window` |
| powerup window / samples | `5013ms / 42` |
| GPIO135 / GPIO142 high seen | `false / false` |
| MDM status / MHI max | `0 / 0` |
| MHI pipe / ks / wlan0 | `false / false / false` |
| PMIC soft-reset native value | `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270` |
| PCIe1 GDSC native value | `pcie_1_gdsc ... 0mV ...` |
| PCIe0 GDSC native value | `pcie_0_gdsc ... 0mV ...` |

## Reference Check

| reference | result |
| --- | --- |
| Android PMIC GPIO9 configured | `true` |
| Android PCIe RC1 positive | `true` |
| Android WLAN positive | `true` |
| prior native PMIC unclaimed | `true` |
| prior native GDSC 0mV | `true` |
| ext-sdx50m contract deasserts PMIC first | `true` |
| ext-sdx50m contract asserts AP2MDM | `true` |
| ESOC_PWR_ON maps to first power-on | `true` |

## Interpretation

The current native path reaches the PM-service lower trigger and remains in `mdm_subsys_powerup`, but the expected lower power surface does not advance:

- PM8150L soft-reset pinctrl remains unclaimed.
- PCIe GDSCs remain at `0mV`.
- AP2MDM GPIO135 never becomes visible high.
- MDM2AP/PCIe/MHI/WLFW/`wlan0` never appear.

Android-positive evidence has the corresponding PMIC GPIO configured and PCIe RC1 progress. Therefore the blocker is aligned with an ext-mdm PMIC/GDSC prerequisite branch below upper PM/CNSS delivery.

## Next

V1307 should add source/build-only support for a focused no-write PMIC/GDSC transition sampler, or classify exact safe init prerequisites before another live lower trigger.

Still blocked before any direct PMIC/GPIO mutation, direct eSoC ioctl, Wi-Fi HAL start, scan/connect, DHCP, route, credential use, or external ping.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_ext_mdm_pmic_gdsc_branch_classifier_v1306.py
python3 scripts/revalidation/native_wifi_ext_mdm_pmic_gdsc_branch_classifier_v1306.py run
```

Both passed.

## Safety

- Host-only classifier; no bridge/device command.
- No PMIC write, userspace GPIO request/hold, direct eSoC ioctl, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
