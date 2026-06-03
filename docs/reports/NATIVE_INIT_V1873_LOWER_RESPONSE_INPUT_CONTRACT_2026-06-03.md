# Native Init V1873 Lower Response Input Contract

## Summary

- Cycle: `V1873`
- Type: host/source-only lower-response input contract selector
- Decision: `v1873-lower-response-input-contract-selected-host-pass`
- Label: `lower-response-readonly-sampler-source-build-next`
- Result: PASS
- Reason: The current private SDX50M route and historical post-esoc0 evidence converge on a pre-Wi-Fi lower-response input gap; the next useful unit is a read-only sampler contract around GPIO142, PCIe RC1/L0, pcie1 power/clock state, SSCTL/sysmon, MHI, ks, WLFW, and wlan0, not a connect attempt.
- Evidence: `tmp/wifi/v1873-lower-response-input-contract`

## Checks

| check | value |
|---|---:|
| `v1872_selected_lower_response_input_contract` | `True` |
| `v1870_current_private_route_has_no_wifi_prereq` | `True` |
| `v1239_places_gap_after_powerup_before_response` | `True` |
| `v1371_proves_endpoint_readiness_gap_after_rc1_power` | `True` |
| `v1502_confirms_pre_l0_endpoint_lines_low` | `True` |
| `v1525_parks_mhi_resume_until_first_l0_exists` | `True` |
| `v1662_requires_power_clock_snapshot_without_write_gate` | `True` |
| `wlanpd_firmware_lane_not_connect_ready` | `True` |
| `helper_has_post_pm_private_lower_observer_surface` | `True` |
| `contract_not_already_implemented` | `True` |

## Evidence Chain

- V1872 selector: Decision: `v1872-pm-vote-closed-lower-response-input-next-host-pass` / Label: `pm-vote-closed-lower-response-input-next`
- V1870 current lower state: mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- V1870 PM return: PM-client register/connect/return-path rc: `0` / `0` / `0`
- V1239 response gap: decision: `v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw`
- V1239 GPIO142: | GPIO142 IRQ | `1` | not observed |
- V1239 PCIe: | PCIe RC1 | RC1 reset/L0 present | not observed in lower publication |
- V1239 ks/MHI: | `ks` / MHI pipe | present | absent |
- V1371 RC1: Decision: `v1371-endpoint-readiness-gap-after-rc1-power-proven`
- V1502 pre-L0: Decision: `v1502-pre-l0-parity-confirms-rc1-link-fail-with-endpoint-lines-low`
- V1525 MHI position: Decision: `v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger`
- V1662 power/clock diff: Decision: `v1662-android-native-power-diff-power-vote-gap-pass`
- V1763 firmware-request lane: Decision: `v1763-v1739-equivalent-firmware-request-gate-closed-host-pass` / Fixed label: `firmware-not-requested`.

## Interpretation

V1873 keeps the blocker below the current PM-client/register path and before Wi-Fi connectivity. V1870 proves the latest private SDX50M run still has no WLFW service 69 or `wlan0`, while V1239/V1371/V1502/V1525 place the actionable gap before first usable PCIe L0/MHI/WLFW publication. V1662 adds a required read-only pcie1 power/clock snapshot dimension, but it does not authorize a power/clock write gate.

The WLAN-PD firmware-request lane remains useful evidence, but it is not a connect-ready lane: V1763 fixes the label as `firmware-not-requested`, and the current private SDX50M route still lacks WLFW service 69 and `wlan0`. Therefore the next unit should be a source/build-only read-only sampler contract, not Wi-Fi HAL, scan/connect, DHCP, routes, or ping.

## Next Contract

- Cycle: `V1874`
- Label: `lower-response-readonly-sampler-source-build`
- Type: `source/build-only first; live disabled until artifact sanity`
- Base: extend the v356 `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only` route
- Scope: trigger only from the existing PM-service/CNSS private SDX50M path; do not directly open `/dev/subsys_esoc0`
- Scope: sample GPIO142/MDM2AP IRQ and readable AP2MDM/MDM2AP pin state at dense post-powerup offsets
- Scope: sample pcie1 GDSC/regulator/clock/link-state/read-only dmesg markers without rc_sel/case, PCI rescan, or bind/unbind
- Scope: sample SSCTL/sysmon, MHI bus/devices, `ks` process/fd state, QRTR WLFW service 69, BDF, firmware-ready, and `wlan0`
- Scope: classify lower progress before any Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- Output label: `lower-input-mdm2ap-silent`
- Output label: `lower-input-rc1-natural-attempt-no-l0`
- Output label: `lower-input-power-clock-snapshot-gap`
- Output label: `lower-input-mhi-or-wlfw-progress-readonly-stop`
- Output label: `lower-input-wifi-prereq-present-readonly-stop`
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.

## Safety Scope

V1873 is host/source-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
