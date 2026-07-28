# S22+ FYG8 P2.80 Child Runtime-Reinit Repair Audit H0

Date: 2026-07-28 KST

## Verdict

`PASS_P280_CHILD_RUNTIME_REINIT_REPAIR_AUDIT_HOST_ONLY`

The exact FYG8 source supports a bounded child-DWC3 runtime
suspend/resume cycle as a plausible repair for the femto-HS PHY power-state
asymmetry. Three qualifications are load-bearing:

1. retained detail `0xb22` does not preserve whether child runtime resume
   occurred inside `dwc3_gadget_pullup()`, so it does not prove that the child
   had never suspended or resumed;
2. the parent peripheral-start path deliberately holds a child runtime-PM
   reference, so a late `power/control=on` write cannot create the required
   suspend edge; and
3. the source-backed transition is parent
   `peripheral -> none -> peripheral`, with an exact child
   `runtime_status=suspended` fence between the two writes.

The next versioned design may combine an early diagnostic window with that
controlled pre-bind reinitialization. It must not describe a successful
reinitialization as direct analog-rail proof.

This unit performed no device contact, build, image change, approval, transfer,
reboot, or flash.

| Claim | Result |
|---|---|
| DEVICE child runtime resume calls full `dwc3_core_init_for_resume()` even for auto resume | **VERIFIED** |
| full child resume calls `usb_phy_init()` and therefore `msm_hsphy_init()` | **VERIFIED** |
| `msm_hsphy_init()` requests power, clocks, reset, and PHY programming | **VERIFIED** |
| retained `0xb22` proves child runtime resume was absent during bind | **REJECTED** |
| retained `0xb22` proves the child never suspended earlier | **REJECTED** |
| the P2.80 parser accepts a run-stop nested inside child runtime resume | **VERIFIED** |
| parent peripheral-start holds a child runtime-PM reference until stop | **VERIFIED** |
| `power/control=on` can force the required child suspend | **REJECTED** |
| parent `none` can release the held child reference and reach child suspend | **SOURCE-VERIFIED, LIVE-UNPROVED** |
| child suspend in DEVICE role followed by resume reinitializes the PHY | **SOURCE-VERIFIED, LIVE-UNPROVED** |
| `power/runtime_usage` is available for a simple userspace read | **REJECTED FOR THIS CONFIG** |

## Exact Inputs

The source and artifacts are the same identities used by the preceding P2.80
femto audit:

```text
source:
  /tmp/p280-postlive-phy-20260728/kernel_platform/msm-kernel

candidate config:
  workspace/private/outputs/s22plus_fyg8_p280_v5/bundle-a/.config

runtime:
  workspace/public/src/native-init/s22plus_fyg8_p280_e3_runtime.inc.c

trace contract:
  workspace/public/src/scripts/revalidation/
    s22plus_fyg8_p280_trace_contract.py
```

The exact femto module remains:

```text
/tmp/p280-postlive-modules-20260728/lib/modules/phy-msm-snps-hs.ko
sha256=22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94
```

## Child DEVICE Resume Is a Full Reinitialization

In `drivers/usb/dwc3/core.c`, `dwc3_resume_common()` dispatches the DEVICE
case without a `PMSG_IS_AUTO()` exclusion:

```text
dwc3_resume_common()
  current_dr_role == DEVICE
    -> dwc3_core_init_for_resume()
       -> reset deassert
       -> clocks enable
       -> dwc3_core_init()
          -> usb_phy_init(dwc->usb2_phy)
          -> usb_phy_init(dwc->usb3_phy)
    -> dwc3_set_prtcap(DEVICE)
    -> dwc3_gadget_resume()
```

The OTG case does skip this work for auto resume, but the DEVICE case does
not. The distinction matters because the first parent peripheral start calls
the child runtime-PM get before the child role switch to DEVICE. A later
resume after the role is DEVICE follows the full path above.

For the active femto USB2 PHY, `usb_phy_init()` reaches
`msm_hsphy_init()`. The normal branch:

1. calls `msm_hsphy_enable_power(..., true)`;
2. enables clocks;
3. resets the PHY;
4. asserts and releases the relevant POR/power-down controls; and
5. applies the exact PHY programming sequence.

This is a source-backed software reinitialization and power-vote request. It
is not a direct measurement that every physical rail reached its requested
voltage.

## Why `0xb22` Does Not Prove Resume Absence

`dwc3_gadget_pullup()` stores `softconnect` before calling
`pm_runtime_get_sync(dwc->dev)`:

```text
ret == 0:
  runtime resume completed; pullup returns early because resume handles
  run-stop

ret > 0:
  child was already active; pullup continues to its direct soft-reset,
  gadget-start, and run-stop path
```

P2.80's trace parser intentionally supports both shapes. Its bind parser:

- accepts an optional `dwc3_runtime_resume()` pair nested inside pull-up;
- requires a `dwc3_gadget_run_stop()` pair to be nested inside that resume
  when the resume pair exists; and
- emits the same `P280_BIND_RUN_STOP_ZERO` classification when run-stop
  returns zero in either shape.

The retained timeout then maps both shapes to detail `0xb22`. It does not
retain `has_resume` or `resume_rc`. The raw in-device trace snapshot did not
survive the closed run.

Therefore `0xb22` proves a clean pull-up/run-stop pair and the hardware-backed
`DEVCTRLHLT` clear, but it does not prove:

- that `pm_runtime_get_sync()` returned one;
- that child runtime resume was absent during bind; or
- that the child had never suspended earlier.

This is not a P2.80 parser nesting bug. The parser already handles the resume
subtree correctly; the retained classification deliberately collapsed two
branches. A successor must preserve the branch explicitly.

## Why the Child Was Expected to Stay Active After Peripheral Start

`dwc3_otg_start_peripheral(..., true)` in `dwc3-msm-core.c` does:

```text
pm_runtime_get_sync(parent)
pm_runtime_get_sync(child)
flush child role-switch work
VBUS override
redriver/PHY connect notifications
usb_role_switch_set_role(child, DEVICE)
...
pm_runtime_put_sync(parent)
```

There is no matching child put in the `on` branch. The matching operation is
in `dwc3_otg_start_peripheral(..., false)`:

```text
pm_runtime_put_sync(child)
if child is not suspended:
  bounded connected wait
  pm_runtime_suspend(child)
pm_runtime_put_sync(parent)
```

The positive child reference is therefore an intentional peripheral-session
hold, not an unexplained leak. While that hold remains, changing
`power/control` cannot make normal runtime idle suspend the child.

The candidate config has:

```text
# CONFIG_PM_ADVANCED_DEBUG is not set
```

Consequently the ordinary child power directory exposes `runtime_status` but
not the advanced-debug `runtime_usage` attribute. Adding a config-dependent
struct-offset reader merely to recover usage count would enlarge the
measurement surface without changing the decision. Exact get/put tracing plus
the `runtime_status` fence is sufficient.

## Source-Backed Controlled Reinitialization

The smallest standard-driver sequence is:

1. Complete the existing initial `none -> peripheral` role phase.
2. Before the first configfs UDC bind, write parent mode `none`.
3. Observe `dwc3_otg_start_peripheral(on=0)` complete.
4. Require the exact child device's `power/runtime_status` to settle at
   `suspended` within a bounded deadline.
5. Write parent mode `peripheral`.
6. Observe `dwc3_otg_start_peripheral(on=1)` complete.
7. Require the child runtime resume and the exact child status `active`.
8. Require parent mode readback `peripheral` and exact real-UDC membership.
9. Perform the existing single configfs UDC bind and configured-state wait.

The parent `none` path clears VBUS/session state and reaches
`dwc3_otg_start_peripheral(..., false)`. That stop path releases the held child
reference. The child already has `current_dr_role == DEVICE`, because the stop
path does not switch the child role back to NONE. Its runtime suspend therefore
uses the DEVICE branch:

```text
dwc3_gadget_suspend()
dwc3_core_exit()
  -> usb_phy_set_suspend(usb2, 1)
  -> PHY power-off/exit and child clock/reset teardown
```

The following parent `peripheral` start calls
`pm_runtime_get_sync(child)` while that role is still DEVICE. A successful
resume then executes the full reinitialization described above before parent
connect notifications and the later UDC bind.

Never use parent role `host` for this experiment. It is unnecessary and would
change the electrical authority class.

## Required Successor Observations

Reuse the P2.80 tracefs lifecycle and ownership rules. Do not introduce a
second tracing framework.

### Window I: natural initialization and first low-power transition

Arm after module 57 and before loading `dwc3-msm.ko`. Preserve ordered,
repeat-tolerant events for:

- `msm_hsphy_init()`;
- `msm_hsphy_set_suspend(..., 1)`;
- `msm_hsphy_enable_power(..., false|true)`; and
- `msm_hsphy_notify_connect()`.

This window determines whether the hypothesized natural off-without-repair
sequence occurred before the intervention.

### Window C: controlled child cycle

Preserve ordered events for:

- parent peripheral stop entry/return;
- child `dwc3_runtime_suspend()` entry/return;
- femto suspend and power-off attempt;
- exact child `runtime_status=suspended`;
- parent peripheral start entry/return;
- child `dwc3_runtime_resume()` entry/return;
- `msm_hsphy_init()` and power-on request;
- exact child `runtime_status=active`; and
- final parent role `peripheral`.

Do not require global singleton counts. Initialization can repeat legitimately.
Match ordered subsequences inside each bounded phase.

### Window B: UDC bind

Keep P2.80's existing pull-up, optional child-resume, and run-stop pairing. The
existing parser already accepts run-stop nested under child runtime resume.
The successor retained record must additionally distinguish:

- bind with no child resume;
- bind with child resume and its return code; and
- malformed or missing diagnostic data.

Even though the controlled cycle should leave the child active before bind,
the optional resume branch remains valid and must not be classified as a
source contradiction.

## Outcome Interpretation

| Early window | Controlled cycle | Host/UDC result | Meaning |
|---|---|---|---|
| off-without-power-on observed | full reinit observed | configured + exact banner | strong causal support and a working bounded repair |
| no natural off path | full reinit observed | configured + exact banner | reinitialization is sufficient, but the original LDO-drop hypothesis is not supported |
| off-without-power-on observed | full reinit observed | still not attached | the asymmetry is not sufficient, or the software power request did not restore the physical path |
| any | child never reaches suspended | no bind attempt | controlled repair was not established; do not attribute failure to USB enumeration |
| any | resume/init trace incomplete or cleanup unowned | any | instrumentation indeterminate |

Exact ACM receipt remains primary success evidence. Trace diagnostics must not
discard an exact run-bound banner. Unclean trace ownership remains fail-closed
because active probe state would make subsequent observations untrustworthy.

## Scope Decision

The mechanism is now sufficiently source-defined for versioned design. No
broader H0 search or web search is needed before that design.

The next design must:

- bind exact parent, child, femto module, vmlinux, source, and config
  identities;
- derive module-qualified body symbols and field offsets from exact artifacts;
- preserve P2.80 historical artifacts byte-for-byte;
- make `runtime_status=suspended` a hard fence rather than a blind delay;
- keep `host` role forbidden;
- retain child-resume presence instead of collapsing it into `0xb22`;
- keep diagnosis and intervention interpretations separate; and
- update the bounded userspace-write safety declaration for the additional
  parent `none` and `peripheral` transitions.

This report authorizes no implementation, build, image generation, device
action, or live run.
