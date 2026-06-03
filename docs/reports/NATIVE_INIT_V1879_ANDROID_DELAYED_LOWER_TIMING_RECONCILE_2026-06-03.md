# Native Init V1879 Android Delayed Lower Timing Reconcile

## Summary

- Cycle: `V1879`
- Type: host-only Android-good delayed lower timing reconciler
- Decision: `v1879-android-delayed-lower-timing-selects-readonly-long-sampler-host-pass`
- Label: `delayed-private-sdx50m-readonly-sampler-next`
- Result: PASS
- Reason: Android-good reaches pcie1 L0, MHI, WLFW request, BDF, FW-ready, and `wlan0` only after a roughly 205-216 second delayed lower window. The latest private SDX50M sampler only covered 0-1000 ms after PM powerup, so a delayed read-only sampler is the next safer gate before any explicit resource/GDSC write path.
- Evidence: `tmp/wifi/v1879-android-delayed-lower-timing-reconcile`

## Checks

| check | value |
|---|---:|
| `android_manifest_pass` | `True` |
| `android_dmesg_has_delayed_success_chain` | `True` |
| `android_pcie1_resource_first_seen_after_240s` | `True` |
| `android_clock_votes_first_seen_with_gdsc` | `True` |
| `android_esoc0_online_after_wlan0_window` | `True` |
| `v1876_current_sampler_is_short_readonly_gap` | `True` |
| `v1878_closed_driver_pm_but_not_delayed_readonly` | `True` |
| `prior_service_window_result_did_not_cover_delayed_private_route` | `True` |
| `prior_endpoint_long_hold_not_current_private_sdx50m_route` | `True` |
| `host_only_no_live_mutation` | `True` |

## Android-Good Timing

- `wlfw_start`: `43.555797` count `1`
- `esoc0_boot_failed`: first `144.566944` count `2`
- `pcie_initialized`: `248.683464` count `13` delay-from-wlfw-start `205.128s`
- `mhi_enable`: `248.709188` count `13`
- `wlfw_request`: `252.163609` count `1` delay-from-wlfw-start `208.608s`
- `BDF`: regdb `252.191737` bdwlan `252.207773`
- `fw_ready`: `257.171735` count `2` delay-from-wlfw-start `213.616s`
- `wlan0`: `257.451228` count `3` delay-from-wlfw-start `213.895s`
- `esoc0_online`: `259.75` delay-from-wlfw-start `216.194s`
- `pcie_1_gdsc`: index `256` uptime `250.62` use_count `1`
- first clock votes at GDSC snapshot: `gcc_pcie1_phy_refgen_clk, gcc_pcie_1_aux_clk, gcc_pcie_1_aux_clk_src, gcc_pcie_1_cfg_ahb_clk, gcc_pcie_1_clkref_clk, gcc_pcie_1_mstr_axi_clk, gcc_pcie_1_pipe_clk, gcc_pcie_1_slv_axi_clk, gcc_pcie_1_slv_q2a_axi_clk, gcc_pcie_phy_refgen_clk_src`

## Key Lines

- wlfw start: `[   43.555797]  [4:             sh: 2304] cnss-daemon wlfw_start: Starting`
- pcie initialized: `[  248.683464]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1 link initialized`
- WLFW request: `[  252.163609]  [6:             sh: 9058] cnss-daemon wlfw_service_request: Start the pthread: 0x0K`
- FW ready: `[  257.171735]  [0: kworker/u16:11:  347] icnss: WLAN FW is ready: 0xd87`
- wlan0: `[  257.451228]  [6: kworker/u16:11:  347] dev : wlan0 : event : 16`

## Current Evidence Reconcile

- V1876 decision: Decision: `v1876-lower-input-power-clock-snapshot-gap-rollback-pass`
- V1876 sample window: offsets ms: `0,1,2,5,10,20,50,100,150,250,500,1000`
- V1876 guards: guard read-only/no-esoc0/no-rc/no-pci/no-hal: `True` / `True` / `True` / `True` / `True`
- V1876 lower prereqs: mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- V1878 decision: Decision: `v1878-no-safe-pcie1-driver-pm-userspace-path-host-pass` / Label: `explicit-resource-gdsc-approval-needed`
- V1569 service-window blocker: Decision: `v1569-test-boot-no-downstream-wifi-progress-blocked` / `helper_result_final_result`: `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`

V1878 correctly closed the currently visible userspace driver-PM path and marked a resource/GDSC write as approval-gated. V1879 does not overturn that safety boundary. It adds a missing read-only timing fact: Android-good lower publication is delayed far beyond the V1876 1 second dense sampler, and older service-window attempts were blocked on a different mdm-helper `/dev/esoc-0` predicate.

Therefore the next lower-risk unit is not Wi-Fi connect/ping and not a resource write. It is a source/build-only delayed private-SDX50M read-only sampler that waits across the Android-good 205-216 second lower-publication window and stops as soon as MHI/WLFW/`wlan0` prerequisites appear.

## Selected Next Gate

- Cycle: `V1880`
- Label: `private-sdx50m-delayed-lower-readonly-sampler-source-build`
- Type: `source/build-only delayed read-only sampler before any live rerun`
- Base: extend the V1874/V1876 private SDX50M lower-response sampler
- Delayed offsets seconds: `0,1,2,5,10,20,30,60,90,120,150,180,210,240,250,260,300`
- Success label: `delayed-lower-wifi-prereq-present-readonly-stop`
- Success label: `delayed-lower-mhi-or-wlfw-progress-readonly-stop`
- Success label: `delayed-lower-pcie-l0-no-wlfw-readonly-stop`
- Success label: `delayed-lower-still-power-clock-gap`
- Guardrail: read-only sampling only; no resource/GDSC/PMIC/GPIO writes
- Guardrail: no direct `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify, BOOT_DONE, forced RC1, PCI rescan, or platform bind/unbind
- Guardrail: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- Guardrail: live handoff, if built and preflighted later, must roll back and stop unless WLFW service 69 plus `wlan0` are present
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.

## Safety Scope

V1879 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC/regulator controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
