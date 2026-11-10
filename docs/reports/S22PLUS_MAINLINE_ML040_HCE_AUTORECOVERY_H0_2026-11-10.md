# ML040 HCE handoff and automatic Download preparation

## Selected unit and physical baseline

The operator requested analysis with Mythos 5.2 followed by the next physical
experiments, then selected automatic Download as the default even when the
experiment result is unclear. This H0 unit prepares that scope on S22+ FYG8.
It grants no run authority. ML039 remains consumed and Android-closed healthy;
A90 and S20+ are outside this change.

ML039 measured HCE `1`, HCS `0x10f`, zero request doorbells and interrupt enable,
and interrupt status `0x400`. It issued no RPMh or local/link command. Those
samples do not establish bootloader causality, electrical validity or exclusive
hardware ownership. ML027/ML028 separately proved normal automatic Download
and original-A return; they did not prove recovery from an unknown UFS state.

## HCE transaction

The report-v6 module admits only the fixed enabled-state preconditions in the
[shared policy](../operations/S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md). It stops
on the first failed read, changed HCE or expired budget. One static slot precedes
one whole-word HCE-zero write. HCE-only polling must finish inside both one
millisecond and the original module budget; even an observed late zero cannot
continue. Only timely zero reaches the unchanged short-circuit HCI/pin guards
and existing hardware path. Stage six cannot repeat handoff. Crypto/unknown
HCE, status clearing, altered reset ordering and hardware retry remain excluded.

The 30-field, 256-byte report distinguishes pre-admission, stop issuance,
poll/time metadata and actual post-state checks. Guest/host interpretation
keeps unknown values unavailable. Earlier report modes retain their meanings.
The current ARM64 module reproduces the retained module bytes exactly; its
original and current source provenance remain separate.

## Automatic return and recovery

V6 forks one recovery child before USB setup after the fixed reboot-mode driver
and OF cell/magic checks. The child owns the sole ordinary Download syscall;
the observer cannot issue a competing reset. Fresh authenticated base and late
child receipts are required before a UFS permit. Complete valid results,
including negative/load/read results, may request early return after raw
capture, result-bound control, ACK and EOF. Functional proof remains separate.

The child accepts early commit before guest time 540 seconds. Otherwise it
attempts the same slot at 555 seconds, after a 15-second quiet interval. No
syscall starts at or after 570 seconds. Parent loss, invalid IPC and a full
reply queue neither renew nor disarm the timer. There is no respawn, second
reset, emergency restart, panic/RDX or hardware watchdog.

After a stop the host observes exact Download within the original N-intent
launch plus 660 seconds. It needs neither completed N nor successful link/ACK
parsing. An intended N requires a later measured USB-node birth than the
launch generation; permission-only identity changes cannot qualify. The actual
A-transfer ticket repeats that check and the fixed deadline. Existing A intents
allow reconstruction and health only. Timeout creates no A intent and leaves
the existing physical recovery path available. Cue interlocks remain binding.

Ordinary reboot can still block on reboot notifiers, probe completion, device
locks or runtime-PM. The selected module has no shutdown callback and no generic
UFS/SCSI host binds. PID1 death, whole-kernel failure, starvation and blocked
reboot are not claimed covered. Reset can lose RAM-only diagnostics. Exact
arrival without a trigger receipt does not prove the trigger's identity.
Conditional unattended F1 remains inactive; first physical qualification still
requires the exact attended one-operation approval and usable Download fallback.

## H0 evidence and review

Private evidence is under
`workspace/private/outputs/s22plus-ml040-hce-handoff-h0-20261110-1/`.

- Actual C producer/reader, authenticated host parser and ARM64 fixtures cover
  HCE admission, drift, timeout/late zero, downstream refusals and no retry.
- Actual C child tests on host and ARM64 cover early commit, timer, parent EOF,
  input flood, malformed IPC, killed child, late scheduling, parent and child
  commit expiry, one returning failed syscall and no respawn.
- Host socket tests cover authenticated arm/late receipts, result-bound return
  for failures, missing/wrong arm proof, malformed/partial results, ACK failure
  and unchanged research deadlines.
- Original Session/Adapter tests cover unknown control, no A attempt on arrival
  timeout, physical fallback, current ticket/birth checks, fixed dispatch caps,
  uncertain A non-replay and completed-A health continuation.
- The exact retained mainline kernel in isolated ARM64 QEMU completed an ordinary
  reset with the observer parked: the unscaled timer case took 555.55 seconds.
  A fresh current-source early-commit VM case reset in 1.97 seconds. QMP recorded
  guest-reset, with no host reset command. QEMU does not model Samsung PMIC/UFS
  failure recovery. The retained timer source predates only the tightened
  child early-commit cutoff; its timer path is unchanged and its exact source
  bytes are retained against the original compile hashes.
- Two fresh key-only artifacts undergo complete observer reproduction,
  canonical CPIO/package checks, actual ARM64 loader/exception-level tests and
  AP-to-boot-to-loader-to-kernel/DT/archive byte joins. Earlier preliminary H0
  artifacts remain separate and are not selected for execution.

The complete focused suite passed **141 tests with no skips**. Touched Python
compiled, the physical observer and module were cross-compiled and inspected,
and the repository boundary/diff checks passed.

Past-failure checklist applicability: ABI/WIRE/SEMANTIC are confirmed by the
actual ARM64 producer, IPC and decoder cases, while physical HCE/reset coverage
remains unconfirmed. ROUTE/RETURN/HOST are confirmed at H0 by actual Session and
Adapter fault paths, exact generation/cap checks and unchanged original-owner
health continuation. ARTIFACT/PERSIST/AUDIT are confirmed by complete byte joins,
raw-first capture and retained source/receipt reconstruction. DISPLAY and
media-backed filesystem persistence are inapplicable to this RAM/no-display
unit. None of these checks supplies device authority.

The independent review identified two concrete automatic-A issues: generation
must be checked on the actual transfer ticket, and a full identity-hash change
can reflect permissions rather than a new USB node. Both were corrected using
sealed birth evidence and covered by focused tests. The final coherent independent review returned PASS_GO with no findings,
verified all frozen bindings and independently passed 65 tests. Fresh complete
qualification then selected v42 and the exact ML040 task. The subsequent
[attended run](S22PLUS_MAINLINE_ML040_RUN_2026-11-10.md) is separately closed.

## Mythos discussion and accounting

Three tool-disabled advisory calls used actual `claude-mythos-5-2`. The discussion
narrowed HCE stop to the source-grounded one-ms bound and existing report size,
then challenged the recovery design's generation, timing and proof semantics.
It is advisory evidence, not the independent capability review or run approval.

Claude Code `/usage` was read before and after the calls. The account session
meter moved from 37% to 81%, weekly from 9% to 13%, and Fable from 18% to 25%;
these are account-wide changes. Provider records total 51,870 input tokens and
69,705 output tokens, including 59,052 thinking tokens. The CLI API-equivalent
cost is USD 3.618072, not verified subscription billing. Credits remained off.
Each call and quota snapshot is retained in the private append-only usage log;
no model fallback or inference retry occurred.
