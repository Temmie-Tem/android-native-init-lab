# ML047 terminal link interrupt diagnostic

ML046 issued DME_LINK_STARTUP after six successful local commands. Its EIO
and unfilled completion fields narrow the failure to an unexpected IRQ_STATUS
sample in the bound command loop. The [physical report](S22PLUS_MAINLINE_ML046_RUN_2026-11-11.md)
records that inference and the original healthy Android closure.

The operator selected one new attended S22+ FYG8 experiment. On the V12 link
command's unexpected-status branch, the producer stores the same local u32
that failed the mask test in the existing interrupt field. It then returns
EIO. This preserves simultaneous completion, startup and error bits. Local
command failures take their existing path. The physical question is which
bits appear if this refusal recurs. A different outcome receives its own
classification.

The wire record retains 33 fields and its 256-byte envelope. The V12 tag
selects the new meaning. The actual automatic-recovery guest seals and
transmits the report, then binds return to the result digest. The host
authenticates the frame and distinguishes an unexpected terminal sample,
a recorded completion, and absence of a terminal sample. A completed command
can have a later module-level error. Full functional success retains its
existing link and power predicates. Rechecking the historical ML046 frame
with the current decoder reproduced every V11 field and rejected V12 format
substitution.

The focused tests run the production HCI command and report formatter on the
host and ARM64/QEMU. They compare V11 and V12 final-command MMIO traces,
errno, issuance counts, completion and refusal fields. The cases cover an
error alone, completion plus errors, bits 31 and 0 together, timeout, local
failure and valid completion with and without a command error. The wide ARM
fixture exercises the actual bounded report reader. A loopback test sends a
real mixed-status producer record over the authenticated witness/permit
protocol, retains NO_PROOF and verifies one result-bound Download control.
Malformed, partial, expired and missing-child cases exercise their original
stops.

The fixed ARM64 module, RAM observer, initramfs, loader and boot-only AP were
built for the fresh candidate. Artifact qualification rejoined the contained
bytes, reproduced the observer and exercised the loader entry tests. Component
validation checked the selected compiler flags, disassembly, fixed kernel,
configuration, PHY tables and overlay against the retained ML046 inputs.

Three host preparation errors were recorded and corrected. The first build
invocation lacked the retained Unicorn import path and stopped before
candidate construction. The first focused test selector named the wrong test
class. The first cue help probe required its capture directory to be created.
The corrected invocations used the retained dependency path, the actual
test class and prepared private capture directories. The cue help child
completed and its raw streams and exit status were verified.

The physical scope uses the original 120-second first response window,
300-second same-boot witness, 540-second research ceiling and 15-second
module budget. It permits one link attempt, one N and one original A. The
reviewed automatic Download attempt, attended physical fallback and final
Android health checks remain bound to the original owner. Each task requires
the exact returned finite approval and current attendance.

Private evidence is under
`workspace/private/outputs/s22plus-ml047-link-irq-h0-20261111-1/`. It
includes the immutable component and candidate, source snapshots, H0
build/test and help-capture results, retained V11 parity and independent
review evidence.

The final aggregate suite passed 177 tests without skips, including the fresh
artifact cases. Independent review passed 81 tests, 30 paired V11/V12 MMIO
traces and 1,582 pin checks. The reviewer reproduced the observer, verified
artifact joins and checked the retained finalizer and ML046 raw evidence.
The final packet digest is
`2327b38bc530f80deb697e11191247b5fefa102b7f9246cc2cdf49a52333f273`.
Capability `b04a715fa529bcc90be758e0557fe326cab29257c79b02e5df88f92af4df73b4`
received independent PASS_GO with zero open findings in receipt
`4db8e4c7c416ae8564f4df4f892e9405e7c346aeaa99719c39c41a48ec977937`.
The reviewed v48 backend and prepared one-operation task use the existing
ordinary-terminal worker.
Current foreground D0 passed all seven raw Android health reads. The exact
finite attended approval is required before the grant opens.

The subsequent [attended physical result and healthy Android closure](S22PLUS_MAINLINE_ML047_RUN_2026-11-11.md) record the consumed ML047 run.
