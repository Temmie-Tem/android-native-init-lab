# S22+ The Real Problem: We Read the modules.dep Symbol Graph, Not the DT Phandle-Supplier Graph — the Whole SoC Substrate Is Missing (live devlink walk, 2026-07-09)

Operator (Claude) read-only analysis on the live rooted device, answering "we
dug through stock, so what's actually the problem?" No writes, no flash. This is
the decisive root cause behind B1=MISS and the whole S4→S8B1 stall.

## The answer

Device probing does not follow `modules.dep` (a **symbol** graph). It follows
the **DT phandle-supplier graph** — `clocks=<&gcc>`, `pinctrl-0=<&tlmm>`,
`power-domains=<&gdsc>`, `interconnects=<...>`, `iommus=<&apps_smmu>`. That is a
different, larger graph, and it is **invisible to a `modules.dep` closure**. We
have been reconstructing it by hand, one attended flash at a time, and it keeps
leaking (M5 dwc3←regulators/PHYs; S7A max77705←i2c-bus; S8B1 i2c-bus←?).

The live stock kernel exposes that graph directly as **device links**. Walking
the transitive supplier closure of `{994000.i2c, a600000.dwc3, a600000.ssusb,
max77705@57-0066}` from `/sys/devices/virtual/devlink/` (859 total edges) yields
an 18-device substrate, backed by these drivers:

```text
100000.clock-controller      DRIVER=gcc-waipio     # GCC: i2c se-clk/m-ahb/s-ahb + ssusb clocks
f000000.pinctrl              DRIVER=waipio-pinctrl  # TLMM: i2c SDA/SCL pin mux
149004.qcom,gdsc             DRIVER=gdsc            # USB3 GDSC power domain
1500000/16e0000/19100000.interconnect DRIVER=qnoc-waipio  # NoC bandwidth votes (ssusb)
15000000.apps-smmu           DRIVER=arm-smmu        # IOMMU for dwc3
b220000.interrupt-controller DRIVER=qcom-pdc        # PDC wakeup IRQ controller
17a00000.rsc:qcom,rpmhclk    -> clk-rpmh            # RPMh clocks
17a00000.rsc:rpmh-regulator-cxlvl/mxlvl -> rpmh-regulator  # RPMh regulators (cx/mx levels)
88e0000.qcom,msm-eud         DRIVER=msm-eud         # EUD (a listed ssusb supplier)
900000.qcom,gpi-dma          DRIVER=gpi             # GPI DMA  (the ONE we already load)
c42d000...pm8350c...pinctrl  -> pmic pinctrl (spmi)
regulator:regulator.2/.6/.18 -> rpmh-regulator LDOs
```

**Cross-checked against our S8B1 set: every one of these is MISSING except
`gpi`.** We load `i2c-msm-geni` + `msm-geni-se` + `gpi` + the max77705 producers,
but not the **clocks (gcc-waipio, clk-rpmh), pinctrl (waipio-pinctrl), power
domains (gdsc), regulators (rpmh-regulator), interconnects (qnoc-waipio), IOMMU
(arm-smmu), or interrupt controller (qcom-pdc)** that every one of those devices
hangs off. So `i2c_msm_geni` loads, finds no clocks/pinctrl, sits on the
deferred-probe list forever, the bus never comes up, `max77705@57-0066` is never
instantiated → `/sys/class/typec/port0` absent → **B1=MISS**.

That is the thing we had not grasped: not "one more module," but **the entire
foundational SoC substrate** (clock/pinctrl/power/interconnect/iommu) that a bare
curated USB module set silently omits.

## Why we kept missing it — and why it is now fixable in one closure

- **modules.dep hides it.** All of the above are phandle references, not symbol
  exports, so a symbol-closure of the USB/i2c leaf modules never pulls them in.
- **The curated-subset approach was a workaround for the M6 watchdog bootloop.**
  M6 (full `modules.load`) bootlooped only because the armed watchdog was
  starved — which we SOLVED at M31B (load `qcom_wdt_core`, kernel-timer pet). So
  the original reason to hand-curate is gone.
- **The devlink closure is bounded and self-excluding.** The 18-device closure
  contains no display/wlan/thermal/sensor devices — those are simply not
  suppliers of USB/i2c — so loading exactly this substrate does **not**
  reintroduce the M6 BUG/panic class.

## S9 recipe: load the devlink-closure substrate, then re-run B1

1. Map each closure driver to its vendor `.ko` from stock `modules.load` +
   `modules.dep` (e.g. `gcc-waipio.ko`, `pinctrl-waipio.ko`, `gdsc-regulator.ko`,
   the `qnoc-waipio`/`icc-*` interconnect `.ko`, `clk-rpmh` via `clk-qcom`,
   `rpmh-regulator.ko`, `qcom-pdc.ko`, `arm-smmu` — **verify which are modules vs
   built-into the GKI kernel; only load the module ones**).
2. Load the substrate **before** `msm-geni-se`/`i2c-msm-geni`/producers, in
   `modules.load`/`modules.dep` order; deferred-probe then completes the chain.
3. Keep the S7A2/S8B1 recipe otherwise (mode=peripheral, minimal ss_acm configfs,
   soft_connect OFF), keep the watchdog loaded (M31B).
4. **Re-run the B1 beacon** (`/sys/class/typec/port0` OR `57-0066` exists →
   reboot-download HIT). B1 flipping to HIT proves the substrate brought the i2c
   bus + max77705 up; only then advance to B2/B3/B4.

## Resolved `.ko` load-set (confirmed: all are vendor modules, none GKI-built-in)

Every closure driver has a matching vendor `.ko` **and** is loaded on live stock
(`lsmod`), so all must be loaded — none are built into the GKI kernel. Use the
**waipio** (SM8450) instances, not diwali/parrot/cape. Load frameworks/parents
before instances; take exact order from `modules.dep`/`modules.load`:

```text
# framework/parent cores first
clk-qcom.ko            # common clk framework (gcc-waipio depends on it)
pinctrl-msm.ko         # pinctrl core (pinctrl-waipio depends on it)
qcom-rpmh.ko           # RPMh RSC @17a00000.rsc = PARENT of clk-rpmh + rpmh-regulator
icc-rpmh.ko            # interconnect framework
icc-bcm-voter.ko       # interconnect BCM voter
# SoC instances
gcc-waipio.ko          # 100000.clock-controller (i2c se-clk/m-ahb/s-ahb + ssusb)
pinctrl-waipio.ko      # f000000.pinctrl (TLMM: i2c SDA/SCL)
clk-rpmh.ko            # RPMh clocks
rpmh-regulator.ko      # RPMh regulators (cx/mx + LDO regulator.2/.6/.18)
gdsc-regulator.ko      # 149004.qcom,gdsc (USB3 power domain)
qnoc-waipio.ko         # 1500000/16e0000/19100000.interconnect
arm_smmu.ko            # 15000000.apps-smmu (dwc3 IOMMU) -- a MODULE here, not built-in
qcom-pdc.ko            # b220000.interrupt-controller -- also a MODULE
# then the transport + producers already in S7A2/S8B1
gpi.ko ; msm-geni-se.ko ; i2c-msm-geni.ko ; <max77705/pdic/altmode chain> ; dwc3-msm ; ...
```

The loop must still confirm exact `.ko` filenames + dep order against
`modules.dep` (some have transitive deps: e.g. `qcom-rpmh` pulls `smem`/`cmd-db`;
`arm_smmu` may pull `qcom_iommu_util`). But the closure above is the complete
provider set — no more one-module-at-a-time guessing.

## Honest scope

Fixing the substrate is necessary and likely unblocks B1/B2 (chip reachable +
cable detect), but B3/B4 (data_role/session/pullup) may still have their own
supplier or userspace needs — now each is observable via the beacon ladder.
Loading gcc/gdsc/rpmh-regulator/interconnect brings up a large, coherent chunk of
the platform the way stock first-stage does; it is the correct level to operate
at, not a risk to avoid.

## Safety

The closure contains power-domain (`gdsc`), regulator (`rpmh-regulator`),
interconnect, and PMIC-pinctrl providers. **Loading these stock DRIVERS so
devices probe normally is not a manual power write** — the drivers auto-manage
their domains via the genpd/regulator/icc frameworks exactly as stock boot does;
that is categorically different from the bright-line "no manual PMIC/regulator/
GDSC/GPIO rail write." The S9 candidate must still write **no** charge-current,
OTG/VBUS-boost, or raw rail/GDSC-enable knobs by hand. Flag this driver-load-vs-
rail-write distinction explicitly at the S9 gate. Read-only host analysis only;
raw dumps (serial) stay in scratchpad; any S9 live test needs a fresh SHA-pinned
boot-only exception.
