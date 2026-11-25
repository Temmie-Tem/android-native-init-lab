# S22+ mainline USB router and hands-off cycle: design discussion

Date: 2026-11-26. Target: SM-S906N / g0q / FYG8, Linux 7.2.11 RAM image.
This is a plan. It grants no device authority, review or activation.

The [Stage 2 run](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_RUN_2026-11-26.md)
showed that one `CONTROL1_W(COM_USB)` removed the replug in one boot. Two
questions follow:
1. Where should the routing write live, so that every mainline boot
   enumerates and stays correct across unplug and replug?
2. With USB no longer needing a replug, can the experiment cycle run with
   no physical intervention, and what must be proved before the contract's
   Conditional Autonomous F1 lane could be activated?

Claude, Codex (gpt-6.2-sol, read-only on the repository) and Gemini Carbon
answered the same brief independently. Claude merged the answers below.

## Facts the discussion relied on

- Upstream 7.2.11 has `drivers/mfd/max77705.c` (top, charger, gauge, LEDs,
  haptic). It has no driver for the CCIC at `0x25`.
- The out-of-tree Tab S8+ typec driver writes `COM_USB` on every data-role
  set. It also needs the CCIC interrupt and programs PD, VBUS and interrupt
  masks.
- In the current RAM image, TLMM and `gpi_dma0` are disabled. Only SE5 I2C
  is enabled, so the CCIC can only be polled.
- The FYG8 vendor MUIC driver writes `COM_USB` on USB or CDP attach. It
  writes `COM_OPEN` on detach when the CCIC reports a detach.
- [ML050](../reports/S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)
  already ran a cable-untouched automatic return. The candidate never
  enumerated. A new Download device appeared 590 s after N launch, and the
  owner transferred A and passed health. That run did not identify which
  caller requested the reset.
- Final Android health needed a health-only continuation after an ADB
  interruption in both Stage 1 and ML050.

## Q1: where the routing write belongs

**Agreed.** The write needs these properties:
- poll status; do not enable TLMM or IRQs for this;
- the mailbox admits only `CONTROL1_R` and `CONTROL1_W(0x09)`;
- write at most once per positively identified attach;
- gate the write on VBUS, CC sink, SDP or CDP, and a fresh echoed open read;
- skip it when the gadget is already configured or the switch reads `0x09`;
- verify completion and read back;
- write nothing on detach (no `COM_OPEN`);
- no unconditional write at probe;
- no PD, VBUS, charger, OTG or role-switch work.

The Tab S8+ port is deferred by all three. dwc3 stays fixed peripheral.

**Disagreement: where the code lives.**

| Option | For | Against |
|---|---|---|
| PID1-spawned userspace helper, started after the timer child is armed (Gemini) | It stays inside the 555 s timer's recovery envelope: a helper crash or I2C wedge still ends in Download. It reuses the reviewed observer code. | Its mailbox access is not owned by the kernel, so another process could also open the I2C bus. It depends on Debian startup in the resident product. |
| Small polling kernel driver at `0x25`, with mailbox work deferred out of probe (Codex) | It serializes the mailbox, tracks attach state independently of Debian, and is the right resident owner. | A probe or I2C bug runs before PID1 arms the timer, where no automatic recovery exists. It is a kernel change and stays attended. |

**Merged recommendation.** Stage the change:
1. **Router v1 is a userspace helper.** PID1 starts it only after the timer
   child is armed and the gadget is bound. It is a pure state machine with
   exclusive use of the I2C bus. This is the version the hands-off cycle
   uses, because its failures fall inside the class the timer already
   recovers.
2. **Router v2 is the same state machine moved into a polling kernel
   driver.** It is reviewed and run attended as a kernel/DT change. It only
   replaces v1 after it matches v1's evidence. The resident Debian product
   uses v2.

**Attach tracking.** Track attach and detach from `BC_STATUS` and
`CC_STATUS0`, not from the UDC state. After an unplug, a fixed-peripheral
dwc3 may report `suspended` rather than `not attached`. Keep Stage 2's 3 s
dwell in v1. Whether the dwell or ordering after bind is needed is still
open, and a later variant can test it.

**Evidence before relying on the router** (attended, each run within its
own approval):
- three cable-untouched boots, covering an SDP and a CDP host port;
- one matched write-disabled control on CDP;
- unplug and replug during a boot: slow and quick, both orientations. Log
  `CONTROL1` after replug. This settles Stage 1's unknown value at
  enumeration;
- a boot with the cable unplugged, then attach;
- a host-to-DCP transition. Require zero writes on detach, DCP, unknown
  state or an already working route;
- stale status, bad echo and timeout exercised in H0 fakes.

## Q2: hands-off cycle

The cycle is:

`rooted Android health → Download (adb) → one boot-only N → mainline RAM boot → timer child armed → router → USB/NCM evidence → authenticated Download (or the 555 s timer) → host waits for a fresh Download by N+660 s → one original A → rooted Android health`

Every piece except the router has already been reviewed and run on the
device. The new work is combining the timer child, router v1, the evidence
exchange and the authenticated Download into one image and one host runner.

| Failure mode | Recovered without touch today? | Gap fix | Risk |
|---|---|---|---|
| Route write refused or failed, no USB | Yes, through the 555 s timer. ML050 landed in Download with the cable untouched. | Router runs after the timer is armed | The ML050 reset caller is unproven |
| NCM, evidence or userspace stall after arm | Yes, if the child, scheduler and restart path survive | Isolate the worker; the child is never cancelled by a parent or ACK | A shared I2C, driver or shutdown lockup can defeat the restart |
| Kernel, uniLoader or ABL hang before the child arms | **No.** The boot partition holds N, so a reset that is not into Download boots N again. | None admitted. Keep these changes attended. | A watchdog may land in Upload/RDX or loop into N. Its landing is unproven. |
| `RESTART2("download")` stalls or mislands | No | Attended fallback | Invoking it does not prove Download arrival |
| Download absent, late or ambiguous | Safe stop only | Exact target, new USB generation, N+660 s cap | A false match could flash the wrong device |
| A transfer fails | Safe stop only | Park; never replay an uncertain A | Physical recovery |
| Final health ADB interruption | Health-only continuation exists | Make the runner invoke the admitted health-only continuation automatically, once | Unexplained failure still stops the session |
| Host owner or host crashes | No | Separately reviewed supervision in the same host epoch | Duplicate ownership or a stranded N |

**Watchdog.** All three flag the Gunyah watchdog as the main open recovery
question. It is not admitted by the contract. Static ABI agreement is not
evidence of where a bite lands: Download, Upload/RDX, or a normal boot back
into N. Any proposal to use it needs its own attended landing proof first.
Until then, failures before the child arms are not automatically recovered.

**Evidence ladder toward activation.**
1. **H0.** Build one combined image and one host runner. Run focused
   normal and failure-path tests against the real runner, including
   ambiguity, crash boundaries, transfer uncertainty and health failure.
   Get independent review of the exact bytes.
2. **Attended, with no touch.** The operator is present, approves each run
   and does not touch the phone. The proposed runs are:
   - three normal cycles, covering SDP and CDP;
   - two with the route write withheld;
   - two with NCM or control unavailable;
   - two with the post-arm worker deliberately stalled.

   Each must complete one N, one A and healthy Android with zero physical
   actions, with a receipt that names the cause where possible.
3. **Review and decision.** Independent review covers the exact runner and
   the failure evidence. The operator then decides whether to activate, and
   issues a finite grant with time and candidate-count limits.

**Initial autonomous scope, if activated.** Only isolated userspace
workload changes that run after the timer child is armed. uniLoader, the
kernel Image and config, the DT, early PID1, the router, the timer child,
authentication, the host transport and original A stay pinned. These stay
attended:
- kernel, DT, router and early-init changes;
- watchdog trials and storage;
- any path that needs keys or a cable;
- recovery after an A or health failure.

## Proposed next steps

1. **H0.** Router v1 helper, derived from the reviewed route observer and
   its fake and decoder, with attach epochs and the agreed gate. Then the
   combined timer, router, evidence and authenticated-Download image, and
   the single host runner with automatic health-only continuation. Codex
   reviews the exact bytes.
2. **Attended.** The router evidence runs and the no-touch cycle runs
   above. They can share boots where the evidence binding allows.
3. **Operator.** The activation decision, after the dossier and review.
