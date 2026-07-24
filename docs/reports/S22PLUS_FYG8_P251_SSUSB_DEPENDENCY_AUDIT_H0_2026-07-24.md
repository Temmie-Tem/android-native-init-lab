# S22+ FYG8 P2.51 SSUSB Dependency Audit (H0)

Date: 2026-07-24 KST

## Scope

This is a host-only focused analysis of the P2.50 boundary:

```text
generation 76: stage 0x83, item 8, gcc-waipio, success
generation 77: stage 0x84, item 9, ssusb, ETIMEDOUT
```

No device was contacted. No candidate was built, packaged, flashed, or
authorized. The question is not whether USB works in general. The question is:

> Why did `/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb` not appear before
> the P2.49 E2 gate deadline?

The reproducible checker is
`s22plus_fyg8_p251_ssusb_dependency_audit.py`. It pins the P2.49 plan/runtime,
the P2.50 retained result, four exact FYG8 vendor DTBs, the shipped
`dwc3-msm.ko`, the FYG8 source archives, and the same-build stock topology.

## Verdict

`PASS_P251_SSUSB_DEPENDENCY_AUDIT_HOST_ONLY`

The exact root cause is **not yet identified**, but the search space is now
bounded to four branches:

1. a direct supplier blocks probe through strict `fw_devlink`;
2. probe starts and defers/fails on GDSC or either USB PHY;
3. all dependencies are ready but a mandatory probe operation fails; or
4. the shared 20-second gate deadline leaves too little dwell for SSUSB.

There is no current evidence for adding another module. An unchanged E2 retry
would not distinguish these branches.

## Evidence Used

| Evidence | Result | What it proves | What it does not prove |
|---|---|---|---|
| P2.50 retained record | GCC `0x83` PASS, SSUSB `0x84` timeout | exact live frontier and clean rollback | provider state or probe entry |
| P2.49 plan | 59 unique modules, required provider/PHY modules present | selected load closure | driver bind |
| P2.49 runtime | module loop precedes gate loop | all module checks finish before gate timing | asynchronous bind completion |
| P2.49 runtime | one deadline is created before all 12 gates | timeout is global | dedicated SSUSB wait duration |
| four vendor DTBs | identical SSUSB supplier/PHY topology | exact board dependency graph | direct-PID1 bind state |
| stock runtime topology | same direct supplier links and bound SSUSB | topology is used on this FYG8 board | candidate state |
| FYG8 source | strict `fw_devlink`, probe ordering, error paths | possible pre-probe and in-probe boundaries | which branch occurred live |
| exact `dwc3-msm.ko` | probe call relocations match key source operations | key operations exist in shipped binary | return value seen during P2.50 |

## Analysis and Inference Ledger

### R1: Module registration is no longer the frontier

The runtime completes the 59-entry insertion and `/proc/modules` verification
loop before starting the bind-gate deadline. P2.50 then reached item 9.

Inference:

- missing module file, insertion failure, or prefix verification failure did
  not stop this run;
- every provider module required by the current static closure was selected;
- this still does not establish that GDSC, PDC, qnoc, EUD, or either PHY bound.

This rejects "add another module" as an evidence-based next action.

### R2: The upstream RPMh/GCC correction worked

The previous valid slot is generation 76 at `0x83`, item 8,
`gcc-waipio`, outcome success. This is stronger than a module-presence check:
the exact GCC driver/device symlink existed.

Inference:

- the P2.43/P2.44 replacement chain reached GCC;
- the P2.42 display-RSC mistake is no longer the active boundary;
- the next unresolved boundary is the SSUSB parent, not the clock-controller
  gate.

### R3: `ETIMEDOUT` does not mean "SSUSB waited 20 seconds"

The runtime creates one deadline:

```c
deadline.tv_sec += S22_P241_GATE_TIMEOUT_SEC; /* 20 seconds */
while (completed < S22PLUS_O2_BIND_GATE_COUNT) {
    ...
}
```

It is not reset after each gate. Therefore the SSUSB observation window is:

```text
0 seconds <= SSUSB dwell <= 20 seconds
```

The exact value is not retained. If GCC appeared near the deadline, SSUSB could
have received only one poll interval. Consequently "late but valid bind" is an
open timing confound, not a proven dependency failure.

### R4: Strict `fw_devlink` can block before `dwc3_msm_probe()`

The exact source defaults to `fw_devlink=on` and
`fw_devlink.strict=true`. No candidate, vendor boot, bootconfig, or captured
same-build bootloader command line overrides those defaults.

Before the bus invokes a probe, `device_links_check_suppliers()` can return
`-EPROBE_DEFER`. OF supplier parsing includes:

- clocks;
- `*-supply` regulators;
- interconnects;
- interrupts; and
- extcon.

The driver core exposes
`/sys/devices/platform/soc/a600000.ssusb/waiting_for_supplier` before bind,
reports whether unresolved firmware-node suppliers remain, and removes it
after a successful bind.

Inference:

- this one stable sysfs value separates pre-probe supplier wait from later
  probe failure much better than another blind timeout;
- P2.50 did not read it, so pre-probe and in-probe failure remain conflated.

### R5: Exact direct suppliers are known

All four concatenated vendor DTBs agree on this parent topology:

| Role | DT provider |
|---|---|
| clocks/reset | `/soc/clock-controller@100000` |
| USB3 GDSC supply | `/soc/qcom,gdsc@149004` |
| interconnect | `/soc/interconnect@16e0000` |
| interconnect | `/soc/interconnect@1` |
| interconnect | `/soc/interconnect@1500000` |
| interconnect | `/soc/interconnect@19100000` |
| wake interrupts | `/soc/interrupt-controller@b220000` |
| extcon supplier | `/soc/qcom,msm-eud@88e0000` |

The child refers to:

| Role | DT provider |
|---|---|
| HS PHY | `/soc/hsphy@88e3000` |
| SS PHY | `/soc/ssphy@88e8000` |
| IOMMU | `/soc/apps-smmu@15000000` |

The same-build stock runtime exposed exactly the platform suppliers above plus
the dynamic GDSC regulator link. This ties the static graph to the real board.

### R6: Probe entry has separate fatal boundaries

The source order inside `dwc3_msm_probe()` is:

1. optional redriver lookup;
2. USB3 GDSC, clocks, and reset;
3. mandatory IRQ/resource setup;
4. first child lookup;
5. HS PHY lookup;
6. SS PHY lookup;
7. interconnect setup;
8. role-switch registration; and
9. extcon/property handling.

Important error semantics:

- GDSC `-EPROBE_DEFER` returns from probe;
- mandatory clock/reset acquisition errors return from probe;
- missing mandatory power-event IRQ returns from probe;
- either `devm_usb_get_phy_by_node()` error returns from probe;
- `of_icc_get()` errors are converted to `NULL` and do not directly abort
  probe, although qnoc can still block earlier through `fw_devlink`.

Thus a `waiting_for_supplier=0` parent can still remain unbound because probe
entered and failed.

### R7: Exact ELF narrows extcon and redriver

The shipped module is SHA-pinned and has:

```text
dwc3_msm_probe address=0x5db0 size=0x12ec
```

Its probe has relocations for redriver, regulator, clocks, IRQs, child lookup,
both PHY lookups, interconnect, and role-switch registration. It has no
`extcon_*` call relocation in the probe. The exact DT also has no
`ssusb_redriver` property, and the redriver helper returns `NULL` when the
phandle is absent.

Inference:

- missing redriver is ruled out;
- EUD remains relevant as a strict firmware-link supplier;
- active probe-internal extcon registration is not the leading branch for this
  exact binary.

## Hypothesis Matrix

| ID | Hypothesis | Status | Reason |
|---|---|---|---|
| H1 | pre-probe `fw_devlink` supplier wait | `OPEN_HIGH_PRIORITY` | exact strict source and direct DT suppliers |
| H2 | probe starts, then GDSC/PHY defers | `OPEN` | exact fatal acquisition paths |
| H3 | probe starts, then mandatory resource/role operation fails | `OPEN_LOWER_PRIORITY` | possible, but no probe-entry evidence |
| H4 | shared deadline leaves insufficient SSUSB dwell | `OPEN_CONFOUND` | no per-gate timing and zero-second lower bound |
| H5 | missing module or GCC provider | `RULED_OUT_FOR_P2.50` | module loop and live GCC success |
| H6 | absent redriver | `RULED_OUT` | no phandle; helper returns `NULL` |
| H7 | `of_icc_get()` error directly aborts probe | `RULED_OUT` | exact source converts errors to `NULL` |

## Bounded Next Discriminator

Do not add stages or modules. Keep the monotonic frontier at stage `0x84`,
item 9, and classify only when the existing SSUSB check reaches its deadline.

Read in this order:

1. `waiting_for_supplier`;
2. seven fixed parent-provider driver symlinks;
3. the HS and SS PHY driver symlinks.

Use a defined subset of the reserved detail band `0xa00..0xaff`:

| Detail | Meaning |
|---|---|
| `0xa01` | GDSC provider unbound |
| `0xa02` | PDC provider unbound |
| `0xa03..0xa06` | one of four qnoc providers unbound |
| `0xa07` | EUD provider unbound |
| `0xa10` | `waiting_for_supplier=1`, fixed providers bound; dynamic/other supplier unresolved |
| `0xa20` | HS PHY unbound |
| `0xa21` | SS PHY unbound |
| `0xa30` | all checked dependencies ready, parent still unbound |

This band is available but not active: the P2.48 contract currently labels
`0xa00..0xfff` as `reserved` and rejects it. P2.52 must define only the exact
SSUSB subset in the existing descriptor single source of truth, then derive
kernel-validator and host-decoder acceptance from that definition. Emitting
these values without that contract change would correctly produce another
formal rejection.

If all fixed dependencies are ready at the global deadline, permit exactly one
SSUSB-only five-second grace and recheck the parent:

- bind during grace confirms H4;
- no bind records `0xa30` and moves the next H0 unit to internal probe/deferred
  reason analysis.

This adds at most five seconds and does not turn the full gate loop into
12 independent 20-second waits.

## Deliberately Deferred

The next candidate should not add:

- a free-form `debugfs/devices_deferred` parser;
- another USB module;
- the Samsung Type-C policy chain;
- one checkpoint stage per provider; or
- shell, configfs, NCM, Debian, or ACM behavior.

Those changes do not answer the current boundary as directly and would enlarge
the candidate before the first discriminator is exhausted.

## Proof Limits

This unit does not prove:

- which parent supplier was bound in direct PID1;
- whether `dwc3_msm_probe()` was entered;
- the actual deferred-probe reason;
- how many seconds SSUSB received in P2.50;
- parent bind, DWC3 child creation, UDC creation, or ACM;
- candidate readiness or live authority.

The source archive plus no-delta-override check establishes the matched source
contract, while exact ELF relocations confirm the key calls. It is not a
reproducible byte-identical rebuild of the shipped vendor module.

## Reproduction

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/\
s22plus_fyg8_p251_ssusb_dependency_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 -m unittest -v \
tests.test_s22plus_fyg8_p251_ssusb_dependency_audit
```

Expected checker verdict:

```text
PASS_P251_SSUSB_DEPENDENCY_AUDIT_HOST_ONLY
```

## P2.51b Refinement

The later P2.51b nested-closure audit preserves this verdict but refines the
bounded discriminator. The SS PHY also has a strict `pinctrl-0` dependency on
Waipio TLMM, and the two PHYs consume five exact RPMh LDO wrapper devices.
Those six paths use details `0xa08..0xa0d` as branch-only timeout reads before
the existing `0xa10`, `0xa20..0xa21`, and `0xa30` outcomes.

No module or stage is added. Exact shipped PHY ELF lacks both sysfs imports
used by the matched source's `CONFIG_USB_PHY_TUNING_QCOM` branch, so tuning is
not a bind blocker.
See
`S22PLUS_FYG8_P251B_PHY_NESTED_CLOSURE_H0_2026-07-24.md`
for the source, DT, module, and cleanup-path evidence.
