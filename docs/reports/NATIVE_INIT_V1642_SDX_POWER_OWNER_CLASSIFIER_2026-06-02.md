# Native Init V1642 SDX50M Power Owner Classifier

## Summary

- Cycle: `V1642`
- Type: host-only SDX50M power owner classifier
- Decision: `v1642-sdx-main-rail-owner-outside-ap-source-pass`
- Result: PASS
- Reason: AP mdm3/eSoC source exposes GPIO handshake only; AP pcie1 supplies are RC-side; SDX VDD_MODEM/WLAN rails live in SDX-side source or bootloader/PMIC domain, not as an AP-native safe write target.

## Checks

- `all_sources_present`: `True`
- `mdm3_ext_sdx50m`: `True`
- `mdm3_has_soft_reset_gpio`: `True`
- `mdm3_has_no_supply_property`: `True`
- `ap_sdx_link_deletes_vdd_mss`: `True`
- `ap_mhi_links_esoc0_to_mdm3`: `True`
- `ap_pcie1_supplies_are_rc_side`: `True`
- `sdx_has_internal_vdd_modem`: `True`
- `sdx_has_wlan_internal_supply`: `True`
- `bootloader_pmic_binaries_absent`: `True`

## Owner Table

| surface | owner | class | finding |
|---|---|---|---|
| AP qcom,mdm3 external-soc node | AP kernel eSoC provider | closed-no-main-rail-control | GPIO handshake only; no regulator/supply property in mdm3 block. |
| AP pcie1 RC supplies | AP msm_pcie driver | diagnostic-not-main-rail | pcie_1_gdsc, pm8150l_l3, pm8150_l5, VDD_CX_LEVEL are RC-side prerequisites; not proven SDX main rail controls. |
| SDXprairie regulators | SDX-side PMIC/RPMH domain | candidate-owner-outside-ap-native | VDD_MODEM_LEVEL, pmxprairie rails, and wlan supplies are defined in SDX-side DTS, not as AP mdm3 controls. |
| bootloader / PMIC config artifacts | bootloader or PMIC firmware if present | missing-artifact | No binary-like xbl/abl/NON-HLOS/pmic/modem artifacts found in bounded repo scope. |

## Interpretation

The unknown SDX50M main-rail prerequisite is not represented as a controllable AP `qcom,mdm3` regulator or AP eSoC provider operation. The AP side links `mhi_0` to `mdm3` and gives pcie1 RC supply names, but those are not sufficient to justify a PMIC/GDSC write gate. SDX-side source names VDD_MODEM and WLAN rails, but those belong to the SDX/PMXPRAIRIE domain and are not currently reachable as a narrow AP-native write surface.

Bounded bootloader/PMIC binary artifact hits: `0`

## Next

V1643 should stay non-mutating: either prepare a read-only partition/artifact acquisition plan for bootloader/PMIC ownership evidence, or hand off that external artifact gap explicitly. Do not design a live PMIC/GPIO/GDSC write until a named owner, voltage/sequence constraints, and rollbackable control surface are identified.

## Safety Scope

V1642 is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
