# Native Init V1592 Wi-Fi Test Boot Strict Classifier

## Summary

- Cycle: `V1592`
- Type: host-only strict reclassification of existing test-boot evidence
- Decision: `v1592-test-boot-no-downstream-wifi-progress-blocked`
- Result: BLOCKED
- Reason: test boot ran and rollback verified, but strict Wi-Fi progress markers were absent
- Evidence: `tmp/wifi/v1592-late-per-proxy-lower-marker-reclassify`
- Source evidence: `tmp/wifi/v1592-late-per-proxy-lower-marker-handoff`
- Handoff/rollback pass: `True`
- Rollback attempt: `existing`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `False`
- Progress decision: `modem-trigger-no-downstream`

## Progress Classification

- `provider_trigger`: `False`
- `rc1_progress`: `False`
- `rc1_l0`: `False`
- `rc1_link_failed`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `icnss_qmi_connected`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`
- `debugfs_pci_msm_case_present`: `None`
- `firmware_mounts_requested`: `1`
- `helper_timed_out`: `0`
- `helper_result_file_seen`: `True`
- `helper_result_contract_seen`: `True`
- `helper_result_size`: `655999`
- `helper_result_late_per_proxy_only`: `1`
- `helper_result_subsys_open_attempted`: `0`
- `helper_result_subsys_trigger_started`: `0`
- `helper_result_subsys_trigger_gate_open`: `1`
- `helper_result_mdm_helper_esoc0_fd_count`: `1`
- `helper_result_pm_proxy_contract`: `1`
- `helper_result_pm_proxy_helper_subsys_modem_fd_count`: `0`
- `helper_result_per_mgr_subsys_modem_fd_count`: `-1`
- `helper_result_pm_full_contract_seen`: `0`
- `helper_result_child_per_mgr_exit_code`: `0`
- `helper_result_child_pm_proxy_exit_code`: `1`
- `helper_result_final_result`: `subsys-trigger-start-failed`
- `helper_result_final_reason`: `service-window-gate-opened-but-trigger-child-did-not-start`
- `pid1_rc1_watcher_requested`: `0`
- `pid1_rc1_watcher_result_summary`: `None`
- `pid1_rc1_watcher_result_file`: ``
- `pid1_rc1_window_sampler_requested`: `0`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: ``
- `pid1_rc1_window_sample_count`: `0`
- `pid1_rc1_window_has_post_500ms`: `False`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
This run was host-only and reclassified existing test-boot evidence;
it did not flash, reboot, or mutate the device.

## Interpretation

The source handoff evidence at
`tmp/wifi/v1592-late-per-proxy-lower-marker-handoff` completed the live
flash/boot/evidence/rollback sequence.  The strict reclassification is needed
because the source dmesg contains `icnss_qmi: Fail to send Shutdown req`, which
is shutdown/error evidence from modem teardown, not WLFW bring-up progress.
Only `icnss_qmi: QMI Server Connected` is treated as ICNSS QMI progress.

The late-`per_proxy` route therefore did not reproduce the older V1238/V1303
PM-service-owned `/dev/subsys_esoc0` powerup path inside the V1591 full
service-window image.  The next blocker is the `pm_proxy`/`per_mgr` lifetime
gap, not RC1/MHI/firmware and not scan/connect readiness.

## Images

- Test image: `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/boot_linux_v1591_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat this result as diagnostic evidence, not Wi-Fi connect readiness.
Do not proceed to scan/connect, credentials, DHCP/routes, or external ping
until the next required lower-layer progress marker is proven.
