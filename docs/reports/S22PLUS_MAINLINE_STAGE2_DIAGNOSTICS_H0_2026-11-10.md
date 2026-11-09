# S22+ stage-two diagnostics: H0 implementation

Status: **H0 VALIDATED / INDEPENDENT PASS_GO / NOT DEVICE ADMITTED**.

The operator requested stage-two diagnostics after consumed ML035, preserving
all guards and the same-boot 300-second witness, with no physical execution.
This bounded unit adds a failure location and the predicates actually evaluated
to the fixed module's report. Completion requires representative actual C
producer/reader/host-consumer checks, ARM64 compilation, independent review and
an isolated commit. It does not create an ML036 candidate, AP, task, grant or
activation, and does not change an existing review receipt or backend selector.

The work is isolated on `codex/s22-stage2-diagnostics-h0`, based on `3249adcaf1`.
The original main checkout, its unfinished Debian journal work, consumed runs,
approvals, workers and recovery owners are outside this change. A90 and S20+
are untouched. [ML035's physical result](S22PLUS_MAINLINE_ML035_RUN_2026-11-10.md)
remains stage 2 / EBUSY with the exact historical predicate unobserved.

## Change and evidence semantics

The module appends two unsigned 32-bit words to the existing 21 fields:

| Word | Meaning |
| --- | --- |
| `stage2_site` | Component in bits 8..15 and failed operation in bits 0..7; zero means no recorded stage-two failure |
| `stage2_checks` | Evaluated conditions in bits 0..10; failed conditions in bits 11..21; already masked HCS bits in bits 22..27 |

The eight components distinguish HCI, reset pin, core clock, UniPro clock,
VCC, VCCQ, reference pad and parent supply. The operation distinguishes the
deadline, version or guard failure and each rate/supply API or readback.
The original operation errno remains unchanged. A voltage-readback mismatch
still returns the original ERANGE; the diagnostic does not invent a hidden
regulator API errno that the old path did not preserve.

The eleven predicates retain their original order: nine HCI quiescence
conditions, reset output direction, then reset high. Short-circuit evaluation
is preserved. The original HCS mask's four bits are retained from that same
read, distinguishing device present, command ready, host error and device
error. Other register predicates report their boolean outcome, not a raw
register snapshot. An unevaluated predicate is `UNOBSERVED`, never `PASS`.
No diagnostic MMIO reread or extra hardware operation is added. The later
pre-link quiescence check and the stage-four supply call cannot overwrite the
stage-two evidence. No stage-two record diagnoses a previous consumed run.

The offline host decoder accepts this format only with explicit
`report_version=3`. Versions 1 and 2 retain their original field counts and
interpretation. It rejects invalid sites, impossible evaluation prefixes,
failed-but-unobserved conditions, inconsistent HCS bits and fixed errno
mismatches. Unknown, partial, unauthenticated and mixed-version reports do
not acquire a diagnostic claim or normal-return permission.

The existing 256-byte report collection and authenticated outer frame are
unchanged: even the unconstrained signed/unsigned 32-bit text maxima occupy
255 bytes for 23 fields. The guest's success-only return gate, the host's
successful-link settlement predicate, 120/300/540/15-second bounds and all
one-shot controls remain unchanged. The live candidate declarations still
select only their retained version 1/2 artifacts; no declaration selects v3.

## Validation

- The focused suite passed 17 tests, including actual host and static ARM64 C
  fixtures under QEMU user emulation. The fixture mechanically extracts the
  production stage, supply, rate and report functions and uses the actual HCI
  source and bounded C result reader before authenticated Python decoding.
  All 48 stage-two failure locations are exercised, including propagated
  API errors and the existing conversion of failed readback to ERANGE.
- A separate fixed-baseline comparison compiled the same fixture against
  the source at `3249adcaf1` and the changed source. All 105 cases on each
  architecture (210 comparisons total) retained the original 21 report fields
  and exact modeled MMIO-read, API-call and deadline-check traces. Inputs and
  original source hashes are retained with the comparison. This proves trace
  parity in the model, not identical physical scheduling or electrical state.
- Existing real HCI cold-link cases, partial/overflow reader cases, strict
  USB report decoding and failure/no-normal-return cases passed. Cross-version
  rejection, impossible diagnostics, authentication failure and the report
  size bound are covered without changing the signed frame or guest reader.
- Eleven actual host-collector loopback cases passed in addition to those
  seventeen tests. The new failure case sends the actual C formatter/reader
  output through the existing socket collector, sealed raw capture and
  rederivation: HCE is FAIL, later HCS is UNOBSERVED, and no Download intent or
  packet is created. The v3 positive case retains the full existing successful
  link/settlement predicates. These are modeled-device H0 tests, not connected
  device observations. One initial test setup failed because the new worktree
  lacked `workspace/private/tmp`; creating that scratch directory fixed setup
  without changing production assertions. Its failed log is preserved.
- The unchanged module builder compiled the changed sources against the
  retained ML035 kernel and an isolated Kbuild copy. `file` reports an ARM
  aarch64 relocatable module; the compile log is empty. The retained kernel,
  transport receipt, config and symbol inputs remain byte-identical. No new
  kernel Image or boot/AP package was needed for this H0 unit.
- ML033's retained v1 and ML034/ML035's retained v2 signed results and witnesses
  were reopened through their pins and authenticated. The old and new decoders
  returned identical facts; all three retained their failure/no-normal-return
  classification and were rejected as v3. This is a bounded compatibility
  replay, not a new complete audit of those physical sessions.
- The complete `start()` function, guest witness, guest result reader/return
  gate and USB-admission source are unchanged from the baseline. The compiled
  module's undefined imports also match ML035's module exactly.

Independent review returned **PASS_GO with no actionable findings**, scoped
only to this H0 diagnostic change. The reviewer independently reran the
seventeen core tests and inspected the fixed-baseline comparisons and actual
module/source receipt. The final collector tests and status-only documentation
are included in the final review addendum. Python compilation, local document
links and diff checks passed. No device-connected read, control, transfer,
module load or physical observation is part of this task.

Checklist applicability: ABI uses actual compiled C and ARM64 execution;
WIRE joins the real formatter/reader to the strict consumer; SEMANTIC preserves
errno and distinguishes unobserved conditions; ARTIFACT preserves consumed
source and kernel provenance; RETURN preserves both success-only gates and
the original recovery lane. New live ROUTE admission is deliberately absent.

Private evidence is under the isolated worktree's
`workspace/private/outputs/s22plus-stage2-diagnostics-h0-20261110-1/`.
The actual module build is in the distinct directory with that same basename
under the original checkout's private outputs. The private build wrapper
verifies the builder/readers are byte-identical, changes only the selected
module-source directory, and keeps all original input validations active.
No retained build directory is used as the output Kbuild tree.

## Deferred work

Normal Download after a proved pre-effect rejection and separation of
capability identity from candidate data are independent, unimplemented
[H0 improvement proposals](../plans/S22PLUS_MAINLINE_RETURN_AND_CAPABILITY_IMPROVEMENTS_H0_2026-11-10.md).
They are not prerequisites for this diagnostic unit, and no guard or witness
duration is relaxed here. Physical qualification and any future adoption
remain separate work; this result grants neither device authority nor UFS
functionality or automatic recovery proof.
