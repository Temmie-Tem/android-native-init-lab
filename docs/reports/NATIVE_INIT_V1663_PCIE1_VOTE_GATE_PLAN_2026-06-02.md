# Native Init V1663 pcie1 Vote Gate Plan

## Summary

- Cycle: `V1663`
- Type: host-only plan for the separately authorized AP-side pcie1 power/clock vote gate
- Decision: `v1663-pcie1-clock-vote-gate-plan-ready`
- Result: PASS
- Reason: V1662 fixed a `power-vote-gap`; the first live mutation should prove only the narrow clock-debug vote surface before any broader regulator/GDSC or PCI path write.
- Device command: `False`

## Inputs

- `v1662_report`: `docs/reports/NATIVE_INIT_V1662_ANDROID_NATIVE_POWER_DIFF_CLASSIFIER_2026-06-02.md`
- `power_diff_contract`: `docs/reports/ESOC_ANDROID_NATIVE_POWER_DIFF_CONTRACT_2026-06-02.md`
- `clock_debug`: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c`
- `pci_msm`: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c`
- `sm8150_pcie_dtsi`: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi`

## Checks

- `v1662_power_vote_gap`: `True`
- `contract_requires_separate_write_gate`: `True`
- `clock_debug_enable_write_surface`: `True`
- `clock_debug_rate_write_surface`: `True`
- `pcie_dtsi_maps_gdsc`: `True`
- `pcie_dtsi_lists_target_clocks`: `True`
- `pci_msm_normal_path_is_broad`: `True`
- `pci_msm_debug_case_broad`: `True`
- `gdsc_direct_write_surface_unproven`: `True`
- `no_live_command`: `True`

## V1662 Gap Carried Forward

- Regulator gaps: `pcie_1_gdsc`
- Clock gaps: `gcc_pcie1_phy_refgen_clk, gcc_pcie_1_aux_clk, gcc_pcie_1_aux_clk_src, gcc_pcie_1_cfg_ahb_clk, gcc_pcie_1_clkref_clk, gcc_pcie_1_mstr_axi_clk, gcc_pcie_1_pipe_clk, gcc_pcie_1_slv_axi_clk, gcc_pcie_1_slv_q2a_axi_clk, gcc_pcie_phy_refgen_clk_src`

## Static Source Notes

- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:38: static int clock_debug_rate_set(void *data, u64 val)`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:48: ret = clk_set_rate(clock, val);`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:50: pr_err("clk_set_rate(%s, %lu) failed (%d)\n", clock->dbg_name,`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:64: clock_debug_rate_set, "%llu\n");`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:119: static int clock_debug_enable_set(void *data, u64 val)`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:125: rc = clk_prepare_enable(clock);`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/msm/clock-debug.c:147: clock_debug_enable_set, "%lld\n");`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:153: gdsc-vdd-supply = <&pcie_0_gdsc>;`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:223: clock-names = "pcie_0_pipe_clk", "pcie_0_ref_clk_src",`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:227: "pcie_tbu_clk", "pcie_phy_refgen_clk",`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:459: gdsc-vdd-supply = <&pcie_1_gdsc>;`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:529: clock-names = "pcie_1_pipe_clk", "pcie_1_ref_clk_src",`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:533: "pcie_tbu_clk", "pcie_phy_refgen_clk",`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:631: gdsc-vdd-supply = <&pcie_1_gdsc>;`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:650: clock-names = "pcie_pipe_clk", "pcie_cfg_ahb_clk",`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:483: MSM_PCIE_ENABLE_LINK,`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:492: MSM_PCIE_ENUMERATION,`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:510: MSM_PCIE_KEEP_RESOURCES_ON,`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:1740: case MSM_PCIE_ENABLE_LINK:`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:1846: case MSM_PCIE_ENUMERATION:`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:2332: case MSM_PCIE_KEEP_RESOURCES_ON:`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4606: static int msm_pcie_enable(struct msm_pcie_dev_t *dev, u32 options)`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:5280: ret = msm_pcie_enable(dev, PM_ALL);`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:8389: ret = msm_pcie_enable(pcie_dev, PM_PIPE_CLK | PM_CLK | PM_VREG);`

## First Live Gate

- Cycle: `V1665`
- Name: `bounded clock-debug vote surface proof`
- Trigger: test boot PID1 mounts debugfs, writes only targeted clock debugfs leaf files, samples the existing pcie1/GPIO/subsystem observables, then disables only clocks it enabled.
- Allowed writes: targeted `/sys/kernel/debug/clk/<target>/rate` and `/sys/kernel/debug/clk/<target>/enable` only.
- Initial target clocks: `gcc_pcie_1_aux_clk_src`, `gcc_pcie_1_aux_clk`, `gcc_pcie_1_cfg_ahb_clk`, `gcc_pcie_1_mstr_axi_clk`, `gcc_pcie_1_slv_axi_clk`, `gcc_pcie_1_clkref_clk`, `gcc_pcie_1_slv_q2a_axi_clk`, `gcc_pcie_phy_refgen_clk_src`, `gcc_pcie1_phy_refgen_clk`, `gcc_pcie_1_pipe_clk`.
- Rates: set refgen/source clocks that Android shows at `100000000`; leave fixed-gate clocks at existing rates.
- Hold: bounded short hold only; no timing/window variants after one result.
- Cleanup: disable only clocks successfully enabled by the test boot, then rollback to `stage3/boot_linux_v724.img` and verify selftest.

## Explicit Non-goals

- No regulator/GDSC direct write in this gate; no safe per-GDSC write surface is proven yet.
- No `/sys/kernel/debug/pci-msm/case` write; `MSM_PCIE_ENABLE_LINK`/`MSM_PCIE_ENUMERATION` are broader normal/debug paths and previously contaminate MDM2AP observation.
- No PMIC/GPIO/PERST write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Result Labels

- `clock-vote-surface-pass-no-gdsc`: clock writes succeed and clean up, but pcie1 GDSC/RC1/MDM2AP do not move.
- `clock-vote-surface-pass-gdsc-moved`: clock writes succeed and pcie1 power/link observables change; next gate can consider a fuller pcie1 normal resource vote.
- `clock-vote-surface-failed`: clock leaf write/readback or cleanup fails; stop and repair the harness.

## Next

Implement V1664 source/build-only test boot support and run one rollbackable V1665 live handoff under this gate.
