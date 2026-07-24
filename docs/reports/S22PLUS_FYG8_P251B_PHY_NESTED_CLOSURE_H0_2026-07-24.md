# S22+ FYG8 P2.51b PHY Nested Closure (H0)

Date: 2026-07-24 KST

## Scope

This is a host-only focused refinement of P2.51. It answers one question:

> Which lower-level suppliers can keep the exact FYG8 GDSC, HS PHY, or SS PHY
> unbound before `a600000.ssusb` can bind?

The unit reads four FYG8 vendor DTBs from one SHA-pinned container, matched
Samsung/Qualcomm source from directly SHA-pinned archive bytes, the P2.49
effective-rootfs audit, the exact stock vendor ramdisk, module metadata, and
shipped ELF relocations. It does not build or package an image, contact a
device, create live authority, or change the `0x84` frontier.

The reproducible checker is:

```text
s22plus_fyg8_p251b_phy_nested_closure_audit.py
```

## Verdict

`PASS_P251B_PHY_NESTED_CLOSURE_HOST_ONLY`

The four DTB variants have one identical nested supplier graph. Every required
provider module and its recursive hard dependencies are already in the exact
59-module P2.49 candidate closure. No module or checkpoint stage should be
added.

The remaining uncertainty is runtime bind state:

- five exact RPMh LDO wrapper devices;
- Waipio TLMM;
- GDSC;
- HS PHY; and
- SS PHY.

These can be classified with bounded reads inside the existing P2.52 timeout
handler. Another unchanged live candidate would still have no decision value.

## Exact Nested Graph

### HS PHY

All four DTBs give `/soc/hsphy@88e3000`:

| Resource | Provider |
|---|---|
| `ref_clk_src` | `/soc/rsc@17a00000/qcom,rpmhclk` |
| `ref_clk` | `/soc/clock-controller@100000` |
| `phy_reset` | `/soc/clock-controller@100000` |
| `vdd` | `ldob5` / `pm8350_l5` |
| `vdda18` | `ldoc1` / `pm8350c_l1` |
| `vdda33` | `ldob2` / `pm8350_l2` |

The exact source treats the source clock, reset, and three regulators as
probe-fatal acquisitions. Its failed regulator path removes the PHY that it
registered earlier, so a later deferred retry is not statically blocked by an
obvious stale PHY registration.

### SS PHY

All four DTBs give `/soc/ssphy@88e8000`:

| Resource | Provider |
|---|---|
| six GCC clocks | `/soc/clock-controller@100000` |
| `ref_clk_src` | `/soc/rsc@17a00000/qcom,rpmhclk` |
| two resets | `/soc/clock-controller@100000` |
| `vdd` | `ldob1` / `pm8350_l1` |
| `core` | `ldob6` / `pm8350_l6` |
| `pinctrl-0` | `/soc/pinctrl@f000000` |

The pinctrl dependency was not listed in the first P2.51 discriminator.
Matched `of/property.c` parses `pinctrl-0` as a firmware supplier, so it belongs
in the nested closure. TLMM in turn uses the already-listed PDC path. Its
modules, `pinctrl-waipio.ko`, `pinctrl-msm.ko`, and `qcom-scm.ko`, are all
already selected.

The SS source registers its USB PHY before acquiring `vdd` and `core`. Unlike
the HS path, its failed probe body has no `usb_remove_phy()` cleanup. This is
not proof that P2.50 leaked a PHY. It is a focused follow-up mechanism only if
P2.52 later proves all nested providers bound while SS PHY remains unbound.

### GDSC

`/soc/qcom,gdsc@149004` has:

- no `clocks`, resets, interconnects, power domains, parent supply, or other
  external provider property;
- one `proxy-supply` phandle pointing back to the same GDSC node.

Matched `of_link_to_phandle()` rejects a consumer linked to itself because the
self node satisfies its ancestor check. Therefore that property does not make
an unresolved external `fw_devlink` supplier.

If the GDSC driver symlink is absent, the remaining branch is inside GDSC
probe/registration. The exact module carries regulator, proxy-consumer, and
debug-regulator calls, and both hard dependencies are selected. Its runtime
return value remains unobserved.

## Module And ELF Closure

The checker independently decompresses the exact 21,813,545-byte FYG8 vendor
ramdisk, parses 452 newc entries, and matches these seven module identities
against both P2.49 static closure and `inventory.tsv`:

- `clk-rpmh.ko`
- `gcc-waipio.ko`
- `gdsc-regulator.ko`
- `phy-msm-snps-hs.ko`
- `phy-msm-ssusb-qmp.ko`
- `pinctrl-waipio.ko`
- `rpmh-regulator.ko`

All recursive hard dependencies are inside the selected 59 modules. Exact
probe ELF relocations confirm the expected clock, reset, regulator, pinctrl,
command-DB, and PHY registration calls.

Neither exact PHY module imports `sysfs_create_group` or
`sysfs_remove_group`. The matched source uses those calls only in the
`CONFIG_USB_PHY_TUNING_QCOM` branch, so that branch was compiled out of the
shipped modules used by P2.49. It cannot explain their bind failure. The GKI
`.config` alone could not establish this vendor-module fact; source plus exact
ELF does.

## Reasoning Ledger

| ID | Evidence | Inference | Limit |
|---|---|---|---|
| R1 | four DTBs have identical lower closure | variant selection is not the P2.50 cause | candidate bind state remains unknown |
| R2 | GDSC has only a rejected self supply link | no hidden external GDSC supplier remains | GDSC probe return is unknown |
| R3 | exact module bytes and all hard deps are selected | module growth is unjustified | insertion does not prove bind |
| R4 | exact PHY ELF lacks both tuning sysfs imports required by matched source | tuning config is ruled out as bind blocker | other probe errors remain |
| R5 | HS cleans failed registration; SS does not | SS cleanup is a later focused lead | no leak/retry failure was observed |

## P2.52 Refinement

Keep stage `0x84`, item 9, the 59-module plan, and the one global deadline.
When the existing SSUSB check expires:

1. read `waiting_for_supplier`;
2. check the seven P2.51 direct provider paths;
3. check these six nested paths only as timeout classification;
4. check HS and SS PHY binds;
5. if all are ready, allow one five-second SSUSB-only grace.

The nested detail mapping is:

| Detail | Missing bind |
|---|---|
| `0xa08` | `waipio-pinctrl/f000000.pinctrl` |
| `0xa09` | SS `vdd`, RPMh `ldob1` |
| `0xa0a` | SS `core`, RPMh `ldob6` |
| `0xa0b` | HS `vdd`, RPMh `ldob5` |
| `0xa0c` | HS `vdda18`, RPMh `ldoc1` |
| `0xa0d` | HS `vdda33`, RPMh `ldob2` |

Existing proposed meanings remain:

| Detail | Meaning |
|---|---|
| `0xa01..0xa07` | first missing direct provider |
| `0xa10` | all enumerated providers bound, `waiting_for_supplier=1` |
| `0xa20..0xa21` | HS or SS PHY unbound |
| `0xa30` | all enumerated dependencies ready, parent still unbound after grace |

These values remain inactive until P2.52 defines them once in the descriptor
single source of truth and derives kernel validation and host decoding from
that definition. This is one timeout classifier, not six new stages or a new
policy layer.

## What This Proves

- four exact vendor DTBs share one nested PHY/GDSC closure;
- all required module bytes and hard dependencies are already packaged;
- TLMM and five RPMh wrapper paths are the remaining bounded provider reads;
- GDSC has no unresolved external DT supplier;
- PHY tuning is compiled out of the exact modules; and
- P2.52 can proceed without broader analysis or module growth.

## What This Does Not Prove

- which nested provider bound in direct PID1;
- whether either PHY probe ran or what it returned;
- whether SS PHY left a stale registration;
- whether GDSC probe succeeded;
- whether SSUSB binds with a dedicated five-second grace; or
- candidate readiness, device health, or live authority.

## Reproduction

```bash
PYTHONPYCACHEPREFIX=/tmp/android_native_init_pycache \
python3 workspace/public/src/scripts/revalidation/\
s22plus_fyg8_p251b_phy_nested_closure_audit.py

PYTHONPYCACHEPREFIX=/tmp/android_native_init_pycache \
python3 -m unittest -v \
tests.test_s22plus_fyg8_p251b_phy_nested_closure_audit
```

Expected verdict:

```text
PASS_P251B_PHY_NESTED_CLOSURE_HOST_ONLY
```
