# Native Init V1383 Android Participant Immediate Corrected RC1 Live

## Summary

- Cycle: `V1383`
- Type: bounded live lower Android participant + immediate corrected RC1 enumerate gate
- Decision: `v1383-corrected-rc1-ltssm-no-downstream-clean`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_android_participant_immediate_corrected_rc1_live_v1383.py`
- Helper: `/cache/bin/a90_android_execns_probe` (`a90_android_execns_probe v284`)
- Evidence:
  - `tmp/wifi/v1383-android-participant-immediate-corrected-rc1-live/manifest.json`
  - `tmp/wifi/v1383-android-participant-immediate-corrected-rc1-live/summary.md`

## Key Observations

| field | value |
| --- | --- |
| private_flag_in_child_script | 1 |
| precondition_flag_in_child_script | 1 |
| corrected_rc1_flag_in_child_script | 1 |
| corrected_triggered | True |
| corrected_phase | late_per_proxy_poll_00 |
| corrected_monotonic_ms | 1707894 |
| corrected_gate_per_mgr_subsys_esoc0_count | 0 |
| corrected_gate_pm_service_powerup_thread_count | 1 |
| corrected_rc_sel_rc | 0 |
| corrected_case_rc | 0 |
| debugfs_control_write_executed | True |
| timing_sample_count | 120 |
| timing_pm_service_powerup_seen | True |
| timing_pcie_rc1_transition_seen | False |
| dmesg_pcie_rc1_transition_seen | True |
| dmesg_esoc0_to_assert_sec | 3.666356000000178 |
| dmesg_release_to_link_failed_sec | 0.109079999999949 |
| dmesg_l0_seen | False |
| dmesg_link_failed_seen | True |
| timing_gpio142_irq_delta | 0 |
| timing_errfatal_irq_delta | 0 |
| timing_pci_dev_max | 0 |
| timing_mhi_bus_max | 0 |
| timing_mhi_pipe_seen | False |
| timing_ks_process_max | 0 |
| timing_wlfw_kmsg_max | 0 |
| timing_wlan0_seen | False |
| pre_last_checkpoint | cnss-netlink-only |
| safety_clear | True |

## Decision

immediate corrected RC1 enumerate fired at the first v284 powerup-thread poll (esoc0-to-assert 3.666s); dmesg shows RC1 LTSSM activity before link failure, but no GPIO142/PCI/MHI/WLFW/wlan0 appeared

## Safety Scope

V1383 remains below Wi-Fi bring-up. It does not start Wi-Fi HAL, scan, connect, credential handling, DHCP/routes, or external ping. The intentional live mutation is limited to pci-msm debugfs `rc_sel=2` and `case=11` immediately when the Android participant lower gate and v284 powerup-thread gate are observed.

## Next

compare V1383 action timing and LTSSM phase against Android before any new participant or lower-branch mutation

## Dmesg RC1 Lines

- `line_esoc0`: [ 1704.113455] [2:  Binder:9304_4: 9928] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0
- `line_test11`: [ 1707.779791] [6:a90_android_exe: 1180] PCIe: TEST: 11
- `line_assert`: [ 1707.779811] [6:a90_android_exe: 1180] msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1.
- `line_phy_ready`: [ 1707.785266] [6:a90_android_exe: 1180] msm_pcie_enable: PCIe RC1 PHY is ready!
- `line_release`: [ 1707.785271] [6:a90_android_exe: 1180] msm_pcie_enable: PCIe: Release the reset of endpoint of RC1.
- `line_poll_compliance`: [ 1707.827341] [3:a90_android_exe: 1180] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE
- `line_link_failed`: [ 1707.894351] [3:a90_android_exe: 1180] msm_pcie_enable: PCIe RC1 link initialization failed (LTSSM_STATE:0x3)
