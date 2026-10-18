# P437 host transfer guard and failure records

Scope: S22+ FYG8, H0 correction of duplicate transfer qualification and private
failure diagnostics. The completion criterion is a reviewed prospective
one-boot proposal using the existing P437 image and verification evidence.
No Debian payload, kernel, root admission, device deadline or recovery rule is
changed. A90 and S20+ are outside this work.

## Correction

The [first P437 attempt](S22PLUS_P437_PRETRANSFER_STOP_2026-10-19.md) remains
consumed and `ANDROID_CLOSED_HEALTHY`, with N=0/A=1. The original type-only
exception cannot establish its exact failing predicate. Its separate H0
investigation demonstrated four complete image qualifications inside a
10-second endpoint window.

The protected-root validator already runs the complete autoboot image
qualification. The general task validator now omits only that identical
second autoboot call; other profiles retain their additional checks. The
arrival observer retains its full guard. Inside the synchronous ticket
revalidation, each observer still checks the pinned Odin path and constructs
the measured USB observer, while complete guards remain before that primitive,
at durable intent and before dispatch. The original 10-second window, endpoint
identity/generation comparison, source/authority/artifact checks, boot-only
archive verification and no-replay rules remain in force. The inherited gap
between ticket observation and dispatch is not continuous endpoint proof.

A transfer exception now saves its type, bounded message and traceback,
current stage, start/failure times, total/stage elapsed time, module-load source
receipt and task receipt under the existing private attempt directory before
owner classification. The stop journal links that record and retains a bounded
message. Diagnostic publication failure preserves the original exception;
cleanup/result-publication failure cannot make the attempted effect replayable.

## Validation and reuse

Touched Python compiles. The 43 focused tests cover task/image qualification,
real boot-only subprocess/raw reconstruction, transfer ordering, the unchanged
deadline, changed-input rejection before dispatch, diagnostic publication
failure, cleanup failure, original recovery and no replay.

Six saved-package integration cases passed: unchanged inputs reach only an H0
would-dispatch marker; changed qualification, key, runtime scope, review and
endpoint generation stop before it. The real task guard took approximately
3 seconds per pass, outside the ticket window. The real endpoint consumer
invoked its observer twice with zero full guards inside that window. Its
sub-millisecond saved-observation timing is not a physical USB measurement.

The P437 A/B image, 146 runtime-source identities and 41 actual ARM64 cases
retain their original provenance. No changed host file is in the runtime
closure. Re-reading their qualification is validation reuse, not a new VM run
or new physical proof. The prior consumed task, review, grant and journal are
preserved. The still-unclaimed candidate may be selected by a fresh task only
after the reviewed host correction and current binding checks.

Private evidence is under
`workspace/private/outputs/s22plus-p437-transfer-guard-h0-20261019-1/`, including
`source-snapshot-1.json`, `host-source-snapshot-1/manifest.json`,
`focused-tests.json`, the guard integration and the independent review.
The integration substitutes saved USB observations and a no-dispatch producer;
it must not be reported as physical USB timing or a successful device boot.

## Independent review and prospective use

Independent review returned **PASS_GO**, with no findings, for the exact
139-file host closure and the unchanged 146-file runtime closure. It also
checked diagnostic bounds, private file permissions, source retention and
original-error preservation. The incident's scoped source/H0/review condition
is satisfied for this closure. The new capability record is
`s22plus_debian_autoboot_p437_transfer_review.json`; the old P437 review is
unchanged. This qualifies the host correction and reuses the existing payload;
it grants no device action and reopens no consumed operation.

The same six integration cases subsequently passed with the real new
capability consumer (`integration-reviewed-1/result.json`). No approval-check
substitution remains in that run. The saved endpoint/physical I/O substitutions
remain explicit, and no USB command or transfer was performed by the test.

Fresh fixed foreground Android D0 preparation then passed: same-boot rooted
original-A health brackets, shell-v2, complete GPT metadata and Android32
statfs at 34,357,624,832 bytes. The existing preparation consumer revalidated
the original-A artifact, recovery provenance, host bindings and unclaimed
candidate. It observed no native filesystem, changed no mode and transferred
no image. No F1 owner or new grant exists.

The concrete new proposal is `ready-1/task/proposal.json`, one attended
operation in 3600 seconds, with task SHA-256
`3a8bc6565a6f6664ba958923e29442b64b2ae2bebc33f05ad0f0c5f1859b32c6`.
Execution still requires that exact returned grant, actual attendance, usable
physical Download/original-A recovery and fresh machine validation. The old
consumed P437 grant remains closed. This bounded preparation is complete;
physical rcS/services/SSH remain unproved.
