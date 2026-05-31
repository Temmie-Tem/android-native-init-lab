# Native Init V1328 MDM2AP Timing Sampler Live

## Summary

- Cycle: `V1328`
- Type: bounded live read-only timing sampler
- Decision: `v1328-mdm2ap-timing-full-window-no-transition`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1328-mdm2ap-timing-sampler-live/manifest.json`
  - `tmp/wifi/v1328-mdm2ap-timing-sampler-live/summary.md`
- Script: `scripts/revalidation/native_wifi_mdm2ap_timing_sampler_live_v1328.py`
- Helper: `/cache/bin/a90_android_execns_probe` (`a90_android_execns_probe v276`)

V1328 ran the compact `mdm2ap_timing` sampler around the existing late
`per_proxy` / `pm-service` path. The sampler captured the full intended timing
window and saw `pm-service` enter the `mdm_subsys_powerup` path, but observed no
MDM2AP, PCIe, MHI, WLFW, or `wlan0` transition.

## Key Observations

| Field | Value |
|---|---:|
| timing_sample_count | `120` |
| timing_sample_interval_ms | `50` |
| timing_pm_service_powerup_seen | `true` |
| timing_max_powerup_thread_count | `1` |
| timing_gpio142_irq_delta | `0` |
| timing_errfatal_irq_delta | `0` |
| timing_pcie_rc1_transition_seen | `false` |
| timing_pci_dev_max | `0` |
| timing_mhi_bus_max | `0` |
| timing_mhi_pipe_seen | `false` |
| timing_mhi_pipe_fd_max | `0` |
| timing_ks_process_max | `0` |
| timing_wlfw_kmsg_max | `0` |
| timing_wlan0_seen | `false` |

## Interpretation

The V1328 result tightens the blocker to the Android-only SDX50M response
prerequisite after native reaches `mdm_subsys_powerup`. The native path is not
failing because the timing window is too short: a full `120 x 50ms` window
captures the powerup thread and still shows no GPIO142/MDM status response, no
MDM errfatal IRQ, no PCIe RC1 transition, no MHI bus/pipe, no `ks`, no WLFW, and
no `wlan0`.

The next gate should classify what Android provides before or during the same
response window that native still lacks. That classification should stay
host/read-only first and should not jump to PMIC/GPIO/eSoC mutation.

## Safety

- `timing_safety_wifi_hal_start=0`
- `timing_safety_scan_connect=0`
- `timing_safety_credentials=0`
- `timing_safety_dhcp_route=0`
- `timing_safety_external_ping=0`
- `timing_safety_pmic_write=0`
- `timing_safety_gpio_request=0`
- `timing_safety_direct_esoc_ioctl=0`

No Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,
PMIC write, GPIO request/hold, direct eSoC ioctl, flash, boot image write, or
partition write occurred. The observer requested cleanup reboot because a PM
process was not proven stopped, and post-run selftest remained
`pass=11 warn=1 fail=0`.
