# Native Init V1629 pm-service Causality Reconciliation

## Summary

- Cycle: `V1629`
- Type: host-only causality classifier over existing Wi-Fi bring-up evidence
- Decision: `v1629-pm-service-causality-reconciled-lower-sdx50m-gate`
- Result: PASS
- Reason: the pm-service OFFLINE/exit path is an effect of real `subsys9=esoc0=OFFLINING`, not the lower Wi-Fi blocker; the next gate must return to SDX50M/MDM2AP response parity.

## Inputs

| input | path |
| --- | --- |
| v1496_manifest | tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json |
| v1497_report | docs/reports/NATIVE_INIT_V1497_AUTO_READINESS_RC1_FAILURE_CLASSIFIER_2026-06-01.md |
| v1498_manifest | tmp/wifi/v1498-msm-pcie-test11-static-analysis/manifest.json |
| v1523_manifest | tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json |
| v1524_manifest | tmp/wifi/v1524-endpoint-trigger-attribution-classifier/manifest.json |
| v1552_manifest | tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json |
| v1556_report | docs/reports/NATIVE_INIT_V1556_V1555_VS_V1552_ENDPOINT_SIGNAL_COMPARATOR_2026-06-02.md |
| v1559_report | docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md |
| v1628_manifest | tmp/wifi/v1628-pm-service-shutdown-list-classifier/manifest.json |
| oob_handoff_report | docs/reports/ESOC_PMSERVICE_CAUSALITY_HANDOFF_2026-06-02.md |
| next_plan | docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md |

## Checks

| check | status |
| --- | --- |
| v1496_rc1_failure_fixed_point | pass |
| test11_path_already_classified | pass |
| endpoint_silent_after_ap_side_power | pass |
| pm_service_offline_track_is_effect | pass |
| fake_online_explicitly_rejected | pass |
| gpio142_mdm2ap_redirect_present | pass |
| android_pre_endpoint_order_reference_present | pass |
| native_endpoint_signal_comparator_present | pass |

## Fixed Points

| cycle | topic | decision |
| --- | --- | --- |
| V1496 | RC1/LTSSM | rc1-ltssm-link-failed-no-l0 |
| V1498 | TEST:11 source contract | v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap |
| V1523 | TEST:11 vs normal path | v1523-test11-shares-enable-normal-trigger-readiness-gap |
| V1524 | trigger attribution | v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume |
| V1552 | endpoint response | v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0 |
| V1628 | pm-service shutdown-list | v1628-shutdown-list-accepted-pm-service-still-exits-before-ipc |

## Current Boundary

| field | value |
| --- | --- |
| v1496_decision | v1496-test-boot-downstream-progress-rollback-pass |
| v1496_final_decision | rc1-ltssm-link-failed-no-l0 |
| v1496_provider_trigger | True |
| v1496_rc1_progress | True |
| v1496_rc1_l0 | False |
| v1496_rc1_link_failed | True |
| v1496_mhi_progress | False |
| v1496_wlfw_progress | False |
| v1496_wlan0_present | False |
| v1498_decision | v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap |
| v1523_decision | v1523-test11-shares-enable-normal-trigger-readiness-gap |
| v1524_decision | v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume |
| v1552_decision | v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0 |
| v1628_decision | v1628-shutdown-list-accepted-pm-service-still-exits-before-ipc |
| v1628_surface_still_offlining | True |
| v1628_shutdown_critical_list_allowed | True |
| v1628_pm_service_exits_before_ipc_or_pm_fd | True |
| v1628_subsys9_state | OFFLINING |
| v1628_helper_result | pm-service-owned-powerup-missing |

## Interpretation

V1496/V1497 already fixed the low-level failure as `rc1-ltssm-link-failed-no-l0`: the provider path triggers, corrected RC1 enumerate reaches PHY/LTSSM progress, and the link fails before L0.  MHI, WLFW, BDF, FW-ready, `wlan0`, scan/connect, DHCP/routes, and external ping remain downstream.

V1498 and V1523 close the idea that debugfs TEST:11 is missing the core AP-side PCIe enable operation.  TEST:11 reaches the common enumerate/enable path; V1552 then proves AP-side GDSC/refclk/pipe/PERST activity can occur while the endpoint remains silent, with no WAKE/MDM-status/errfatal IRQ and no L0.

V1621-V1628 repaired property-root and shutdown-critical-list handling, but `pm-service` still exits on the OFFLINE system-info path.  The out-of-band handoff corrects the causality: `subsys9=OFFLINING` is true because SDX50M did not power up.  Faking ONLINE would only advance an upper layer on false state and then hit the already-proven `/dev/subsys_esoc0`/`mdm_subsys_powerup`/MDM2AP block.

Therefore the pm-service property/system-info track is closed for now.  The actionable question is what Android-good does between AP2MDM/PM8150L-PON assertion and GPIO142/MDM2AP response that native still lacks, or whether native's asserted sequence is electrically ineffective.

## Next Gate

- Recommended cycle: `V1630`
- Type: host-only lower-layer classifier/design
- Focus: Android-good vs native AP2MDM/PM8150L-PON/MDM2AP/RC1 first-response parity
- Reject: fake ONLINE system-info, pm-service property chasing, blind TEST:11 retry
- Output should be an Android-good vs native-fail timeline table for AP2MDM, PM8150L GPIO9/PON, MDM2AP GPIO142/IRQ, RC1 PHY/LTSSM/L0, MHI, WLFW/BDF/FW-ready, and `wlan0`.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, platform bind/unbind, or fake ONLINE/system-info bind.
