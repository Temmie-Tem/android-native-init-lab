# S22+ P450: fixed journal recovery preparation after P449

Status: **PASS_GO; approval returned; HOST_PREGRANT_BLOCKED; no device effect**.
Only `SM-S906N/g0q/S906NKSS7FYG8` is selected.

The operator selected fixed journal recovery followed by a separate read of
P448's early/runtime pair. The closed
[P449 reader](S22PLUS_AUTOBOOT_EVIDENCE_P449_RUN_2026-10-21.md)
authenticated the complete first-boot early file but found runtime absent in
a dirty checkpointed home-block view: state 1, RECOVER 1, orphan 0. Those
fields do not prove complete writer eligibility or non-execution of runtime.

P450 is a fresh instance of the existing
[strict journal-recovery profile](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md).
Retain the pathless internal-JBD2 replayer, checker,
`post-autoboot-p432-v1` comparison selection, bounded owner, partition RO
restoration and original-A recovery. Change only the fresh candidate identity
and current capability selection; add no general repair, deletion, wildcard
history admission, installed execution or uncertain-effect retry.

The existing comparison table intentionally does not admit the later P432
runtime, P437/P441 pairs, P445 early file or P448 pair. Complete root comparison
is therefore expected to remain negative. Successful replay, read-only checker,
protected cleanup, full root admission and Android health are separate facts.
Later file retrieval and qualification must precede any new history admission.
No absent P448 runtime bytes are fabricated or included in this table.

The bounded preparation unit completes actual A/B package and consumer checks,
representative ARM64 cases, relevant unchanged-evidence reuse, focused checks,
independent source-bound review and fixed connected D0 preparation. The
concrete one-operation/1800-second attended proposal is prepared before asking
for its exact returned grant. The consumed P449 read approval cannot authorize
this distinct persistent-write operation.

Execution freshly checks exact partition identity/checksum/features, journal
bounds, zero error state and the selected eligibility rules. Original A restores
Android boot and health; it cannot undo partial native_data writes. A writer or
transfer uncertainty never permits replay. After healthy closure, a separate
fixed reader will determine whether the P448 runtime file becomes visible.

The separate [P451 reader](S22PLUS_AUTOBOOT_EVIDENCE_P451_H0_2026-10-21.md)
is prepared alongside P450 so their host capability selectors can be frozen
and reviewed together. Each operation retains its own one-operation/1800-second
attended task and returned grant. P451 begins only after P450's healthy closure
and fresh exact machine checks; preparing it does not predict recovery success.

Past-failure applicability: ARTIFACT/ROUTE require the actual A/B archive and
task to reopen; SEMANTIC/WIRE distinguish settled strict replay, checker and
comparison results, including expected extra-file rejection; IO/PERSIST/RETURN
retain bounded child settlement, raw-first evidence, original journal and one
A return. ABI/HOST/DISPLAY introduce no changed runtime mechanism. AUDIT binds
the current source and retained failure corpus without repinning consumed runs.

Private evidence:
`workspace/private/outputs/s22plus-journal-recovery-p450-h0-20261021-1/`.
No Opus call has been needed for this unchanged machinery. Any later external
model use requires the requested before/after usage and actual-token accounting.
A90 and S20+ are outside this work.

## Qualification

Fresh physical and virtual A/B helpers and complete boot-only packages pass.
The actual image consumer validates the archive, Image/CPIO and execution
binding. `file` identifies a statically linked AArch64 helper. Of the 169
runtime source keys, 168 are byte-identical to P443; the shared automatic-boot
profile contains later features. The selected old journal binding, comparison
table and inspection header remain byte-identical to P443. No later history
selection is enabled by those added features.

Three fresh ARM64 cases pass: clean-root writer skip, committed replay with
revoked/uncommitted data preserved, and rejection of an unadmitted runtime
file after settled replay/checker completion. Eight journal and six shared
task tests pass, with touched-Python compilation. Independent review is
**PASS_GO / V3_REACHABLE_CAPABILITY**, findings empty, against the same frozen
140-host-source closure used by P451 and this candidate's 169 runtime sources.
It rederives nine retained cases, seven scope negatives and the existing
settled-negative/no-replay owner behavior. Actual package/builder/CPIO checks
confirm the selected legacy path cannot enter newer history selections.

Fresh fixed foreground Android D0 completed 17 successful bounded captures.
Same-boot original-A root-health brackets, shell-v2, exact GPT and Android32
capacity pass. Current host/lane/holders, original-A/recovery binding and no
F1 owner pass; the actual task/proposal reopen. The host capability and runtime
sources were preserved before these reads. No mode change, image transfer,
native_data access or grant opening occurred.

The proposal permits only one attended journal-recovery operation within 1800
original BOOTTIME seconds, with one N and one original A. Its exact returned
approval is recorded below; the grant still requires successful host preflight.
No P451 approval extends this budget or supplies replay authority after a
P450 uncertainty.

## Approved start blocked before device access

The operator returned both exact one-operation/1800-second attended approval
strings. The unchanged P450/P451 task, capability, artifacts and frozen source
snapshots revalidated, with no F1 owner. P450's grant opener then stopped in
its host-only tty-holder census: `pkcheck` succeeded, but `pkexec` returned 127
with `pkexec must be setuid root`. The binary is root-owned mode 4755; the
current command process has `NoNewPrivs=1`, which prevents its privilege gain.

No grant or operation exists and no device command was issued. Preserve this
as a host preflight failure, not a device-session failure or consumed candidate.
The six raw files were retained byte-for-byte in the private task's
`grant-host-preflight-failed-1` directory, with immutable relocation intent,
source/destination hashes and successful raw-receipt reopening. No check,
installed file, capability, approval, task or runtime source was changed.
P451 remains unopened until P450 completes and closes healthy.

A private operator-terminal entry point calls the original grant opener and
reviewed CLI with the returned approval. It stops before any attempt if its
process still has `NoNewPrivs`, or if a grant, operation or new preflight attempt
already exists. Its syntax and current-environment refusal were checked; that
refusal is not a successful host census or physical qualification. The current
agent environment cannot execute the required privileged census.
