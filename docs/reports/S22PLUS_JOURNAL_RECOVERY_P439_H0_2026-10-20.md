# S22+ P439 journal recovery preparation

Preparation status: **PASS_GO / READY_CONNECTED_FIXED_D0**. The preparation
opened no grant, transfer or filesystem-write effect. The subsequent
[P439 physical run](S22PLUS_JOURNAL_RECOVERY_P439_RUN_2026-10-20.md) is now
consumed and closed healthy, with a negative complete-root comparison.
Target: `SM-S906N/g0q/S906NKSS7FYG8`; A90 and S20+ are outside this work.

## Bounded task

Prepare one fresh instance of the existing
[fixed journal recovery](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md)
after the closed P437 writer and P438 protected reader. Completion requires a
qualified fresh boot-only package, review of the current reachable capability,
and a concrete one-operation, 1800-second attended proposal. Execution still
requires the lane's returned grant, current target/health checks and usable
attended original-A recovery.

P438 authenticated the complete P437 early file but saw no runtime file in
the dirty home-block view: state 1, RECOVER 1, orphan head 0. This is a new
post-P437 journal state, not permission to replay consumed P434. The old
candidate, grant, evidence and RECOVERY_NOT_PROVED result remain unchanged.

## Selected behavior and expected limits

Retain the existing `post-autoboot-p432-v1` selection, strict replayer,
checker and two-file historical comparison. No writer, path class, mutable
exception or recovery behavior is added. The new candidate changes its fresh
identity; the current host closure receives a separate capability receipt.

The selected comparison excludes already observed P432 runtime and P437 early
files. Complete root admission is therefore expected to fail if those files
are present, even if replay and the read-only checker succeed. Preserve that
negative result. The policy explicitly requires separate retrieval and
qualification for files exposed by replay; do not delete files, widen the
comparison or retry the writer.

Writer settlement, restored partition RO, checker outcome, full comparison
and Android closure remain separate claims. A completely observed rejection
may take the existing normal return only after all cleanup conditions pass.
Uncertain I/O or child state requires the original attended physical recovery.
Original A does not undo native_data writes.

After healthy closure, a separate fixed P437-pair reader can retrieve any
newly visible runtime bytes. Those authenticated bytes and an exact new
history selection are prerequisites to qualifying the planned idle-policy
watchdog comparison. P439 alone cannot admit that writable experiment.

Private preparation and raw evidence are under
`workspace/private/outputs/s22plus-journal-recovery-p439-h0-20261020-1/`.

## Qualification and connected readiness

- Fresh `p439` / `v0.11.0-rc.0` boot-only A/B packages are byte-identical.
  Actual archive, Image, CPIO and live image-consumer checks passed.
- The physical and virtual helper ELFs differ from the prior qualified
  helpers only in the fresh run identity and GNU build ID. The exact selected
  generated headers/table, strict replayer and checker remain unchanged.
- Three fresh ARM64 VM cases passed: clean-root writer skip, committed replay
  with revoked/uncommitted blocks preserved, and an additional runtime file.
  In the last case the writer/checker complete, partition RO and unmount pass,
  and the full comparison correctly remains `RECOVERY_NOT_PROVED`.
- Nine retained ARM64 cases were rederived from their original pinned
  fixtures/raw evidence. Fourteen focused journal/task tests and touched
  Python compilation passed.
- Independent review returned `PASS_GO`, no findings, covering 139 current
  host sources and 169 runtime sources, actual artifacts, source/evidence
  reuse, settled-negative return, finite authority and original-A recovery.
  The prospective P439 receipt leaves all historical reviews unchanged.
- Exact rollback bytes and retained recovery provenance passed. Fresh fixed
  D0 preparation proved rooted original-A health in both brackets, exact
  partition hashes, Android32 GPT/capacity and current target binding.
  Raw-derived preparation and the actual live task validator both passed.

The concrete proposal is one `journal-recovery` operation, 1800 original
BOOTTIME seconds, attended, with one N and at most one original A shared by
normal return and recovery. No grant is open and no F1 owner exists.
Current physical attendance/Download availability and the exact returned
proposal remain required by the selected lane's “One attended operation”
clause. Preparation did not inspect native_data or establish its current
cleanliness. The prior P438 dirty observation remains the latest such evidence.

All 46 preexisting changed paths are preserved. The shared candidate catalog
adds only P439; removing that row reproduces its previous bytes. The active
goal condenses completed P420 history into links to its retained full reports.
A90 and S20+ were untouched.
