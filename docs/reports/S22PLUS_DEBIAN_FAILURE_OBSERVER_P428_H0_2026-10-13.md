# S22+ P428 H0: distinguish work failure, evidence failure and child outcome

Status: **PASS_GO_H0_ONLY**. No new device authority or physical run.
P426/P427 remain consumed and closed healthy. This unit implements and tests
production-present failure observation, using the existing S22+ checklist.

## Bounded completion criterion

A real ARM64 producer and its real host decoder must distinguish fixed module
return/errno, primary evidence failure, worker exit, worker signal and a worker
still uncollected at the original deadline. The normal and failure evidence must
come from the same diagnostic code included in the prospective physical
initramfs. VM-only terminal prints cannot satisfy that criterion. A wholly lost
carrier remains UNKNOWN; host success, VM shutdown or later Android health is
never substituted for device-generated evidence.

This is H0 implementation, qualification and independent review. It does not
activate a new profile, update a consumed review, open a grant or replay a
candidate. Samsung hardware readiness and actual post-return retention remain
physical questions. No new AP transfer or connected device command is selected.

## Evidence behind the change

P426 preserved 156 authenticated RAM records ending at `ufs_qcom` BEGIN; P427
found the sealed run file absent in a clean home-block view. This does not locate
a kernel stall. The current module path combines insertion, fd close, presence
and evidence checks before DONE. A failed evidence write/readback stops work;
its final error report shares that fallible path. The shell saves child status
only in RAM and parks. Existing VM qualification replaces that park with status
and RAM-file console output that is absent from the physical image.

The distinction between safe rejection and recoverable diagnosis was therefore
not demonstrated. Preserve every old source, raw capture, classification and
qualified artifact with its original scope.

## Selected implementation

Keep Debian shell `/init` and its fixed preparation-then-file-helper sequence.
Inside each existing helper, before opening worker resources, one fixed parent
forks one worker running the same executable's fixed function. No selectable
command, extra executable, daemon, pipe, USB endpoint or new persistent surface
is introduced. The parent remains a direct child of the measured Debian PID1;
the worker validates that exact known parent. Initial-PID1 measurement must
explicitly reflect this one-level ancestry rather than retaining a false direct
parent claim. A separate prospective diagnostic identity preserves old formats.

An anonymous shared RAM structure publishes stable atomic snapshots. Work phase,
module ordinal, immediate syscall return/errno, later close/presence outcomes and
primary evidence stage/result remain separate. State changes precede fallible
recording. The parent collects exact wait status for its one worker and publishes
bounded authenticated diagnostics through the existing checked kernel-log
carrier. Such evidence is separate from the worker's primary log and from any
persistent run file. The same kernel carrier may lose both; no guaranteed
retention or independent hardware channel is claimed.

The original absolute BOOTTIME bound inhibits subsequent worker effects. At
expiry the parent may report an uncollected worker and last stable phase; it
must not claim a blocked syscall was cancelled, a child settled, a filesystem
unmounted or recovery completed. It cannot advance the shell to the next helper.
Parent-death handling includes the post-configuration parent-identity race check.
The existing checker owns its own exact-child settlement and storage cleanup.
Collecting the outer worker never proves those descendants or cleanup complete.

The prospective file surface remains the existing clean-only native_data run
file, bounds and one-shot cleanup. This H0 unit adds no journal replay, repair,
module retry, installed Debian execution or recovery mechanism.

## Checklist application and qualification

Use the existing [checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md)
for every S22+ change, selecting only applicable rows and recording evidence in
the existing change report. No new approval step or global failure-count gate
is created. Update the existing rows for this observed omission.

| ID | Initial disposition and required evidence |
| --- | --- |
| ABI | Confirmed in H0: retained FYG8 UAPI constants and ARM64 compiler assertions; actual ARM64 shared atomics, fork/wait, signals and time behavior. Samsung blocked-kernel behavior remains unproved. |
| IO | Confirmed in H0: primary write/sync/readback errors, file short write and sync, parent sync, interrupted wait/sleep and finite pending-worker observation; no output pipe. |
| SEMANTIC | Confirmed in H0: immediate module return/errno differs from evidence failure; exact exit/signal/wait outcome; coherent tuples and explicit log-return validity. No cancellation, descendant or cleanup inference. |
| WIRE | Confirmed in H0: real C kernel-log bytes, raw serial preservation and real decoders in 18 cases; absent/torn/foreign input and missing START do not create a successful worker result. |
| PERSIST | Confirmed in H0: saved raw reopened; separate ARM64 mountless reader retrieves and verifies the actual version-3 file. Physical post-return retention remains unconfirmed. |
| ROUTE | Confirmed: prospective physical CPIO and ARM64 VM use the same observer source; diagnostic VM adds only poweroff at the shell park. It emits no VM semantic terminal or RO footer. |
| ARTIFACT | Confirmed: deterministic A/B physical initramfs, 204 frozen source paths, generated seals, static ARM64 helpers and 82 actual module files joined to CPIO. No AP transfer candidate or device activation is produced. |
| AUDIT | Confirmed: current P426 consumer and frozen sources were compared with raw evidence before diagnosis. Its root cause remains unresolved. |
| HOST | Confirmed for H0 only: bounded VM timeout preserves raw before decoding; simulated disks remain private regular files. Existing connected host machinery is unchanged and gains no qualification here. |
| DISPLAY | Not applicable: no display change or display-based inference. |
| RETURN | Preserved: P426/P427 closure and no-replay remain unchanged; no new physical recovery claim. |

Representative faults must include module errno, primary RAM/kernel-log evidence
failure, worker signal, worker pending, malformed/absent carrier and a normal
complete path. Tests may substitute Samsung discovery/module effects for ARM64
virt and inject declared failures. They must not manufacture missing production
status records. Independent review covers this changed observer/ancestry scope
and the checklist's real producer-to-consumer evidence.

## Implemented result

The prospective identity is P428 / `v0.7.0-rc.1` /
`debian-failure-observer-v1`. It has a separate authenticated domain and
version-3 file magic; old decoders reject the new file. Diagnostic-off builds
retain their old formats, direct-parent rule and collapsed primary EIO behavior.
Consumed artifacts, source snapshots, approvals and review tips are untouched.

Both helpers measure the exact initial Debian shell, `/init` and PID1 command
line before forking. The file worker additionally retains its existing helper
and RAM-log measurements. The one-level worker ancestry is explicit. Each
helper has one shared anonymous RAM object with lock-free 32-bit atomic fields,
a generation check and a separate parent stop flag. Result/value/validity tuples
are published together; a killed odd-generation writer yields an explicitly
unstable snapshot. The first instrumented work/evidence error remains sticky even if the
terminal logging attempt succeeds or fails differently.

Each parent publishes at most START and one terminal record through the existing
checked kernel-log write/readback primitive. A terminal is independently
authenticated; missing START does not discard it. Missing or malformed terminal
records leave that helper UNKNOWN. A measured successful worker exit does not
prove another helper, checker descendants, filesystem unmount, post-return
retention or recovery. A pre-call phase means only that the call was armed.

The fixed absolute 300-second BOOTTIME ceiling is checked by the worker before
later module/storage effects. Clock failure is separate from deadline expiry.
A pending or observer-error parent parks and cannot release the shell to the
next helper. Parent-death setup includes the identity race check; this does not
claim that SIGKILL cancels an uninterruptible kernel call or cleans up descendants.

## Validation evidence

Private evidence is under
`workspace/private/outputs/s22plus-debian-failure-observer-p428-h0-20261013-1/`.
`build-2/build.json` freezes the final producer construction and actual A/B CPIO
joins. Both executables are static AArch64 ELF. `vm-1/result.json` contains 18
real ARM64 cases with preserved serial bytes, independent diagnostic decoding,
primary-log decoding and before/after virtual-disk checks:

- normal completion and interrupted observation;
- module errno, failed BEGIN, failed DONE, RAM sync and kernel readback error;
- unexpected exit, signal, pending worker and late return;
- parent death, lost parent diagnostic and unstable shared snapshot;
- short file write, file sync, parent sync and unmount error.

The late-return case additionally verifies the authenticated production primary
log: exactly one module BEGIN/return and terminal `REJECTED/error=110`, with no
subsequent module attempt. A lost parent diagnostic remains missing even if the
independent writer later produces its own records. No VM footer substitutes for
these observations. Declared failure injection and board/module substitution are
VM-only; they do not establish Samsung driver or retained-RAM behavior.

`vm-1/normal/reader-boot/result.json` and `file-proof.json` join the real writer
with a separate ARM64 mountless-reader boot and the explicit version-3 decoder.
The recovered file proves authenticated pre-unmount progress under the measured
initial Debian PID1 ancestry; its original no-USB/no-unmount-return proof limits
remain intact. `focused-tests.log` records 71 passing protocol/owner regression
tests. Touched Python passed `py_compile`; scoped repository-boundary, content, link and diff checks pass.

Independent review requested corrections to atomic tuple publication, logging
return validity, early ancestor measurement, clock-error classification, late
return verification, parent-sync evidence and distinct artifact identity. These
were incorporated before the final qualification. Its final disposition is
**PASS_GO for this H0 observer construction and validation only**.

The independent reviewer redecoded all 18 raw diagnostic/primary streams,
checked actual physical and VM CPIO members, current virtual-disk digests and
204 physical / 224 VM source paths, and independently reopened the version-3
file with old-version rejection. The reviewed build receipt is
`5f794a74798b98d0a288125bd740863c8f07f78164f57f76623039b0f5491d92`;
the VM-suite receipt is
`94be816ba153f40dfceeb3b4df5d183e9d72078b4aeb778a395fed03d4abd1f2`.
This review activates no F1 owner, grant or physical candidate. No device action
occurred; A90, S20+ and all 46 pre-existing dirty paths remain untouched.
