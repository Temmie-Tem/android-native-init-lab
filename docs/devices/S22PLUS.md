# Samsung Galaxy S22+ FYG8

## Device / SoC / kernel

- Device: Samsung Galaxy S22+ (`SM-S906N`, `g0q`), exact firmware
  `S906NKSS7FYG8`.
- SoC: Qualcomm SM8450 / Snapdragon 8 Gen 1 (`taro`).
- Kernel: source-matched Samsung vendor Linux
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`.

## Role

The S22+ is the source-matched rebuilt-kernel and direct-native-PID1 research
target. It established the kernel-to-native-exec boundary and now concentrates
on the harder early USB problem: reconstructing enough of the vendor module,
supplier, role, gadget, and physical-attach chain to make a native runtime
observable without Android userspace.

## Proven capabilities

- **PROVED — reproducible source-matched kernel build.** The rebuilt Full-LTO
  kernel has the expected format and identity, and a bounded live candidate
  booted the exact FYG8 Android userspace before clean rollback.
- **PROVED — rebuilt-kernel early Android witness.** A later guarded candidate
  reached the expected early Android PID1 path and preserved its retained
  marker through the accepted acquisition channel.
- **PROVED — direct native `/init` exec acceptance.** R4W1-D produced one exact
  retained marker after successful `kernel_execve("/init")` while current was
  PID 1. This proves the kernel accepted the intended native executable as PID
  1. It does not prove execution of the first userspace instruction.
- **PROVED — recovery-safe experiment mechanics.** Process-v2 runs distinguish
  transfer, observation, rollback, and final health and preserve candidate
  no-replay. Several later USB experiments closed safely as no-proof or
  refutation without promoting candidate success.
- **PROVED host-side — current USB plan static closure.** The P3.19 plan has 73
  rows, no missing declared dependency or ordering violation, exact module
  bytes for its 72 vendor rows, and a built-in DWC3/gadget core. This is only a
  static membership/order/ABI result.

## Partially proven / observed

- **observed — stock Android and stock first-stage CDC ACM are functional.** A
  bounded stock control completed 128 framed exchanges, and an early Android
  boot service repeated that result. Neither proves native-PID1 USB bring-up.
- **observed — direct-native candidates repeatedly lacked host-visible ACM.**
  This is a real symptom, but older witnesses often could not identify the
  first failing device-side gate.
- **PROVED within P3.15 only — restart-side functional witnesses executed.**
  The same run refuted the clean four-outer-work model. It did not prove USB2
  pull-up at the connector, attachment, or transport.
- **observed — stock recovery can write the SSUSB mode to `peripheral` and wait
  for `a600000.dwc3`.** This positive control supports the direct-role design
  shape, but uses a different runtime/Image and does not prove candidate bind.

## Not yet proven

- The first instruction of the direct native userspace, subsequent mounts,
  child execution, or a native control loop.
- Candidate-runtime bind of the `a600000.ssusb` parent.
- Creation/bind of the built-in `a600000.dwc3` child and publication of
  `/sys/class/udc/a600000.dwc3`.
- Successful configfs gadget bind, DWC3 pull-up/connect, physical host attach,
  tty publication, or framed native transport.
- A complete natural UCSI/PMIC-GLINK role path in the current candidate plan.
- A fresh P3.19 baseline or any current ready/run manifest, approval, F1
  result, or standing live authority.

## Current frontier

The USB frontier is intentionally split into four causal layers:

```text
SSUSB parent (a600000.ssusb)
  -> DWC3 child (a600000.dwc3)
    -> UDC (/sys/class/udc/a600000.dwc3)
      -> transport (gadget bind -> pull-up/connect -> host tty -> framed bytes)
```

For the current P3.19 closure, module membership, declared dependencies,
ordering, relevant symbol providers, the `mode_store -> dwc3_msm_set_role`
edge, and the runtime's intended `mode=peripheral` write are **PROVED
host-side**. Dynamic supplier availability, `dwc3_msm_probe()`, parent bind,
child creation, UDC publication, and every transport step are **unproved at
candidate runtime**.

The immediate process blocker is also separate: machine integration remains
`FRESH_BASELINE_MISSING`. The new canonical-arm V3 producer is independently
reviewed `PASS_GO` but **not active**; it created no approval, reboot, device
contact, result, or live authority. Thus the repository has a sharper
discriminator and a qualified host capability, not a new USB success.

## Major milestones

1. Exact FYG8 source and Full-LTO build closure produced a rebuilt kernel that
   booted Android.
2. Retained-witness work established reliable acquisition and strict absence
   classification boundaries.
3. R4W1-D proved direct native `/init` exec acceptance at PID 1.
4. Later USB runs separated functional restart witnesses from connector and
   transport claims, including explicit refutations and no-proof terminals.
5. P3.19 moved the frontier from broad connector/MUX speculation to the
   explicit SSUSB-parent → DWC3-child → UDC → transport chain.
6. The current 73-row plan closed static module/order/ABI questions while
   preserving all dynamic runtime questions as unproved.

## Architecture summary

```text
bootloader
  -> source-matched Samsung 5.10.226 kernel
    -> custom static /init accepted as PID 1
      -> load ordered vendor USB/provider closure
      -> bind a600000.ssusb parent
      -> materialize built-in a600000.dwc3 child and UDC
      -> set peripheral role and bind configfs gadget
      -> enumerate ACM and exchange framed bytes
```

Only the first two lines through exec acceptance are established as a direct
native live result. The USB lines describe the current tested architecture and
runtime gates, not a completed path.

## Authoritative evidence links

- Current frontier: [GOAL.md](../../GOAL.md)
- Binding target contract: [S22+ FYG8 target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
- Historical run ledger: [S22+ campaign ledger](../operations/CAMPAIGN_LEDGER_S22PLUS.md)
- Epistemic experiment index: [native PID1/userspace evidence ledger](../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md)
- Rebuilt-kernel Android proof: [R3C1 live result](../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md)
- Direct PID1 boundary: [R4W1-D live pass](../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md)
- Stock ACM positive control: [O0 stock USB control](../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md)
- Current static USB closure: [P3.19 SSUSB/UDC plan closure](../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md)
- Fresh-baseline blocker: [P3.19 Process-v2 prerequisites](../reports/S22PLUS_FYG8_P319_PROCESS_V2_INTEGRATION_PREREQUISITES_H0_2026-08-21.md)
- Current non-active producer: [P3.19 D1 canonical-arm V3](../reports/S22PLUS_FYG8_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_H0_2026-08-29.md)
