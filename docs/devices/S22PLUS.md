# Samsung Galaxy S22+ FYG8

**English** · [한국어](S22PLUS.ko.md)

## Device / SoC / kernel

- Device: Samsung Galaxy S22+ (`SM-S906N`, `g0q`), exact firmware
  `S906NKSS7FYG8`.
- SoC: Qualcomm SM8450 / Snapdragon 8 Gen 1 (`taro`).
- Kernel: source-matched Samsung vendor Linux
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`.

## Role

The S22+ is the source-matched rebuilt-kernel and direct-native-PID1 research
target. It now has bounded native-PID1 USB communication and authenticated
fixed-command execution without Android userspace. Current work improves
session reliability and failure observation. Functional transport proof and
detailed USB/Max77705 causal explanations are evaluated separately.

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
  1. That historical marker alone did not prove the first userspace instruction;
  the later native-PID1 communication results below establish runtime execution.
- **PROVED — native-PID1 ACM arrival and bidirectional commands.** P3.25
  retained the exact native banner. P3.26 proved the fixed bidirectional
  exchange and BusyBox child execution; P3.27 proved three framed fixed
  commands with clean completion.
- **PROVED — authenticated bounded sessions.** P3.30 completed authentication
  and three fixed commands. P3.35 proved three authenticated sessions in one
  run: two on one tty descriptor and one after a planned host close/reopen,
  with nine command executions, all exiting zero, and clean session closes. Exact
  rollback and rooted FYG8 final health passed for those successful runs.
- **PROVED — recovery-safe experiment mechanics.** Process-v2 runs distinguish
  transfer, observation, rollback, and final health and preserve candidate
  no-replay. Several later USB experiments closed safely as no-proof or
  refutation without promoting candidate success.
- **PROVED host-side — historical P3.19 USB plan static closure.** The plan has 73
  rows, no missing declared dependency or ordering violation, exact module
  bytes for its 72 vendor rows, and a built-in DWC3/gadget core. This is only a
  static membership/order/ABI result.
- **PROVED — P3.19 recovered final health.** The exact candidate and rollback
  each transferred once, the journal closed, and rooted FYG8 Android health
  passed. The formal result is `NO_PROOF_OBSERVER`, not USB success, and the
  candidate is consumed without replay.

## Partially proven / observed

- **observed — stock Android and stock first-stage CDC ACM are functional.** A
  bounded stock control completed 128 framed exchanges, and an early Android
  boot service repeated that result. Neither proves native-PID1 USB bring-up.
- **observed — older direct-native runs lacked an accepted ACM receipt.**
  This did not always mean no endpoint existed: P3.23/P3.24 later localized
  host selector and tty-property defects. Their consumed no-proof results
  remain separate from P3.25's accepted native banner.
- **observed — later session failures remain.** P3.35's later idle action was
  uncertain before authentication or command execution. P3.36–P3.39 retained
  native banners but no successful authenticated session. P3.39 exposed a host
  collector that stopped before the additional failure diagnostics.
- **designed — initial OPEN failure-capture successor.** P3.40 host work
  targets the existing diagnostic stream; it is not a new live success.
- **PROVED within P3.15 only — restart-side functional witnesses executed.**
  The same run refuted the clean four-outer-work model. It did not prove USB2
  pull-up at the connector, attachment, or transport.
- **observed — stock recovery can write the SSUSB mode to `peripheral` and wait
  for `a600000.dwc3`.** This positive control supports the direct-role design
  shape, but uses a different runtime/Image and does not prove candidate bind.

## Not yet proven

- **unproved —** reliable long-idle/reopen behavior beyond the bounded
  successful sessions.
- A general interactive PTY/shell, caller-selected commands, file transfer,
  persistent service, or autonomous F1 operation.
- A complete causal account of the USB/Max77705 bring-up and natural
  UCSI/PMIC-GLINK role path. End-to-end transport success does not independently
  measure every intermediate driver event or resolve the supplemental Carrier.
- The cause of the later initial OPEN header rejection. Missing diagnostic
  bytes from a failed collector do not prove the device sent none.

## Current frontier

Snapshot checked on 2026-09-05: P3.35 is the accepted three-session reference;
it does not make later candidates successful. P3.39 closed with one candidate
and one rollback, healthy rooted FYG8 return, and `NO_PROOF`. Its capture
retained the native banner and the header-validation failure, but missed the
additional words needed to explain that failure.

P3.40 is host work on that initial capture path. The immediate goal is usable
failure evidence and repeatable sessions over the established ACM channel.
The exact current preparation/review state belongs in [GOAL.md](../../GOAL.md)
and the target contract. This page creates no execution authority or replay.

## Major milestones

1. Exact FYG8 source and Full-LTO build closure produced a rebuilt kernel that
   booted Android.
2. Retained-witness work established reliable acquisition and strict absence
   classification boundaries.
3. R4W1-D proved direct native `/init` exec acceptance at PID 1.
4. Later USB runs separated functional restart witnesses from connector and
   transport claims, including explicit refutations and no-proof terminals.
5. P3.19 closed static module/order/ABI questions but its live result exposed
   an observer failure and provided no USB success.
6. P3.25 proved native-PID1 ACM arrival; P3.26/P3.27 added bidirectional
   BusyBox execution and framed fixed commands.
7. P3.30 proved authentication; P3.34/P3.35 established bounded multiple
   sessions with healthy rollback. Later idle/reopen failures remain separate.

## Architecture summary

```text
bootloader
  -> source-matched Samsung 5.10.226 kernel
    -> custom static /init running as PID 1
      -> vendor USB bring-up and CDC ACM
      -> authenticated bounded session
        -> fixed BusyBox commands and framed results
      -> exact boot rollback and rooted Android health
```

The bounded flow is supported by the linked successful runs. It is not a
general shell or a continuously operating service, and it does not settle
every internal USB causal question.

## Authoritative evidence links

- Native ACM arrival: [Native ACM arrival](../reports/S22PLUS_FYG8_P325_F1_ACM_PRIMARY_PASS_2026-09-02.md)
- Bidirectional BusyBox proof: [Bidirectional BusyBox proof](../reports/S22PLUS_FYG8_P326_F1_BIDIRECTIONAL_USB_BUSYBOX_PASS_2026-09-02.md)
- Framed fixed commands: [Framed fixed commands](../reports/S22PLUS_FYG8_P327_F1_FRAMED_EXEC_FIXED_COMMANDS_PASS_2026-09-02.md)
- Authenticated commands: [Authenticated commands](../reports/S22PLUS_FYG8_P330_F1_AUTHENTICATED_COMMAND_PASS_2026-09-03.md)
- Three-session proof: [Three-session proof](../reports/S22PLUS_FYG8_P335_F1_ATTENDED_RESIDENT_PASS_2026-09-04.md)
- Initial capture failure: [Initial capture failure](../reports/S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md)
- Current frontier: [GOAL.md](../../GOAL.md)
- Binding target contract: [S22+ FYG8 target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
- Historical run ledger: [S22+ campaign ledger](../operations/CAMPAIGN_LEDGER_S22PLUS.md)
- Epistemic experiment index: [native PID1/userspace evidence ledger](../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md)
- Rebuilt-kernel Android proof: [R3C1 live result](../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md)
- Direct PID1 boundary: [R4W1-D live pass](../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md)
- Stock ACM positive control: [O0 stock USB control](../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md)
- Historical static USB closure: [P3.19 SSUSB/UDC plan closure](../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md)
- Historical USB audit and live interpretation: [P3.19 comprehensive USB audit](../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md)
- Additive post-live decoder: [`s22plus_fyg8_p319_postlive_decoder.py`](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_postlive_decoder.py)
- Historical H0 kmsg prototype: [`s22plus_fyg8_p319_kmsg_record_envelope.py`](../../workspace/public/src/scripts/analysis/s22plus_fyg8_p319_kmsg_record_envelope.py)
