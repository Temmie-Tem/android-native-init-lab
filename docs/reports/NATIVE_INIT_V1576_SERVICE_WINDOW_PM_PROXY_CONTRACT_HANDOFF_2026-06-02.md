# Native Init V1576 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1576`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1576-test-boot-no-downstream-wifi-progress-blocked`
- Result: BLOCKED
- Reason: test boot ran and rollback verified, but strict Wi-Fi progress markers were absent
- Evidence: `tmp/wifi/v1576-service-window-pm-proxy-contract-handoff`
- Handoff/rollback pass: `True`
- Rollback attempt: `from-native`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `False`
- Progress decision: `no-provider-no-downstream`

## Progress Classification

- `provider_trigger`: `False`
- `rc1_progress`: `False`
- `rc1_l0`: `False`
- `rc1_link_failed`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`
- `debugfs_pci_msm_case_present`: `None`
- `helper_timed_out`: `0`
- `helper_result_file_seen`: `True`
- `helper_result_contract_seen`: `True`
- `helper_result_size`: `622551`
- `helper_result_subsys_open_attempted`: `0`
- `helper_result_subsys_trigger_started`: `0`
- `helper_result_subsys_trigger_gate_open`: `0`
- `helper_result_mdm_helper_esoc0_fd_count`: `0`
- `helper_result_pm_proxy_contract`: `1`
- `helper_result_pm_proxy_helper_subsys_modem_fd_count`: `0`
- `helper_result_per_mgr_subsys_modem_fd_count`: `-1`
- `helper_result_pm_full_contract_seen`: `0`
- `helper_result_final_result`: `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`
- `helper_result_final_reason`: `service-window-gate-did-not-see-dev-esoc-0`
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

- Test image: `tmp/wifi/v1575-service-window-pm-proxy-contract-test-boot/boot_linux_v1393_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. Do not proceed to scan/connect, credentials, DHCP/routes,
or external ping until at least RC1/MHI/WLFW/`wlan0` progress is proven.
