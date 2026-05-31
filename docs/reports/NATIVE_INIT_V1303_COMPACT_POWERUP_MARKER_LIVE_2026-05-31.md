# Native Init V1303 Compact Powerup Marker Live

## Summary

- Cycle: `V1303`
- Type: bounded live observer
- Decision: `v1303-powerup-marker-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1303-compact-powerup-marker-live/manifest.json`
  - `tmp/wifi/v1303-compact-powerup-marker-live/summary.md`

V1303 reran the compact dense late-`per_proxy` response sampler with deployed helper `a90_android_execns_probe v273`. The new `powerup_marker` closed the V1299/V1300 ambiguity: `pm-service` reached `/dev/subsys_esoc0` through `openat` and blocked in `mdm_subsys_powerup`, but GPIO142/MHI/WLFW/`wlan0` still did not respond.

## Key Results

| field | value |
| --- | --- |
| sample_count | `42` |
| powerup_marker_phase_count | `42` |
| max_powerup_thread_count | `1` |
| powerup_subsys_esoc0_inferred_seen | `true` |
| powerup_first_path_values | `/dev/subsys_esoc0` |
| powerup_first_wchans | `mdm_subsys_powerup` |
| powerup_first_syscall_names | `openat` |
| max_mdm_status_count_total | `0` |
| max_mhi_bus_count | `0` |
| mhi_pipe_seen | `false` |
| wlan0_seen | `false` |

## GPIO/Power Observations

- `tlmm_gpio135_debugfs_target_line_seen=true`
- `tlmm_gpio135_debugfs_target_lines`: `gpio135 : out 0 16mA no pull`
- `tlmm_gpio142_debugfs_target_line_seen=true`
- `tlmm_gpio142_debugfs_target_lines`: `gpio142 : in  0 8mA no pull`
- `gpiochip_lineinfo_seen=true`
- `gpiochip_lineinfo_kernel_owned_seen=true`
- `gpiochip_lineinfo_ap2mdm_consumer_seen=true`
- `gpiochip_lineinfo_zero_action_ok=true`
- `pmic_soft_reset_seen=true`
- `pcie1_gdsc_seen=true`
- `pcie0_gdsc_seen=true`

These observations point the next classifier at the AP2MDM/MDM2AP response boundary: the kernel reaches the eSoC powerup path, but no MDM2AP IRQ, PCIe/MHI, WLFW, or `wlan0` progress appears.

## Cleanup / Health

- Debugfs was mounted for read-only observation and absent after cleanup.
- Post-run native status returned `BOOT OK shell`.
- Post-run selftest remained `pass=11 warn=1 fail=0`.
- Netservice remained disabled with `ncm0=absent` and `tcpctl=stopped`.
- No matching service-manager, `pm-service`, `pm-proxy`, `cnss`, `mdm_helper`, `per_proxy`, or `per_mgr` residual process was found in the post-run ps grep.

## Safety

- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, Wi-Fi bring-up, flash, boot image write, or partition write occurred.
- No PMIC write, userspace GPIO request/hold, or direct eSoC ioctl occurred.
- The only live actor scope was the already bounded PM-service observer path.

## Next

V1304 should be host-only or read-only classifier work: compare V1303's `mdm_subsys_powerup` + GPIO135/142 state against Android-positive evidence and determine whether the next blocker is AP2MDM GPIO assertion, MDM2AP status response, or an earlier ext-mdm power/PMIC prerequisite.
