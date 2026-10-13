# S22+ P428 H0: distinguish work failure, evidence failure and child outcome

Status: **DESIGN_SELECTED_H0_ONLY**. No new device authority or physical run.
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

## Checklist application before implementation

Use the existing [checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md)
for every S22+ change, selecting only applicable rows and recording evidence in
the existing change report. No new approval step or global failure-count gate
is created. Update the existing rows for this observed omission.

| ID | Initial disposition and required evidence |
| --- | --- |
| ABI | Pending: actual ARM64 fork/wait, atomic snapshot, time and signal behavior; correct target constants. |
| IO | Pending: failed/short evidence I/O, readback failure, bounded output and stalled worker; no pipe dependency. |
| SEMANTIC | Pending: distinct syscall, cleanup, log and wait facts; no inference of cancellation or descendant settlement. |
| WIRE | Pending: actual C authenticated diagnostic bytes through kernel-log capture and real decoder; missing/torn/foreign records rejected or explicitly partial. |
| PERSIST | Pending: production recording path after failure; preserved raw bytes before decoding; RAM/returned/file proof meanings remain separate. |
| ROUTE | Pending: physical and VM initramfs include the same wrapper/diagnostic route; no VM-only semantic terminal is accepted. |
| ARTIFACT | Pending: actual physical/virtual counterpart sources, generated seals, CPIO and static ARM64 binaries. |
| AUDIT | Confirmed: current source matches frozen P426 inputs; exact raw prefixes and actual packaged shell were read without device contact. |
| HOST | Applicable only to H0 producer/collector execution; connected host machinery is unchanged and not qualified anew here. |
| DISPLAY | Not applicable: no display change or display-based inference. |
| RETURN | Preserved: P426/P427 closure and no-replay remain unchanged; no new physical recovery claim. |

Representative faults must include module errno, primary RAM/kernel-log evidence
failure, worker signal, worker pending, malformed/absent carrier and a normal
complete path. Tests may substitute Samsung discovery/module effects for ARM64
virt and inject declared failures. They must not manufacture missing production
status records. Independent review covers this changed observer/ancestry scope
and the checklist's real producer-to-consumer evidence.
