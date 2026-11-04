# ML024: let SSH use the time remaining after validation

Status: **H0 QUALIFIED / INDEPENDENT PASS_GO; PHYSICAL RUN CONSUMED /
NO_PROOF / ANDROID_CLOSED_HEALTHY**.
The [run report](S22PLUS_MAINLINE_ML024_RUN_2026-11-04.md) records USB-window
expiry before any SSH attempt, completed original-A recovery and proof limits.
The preparation evidence below retains its original scope.

## Selected unit and correction

[ML023](S22PLUS_MAINLINE_ML023_RUN_2026-11-04.md) obtained live packaged Debian
PID1/USB and sshd readiness but stopped before spawning the SSH client. Its
intent selected a twenty-second timeout with 22.502 seconds left before the
acquisition deadline. The complete raw pre-spawn phase took 3.558 seconds.
The retained exception type does not identify the exact original guard cause;
the offline timing reproduction nevertheless exposes an ordering defect.

The old callback required the complete precomputed timeout still to fit after
the full guard and executable check. That rejected useful remaining time.
When the initial timeout was below twenty seconds, it left only the calculation's
0.1-second margin for validation. ML024 removes that stale fit predicate.
It preserves the semantic guard and executable hash at the same position.

The existing raw producer already checks the absolute `CLOCK_BOOTTIME` deadline
after the callback, before `Popen`, throughout acquisition and after process
exit. It clips waiting to the earlier of the monotonic timeout and the absolute
deadline. The intent's timeout is a ceiling computed at intent time; validation
may reduce the actual available runtime. No raw API, schema, evidence consumer,
package, daemon configuration, wire format or recovery behavior changes.

The original observation window and its four-second settlement allowance stay
unchanged. The allowance is not a hard real-time cleanup guarantee: termination,
reaping and durable writes can be delayed. Late capture completion cannot pass
the existing original-window check. The time check and process creation are not
atomic, and this makes no remote-child cancellation or automatic recovery claim.
The existing post-SSH endpoint census follows that completion timestamp.

There is no additional arbitrary minimum-duration gate. A very short remaining
budget may produce a failed one-shot attempt; the absolute bound and original
stopped owner still apply. ML023 remains consumed and cannot be replayed.
The prospective ML024 candidate retains the functional kernel/config/DT/PHY
and packaged Debian SSH workload, with fresh candidate/key/retained-marker
identity and exact qualification before any new finite attended approval.

## Focused validation

The unchanged old implementation fails the new timing regression. With the
correction, the focused SSH/raw-producer/mainline-owner/terminal suite reports
**64 tests OK**, including actual local subprocess acquisition and offline proof.
An independent clean run of the current SSH/raw subset passes **28 tests**.
The broader log contains an unchanged readiness-fixture background traceback:
its settle helper can return when `result.json` appears, before the writer's
final pin/lstat, and temporary-directory deletion can then race that writer.
The reviewer reproduced this fixture race separately. Production readiness
does not perform that fixture deletion, and `capture_ssh` is not on the path.
The original log alone does not distinguish the exact fixture deletion source;
the traceback is retained rather than called a clean full-suite result.

- a 3.558-second modeled second-guard delay in a 26.502-second window permits
  successful capture and offline rederivation while retaining a twenty-second
  ceiling; endpoint tampering still rejects;
- a shorter initial budget survives validation longer than its old 0.1-second
  margin;
- an expired callback never starts a child and durably preserves failure;
- a semantic guard failure still prevents spawning;
- a child that ignores SIGTERM is killed and reaped at the clipped acquisition
  deadline, with partial raw output and timeout preserved; another call cannot
  spawn again;
- existing suspend/clock-jump, late zero-exit, output-bound, single-invocation,
  base-proof preservation and original-A recovery cases retain their checks.

Touched Python compiles. Both fresh ARM64 observer binaries reproduce exactly.
The new Image/loader passes twenty loader cases, three actual exception-level
boots, 342 marker cases and six actual exception-level marker runs. Repeated
boot-only AP packages match. The exact kernel/package closure passes live VM
base/SSH authentication, wrong HMAC and all six constrained SSH cases, followed
by complete raw rederivation. Five honestly repinned CPIO mutations reject.
The functional config/DT/PHY are identical to ML023; candidate and SSH keys
are fresh. Exact signed 22-package/27-ELF closure and Image/DTB/initramfs/AP
joins remain separate from source-review qualification.

The raw producer is unchanged. The timing fixtures
advance `CLOCK_BOOTTIME` without waiting through the modeled validation delay;
they prove the ordering and producer/consumer behavior, not measured physical
SSH latency or ML023's exact original exception message.

Past-failure checklist application: HOST/SEMANTIC concern the precomputed
timeout and effect-time guard; WIRE/PERSIST/ROUTE concern real raw publication,
offline rederivation and no replay; ARTIFACT/AUDIT preserve consumed provenance
and qualify a fresh candidate. No display, UFS, installed root, authority or
automatic recovery feature is added. Further historical retention/watchdog
attribution is outside this useful SSH unit.

## Review and preparation

Two advisory critique/challenge rounds with Claude Opus 5.5 High and Gemini 4
Argon High are complete. Both support the minimal correction using the existing
absolute deadline and identify no remaining blocker in their supplied evidence.
The challenge corrected initial overclaims about exact original cause, atomic
spawn prevention and guaranteed four-second cleanup. Claude withdrew its
optional arbitrary duration floor. These discussions do not substitute for
the independent source/artifact review or actual local verification.

The final independent review is **PASS_GO**, with no findings, against 95
public source pins and 354 artifact/raw evidence pins. It rederived exact
package/CPIO/key/observer/Image/DTB/loader/AP joins, complete VM proof and the
full kernel-tree comparison, whose only difference is fresh V1 `head.S` data.
The isolated actual image/task/current-terminal consumers passed with raw,
subprocess, socket, readiness, grant and start acquisition blocked, zero
acquisition calls, and missing human approval rejected.

The reviewed capability and backend V30 receipts are now published. The two
stable worker inputs remain unchanged, and the connected worker reports V30.
Actual production image/task/terminal preparation passes against ML023's
closed healthy predecessor. Eight honestly rebound mode, identity,
qualification and SSH-proof mutations reject through the real image consumer.
Existing consumed receipts, approvals, journals, artifacts and raw evidence
retain their original identities. The policy's named review path and profile
selector move together to the new receipt; that reference-target change is
included in the independent review.

One fixed preapproval D0 completed. All seven Android health raw captures
rederive with successful producer status and empty stderr, establishing the
current exact target, original-A identity and healthy Android state. No grant,
candidate control, partition transfer or attendance assertion was created.
The actual generated task subsequently received its exact one-operation,
1800-second approval and explicit attendance/usable Download confirmation.
Health was refreshed before opening the grant because its earlier readiness
was close to expiry. The repeated ML023 approval was not used for ML024.
Source freezes, unchanged initial unrelated files, local links, private-value
exclusion, goal length and scoped diff checks complete the preparation commit.

Private preparation, discussion and validation evidence is under
`workspace/private/outputs/s22plus-mainline-ml024-ssh-budget-h0-20261104-1/`.
ML024 is now consumed and no successor task is armed. A90 and S20+ are
untouched and unrelated dirty work is preserved.

## External-model accounting

All four calls completed without inference retries, fallback or tool actions.
Private before/after snapshots and token records are appended to the usage
ledger. Claude reported 4 uncached input tokens, 14,545 cache-creation tokens
and 14,720 output tokens, including 8,276 thinking tokens. Its reported
list-price equivalent is USD 0.410776, not actual subscription billing.
Five-hour account usage snapshots moved from 5% to 7%; these account-wide
readings do not measure exact usage by these calls.

Argon reported 35,762 input and 15,890 output tokens, including 10,923 thinking
tokens, for 51,652 total. Fresh-process weekly remaining snapshots were 85.99%,
85.11% and 83.98%. Its CLI updated from 1.4.12 to 1.5.0 between the two calls;
both results retain their actual command/init/usage evidence and completed
normally. Actual subscription charges were unavailable. Quota movement,
per-call tokens and price equivalents remain separate.
