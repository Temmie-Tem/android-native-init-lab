# Native Init V1589 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1589`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1589-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1589-service-window-lower-marker-handoff`
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
- `helper_result_size`: `762685`
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

- Test image: `tmp/wifi/v1588-service-window-lower-marker-test-boot/boot_linux_v1588_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Lower-marker Findings

The V1588 helper added `android_wifi_service_window.lower_marker` summary
evidence inside the V1589 live window.

| field | value |
| --- | --- |
| `sample_count` | `20` |
| `pm_proxy_helper_alive_seen` | `1` |
| `pm_proxy_helper_subsys_modem_fd_max` | `1` |
| `per_mgr_alive_seen` | `0` |
| `per_mgr_subsys_modem_fd_max` | `-1` |
| `pm_proxy_alive_seen` | `1` |
| `mdm_helper_alive_seen` | `1` |
| `mdm_helper_esoc0_fd_max` | `1` |
| `trigger_child_alive_seen` | `1` |
| `trigger_child_subsys_esoc0_fd_max` | `0` |
| `global_subsys_modem_fd_max` | `1` |
| `global_dev_esoc0_fd_max` | `1` |
| `global_subsys_esoc0_fd_max` | `0` |
| `pm_service_powerup_seen` | `0` |
| `pcie_rc1_transition_seen` | `0` |
| `mhi_bus_max` | `0` |
| `mhi_pipe_seen` | `0` |
| `ks_process_max` | `0` |
| `wlfw_start_kmsg_max` | `0` |
| `wlfw_service_request_kmsg_max` | `0` |
| `bdf_kmsg_max` | `0` |
| `fw_ready_kmsg_max` | `0` |
| `wlan0_seen` | `0` |
| `checkpoint` | `cnss-netlink-only` |

The scoped trigger child reached `mdm_subsys_powerup`, but no returned
`/dev/subsys_esoc0` fd, RC1/LTSSM transition, runtime MHI, `ks`, WLFW start,
BDF, FW-ready, or `wlan0` followed.  The PM proxy helper held
`/dev/subsys_modem`, but `pm-service` was not alive in the lower-marker window,
so the Android-good PM-service-owned powerup route is still not reproduced.

## Next

Treat V1589 as a successful rollbackable lower-marker handoff, not as Wi-Fi
bring-up.  The next bounded gate should classify why `pm-service` exits before
the lower-marker window and why the current scoped `/dev/subsys_esoc0` trigger
does not reproduce Android's PM-service-owned `mdm_subsys_powerup` path.  Do
not proceed to scan/connect, credentials, DHCP/routes, or external ping until
WLFW start, BDF, FW-ready, and `wlan0` exist in native.
