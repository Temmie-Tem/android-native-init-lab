# Native Init V1673 pcie1 Clock Vote Handoff

## Summary

- Cycle: `V1673`
- Type: one-run rollbackable bounded live pcie1 clock-debug vote proof
- Decision: `v1673-clock-vote-surface-failed`
- Result: REVIEW
- Label: `clock-vote-surface-failed`
- Reason: bounded direct clock write attempts ran, but all enable writes failed (success_count=0, failure_count=10, cleanup_failure_count=0)
- Evidence: `tmp/wifi/v1673-pcie1-clock-vote-direct-retry-handoff`
- Handoff/rollback pass: `True`

## Clock Vote Classification

- `begin`: `True`
- `wait_begin`: `True`
- `wait_ready_count`: `0`
- `wait_sample_count`: `897`
- `wait_elapsed_ms`: `45043`
- `async_begin_rc`: `-5`
- `success_count`: `0`
- `failure_count`: `10`
- `rate_success_count`: `0`
- `cleanup_success_count`: `0`
- `cleanup_failure_count`: `0`
- `safety_zero`: `True`
- `forbidden_seen`: `False`
- `pcie1_gdsc_max_use`: `0`
- `mdm2ap_gpio142_irq_delta`: `0`
- `errfatal_irq_delta`: `0`
- `rc1_progress`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `wlan0_present`: `False`

## Clock Vote Excerpt

- `pcie1_clock_vote.wait_begin=1 async=1 wait_ms=45000 result_path=/cache/native-init-wifi-test-boot-v1672-pcie1-clock-vote-direct.result elapsed_ms=0`
- `pcie1_clock_vote.wait_end=1 ready_count=0 sample_count=897 elapsed_ms=45043`
- `A90_V1664_CLOCK_VOTE_SNAPSHOT phase=pre elapsed_ms=45043`
- `pcie1_clock_vote.clock_00.phase=pre name=gcc_pcie_phy_refgen_clk_src enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_01.phase=pre name=gcc_pcie1_phy_refgen_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_02.phase=pre name=gcc_pcie_1_aux_clk_src enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_03.phase=pre name=gcc_pcie_1_aux_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_04.phase=pre name=gcc_pcie_1_cfg_ahb_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_05.phase=pre name=gcc_pcie_1_mstr_axi_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_06.phase=pre name=gcc_pcie_1_slv_axi_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_07.phase=pre name=gcc_pcie_1_clkref_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_08.phase=pre name=gcc_pcie_1_slv_q2a_axi_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_09.phase=pre name=gcc_pcie_1_pipe_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.begin=1`
- `pcie1_clock_vote.wait_ready_rc=-2`
- `pcie1_clock_vote.mode=bounded-clock-debug-vote-surface-proof`
- `pcie1_clock_vote.allowed_clock_debug_writes=1`
- `pcie1_clock_vote.safety_regulator_write=0`
- `pcie1_clock_vote.safety_gdsc_write=0`
- `pcie1_clock_vote.safety_pci_case_write=0`
- `pcie1_clock_vote.safety_forced_rc1=0`
- `pcie1_clock_vote.safety_pmic_write=0`
- `pcie1_clock_vote.safety_gpio_write=0`
- `pcie1_clock_vote.safety_esoc_notify=0`
- `pcie1_clock_vote.safety_boot_done_spoof=0`
- `pcie1_clock_vote.safety_pci_rescan=0`
- `pcie1_clock_vote.safety_platform_bind=0`
- `pcie1_clock_vote.safety_wifi_hal_start=0`
- `pcie1_clock_vote.safety_scan_connect=0`
- `pcie1_clock_vote.safety_credentials=0`
- `pcie1_clock_vote.safety_dhcp_route=0`
- `pcie1_clock_vote.safety_external_ping=0`
- `pcie1_clock_vote.action_00 name=gcc_pcie_phy_refgen_clk_src rate_value=100000000`
- `pcie1_clock_vote.action_01 name=gcc_pcie1_phy_refgen_clk rate_value=100000000`
- `pcie1_clock_vote.action_02 name=gcc_pcie_1_aux_clk_src rate_value= rate_rc=0 enable_rc=-2 path=/sys/kernel/debug/clk/gcc_pcie_1_aux_clk_src/enable`
- `pcie1_clock_vote.action_03 name=gcc_pcie_1_aux_clk rate_value= rate_rc=0 enable_rc=-2 path=/sys/kernel/debug/clk/gcc_pcie_1_aux_clk/enable`
- `pcie1_clock_vote.action_04 name=gcc_pcie_1_cfg_ahb_clk rate_value= rate_rc=0 enable_rc=-2 path=/sys/kernel/debug/clk/gcc_pcie_1_cfg_ahb_clk/enable`
- `pcie1_clock_vote.action_05 name=gcc_pcie_1_mstr_axi_clk rate_value= rate_rc=0 enable_rc=-2 path=/sys/kernel/debug/clk/gcc_pcie_1_mstr_axi_clk/enable`
- `pcie1_clock_vote.action_06 name=gcc_pcie_1_slv_axi_clk rate_value= rate_rc=0 enable_rc=-2 path=/sys/kernel/debug/clk/gcc_pcie_1_slv_axi_clk/enable`
- `pcie1_clock_vote.action_07 name=gcc_pcie_1_clkref_clk rate_value= rate_rc=0 enable_rc=-2 path=/sys/kernel/debug/clk/gcc_pcie_1_clkref_clk/enable`

## Power/Timing Excerpt

- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `sample=post_provider_micro_1200ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`

## Safety Scope

This run used only the V1672 bounded clock-debug vote surface inside the
test boot. It did not write regulator/GDSC state, `/sys/kernel/debug/pci-msm/case`,
PMIC/GPIO/PERST, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind,
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
Rollback restored `stage3/boot_linux_v724.img` and the base handoff verified
native selftest when `handoff_pass=True`.

## Next

The bounded direct clock-debug write attempt executed and remained inside
the approved clock-only surface, but all target `enable` writes failed.
This closes the debugfs clock-vote surface as a practical pcie1 power-vote
mechanism. Do not keep repeating timing/readiness variants.
The next step is a new plan for a legitimate pcie1 driver PM path or a
separately approved, narrowly targeted pcie1 resource/GDSC gate.
