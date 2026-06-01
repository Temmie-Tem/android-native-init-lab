# Native Init V1586 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1586`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1586-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced firmware/PIL and lower Wi-Fi service evidence and rollback verified
- Evidence: `tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff`
- Handoff/rollback pass: `True`
- Rollback attempt: `from-native`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `True`
- Progress decision: `firmware-progress-no-wlan0`

## Progress Classification

- `provider_trigger`: `True`
- `rc1_progress`: `False`
- `rc1_l0`: `False`
- `rc1_link_failed`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `True`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`
- `debugfs_pci_msm_case_present`: `None`
- `firmware_mounts_requested`: `1`
- `helper_timed_out`: `0`
- `helper_result_file_seen`: `True`
- `helper_result_contract_seen`: `True`
- `helper_result_size`: `758102`
- `helper_result_subsys_open_attempted`: `1`
- `helper_result_subsys_trigger_started`: `1`
- `helper_result_subsys_trigger_gate_open`: `1`
- `helper_result_mdm_helper_esoc0_fd_count`: `1`
- `helper_result_pm_proxy_contract`: `1`
- `helper_result_pm_proxy_helper_subsys_modem_fd_count`: `0`
- `helper_result_per_mgr_subsys_modem_fd_count`: `-1`
- `helper_result_pm_full_contract_seen`: `0`
- `helper_result_final_result`: `start-only-reboot-required`
- `helper_result_final_reason`: `process-not-proven-stopped`
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
Device mutation included flashing the test boot image, any bounded
in-boot actions declared by that test image's artifact contract, and
rolling back to `stage3/boot_linux_v724.img`. If enabled, native direct
rollback may restore the boot partition from a pre-staged `/cache`
rollback image when recovery ADB is unavailable.

## Images

- Test image: `tmp/wifi/v1585-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/boot_linux_v1393_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat V1586-class evidence as firmware/PIL progress without interface bring-up.
The next bounded gate should preserve firmware mount parity and add focused
RC1/MHI/WLFW request markers before any scan/connect, credentials, DHCP/routes,
or external ping.
