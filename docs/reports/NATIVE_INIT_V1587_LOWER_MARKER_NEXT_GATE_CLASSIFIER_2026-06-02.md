# Native Init V1587 Lower-Marker Next-Gate Classifier

## Summary

- Cycle: `V1587`
- Type: host-only current-route reconciliation classifier
- Decision: `v1587-v1586-current-lower-marker-gate-required`
- Result: `PASS`
- Reason: V1496 RC1/LTSSM and msm_pcie static work are already classified; V1586 is the current active route and needs focused RC1/MHI/WLFW request-state sampling before any connect work
- Evidence: `tmp/wifi/v1587-lower-marker-next-gate-classifier`

## Inputs

| input | path |
| --- | --- |
| native_v1496 | tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json |
| v1535_first_l0_classifier | tmp/wifi/v1535-first-l0-trigger-candidate-classifier/manifest.json |
| v1560_order_classifier | tmp/wifi/v1560-android-order-vs-native-route-classifier/manifest.json |
| v1586_current_handoff | tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff/manifest.json |
| v1586_dmesg | tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff/test-v1393-dmesg.stdout.txt |
| v1586_helper_result | tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff/test-v1393-helper-result.stdout.txt |

## Fixed Predicates

| predicate | value |
| --- | --- |
| v1496_rc1_link_failed_no_l0_fixed | yes |
| v1535_msm_pcie_static_candidate_done | yes |
| v1560_android_order_vs_native_route_done | yes |
| v1586_current_firmware_progress_no_wlan0 | yes |

## V1586 Current Route

| field | value |
| --- | --- |
| final_decision | firmware-progress-no-wlan0 |
| provider_trigger | True |
| modem_trigger | True |
| firmware_mounts_requested | 1 |
| helper_result_subsys_open_attempted | 1 |
| helper_result_subsys_trigger_started | 1 |
| helper_result_mdm_helper_esoc0_fd_count | 1 |
| helper_result_pm_proxy_contract | 1 |
| helper_result_pm_full_contract_seen | 0 |
| rc1_progress | False |
| mhi_progress | False |
| wlfw_progress | True |
| bdf_progress | False |
| fw_ready_progress | False |
| wlan0_present | False |

## V1586 Timing Markers

| marker | first_time |
| --- | --- |
| pm_proxy_helper_subsys_modem | 2.396513 |
| modem_loading | 2.397969 |
| modem_brought_out_of_reset | 2.897151 |
| cnss_diag_netlink | 5.007639 |
| cnss_daemon_netlink | 5.506785 |
| subsys_esoc0 | 6.304406 |
| bdf | missing |
| fw_ready | missing |
| wlan0 | missing |

## V1586 Marker Counts

| marker | count |
| --- | --- |
| rc1 | 0 |
| ltssm_l0 | 0 |
| mhi_runtime | 0 |
| wlfw_start | 0 |
| icnss_qmi | 1 |
| bdf | 0 |
| fw_ready | 0 |
| wlan0 | 0 |

## V1586 Helper Contract Snapshot

| field | value |
| --- | --- |
| mode | guarded-pm-proxy-contract-subsys-trigger-capture |
| pm_proxy_contract | 1 |
| pm_full_contract_seen | 0 |
| pm_proxy_helper_subsys_modem_initial_count | 0 |
| pm_proxy_helper_subsys_modem_final_count | 0 |
| per_mgr_subsys_modem_initial_count | -1 |
| per_mgr_subsys_modem_final_count | -1 |
| mdm_helper_esoc0_gate_count | 1 |
| subsys_trigger_gate | service-window-mdm-helper-esoc-fd |
| subsys_trigger_gate_open | 1 |
| subsys_trigger_started | 1 |
| result | start-only-reboot-required |
| reason | process-not-proven-stopped |

## Interpretation

V1496 remains a valid forced-RC1 failure: it reaches RC1 PHY/LTSSM progress and fails before L0.  However, the repository already contains the follow-up `msm_pcie` static and first-L0 candidate classifiers, so repeating a V1496-only dossier is not the best next unit.

V1560 also adds an ordering caveat: Android-good evidence reaches `cnss-daemon wlfw_start` and BDF/FW-ready/`wlan0`, while the native RC1 route only sees generic CNSS/netlink plus forced enumerate.  The active latest evidence is V1586, which advances firmware mounts, modem PIL, private devnodes, `mdm_helper` `/dev/esoc-0`, and `subsys_esoc0` trigger coverage, but still has no RC1/L0, MHI, BDF, FW-ready, or `wlan0`.

Therefore the next gate should not use credentials or attempt scan/connect.  It should preserve V1586 parity and add compact lower-marker sampling to determine whether the remaining gap is PM contract lifetime, missing WLFW request-state transition, no RC1 attempt on the current route, or post-RC1/MHI absence.

## Next Gate

- Recommended cycle: `V1588`
- Type: source/build-only focused lower-marker sampler design
- Focus: preserve V1586 service-window firmware parity, then sample missing RC1/MHI/WLFW request-state boundaries

### Requirements

- do not repeat V1496 RC1 dossier or V1535 msm_pcie static analysis unless new input appears
- preserve V1586 firmware-only global vendor overlay and helper private sda29 vendor namespace
- sample process lifetimes and compact fd counts for pm_proxy_helper, pm-service, pm-proxy, mdm_helper, cnss_diag, cnss-daemon, and wificond
- sample subsystem states, RC1/LTSSM, MHI bus/pipe, QRTR/WLFW, BDF, FW-ready, and wlan0 markers in one bounded window
- keep scan/connect, credentials, DHCP/routes, external ping, blind eSoC notify/BOOT_DONE, PMIC/GPIO/GDSC direct writes, global PCI rescan, and platform bind/unbind blocked

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
