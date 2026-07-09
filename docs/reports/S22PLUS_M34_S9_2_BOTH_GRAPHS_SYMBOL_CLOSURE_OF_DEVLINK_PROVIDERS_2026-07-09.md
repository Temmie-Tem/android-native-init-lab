# S22+ Why S9 Still Missed: We Loaded the devlink Providers But Not Their modules.dep Symbol-Deps — the Complete Set Needs BOTH Graphs (2026-07-09)

Operator (Claude) host-only analysis after S9 (full devlink substrate) still
returned B1=MISS. No writes, no flash. This proves the "static blueprint + living
result, together" point concretely and gives the corrected S9.2 load-set.

## The result that forced this

S9 loaded the 16-module devlink **supplier** closure (`gcc-waipio`,
`pinctrl-waipio`, `gdsc-regulator`, `qnoc-waipio`, `arm_smmu`, `qcom-pdc`,
`clk-rpmh`, `rpmh-regulator`, `clk-qcom`, `icc-rpmh`, `icc-bcm-voter`,
`pinctrl-msm`, `gpi`, `msm-geni-se`, `i2c-msm-geni`) — and B1 was **still MISS**:
`/sys/class/typec/port0` and `/sys/bus/i2c/devices/*-0066` still absent.

## Why: providers have their OWN symbol-deps, and we skipped them

The devlink graph told us **which provider devices** the USB/i2c chain needs. But
each provider **module** has its own `modules.dep` **symbol** dependencies that
must also be loaded, or `insmod` fails silently (and native init is blind to
that). Computing the transitive `modules.dep` closure of the S9 set shows **16
more modules** are required and were not loaded:

```text
cmd-db.ko            <-- RPMh command DB: gcc/clk-rpmh/rpmh-regulator/qcom-rpmh
                         CANNOT PROBE without it -> no clocks -> i2c dead
smem.ko              <-- shared memory, foundational
qcom-scm.ko          <-- secure monitor calls (arm_smmu, secure_buffer, ...)
socinfo.ko           <-- SoC info, common probe dep
qcom_ipc_logging.ko  <-- logging, dep of many
qcom_iommu_util.ko   \
secure_buffer.ko      >  arm_smmu (dwc3 IOMMU) deps
iommu-logger.ko      /
proxy-consumer.ko    \
debug-regulator.ko    >  regulator framework helpers
clk-dummy.ko         /
minidump.ko          \
sec_debug.ko          >  geni/substrate crash-registrar deps (seen at M28 too)
qnoc-qos.ko          <-- interconnect QoS
icc-debug.ko
qcom_rpmh.ko         <-- (name-form of the RPMh RSC parent)
```

`cmd-db` is the smoking gun: on this SoC the GCC and every RPMh clock/regulator
resolves resource addresses through the command DB. Without `cmd-db.ko`, the RPMh
RSC + clocks + regulators fail to probe, so `gcc-waipio` has no upstream, so
`994000.i2c` never gets `se-clk`/`m-ahb`/`s-ahb`, so it defers forever → B1 MISS.
This is the same class as the whole saga, now at the substrate's substrate.

## The general rule (your "static + living together", made exact)

The complete native-init load-set for any device target is the transitive
closure over **BOTH** graphs, seeded from the target devices:

```text
COMPLETE_SET = closure(
    seeds = {target devices},
    edges = devlink-supplier-graph   (LIVING: /sys/devices/virtual/devlink/, "which providers")
          ∪ modules.dep-symbol-graph (STATIC: modules.dep, "each provider's symbol-deps")
)
ordered by modules.load
```

- **devlink alone** (S9) → providers without their symbol-deps → insmod/probe
  fails → MISS.
- **modules.dep alone** (M5..S7A) → symbol-deps without the phandle providers →
  probe defers → MISS.
- **Both, together** → complete. Neither graph is sufficient alone; that is
  exactly why we kept missing it.

## S9.2 recipe

1. Load-set = the 32-module BOTH-graphs closure above (16 devlink providers + 16
   symbol-deps), plus the max77705/pdic/altmode producer chain and its own
   BOTH-graphs closure, plus dwc3/typec.
2. **Order by stock `modules.load`** — it already places `cmd-db`, `smem`,
   `qcom-scm`, `socinfo`, `qcom_ipc_logging`, RPMh, then `gcc`, then pinctrl,
   then the QUP/geni i2c, then the max77705 chain, in the correct foundation-first
   order. Simplest robust implementation: load the `modules.load` prefix filtered
   to the closure set, in `modules.load` order.
3. Keep watchdog (M31B), mode=peripheral, minimal ss_acm, soft_connect OFF.
4. **Re-run B1.** `cmd-db`/`smem`/`scm`/`socinfo` present should let RPMh→gcc→i2c
   probe; B1 flipping to HIT proves the bus + max77705 came up.

Optional finer instrumentation if B1 still misses: a pre-B1 beacon that reports
whether the substrate modules actually `insmod`-ed and whether
`/sys/devices/platform/soc/100000.clock-controller/driver` bound (gcc probed) and
`/sys/kernel/debug/devices_deferred` is empty for `994000.i2c` — to see the
insmod/probe layer we are currently blind to.

## Still-pending, secondary (after B1 passes)

Widening the devlink closure to the role/session/pullup path (B2–B4) — including
whether the role reaches dwc3 by I2C-direct (`pdic_max77705`→TCM→dwc3) or via
`altmode-glink`→`pmic_glink`→charger-DSP (a glink/rpmsg/remoteproc substrate that
devlink may not surface) — remains queued. It is moot until B1 (bus + chip up)
passes, so do S9.2 first.

## Safety

Read-only host analysis (`modules.dep` on disk + already-captured devlink). The
added modules (`cmd-db`/`smem`/`qcom-scm`/`socinfo`/regulator-helpers/iommu-utils)
are stock driver loads enabling normal probe — not manual PMIC/regulator/GDSC/rail
writes. `qcom-scm` provides the SCM interface drivers use; it is not a partition
or power write. S9.2 candidate stays boot-only, watchdog-managed, writes no
charge/OTG/rail knobs. Any live test needs a fresh SHA-pinned boot-only exception.
