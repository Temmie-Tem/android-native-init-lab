# S22+ one attended MAX77705 USB route intervention (Stage 2)

Status: **REVIEW_GATED_CAPABILITY**

This scope asks one question for one boot of SM-S906N / g0q / FYG8: does a
single `CONTROL1_W(COM_USB)` (`0x09`) let the host enumerate the mainline
gadget without the phone-end replug?

The [Stage 1 observation](../reports/S22PLUS_MAINLINE_MAX77705_USB_RUN_2026-11-25.md)
read the switch at explicit `COM_OPEN` (`0x3f`) with VBUS, a CDP port and a CC
sink already present. The host port stayed "not attached" until the replug.
The [design discussion](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_H0_2026-11-25.md)
chose one gated write over a second read-only run.

The existing mainline RAM owner runs one Android-origin operation. Every
condition of that owner applies unchanged:
- physical attendance;
- effect-time identity and health;
- the fixed observation window;
- the attach cue and its resolution interlock on this image's ordinary
  evidence route. Here the cue is the fallback that returns the record if the
  write does not help, so the cue dialog is started with `--issue-delay 45`;
- manual Download;
- original-A return;
- no replay.

**Board artifact.** The selected artifact is the
[qualified route board package](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_H0_2026-11-25.md#board-package).
Its kernel Image and DT are the Stage 1 ones: `I2C_QCOM_GENI=y`, and SE5 with
its QUP wrapper enabled and its pinctrl removed. MPSS, UFS, SD, every remote
processor, TLMM and `gpi_dma0` stay disabled. Only the RAM observer differs.
It is built from [`max77705-usb-route.h`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705-usb-route.h).
The exact qualification pins one AP, a key commitment, a self-contained
decoder and the loader-produced FDT.

**Bus effects.** On `0x25`, the observer sends three kinds of write, and
nothing else:

| Write | Purpose | Limit |
|---|---|---|
| `0x05 → 0x21` | `CONTROL1_R` mailbox command | at most 32 commands in total |
| `0x00 → 0x41` | mailbox start strobe | one per command |
| `[0x21, 0x06, 0x09]` | `CONTROL1_W(COM_USB)` as Samsung's bulk opcode write | at most once per boot, never retried |

Each read also sends its register address in write direction, to the PMIC,
the USBC and the FSA4480 alike. No register value is written to the PMIC or
the FSA4480. Reads clear the volatile `UIC_INT` and `CC_INT` latches.

**The write gate.** The write is attempted at most once, after the gadget is
bound. All of the following must hold:
1. the identity gate passed;
2. the UDC has read "not attached" for a continuous 3 s dwell, with no IC
   change, no recorded interrupt flag other than the mailbox response (the
   boot chain's CC latch excepted) and no failed read since boot;
3. a fresh `CONTROL1_R` returns `0x3f` with the opcode echo;
4. right after that read, the UDC, then the interrupts and status, then the
   UDC again, are re-sampled. They show no change, the UDC is "not attached"
   on both sides, VBUSDet is set, ChgTyp is SDP or CDP, and CCStat is sink;
5. at most 50 ms elapse between the start of that re-sample and the write.
   The same clock value is recorded as the write time.

If any condition fails, nothing is written and the reason is recorded. A
pre-read of `0x09` or `0x00` is recorded and also means no write.

**Kernel effects for the exact candidate.** The Image and the loader-handed DT
are identical to the adopted [Stage 1 candidate](S22PLUS_MAINLINE_MAX77705_USB_V1.md#kernel-effects-for-the-exact-candidate).
Its built-in SCM probe effects, SE5 serial-engine effects and disabled
subsystems therefore apply here unchanged. Only the ramdisk differs, and with
it the boot package SHA-256, the loader and the `linux,initrd-end` value in
`/chosen`.

**Effects of the write.** `COM_USB` is what Samsung's FYG8 MUIC driver
writes on every USB or CDP attach. NoBCComp stays 0, so BC1.2 comparison is
kept. The write changes the D+/D− routing of the connector for this boot
only. The next boot chain runs its own MUIC initialization, and Android's
driver re-detects at probe. No charger, PD, firmware, reset or FSA4480
command is sent.

**Observation and outcomes.** A single NCM challenge returns the record. The
record spans boot to request, with UDC-state events and a read at the request.
The existing transfer window, endpoint continuity, authenticated request,
sealed response and exact loader FDT apply.

| Record verdict and host side | Outcome |
|---|---|
| `ROUTE_CONFIGURED_WITHOUT_REPLUG` and no cue issued before the response | Observed: in this boot, the routing write removed the replug dependency. |
| `ROUTE_CONFIGURED_WITHOUT_REPLUG` but a cue was issued first | Observed as `ROUTE_CONFIGURED_AFTER_CUE`; not a cable-untouched pass. |
| `ROUTE_CONFIGURED_AFTER_REPLUG` | Observed: `0x09` held, but the host enumerated only after a cable change. Routing was not sufficient. |
| `ROUTE_PARTIAL_ENUMERATION`, `ROUTE_WRITE_NOT_HELD` | Observed, with the reading the [design report](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_H0_2026-11-25.md#outcomes) gives. |
| `ENUMERATED_BEFORE_WRITE`, `SKIP_INITIAL_COM_USB`, `SKIP_PREWRITE_NOT_OPEN` | Observed state; the intervention was not needed or not reached. |
| `ROUTE_WRITE_FAILED`, `ROUTE_COVERAGE_GAP`, `ROUTE_AMBIGUOUS_ORDER`, `ROUTE_NO_READBACK`, `ROUTE_NO_ENUMERATION`, `EVENTS_DROPPED`, any other `SKIP_*` (including `SKIP_STALE`) | Inconclusive for the intervention; the record is retained. |
| `NO_PROOF_*` | The authenticated boot evidence and the reason are retained. |
| Missing or rejected evidence, or a missing or unresolved cue closure | The intervention stays unproved. |
| Observation error | The existing physical recovery path is followed. |

Final Android return and health must be established independently before
terminal closure. Physical recovery requires the same original owner and the
original A.

**Scope of the result.** A verdict describes this one boot. A pass shows that
the write was sufficient in this boot; it does not show the mechanism or that
every boot needs it.

**Target adoption.** The [target contract](targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
adopts this scope as a **REVIEW_GATED_CAPABILITY**. Each run requires:
- the selected route review at `PASS_GO` for the exact owner closure, checked
  before candidate code is imported;
- the exact board qualification named by the binding module;
- current target identity and a usable original-A recovery path;
- the existing fixed foreground preapproval D0 on a fresh task;
- one new finite attended mainline RAM grant under the
  [mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md);
- the operator's attendance for the fallback cue and its explicit resolution.

It grants no other `CONTROL1_W` value, no second write, no PMIC, charger,
PD or FSA4480 write, and no Linux storage, installed-root, reset,
automatic-recovery, retry or replay capability. Preparing a task is H0.

## Successor reviews and adoption

This scope, its hooks in the shared mainline modules and its target
adoption are published together. The branch selects five pending records
under `workspace/public/src/device-action/bindings/`:
- `s22plus_approved_terminal_persistent_v60_review.json`
- `s22plus_loader_android_timing_v3_cue_v4_review.json`
- `s22plus_mainline_scm_ordinary_cue_v5_review.json`
- `s22plus_mainline_max77705_usb_v3_review.json`
- `s22plus_mainline_max77705_route_v1_review.json`

After independent review of the exact bytes, publish the scope, all five
`PASS_GO` records, the task selectors and the gateway selector pin for the
approved v60 receipt in one squash on the operating HEAD. Keep the published
receipts and task evidence. Under the existing admission lock and target
session lease, use the [shared cutover procedure](../reports/S22PLUS_MAINLINE_ORDINARY_CUE_H0_2026-11-22.md#integration-hold-and-atomic-adoption)
to close old owners and tasks with their original reviews and resolve staged
approvals. Run the read-only checker against the exact squash before switching
the operating checkout.
