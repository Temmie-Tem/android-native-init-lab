# Native Init V1345 Current Route MDM2AP Timing Sampler Live

## Summary

- Cycle: `V1345`
- Type: bounded live lower-response timing sampler
- Decision: `v1345-current-route-mdm2ap-full-window-no-transition`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-live/manifest.json`
  - `tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-live/summary.md`
- Script: `scripts/revalidation/native_wifi_current_route_mdm2ap_timing_sampler_live_v1345.py`
- Helper: `/cache/bin/a90_android_execns_probe` (`a90_android_execns_probe v279`)

## Key Observations

| field | value |
| --- | --- |
| private_flag_in_child_script | 1 |
| private_cnss_bind_rc | 0 |
| private_cnss_expected_c_string | SDX50M |
| timing_sample_count | 120 |
| timing_pm_service_powerup_seen | True |
| timing_gpio142_irq_delta | 0 |
| timing_errfatal_irq_delta | 0 |
| timing_pcie_rc1_transition_seen | False |
| timing_pci_dev_max | 0 |
| timing_mhi_bus_max | 0 |
| timing_mhi_pipe_seen | False |
| timing_mhi_pipe_fd_max | 0 |
| timing_ks_process_max | 0 |
| timing_wlfw_kmsg_max | 0 |
| timing_wlan0_seen | False |
| timing_safety_clear | True |

## Cleanup And Health

| field | value |
| --- | --- |
| debugfs_mounted_before | False |
| debugfs_mounted_by_cycle | True |
| debugfs_cleanup_attempted | True |
| debugfs_mounted_after | False |
| reboot_cleanup_status_healthy | True |
| reboot_cleanup_version_seen | True |
| reboot_cleanup_wait_sec | 47.35 |
| post_status_ok | True |
| post_selftest_ok | True |
| post_selftest_payload | selftest: pass=11 warn=1 fail=0 duration=41ms entries=12 |

## Decision

current private SDX50M route reached mdm_subsys_powerup, but full timing window saw no GPIO142/errfatal/PCIe/MHI/ks/WLFW/wlan0 transition

V1345 remains below Wi-Fi bring-up. It does not start Wi-Fi HAL, scan,
connect, credential handling, DHCP/routes, or external ping.

## Next

classify Android-only SDX50M response prerequisite before any PMIC/GPIO/eSoC mutation
