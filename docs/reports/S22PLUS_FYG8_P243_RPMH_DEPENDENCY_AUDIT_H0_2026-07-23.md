# S22+ FYG8 P2.43 RPMh dependency audit

Date: 2026-07-23 KST
Tier: H0 host-only
Status: `PASS_P243_RPMH_DEPENDENCY_AUDIT_HOST_ONLY`
Device contact: none
Live authority: none

## Verdict

P2.42 waited on the wrong RSC instance for the USB proof chain.
`af20000.rsc` is the display RSC. All four exact vendor DTBs give it no
`power-domains` property and require display clock ID `0x48` from
`clock-controller@af00000`, whose FYG8 driver is `dispcc-waipio.ko`. The exact
59-module P2.42 plan contains all four hard dependencies of that module but
does not contain the module itself.

The exact kernel source defaults `fw_devlink` to strict/on, treats DT clocks as
required suppliers, and checks suppliers before calling a platform driver's
probe. No override was found in the candidate boot cmdline, stock
`vendor_boot` cmdline/bootconfig, or the hash-pinned same-FYG8 stock cmdline
capture. This gives a source-and-artifact-closed explanation for the missing
display-RSC bind: its display-clock supplier was absent, so
`rpmh_rsc_probe()` could be deferred before entry.

This is not a direct observation of the P2.42 candidate's supplier state or
runtime cmdline. The durable classification is therefore:

```text
STATIC_MISSING_DISPLAY_CLOCK_SUPPLIER_EXPLANATION
p242_live_root_cause_proven=false
```

Adding `dispcc-waipio.ko` would satisfy an irrelevant display gate and widen
scope. It is not the correction.

## Exact Dependency Split

The FYG8 vendor DTB contains four concatenated Waipio/WaipioP variants. All
four have the same split, and all 11 DTBO entries add children without
overriding either RSC parent's dependency properties.

| RSC | Role | Required supplier | P2.42 meaning |
|---|---|---|---|
| `/soc/rsc@af20000` | display RSC | display clock from `/soc/clock-controller@af00000` | old gate, not on the USB/GCC chain |
| `/soc/rsc@17a00000` | apps RSC | `/soc/psci/cluster-pd` power domain | USB-relevant RPMh parent |

The apps-RSC power-domain provider is built into the exact candidate kernel:

1. `/soc/psci` is compatible with `arm,psci-1.0`.
2. Its child `/soc/psci/cluster-pd` has `#power-domain-cells = <0>`.
3. exact `cpuidle-psci-domain.c` binds the parent, initializes each child with
   that property, and calls `of_genpd_add_provider_simple()`;
4. exact OF platform naming derives `soc:psci`; and
5. the candidate config enables `CONFIG_ARM_PSCI_CPUIDLE_DOMAIN=y` and the
   required generic-domain support.

The apps RSC then creates the RPMh clock and regulator child devices.
`gcc-waipio` consumes:

- `17a00000.rsc:qcom,rpmhclk`;
- `17a00000.rsc:rpmh-regulator-cxlvl`; and
- `17a00000.rsc:rpmh-regulator-mxlvl`.

The exact P2.42 plan already contains `qcom_rpmh`, `clk-rpmh`,
`rpmh-regulator`, and `gcc-waipio`. No module-set growth is needed.

## Probe Boundary

The exact source order is:

```text
driver core checks DT suppliers
  -> unavailable supplier returns -EPROBE_DEFER
  -> rpmh_rsc_probe() begins
     -> cmd_db_ready()
     -> resources/TCS/IRQ
     -> attach power-domain only when the node has power-domains
     -> populate RPMh child providers
```

This separates the two RSC instances:

- the failed display node never takes the power-domain branch because it has no
  `power-domains` property;
- the apps node can enter only after its PSCI provider is available, then must
  complete probe before its RPMh clock/regulator children can bind.

P2.42's passed `cmd-db` userspace gate does not prove that the display RSC
entered `rpmh_rsc_probe()`. Its missing clock supplier can defer it earlier.

## Bounded Replacement

P2.44 should replace the existing `rpmh` and `gcc-waipio` gates with one
ordered provider chain while preserving the other gate order:

| New order within provider chain | Predicate |
|---:|---|
| 1 | `/sys/bus/platform/drivers/psci-cpuidle-domain/soc:psci` |
| 2 | `/sys/bus/platform/drivers/rpmh/17a00000.rsc` |
| 3 | `/sys/bus/platform/drivers/clk-rpmh/17a00000.rsc:qcom,rpmhclk` |
| 4 | `/sys/bus/platform/drivers/qcom,rpmh-regulator/17a00000.rsc:rpmh-regulator-cxlvl` |
| 5 | `/sys/bus/platform/drivers/qcom,rpmh-regulator/17a00000.rsc:rpmh-regulator-mxlvl` |
| 6 | `/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller` |

The full E2 gate count becomes 12:

```text
hwspinlock -> smem -> cmd-db
  -> psci-domain -> apps-rsc -> rpmh-clock -> cxlvl -> mxlvl -> gcc
  -> ssusb -> dwc3-core -> udc
```

With the existing base `0x7b`, gate stages occupy `0x7b..0x86`; terminal
success remains `0x8f`. P2.44 must update the runtime, checkpoint transition
model, generated plan, static checker, and tests together. It must not merely
replace one path string.

## Evidence Classes

`VERIFIED`:

- exact source archives, candidate config, boot/vendor-boot inputs, vendor
  DTB, DTBO, module plan, inventory, and dependency TSV are SHA-pinned;
- the four DTBs have the same RSC split;
- the 11 overlays do not change either RSC parent dependency;
- PSCI provider registration and its platform bus ID are source-closed;
- clocks, power domains, and regulator supplies are required `fw_devlink`
  suppliers in the exact source;
- P2.42 selected the USB RPMh/GCC modules but omitted the unrelated display
  supplier; and
- the proposed chain adds no module.

`STRONG STATIC EXPLANATION`:

- the absent display-clock supplier deferred `af20000.rsc` before
  `rpmh_rsc_probe()`.

`OPEN UNTIL A LATER LIVE RUNG`:

- the P2.42 candidate's effective runtime cmdline and supplier-link state;
- PSCI provider, apps RSC, RPMh child-provider, and GCC binds under direct PID
  1; and
- every downstream SSUSB, DWC3, UDC, and host USB result.

## Validation

The H0 checker is:

```text
workspace/public/src/scripts/revalidation/
  s22plus_fyg8_p243_rpmh_dependency_audit.py
```

It fails closed on artifact drift, source-contract drift, DT/DTBO topology
drift, module-plan drift, or a boot-argument override. Six focused tests pass.
The checker contains no build, device, reboot, Odin, or flash action.

An independent host-only review agreed that the display gate is
overconstrained and not a USB prerequisite, and required the same caveat:
the static explanation is strong but not a direct P2.42 runtime root-cause
observation.

The Linux driver-core behavior is independently consistent with the official
[Android common kernel source](https://android.googlesource.com/kernel/common/+/refs/tags/android14-6.1-2025-04_r6/drivers/base/core.c)
and [kernel device-link documentation](https://docs.kernel.org/driver-api/device_link.html).
The PSCI child-provider behavior is also present in the official
[Android common cpuidle PSCI domain driver](https://android.googlesource.com/kernel/common/+/refs/tags/android14-6.1.147_r00/drivers/cpuidle/cpuidle-psci-domain.c).

## Boundary And Next Unit

P2.43 created no image, candidate, D0 binding, approval, or live authority and
did not contact the device.

Next is P2.44 H0: implement the 12-gate provider-chain contract and its strict
stage model, then run focused host tests. Candidate construction, Full-LTO,
D0, and F1 remain out of scope until that implementation has a separate
host-only closure.
