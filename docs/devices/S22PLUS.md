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
command execution without Android userspace. P348 additionally proved bounded
caller-selected shell commands in a read-only child view. Work since then moved
to driving the panel directly from native PID 1: the P353-P361 series compared
framebuffer paths and culminated in operator-observed clean output and repeated
cached-buffer selection, and P362-P364 turned to native reboot/Download control,
which remains unproved. Work since P375 has added an authenticated root command
console and a native status HUD painted by PID 1. The P349 RAM workspace unit stays host-qualified and
paused. Functional transport proof and
detailed USB/Max77705 causal explanations are evaluated separately.

## Visual evidence

Photographs and clips of the P353-P361 display bring-up runs, ordered as a
comparison rather than a chronology, are on a separate page:
[S22+ display visual evidence](S22PLUS_DISPLAY_VISUAL_EVIDENCE.md).

One continuous recording of the P376 run, in which native PID 1 paints its own
status text and advances an uptime counter on the panel, is on its own page:
[S22+ boot HUD visual evidence](S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.md).

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
- **PROVED — bounded read-only research shell.** P347 passed five shell
  qualification sessions. P348 passed six initial sessions / 18 commands,
  including a 120-second idle and clean reopen, then all five later acceptance
  actions: checked snapshot, exit 7, timeout, authenticated cancel and
  post-cancel output. Exact Magisk rollback and rooted FYG8 final health passed.
  P348's last later witness was 390.137 seconds after lease opening; this does
  not prove one hour. Both candidates are closed and consumed.
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
- **observed — historical session failures remain distinct.** P3.35's later idle action was
  uncertain before authentication or command execution. P3.36–P3.39 retained
  native banners but no successful authenticated session. P3.39 exposed a host
  collector that stopped before the additional failure diagnostics.
- **designed / host-qualified — P349 RAM workspace.** A/B builds, bounded
  namespace/syscall tests and independent capability review passed for `/work`
  (8 MiB, 256 inodes, UID/GID 65534) and fixed BusyBox script execution. Both
  approved invocations aborted during host authentication before Download or
  candidate transfer. No P349 native session ran.
- **PROVED within P3.15 only — restart-side functional witnesses executed.**
  The same run refuted the clean four-outer-work model. It did not prove USB2
  pull-up at the connector, attachment, or transport.
- **observed — stock recovery can write the SSUSB mode to `peripheral` and wait
  for `a600000.dwc3`.** This positive control supports the direct-role design
  shape, but uses a different runtime/Image and does not prove candidate bind.

## Not yet proven

- **unproved —** actual hour-long residency and reliable long-idle/reopen
  beyond the bounded successful sessions.
- On-device P349 RAM persistence, script execution and its timed witnesses.
- A general interactive PTY, unrestricted root shell, general file transfer,
  persistent service, arbitrary ELF qualification or autonomous F1 operation.
  P348's proved caller-selected commands remain confined to its bounded view.
- A complete causal account of the USB/Max77705 bring-up and natural
  UCSI/PMIC-GLINK role path. End-to-end transport success does not independently
  measure every intermediate driver event or resolve the supplemental Carrier.
- The cause of the later initial OPEN header rejection. Missing diagnostic
  bytes from a failed collector do not prove the device sent none.

## Current frontier

Snapshot checked on 2026-09-09. The most recent completed display milestone is
the P353-P361 line. Those runs compared framebuffer paths, and each closed with a
machine verdict that **PROVED** authenticated dispatch and exact rollback, while
the clean output itself is **observed** by the operator and corroborated by
photographs and clips, not proved by readback. P361 is the furthest of them:
eleven blocking atomic commits alternating between two prepainted cached buffers,
ending held on the first. Why write-combine buffers corrupted and cached buffers
did not remains **unproved**. See
[display visual evidence](S22PLUS_DISPLAY_VISUAL_EVIDENCE.md).

P362 closed as host analysis plus one fixed D0 module census. P363 and P364
attempted native reboot/Download control and both closed `NO_PROOF_OBSERVER`
with healthy rollback; P364's diagnostic channel retained 28 authenticated
progress frames before an SDAM provider check returned EINVAL, so renderer
creation and Download control were not reached. **Native normal reboot and
Download remain unproved.**

P365 then closed `NO_PROOF_OBSERVER` as well, but reached further: its corrected
ARM64 flags passed every preparation stage, and 46 authenticated progress
records, ten swap submissions and an accepted Download CONTROL were retained.
The operator **OBSERVED** changing screen output followed by screen-off and
arrival in Download mode without physical intervention, further than P363 or
P364 reached. The machine's bounded Download-arrival and causal proof remain
**unproved**. The execution stopped during post-CONTROL USB inventory after the
device node disappeared; one same-journal rollback-only recovery then restored
the exact rooted FYG8 state and verified final health.

P375 and P376 then closed successfully. P375 gave native PID 1 an authenticated
root command console over its CDC ACM transport; P376 added a separate text HUD
child beside it. P376's attended run passed all six fixed qualifications and its
three planned commands, retained three matched HUD frames and a later
`HUD_STILL_UPDATING` confirmation, and completed one exact rollback with verified
final health. The operator **OBSERVED** the `NATIVE INIT` text and an increasing
uptime on the physical panel; machine pixel proof is not claimed, and the run's
ACK-only `software_download_arrival=UNPROVED` and supplemental
`p376_proof_class=NO_PROOF_OBSERVER` are unchanged. See
[boot HUD visual evidence](S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.md).

Work after P376 extended the HUD to fixed system-status collection — uptime,
console state, memory used/total/available, aggregate CPU usage, and battery
capacity, charge status and temperature — under the same immutable-buffer and
matched-flip retirement rules. Physical display remains operator observation
there too, and kernel/PID1-stall recovery is still not claimed.

Completed scopes are named as functional versions under the
[S22+ version/candidate/run naming convention](../operations/S22PLUS_FYG8_VERSIONING.md),
which maps each version to unchanged artifacts and to its historical P number.
**The exact current functional version and the active bounded unit are
maintained in [`GOAL.md`](../../GOAL.md), not on this page.** A version name
records a verified bounded scope; it is never a new build, a resident native
install, or a claim of stability, repeated boot or long-running operation.

The P349 RAM workspace and actual-hour witness unit remains
host-qualified and paused; neither of its prepared invocations transferred a
candidate.

The exact current state belongs in [GOAL.md](../../GOAL.md) and the target
contract. This page creates no execution authority or replay.

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

8. P347 qualified the isolated read-only shell; P348 proved later caller-selected
   use and clean reopen, followed by exact healthy rollback.
9. P349 qualified a RAM workspace on the host. Both live invocations stopped
   before transfer; the actual-hour and on-device RAM tests await attendance.

## Architecture summary

```text
bootloader
  -> source-matched Samsung 5.10.226 kernel
    -> custom static /init running as PID 1
      -> vendor USB bring-up and CDC ACM
      -> authenticated bounded session
        -> bounded read-only BusyBox shell commands and framed results
      -> exact boot rollback and rooted Android health
```

The bounded flow is supported by the linked successful runs. It is not an
unrestricted root shell or a continuously operating service, and it does not settle
every internal USB causal question.

## Authoritative evidence links

- [Read-only shell qualification](../reports/S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md)
- [Retained read-only shell result](../reports/S22PLUS_FYG8_P348_RETAINED_SHELL_PREPARED_2026-09-06.md)
- [RAM workspace preparation and authentication stops](../reports/S22PLUS_FYG8_P349_RAM_WORKSPACE_PREPARED_2026-09-06.md)
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
