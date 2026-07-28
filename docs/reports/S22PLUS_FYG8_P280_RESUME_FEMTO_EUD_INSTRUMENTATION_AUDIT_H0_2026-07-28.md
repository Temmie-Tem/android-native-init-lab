# S22+ FYG8 P2.80 Resume/Femto/EUD Instrumentation Audit H0

Date: 2026-07-28 KST

## Verdict

`PASS_P280_RESUME_FEMTO_EUD_INSTRUMENTATION_AUDIT_HOST_ONLY`

This unit audits the proposed next discriminator against the owned FYG8 kernel
source, exact stock modules, and the closed P2.80 trace contract. It performed
no device contact, build, image change, approval, transfer, reboot, or flash.

| Proposed claim | Result |
|---|---|
| nonnegative parent `pm_runtime_get_sync()` proves `dwc3_msm_resume()` ran | **REJECTED** |
| DWC3 core reset/run-stop proves at least the core clocks were usable | **VERIFIED** |
| `dwc3_msm_resume()` completion plus one `hs_phy->flags` sample collapses all remaining electrical branches | **REJECTED** |
| P2.80 trace lifecycle can be reused without a new generic framework | **VERIFIED WITH VERSIONED CONTRACT EXTENSION** |
| the FYG8 femto-HS PHY source is unavailable | **REJECTED** |
| EUD flags can be sampled in the same bounded observation | **VERIFIED WITH LIMITED MEANING** |

## Source Availability

The apparent source blocker came from treating `/tmp/p277-kernel-src`, an
incomplete temporary extraction, as the source inventory. The owned FYG8 OSRC
archive contains all three relevant members:

```text
kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c
kernel_platform/msm-kernel/drivers/usb/phy/phy-msm-snps-hs.c
kernel_platform/msm-kernel/drivers/soc/qcom/eud.c
```

The femto driver is under `drivers/usb/phy`, not `techpack`. Absence of a
populated `techpack` directory is therefore not a blocker.

The exact stock `phy-msm-snps-hs.ko` is unstripped and retains local function
symbols for:

```text
msm_hsphy_set_suspend
msm_hsphy_notify_connect
msm_hsphy_notify_disconnect
```

Its module runtime name is `phy_msm_snps_hs`. The exact stock
`dwc3-msm.ko` likewise retains local symbols for `dwc3_msm_resume`,
`dwc3_msm_suspend`, both runtime-PM callbacks, and
`dwc3_otg_start_peripheral`. A successor contract can bind exact source and
module identities without relying only on guessed disassembly.

## Runtime-PM Boundary

The exact PM core returns `1` from `rpm_resume()` when a device is already
`RPM_ACTIVE`. P2.80 records only the sign class of the two
`pm_runtime_get_sync()` results. Its retained nonnegative parent result
therefore proves that the parent PM request was not rejected; it does not prove
that `dwc3_msm_runtime_resume()` or `dwc3_msm_resume()` executed during that
window.

The exact DWC3 core gives an independent, narrower hardware fact:

- core soft reset writes `DCTL.CSFTRST` and waits for hardware to clear it;
- the source states that DWC3 3.1 clears the bit after clocks synchronize; and
- run-stop writes `DCTL.RUN_STOP` and observes `DSTS.DEVCTRLHLT` clear.

This proves that the DWC3 core had enough live clocking to process those
register operations. It does not identify which earlier parent-PM path enabled
the clocks, and it does not prove that the parent resume helper reached its HS
PHY resume or final `in_lpm=0` point.

In `dwc3_msm_resume()` the useful ordered boundaries are:

1. entry and the `in_lpm` early-return decision;
2. `usb_phy_set_suspend(mdwc->hs_phy, 0)`;
3. power-collapse recovery; and
4. `atomic_set(&mdwc->in_lpm, 0)`.

There is another `in_lpm=0` store in the connection-done event path, so the
field is not a globally unique resume witness. In a run that remains
`not attached`, connection-done is not evidenced, but a successor must still
bind its observation to the ordered resume call rather than treating a naked
field value as universal proof.

## Why One Flags Sample Does Not Collapse the Boundary

The source and exact module distinguish three independent effects:

### HS PHY resume

`msm_hsphy_set_suspend(..., 0)` calls `msm_hsphy_enable_clocks(..., true)` and
sets `suspended=false`. The clock helper ignores every
`clk_prepare_enable()` return value and marks `clocks_enabled=true` anyway.
Entry/return or the Boolean fields therefore prove control-path execution, not
successful electrical clocking.

### Connect notification

`msm_hsphy_notify_connect()` sets `cable_connected=true` and returns zero. It
does not update `usb_phy.flags`. The exact module disassembly corroborates a
single byte store to the cable-connected field.

### VBUS override

`dwc3_override_vbus_status()` writes the HS `UTMI_OTG_VBUS_VALID` and SS
`LANE0_PWR_PRESENT` controller fields. It does not update `usb_phy.flags`.

Consequently, a `hs_phy->flags` value cannot distinguish successful
connect-notify, VBUS override, and femto PHY electrical readiness. Those
branches cannot be collapsed into one flags sample without losing the exact
discrimination sought by the next F1.

## EUD Scope

The flags field does carry the EUD-specific bits
`EUD_SPOOF_DISCONNECT`, `EUD_SPOOF_CONNECT`, and `PHY_SUS_OVERRIDE`.
`dwc3_ext_event_notify()` can clear and rewrite the spoof bits, and the femto
suspend path consumes `EUD_SPOOF_DISCONNECT`.

An exact-point flags sample can therefore answer whether an EUD spoof flag was
active at that point. It cannot prove that no transient EUD event occurred
earlier. Existing stock evidence also records EUD disabled and a rejected
secure enable attempt, so EUD remains a bounded secondary discriminator, not
the headline root-cause branch.

Fetching `hs_phy->flags` is not free in the contract sense. P2.80 currently
captures register arguments, signed returns, and two source-derived post-call
offsets. A nested memory fetch would add a structure-offset and fetch-expression
contract that must be pinned against source and exact module code and covered
by a focused mutation/control test.

## Reuse Boundary

The P2.80 tracefs lifecycle, cleanup rules, fail-soft diagnostic precedence,
64-KiB per-CPU buffer, and generic kprobe control can be reused. P2.80 itself
is closed and immutable.

A successor still needs a versioned descriptor/parser/source contract because:

- it adds module-local targets from `phy_msm_snps_hs`;
- event count and ordering change;
- exact module identity and runtime module name become inputs;
- any nested field fetch adds source-derived offsets; and
- retained classification must separate missing instrumentation from a
  function that was armed but not called.

This does not require a second generic trace framework or a new broad detail
band. It is also not merely "add two target strings."

## Minimal Next Design Input

Before another Full-LTO or F1, define the smallest ordered observation that can
separate:

1. parent resume not called, early-returned, or completed;
2. femto `set_suspend(..., 0)` not called versus called;
3. femto connect-notify not called versus called;
4. VBUS override path not reached versus reached; and
5. EUD spoof flags absent versus present at the selected point.

Retain the final exact `current_speed` class that P2.80 read and discarded.
Do not claim femto electrical readiness solely from a zero-returning suspend
callback because its clock-enable errors are swallowed. Prefer function
entry/return and exact post-call observations over unrestricted MMIO reads;
add a bounded register read only if source-level path evidence still leaves an
unresolved physical branch.

This audit authorizes no candidate work or device action. The next bounded unit
is a versioned H0 design using these proof limits, followed by static
validation. Any eventual F1 still requires a fresh manifest, preflight,
approval, exact rollback, and attended Process v2 transaction.
