# Native Init V1872 Lower Response Input Reconcile

## Summary

- Cycle: `V1872`
- Type: host-only blocker realignment after private SDX50M retry
- Decision: `v1872-pm-vote-closed-lower-response-input-next-host-pass`
- Label: `pm-vote-closed-lower-response-input-next`
- Result: PASS
- Reason: Current and historical evidence already closes PM-client register/connect and post-ack open reachability; private SDX50M reuse is a known lower-response gap, so the next unit should target the response-input contract after mdm_subsys_powerup rather than another PM vote repair.
- Evidence: `tmp/wifi/v1872-lower-response-input-reconcile`

## Checks

| check | value |
|---|---:|
| `v1871_identified_pm_vote_gap` | `True` |
| `v1870_private_retry_has_no_wifi_prereq` | `True` |
| `v1808_pm_client_boundary_closed` | `True` |
| `v1847_post_ack_open_success_static` | `True` |
| `v1849_private_sdx50m_reuse_is_known_lower_gap` | `True` |
| `v1239_gap_after_esoc0_before_response` | `True` |
| `hard_stops_preserved` | `True` |

## Boundary Evidence

- V1870 decision/lower: Decision: `v1870-private-mount-sdx50m-selected-rollback-pass` / lower-continuation label: `lower-continuation-static-gap`
- V1870 lower state: mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- V1808 PM return: PM init return-path rc: `0`
- V1847 open context: open-context path/state/fd: `/dev/subsys_modem` / `0x2` / `0x7`
- V1849 lower-gap line: The known failure is below PM-service eSoC open: native lacks the downstream GPIO142/PCIe/SSCTL/MHI/WLFW/`wlan0` response that Android gets.
- V1239 response gap: decision: `v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw`
- V1239 mdm_subsys_powerup: | Binder `mdm_subsys_powerup` | present | present |
- V1239 GPIO142: | GPIO142 IRQ | `1` | not observed |
- V1239 ks/MHI: | `ks` / MHI pipe | present | absent |

## Interpretation

V1871 correctly avoided another blind private-mount retry, but the older V1808/V1847/V1849/V1239 chain is stronger than a new PM-vote repair: PM-client register/connect/return already reached zero, PM-service post-ack open reached a supported devnode, and the private SDX50M/eSoC route is already known to stall below `mdm_subsys_powerup` before GPIO142, PCIe, MHI, WLFW, BDF, and `wlan0` response.

Therefore V1872 changes the next blocker from `PM register/vote repair` to `lower response-input contract selection`. This is a host-only decision; it does not make a live mutation safe by itself.

## Next

- Cycle: `V1873`
- Label: `lower-response-input-contract-source-only`
- Type: `host/source-only first`
- Scope: Join Android-positive and native-static evidence around mdm_subsys_powerup response inputs: GPIO142 IRQ, PCIe RC1/link state, SSCTL/sysmon, MHI pipe creation, and ks lifetime/order.
- Success criterion: select one cleanup-safe read-only live discriminator before any new mutation
- Success criterion: preserve no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- Success criterion: preserve no direct eSoC open, fake ONLINE, forced RC1, PMIC/GPIO/GDSC writes, or PCI rescan/platform bind-unbind
- Success criterion: only consider Wi-Fi connect after WLFW service 69 and wlan0 both exist
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.

## Safety Scope

V1872 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
