# Native Init V1849 SDX50M Private Route Reuse Classifier

## Summary

- Cycle: `V1849`
- Type: host-only reconciliation of current CNSS selection and historical private-SDX50M lower-gap evidence
- Decision: `v1849-private-sdx50m-route-known-lower-gap-host-pass`
- Label: `private-sdx50m-route-known-lower-gap`
- Result: PASS
- Reason: The private SDX50M CNSS route is known to change PM selection and reach eSoC powerup, but prior evidence already moves the blocker below /dev/subsys_esoc0 before GPIO142/PCIe/WLFW/wlan0 publication
- Evidence: `tmp/wifi/v1849-sdx50m-private-route-reuse-classifier`

## Current Route

- V1848 decision/label: `v1848-cnss-pm-register-selects-modem-not-sdx50m-host-pass` / `cnss-pm-register-selects-modem-record`
- Current requested/candidates: `['modem']` / `['SDX50M', 'modem']`
- Current PM map: `{'SDX50M': '/dev/subsys_esoc0', 'modem': '/dev/subsys_modem'}`
- Current open/lower: `/dev/subsys_modem` fd `0x7` / `stable-mdm3-offlining`

## Historical Private Route

- V1221 decision: `v1221-sdx50m-per-mgr-esoc0` / pass `True`
- Private daemon bind/source: rc `0` / `/cache/bin/cnss-daemon.sdx50m`
- Patched daemon SHA: `784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd`
- CNSS registrations: `['modem', 'SDX50M']`
- eSoC route: per_mgr_esoc0 `True` pm_actor `True` mdm_subsys_powerup `True`
- late PM wchans: `['do_sigtimedwait', 'do_select', 'binder_ioctl_write_read', 'sdx50m_toggle_soft_reset', '0', 'mdm_subsys_powerup']`
- lower publication: mdm3 `OFFLINING` markers `{'bdf': 0, 'kernel_warning': 0, 'mhi': 0, 'qca6390': 0, 'qrtr_rx': 2, 'qrtr_tx': 0, 'rpmsg': 0, 'service_notifier': 0, 'sysmon_qmi': 0, 'wlan0': 0, 'wlan_pd': 0, 'wlfw': 0}` wlan0_up `False`
- V1221 guardrails: `{'wifi_hal_start_executed': False, 'scan_connect_executed': False, 'credential_use_executed': False, 'dhcp_route_executed': False, 'external_ping_executed': False, 'wifi_bringup_executed': False, 'partition_write_executed': False, 'flash_executed': False, 'reboot_executed': False}`

## Lower-Gap Follow-Up

- V1222: `v1222-esoc-powerup-crash-before-wlfw` / `eSoC open reached mdm_subsys_powerup but modem-down/crash markers appeared; states=['OFFLINING']`
- V1223: `v1223-sdx50m-crash-source-contract-gap-classified` / `Native now reaches SDX50M eSoC power-up via pm-service but crashes before WLFW; Android success includes the init-managed mdm_helper/ks MHI image-link contract that direct native mdm_helper lacked.`
- V1239: `v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw` / `native now reaches the same pm-service /dev/subsys_esoc0 powerup entry as Android, but does not receive the downstream GPIO142/PCIe/SSCTL/WLFW response`
- V1239 checks: `[{'detail': 'Android reference reaches mdm3 ONLINE, WLFW/BDF, and wlan0', 'name': 'android-positive-reference', 'status': 'pass'}, {'detail': 'gpio142=1 pcie_rc1_lines=18 sysmon_esoc0=1', 'name': 'android-post-esoc0-powerup-chain', 'status': 'pass'}, {'detail': 'late_started=True actor_esoc0=True', 'name': 'native-reaches-pm-service-esoc0', 'status': 'pass'}, {'detail': "mdm3=['OFFLINING'] wlfw=0 wlan0=False", 'name': 'native-no-lower-publication', 'status': 'pass'}, {'detail': 'V1238 did not run Wi-Fi HAL/connect/network/flash actions', 'name': 'guardrails-clean', 'status': 'pass'}]`

## Interpretation

- Repeating the private SDX50M CNSS route is not an information-gaining next live step by itself; V1221 already proved it changes PM selection and reaches the eSoC powerup path.
- The known failure is below PM-service eSoC open: native lacks the downstream GPIO142/PCIe/SSCTL/MHI/WLFW/`wlan0` response that Android gets.
- The current safe next unit should classify the lower response-input contract from source or existing evidence before any live route that can cause another `/dev/subsys_esoc0` powerup attempt.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- Next source-only unit: join Android positive response inputs with native lower-gap evidence around `mdm_subsys_powerup`, especially GPIO142, PCIe RC1, SSCTL/sysmon, MHI pipe creation, and `ks` lifetime/order.
