# S22+ FYG8 Max77705 USB2 MUX Hypothesis and Falsification H0

Date: 2026-08-11 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Draft verdict: `PRIORITY_RESIDUAL_HYPOTHESIS_NOT_CAUSALLY_PROVEN`

Review state: `DRAFT_UNCOMMITTED_INDEPENDENT_SOURCE_REVIEW_PENDING`

S22+ analysis base while drafting:
`3d04ca11ed3374530a3b611d8760075a1888a706`
(`docs(s22plus): select Max77705 role producer`). The later branch parent may
also contain unrelated, already committed A90 work; it does not change this
report's S22+ source authority.

## Scope and authority

This is host-only source, artifact, and existing-evidence analysis. No device
was contacted, no candidate or module plan was changed, and no D0, D1, or F1
authority follows. P3.15 remains consumed and non-replayable. The unrelated
pre-existing A90 worktree changes were not touched.

This draft exists so a second reviewer can remove unsupported hypotheses,
check every retained assertion against the exact source and artifacts, and
preserve why the Max77705 D+/D- MUX theory arose. It is not yet promoted into
`GOAL.md`, the S22+ campaign ledger, or an execution contract, and it must not
be used as a candidate authorization.

## Why this hypothesis arose

The P3 series progressively established the controller-side digital path while
the PC-side observer remained completely silent:

- the HS PHY clock requests and both ref-clock prepare/enable returns were
  successful in P3.12;
- the wrapper reached device role and programmed session-valid state;
- P3.15 retained gadget-start, RUN_STOP-on, QSCRATCH, state, and event-config
  witnesses; and
- the exact host sidecar still observed no candidate USB connection after the
  Download endpoint departed.

The P3.15 61-module plan contains Samsung notifier consumers such as
`usb_notify_layer.ko`, `common_muic.ko`, `vbus_notifier.ko`,
`pdic_notifier_module.ko`, and `usb_typec_manager.ko`, but omits the exact
Max77705 I2C/MFD/PDIC producer closure. That consumer-without-producer shape,
combined with a controller that believes the session is valid and a host that
sees no attach attempt, made an open connector-side D+/D- switch a particularly
direct residual mechanism.

An open MUX is compatible with the observed signature: the internal DWC3/PHY
path may run and become idle while the host sees neither reset nor malformed
enumeration because the USB2 conductors never reach the connector.

That compatibility is not causality. The historical candidate correction,
QSCRATCH source correction, S-Boot uncertainty, and possible IC autonomy below
remain mandatory counterevidence.

## Exact-source facts that support the mechanism

### CONTROL1 is a USB2 data-path switch

The exact FYG8-matched header defines:

```text
NoBCComp [7] / RCPS [6] / D+ [5:3] / D- [2:0]
000: Open / 001,100: USB / 011,101: UART
```

It builds separate `COM_OPEN`, `COM_USB`, `COM_UART`, `COM_USB_CP`, and
`COM_UART_CP` values. This is not merely a Type-C role-notification register;
it selects the USB/UART path on D+ and D-.

Source:

- `workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/linux/usb/typec/maxim/max77705-muic.h:359-405`
- exact header SHA-256:
  `3f7f2b9790940d61ec6bb636f87fd750f7971f1c609c06e6380d11907f701cb1`

### A USB/CDP/OTG detection explicitly commands COM_USB

The normal USB attach path is:

```text
max77705_muic_init_detect()
  -> max77705_muic_detect_dev(MUIC_IRQ_INIT_DETECT)
  -> five-byte status read
  -> max77705_muic_check_new_dev()
  -> ATTACHED_DEV_USB/CDP/OTG
  -> max77705_muic_attach_usb_path() or com_to_usb_ap()
  -> max77705_switch_path(COM_USB)
  -> COMMAND_CONTROL1_WRITE (0x06)
  -> max77705_usbc_opcode_write()
```

Relevant exact-source locations:

- initial detect:
  `drivers/usb/typec/maxim/max77705-muic.c:2301-2309`
- five-byte hardware-status read and classification:
  `drivers/usb/typec/maxim/max77705-muic.c:1666-1740`
- USB/CDP/OTG dispatch:
  `drivers/usb/typec/maxim/max77705-muic.c:1398-1432`
- AP USB path:
  `drivers/usb/typec/maxim/max77705-muic.c:1146-1161`
- CONTROL1 command construction:
  `drivers/usb/typec/maxim/max77705-muic.c:326-348`

All paths above are relative to:
`workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/`.
The exact `max77705-muic.c` SHA-256 is
`bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab`.

This is stronger than the loose statement that the PDIC driver only sends role
notifications. For USB/CDP/OTG it performs an explicit connector-path command.

### `write_vps_regs()` does not establish the pre-driver hardware state

`write_vps_regs()` derives `prev_switch` from the software
`attached_dev`/VPS table and assumes `COM_OPEN` when there is no previous
software cable. It does not read CONTROL1, and its alternate switch write is
compiled out under `#if 0`:

`drivers/usb/typec/maxim/max77705-muic.c:437-464`.

The probe-side assignments
`attached_dev = ATTACHED_DEV_NONE_MUIC` and `switch_val = COM_OPEN` at
`max77705-muic.c:2522-2526` are software initialization only. They are not
proof that the IC or S-Boot left the physical MUX open.

The USB attach path is separate and still issues the direct COM_USB command.
Therefore the correct conclusion is:

- the driver does not passively reveal the inherited CONTROL1 state; and
- once it classifies USB/CDP/OTG, it attempts to program COM_USB explicitly.

### Queue success is not physical-state readback

`max77705_switch_path()` is `void` and ignores the return from
`max77705_usbc_opcode_write()`. The opcode helper queues a write command and a
response entry, starts the queue when appropriate, and normally returns zero.
The low-level I2C write and later AP-command response happen asynchronously.

Consequently these observations have different proof strengths:

```text
COM_USB source branch reached       != command queued
command queued                       != low-level I2C write succeeded
I2C write returned zero              != matching IC response arrived
matching response arrived            != CONTROL1 readback is COM_USB
```

The exact source already has CONTROL1 read/write opcode identifiers (`0x05`
and `0x06`) and generic opcode-read machinery, but the normal MUIC initial
detect does not read CONTROL1 before or after its COM_USB command. A future
pre/post-state claim therefore needs an explicit, reviewed readback mechanism;
it cannot be inferred from the cached VPS state or a successful queue call.

## Required corrections to the originating claim

### Correction 1: PDIC appeared in historical candidates

The statement "`pdic_max77705.ko` was never in any candidate plan" is false
for the repository as a whole. It appeared in earlier M7/M11/M12/M18/M34
plans. Most importantly, M34 S7A2 carried an 86-module closure with:

```text
msm-geni-se.ko -> gpi.ko -> i2c-msm-geni.ko
  -> mfd_max77705.ko -> pdic_max77705.ko
```

and still produced no host-visible USB endpoint during eighteen snapshots.

Authority:
`docs/reports/S22PLUS_NATIVE_INIT_M34_S7A2_GENI_I2C_LIVE_RESULT_2026-07-09.md`.

S7A2 does not cleanly refute the MUX hypothesis. Its retained result proves the
module recipe and host silence, but not that the modules all loaded and bound,
that `994000.i2c/max77705@66` probed, that initial detect classified the PC as
USB/CDP, or that a COM_USB command reached and changed the IC. Its private raw
run directory is no longer present in the current workspace, so those facts
cannot be reconstructed from the consumed run.

The accurate historical statement is:

> The current P3.15 plan omitted the Max77705 producer closure. Earlier
> candidates included it, but no retained run cleanly proved
> bind -> initial detect -> COM_USB command -> response/readback.

This makes the hypothesis historically unclosed, not entirely new.

### Correction 2: P3.12 QSCRATCH does not prove a notifier producer

The P3.12 materialized runtime explicitly writes `peripheral` to the wrapper's
mode node:

`workspace/private/outputs/s22plus_fyg8_p312/intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c:3766-3774`.

The exact downstream wrapper maps DEVICE role to:

```text
mdwc->vbus_active = true
mdwc->id_state = DWC3_ID_FLOAT
```

at `drivers/usb/dwc3/dwc3-msm-core.c:4721-4757`. Its peripheral-start path
then calls `dwc3_override_vbus_status(mdwc, true)` and writes
`UTMI_OTG_VBUS_VALID` bit 20 at `dwc3-msm-core.c:6607-6663`.

Therefore P3.12's bit-20 result has a complete candidate-local producer and
does not demonstrate that Max77705, `usb_typec_manager`, or
`usb_notifier_qcom` delivered VBUS. It proves that the controller was told
VBUS/session-valid through the explicit role path even while the connector
data-path state remained unknown.

The exact downstream `dwc3_override_vbus_status()` does not set
`SW_SESSVLD_SEL` bit 28. P3.12 observed that bit set, but this analysis has not
identified its producer. Bit 28 must remain `ORIGIN_UNRESOLVED`; it is not
promoted to notifier or MUX evidence.

This correction actually sharpens the residual mismatch:

```text
DWC3 controller session-valid: software-forced and observed
Max77705 connector D+/D- route: unmeasured
host attach: absent
```

### Correction 3: a software COM_OPEN default is not a hardware reset fact

The driver initializes its cache to NONE/COM_OPEN. That is a software model,
not a read of CONTROL1. The exact public MAX77705 reset behavior is not present
in the local source or an authoritative public datasheet available to this
audit.

An official Analog Devices guide for the related MAX77958 documents the same
`0x05` CONTROL1 Read / `0x06` CONTROL1 Write architecture and an open reset
state, but it is a different part and cannot establish the MAX77705 reset value
or Samsung firmware behavior:

`https://www.analog.com/media/en/technical-documentation/user-guides/max77958-customization-script-and-opcode-command-guide.pdf`

That document is analogy only and must not be used as exact FYG8 authority.

## Open counter-hypotheses

### S-Boot may program the MUX

Download mode repeatedly enumerates without Linux or `pdic_max77705.ko`.
S-Boot can therefore establish a working USB path in Download mode.

That fact does not distinguish:

1. S-Boot programs COM_USB on every boot and the candidate inherits it;
2. S-Boot programs COM_USB only for Download mode;
3. S-Boot programs it, but Odin auto-reboot, PMIC reset, or kernel handoff
   reopens or otherwise changes the switch; or
4. the IC firmware autonomously changes the path after handoff.

The current private firmware extraction contains boot, vendor_boot, recovery,
DTBO, and vbmeta images, but no analyzable BL/S-Boot/ABL/XBL image. The two
retained `sboot_preamble_response.bin` files are transport responses, not a
bootloader binary suitable for this question. Current H0 evidence therefore
cannot decide the all-boots-versus-Download-only branch.

This uncertainty should be recorded rather than used as a permanent blocker.
A candidate with direct MUX command/readback witnesses remains informative in
either S-Boot case.

### IC firmware may have autonomous behavior

The exact header describes `NoBCComp=0` as comparing with BC1.2 and
`NoBCComp=1` as ignoring BC1.2/manual control. This leaves room for internal
firmware and charger-detection behavior. It does not prove that the IC
autonomously changes CONTROL1 from Open to USB without the AP command.

The exact Linux flow reads hardware status, classifies the cable, and then
issues an explicit COM_USB command. Until CONTROL1 is read before initial
detect, autonomy remains possible but unproven.

## What the next bounded experiment must prove

The useful successor is not "add six modules and see whether USB appears."
It is a 66-module, PC-powered, natural-UFP attach discriminator with explicit
control-plane witnesses. It is distinct from the previously proposed OTG-host
test: the connected PC supplies VBUS, so the provisional 86-module phone-VBUS
source closure is not required for this question.

Relative to P3.15, the provisional producer closure removes
`ucsi_glink.ko` and adds:

```text
gpi.ko
msm-geni-se.ko
i2c-msm-geni.ko
spu_verify.ko
mfd_max77705.ko
pdic_max77705.ko
```

This is dependency arithmetic only. It is not a qualified module plan or live
authority.

The minimum witness chain is:

1. exact modules loaded in the qualified order;
2. `994000.i2c` and the Max77705 MFD/USBC/MUIC/PDIC drivers actually bound;
3. `max77705_muic_init_detect()` ran while the PC supplied VBUS;
4. the five-byte status read succeeded and classified USB/CDP/timeout-open or
   recorded the exact alternative;
5. the AP USB path selected `COM_USB` and queued `CONTROL1_WRITE(0x06)` with
   the expected value;
6. the low-level I2C opcode write succeeded;
7. the matching AP-command response arrived without response mismatch;
8. preferably, an explicit post-write CONTROL1 read returned the exact MUX
   value;
9. the Samsung notifier suffix and DWC3 start path were separately attributed,
   without confusing them with the runtime's explicit `peripheral` write; and
10. the existing host USB sidecar recorded enumeration or exact silence.

For clean causal attribution, add a CONTROL1 read before initial detection and
another after the COM_USB response. No current normal-path read provides that
pair. Introducing it changes observer/execution behavior and requires its own
bounded design, exact opcode-response contract, fixture, and proportional
independent review. It must not be improvised through the `fw_update` sysfs
surface during a live run.

If pre-read implementation is disproportionate, a first successor may retain
bind/detect/write/response plus post-read. That is still informative, but it
cannot claim that the driver changed an inherited Open state.

## Predeclared result meanings

| Observation | Permitted conclusion |
|---|---|
| module or bind failure | producer closure failed; no MUX claim |
| bind succeeds, initial detect absent | scheduling/probe-completion boundary; no MUX claim |
| detect runs but does not classify USB/CDP | exact status-classification result; COM_USB hypothesis not exercised |
| COM_USB branch without low-level write/response | opcode transport/IC result unresolved |
| low-level write and response, no readback | command accepted at the observed software/transport boundary; physical MUX state unproved |
| post-read is not COM_USB | strong support for a Max77705 control-path failure boundary |
| pre=Open, post=USB, host enumerates | strongest causal support for the MUX hypothesis |
| pre=Open, post=USB, host remains silent | MUX transition occurred but was insufficient; move past MUX state |
| pre=USB, post=USB, host enumerates | complete PDIC closure is sufficient, but MUX transition alone is not isolated from other PDIC side effects |
| pre=USB, post=USB, host remains silent | COM_USB state alone is strongly refuted as the missing cause |
| response/readback malformed or observer loss | `NO_PROOF_OBSERVER`; no electrical or connector claim |

No negative result proves an analog defect. A verified COM_USB state with host
silence would eliminate this specific switch-state hypothesis and return the
frontier to the remaining connector/line/electrical boundary.

## Claims the independent reviewer should delete if found elsewhere

The following claims are not supported and should not be copied into a
successor contract:

1. "No candidate ever included `pdic_max77705.ko`."
2. "P3.12 QSCRATCH proves a live Type-C/PDIC notifier producer."
3. "The driver's cached COM_OPEN initialization proves the inherited hardware
   MUX state."
4. "Download enumeration proves COM_USB survives every normal boot handoff."
5. "NoBCComp=0 proves autonomous COM_USB switching."
6. "A successful opcode queue call proves the physical MUX changed."
7. "The old S7A2 host silence cleanly refutes Max77705 because the module name
   was present in its recipe."

## Claims that survive this H0 pass

1. The exact Max77705 CONTROL1 model contains the connector-side USB2 D+/D-
   switch.
2. USB/CDP/OTG classification explicitly attempts a COM_USB write.
3. P3.15 omitted the exact GENI-I2C/MFD/PDIC producer closure.
4. P3.12/P3.15 proved substantial controller-side digital progress without
   proving the connector MUX state.
5. An open or non-USB MUX is compatible with the complete host silence.
6. S-Boot inheritance and IC autonomy remain unresolved counter-hypotheses.
7. A 66-module PC-VBUS natural-UFP discriminator can avoid the provisional
   86-module phone-VBUS closure, provided it measures execution rather than
   assuming it from module presence.

## Independent review checklist

The second reviewer should independently verify:

- the exact source hashes and line ranges above;
- whether CONTROL1 response handling provides a stronger existing positive
  acknowledgment than identified here;
- whether any normal boot path already issues CONTROL1 Read before initial
  detect;
- whether any retained historical S7A2/S8/S9 artifact proves actual PDIC bind
  or COM_USB execution and changes the historical conclusion;
- whether another exact driver or boot-stage source programs the same MUX;
- whether the six-module delta and order remain exact against the selected
  P3.15 plan;
- whether PC-powered natural UFP attach bypasses the previously documented
  host-only `usb_sl` and phone-VBUS gates without adding a hidden Android
  userspace prerequisite; and
- whether a useful readback can be obtained without an unsafe or overly broad
  new execution mechanism.

The review should return claim-level `KEEP`, `REWRITE`, or `DELETE` findings.
Only after that review should this draft be corrected, promoted into
`GOAL.md`/the S22+ ledger, and committed.
