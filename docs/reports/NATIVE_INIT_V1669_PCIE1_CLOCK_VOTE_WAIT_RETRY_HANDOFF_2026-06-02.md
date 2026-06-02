# Native Init V1669 pcie1 Clock Vote Handoff

## Summary

- Cycle: `V1669`
- Type: one-run rollbackable bounded live pcie1 clock-debug vote proof
- Decision: `v1669-clock-vote-surface-failed`
- Result: REVIEW
- Label: `clock-vote-surface-failed`
- Reason: rollback and cleanup succeeded, but no clock enable write succeeded; target enable leaves were not observed before the bounded wait expired (ready_count=0, wait_elapsed_ms=45020, async_begin_rc=-2)
- Evidence: `tmp/wifi/v1669-pcie1-clock-vote-wait-retry-handoff`
- Handoff/rollback pass: `True`

## Clock Vote Classification

- `begin`: `False`
- `wait_begin`: `True`
- `wait_ready_count`: `0`
- `wait_sample_count`: `897`
- `wait_elapsed_ms`: `45020`
- `async_begin_rc`: `-2`
- `success_count`: `0`
- `failure_count`: `0`
- `rate_success_count`: `0`
- `cleanup_success_count`: `0`
- `cleanup_failure_count`: `0`
- `safety_zero`: `False`
- `forbidden_seen`: `False`
- `pcie1_gdsc_max_use`: `0`
- `mdm2ap_gpio142_irq_delta`: `0`
- `errfatal_irq_delta`: `0`
- `rc1_progress`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `wlan0_present`: `False`

## Clock Vote Excerpt

- `pcie1_clock_vote.wait_begin=1 async=1 wait_ms=45000 result_path=/cache/native-init-wifi-test-boot-v1668-pcie1-clock-vote-wait.result elapsed_ms=0`
- `pcie1_clock_vote.wait_end=1 ready_count=0 sample_count=897 elapsed_ms=45020`
- `pcie1_clock_vote.async_begin_rc=-2 hold_ms=30000`
- `pcie1_clock_vote.cleanup_begin=1 elapsed_ms=45020`
- `pcie1_clock_vote.cleanup_09 name=gcc_pcie_1_pipe_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_08 name=gcc_pcie_1_slv_q2a_axi_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_07 name=gcc_pcie_1_clkref_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_06 name=gcc_pcie_1_slv_axi_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_05 name=gcc_pcie_1_mstr_axi_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_04 name=gcc_pcie_1_cfg_ahb_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_03 name=gcc_pcie_1_aux_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_02 name=gcc_pcie_1_aux_clk_src skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_01 name=gcc_pcie1_phy_refgen_clk skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_00 name=gcc_pcie_phy_refgen_clk_src skipped=1 enable_rc=-11`
- `pcie1_clock_vote.cleanup_success_count=0`
- `pcie1_clock_vote.cleanup_failure_count=0`
- `pcie1_clock_vote.cleanup_end=1`
- `A90_V1664_CLOCK_VOTE_SNAPSHOT phase=post_cleanup elapsed_ms=45020`
- `pcie1_clock_vote.clock_00.phase=post_cleanup name=gcc_pcie_phy_refgen_clk_src enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_01.phase=post_cleanup name=gcc_pcie1_phy_refgen_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_02.phase=post_cleanup name=gcc_pcie_1_aux_clk_src enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_03.phase=post_cleanup name=gcc_pcie_1_aux_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=19200000 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_04.phase=post_cleanup name=gcc_pcie_1_cfg_ahb_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_05.phase=post_cleanup name=gcc_pcie_1_mstr_axi_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_06.phase=post_cleanup name=gcc_pcie_1_slv_axi_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_07.phase=post_cleanup name=gcc_pcie_1_clkref_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_08.phase=post_cleanup name=gcc_pcie_1_slv_q2a_axi_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.clock_09.phase=post_cleanup name=gcc_pcie_1_pipe_clk enable_read_rc=0 enable=0 prepare_read_rc=0 prepare=0 rate_read_rc=0 rate=0 enabled_by_test=0 enable_rc=-11 cleanup_rc=-11`
- `pcie1_clock_vote.async_cleanup_rc=0`
- `pcie1_clock_vote.async_end=1`

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
- `sample=post_provider_micro_1200ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV `
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

## Safety Scope

This run used only the V1668 bounded clock-debug vote surface inside the
test boot. It did not write regulator/GDSC state, `/sys/kernel/debug/pci-msm/case`,
PMIC/GPIO/PERST, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind,
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
Rollback restored `stage3/boot_linux_v724.img` and the base handoff verified
native selftest when `handoff_pass=True`.

## Next

The separate result file was collected and rollback passed, but the async
vote child timed out on the current readiness predicate. Post-cleanup
`enable_read_rc=0` lines show the target clock debugfs leaves were readable,
so the next source/build unit should replace the `lstat + S_ISREG` readiness
predicate with an open/read-based predicate before interpreting hardware behavior.
