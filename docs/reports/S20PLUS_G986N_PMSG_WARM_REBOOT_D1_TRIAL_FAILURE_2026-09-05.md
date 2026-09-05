# S20+ PMSG warm-reboot marker D1: V1 trial failure and root cause

Date: 2026-09-05. Target: `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`.
Status: **V1 TRIAL FAILED BEFORE ANY MARKER BYTE AND IS CLOSED NO_PROOF HEALTHY;
HOST SCRIPT DEFECT PROVEN; V2 CORRECTED AFTER BLOCKING REVIEW AND DORMANT**.
Device reboots, mode transitions, partition operations and
S22+/A90/other-target commands in this trial: **0**.

## What ran

The reviewed capability was activated by flipping only the runner's `ACTIVE`
boolean and the target section status. The resulting source SHA-256
`5da0ff52ed719c3c3de6f67242b28c3f71f3028f991befe460cfbb16e8d507e5` is the exact
value the final independent review had pre-approved for activation, and the
normalized SHA-256 stayed `8605430e64f8aa33c7535e3707a7ca50461c29df39867bc40b3b297afb3acf33`
as pinned in the target section. The focused suites passed 21/21 and 18/18 and
the repository boundary check was clean before the one `--connected` invocation.

The invocation reached the root marker writer and stopped there:

| Fact | Value |
|---|---|
| verdict | `PMSG_TRIAL_HEALTH_PENDING_NO_REPLAY` |
| failure class | `RootHealthD0Error`, writer exit `65` |
| marker intent | consumed |
| marker bytes written | none |
| reboot intent | not consumed |
| host / selected-target / inventory / root commands | 7 / 5 / 2 / 2 |
| S22+ / A90 / other-target commands | 0 / 0 / 0 |
| replay permitted | false |

Exit `65` is the writer's PMSG descriptor stage. Every `exit 64` predicate ahead
of it passed, so the trial positively established root in the Magisk domain,
Magisk 30.7/30700, enforcing SELinux, stock `/system/bin/init` PID 1, the exact
model/device/name/incremental, completed boot and the bound boot digest. The
device stayed on its source boot throughout.

## Root cause

The failing predicate is the descriptor-pin verification in `write_script`:

```sh
exec 3< /dev/pmsg0
[ -c /proc/self/fd/3 ] || exit 65                                    # passed
[ "$(stat -Lc '%t:%T:%h' /proc/self/fd/3)" = 'fc:0:1' ] || exit 65   # failed
```

The bounded capture retained only digests, so the 51-byte stderr was identified
by exhaustive candidate hashing against
`594416db8548e86b6740d69ca457c061a58b0936fa60039e631140d71e488a51`. The single
match is:

```
stat: '/proc/self/fd/3': No such file or directory
```

`[ -c … ]` is a shell builtin and sees the shell's own descriptor table, so it
passes. `stat` is a separate process, and `/proc/self` there names *`stat`*.
The root script is dispatched as `su -c <script>`, which runs it under Android's
`/system/bin/sh` — MirBSD KSH. mksh follows ksh semantics and marks descriptors
above 2 opened by `exec` close-on-exec, so the pinned descriptor is gone by the
time the helper is exec'd. The check can never pass on this target.

This was reproduced offline, without device contact, by running the target's own
shell binary from the retained stock IYC2 ramdisk extract under `qemu-aarch64`:

```
# shell identity
@(#)MIRBSD KSH R57 2019/03/01 Android

# V1 shape: external stat via /proc/self/fd/N   -> exit 65
stderr bytes: 51
stderr sha256: 594416db8548e86b6740d69ca457c061a58b0936fa60039e631140d71e488a51

# V2 shape: external stat via /proc/$$/fd/N     -> V2_DESCRIPTOR_PIN_VERIFIED
```

The reproduced stderr is byte-identical to the device's, so the cause is proven
rather than inferred.

## Why the existing tests did not catch it

The V1 suite's producer fixtures run the generated script through the **host**
shell. The same reproduction shows `dash` and `bash` both returning `1:5:1` for
an external `stat` on `/proc/self/fd/3`: they do not set close-on-exec on
`exec`-opened descriptors, so the host models the check as passing. The 21/21
result was accurate about the host and silent about the target. A hostile suite
that never executes the device's shell cannot constrain device shell semantics.

## What is consumed

The marker intent was published before dispatch, so by the target section's
own rule the marker action is consumed even though no marker byte reached
`/dev/pmsg0`. The fixed trial directory is globally non-reusable and this
transaction cannot be retried under V1. No reboot, mode transition, flashing,
partition access, pstore mutation or configuration change occurred, and the
device was left healthy on its source boot.

The fixed read-only `--resume` then closed the trial with one current health
observation and no write, reboot or wait. It published
`NO_PROOF_PMSG_TRIAL_HEALTHY` with `healthy` true, `marker_match` false,
`ordinary_reboot_attributed` false, `first_return_continuity` true, no
observation gap, one root command, zero S22+/A90/other-target commands, and
released the shared routine-actions guard. The observed boot equals the bound
source boot, as expected for a trial that never rebooted.

The closure had to run before any edit to the runner's `ACTIVE` boolean or the
target section status line, because `require_active()` re-checks both and
editing either first would have stranded the guard.

## V2

Keep the pin, change how it is verified. `/proc/$$` names the shell's own
descriptor table rather than the helper's, and close-on-exec does not remove
the descriptor from the shell — only from processes it exec's. Replacing
`/proc/self/fd/N` with `/proc/$$/fd/N` in the *external* checks restores the
verification without weakening it:

- the pathname is still never opened with create or truncate;
- the character type, `rdev` and link count are still confirmed before the
  write descriptor is derived;
- the write open `exec 4> /proc/$$/fd/3` still re-derives from the pinned
  descriptor, and is performed by the shell itself;
- the same predicates then confirm descriptor 4 before the marker `printf`.

The reader needed the same treatment for its `/proc/self/fd/3` metadata
comparison, and got it.

V2 is implemented in the same owner file and is dormant. It changes the version
to `s20plus-g986n-pmsg-warm-reboot-d1-v2`, moves the fixed trial to
`workspace/private/runs/s20plus-g986n-pmsg-warm-reboot-d1-v2/`, and rewrites the
external descriptor references in both generated scripts. Nothing else in the
journal model, bounds, privacy rules or entry points changed.

| Identity | Value |
|---|---|
| dormant source SHA-256 | `f6c8f8faee6f9a4724d74060f1bb2385bc9a936d0b4e7dc86f118480a3df206a` |
| normalized SHA-256 | `d51eb1b6f51adc0739b9e17053b52bbab8ca2e39d211921ebd204c02ba21c52b` |

The reader carried the same defect and would also have failed at exit `65` even
if the marker had been written, so V1 could not have produced a positive result
by any route.

A new suite, `tests/test_s20plus_g986n_pmsg_device_shell_semantics.py`, closes
the frame error. Four shape guards always run: no generated script addresses a
descriptor through `/proc/self`, no helper in this runner's own generated bytes
resolves through `PATH`, the pin precedes the write, and the probe shares the
writer's pin while writing nothing. Six fixture tests execute the complete
generated scripts through the target's own shell under qemu, including the
reader. One asserts that reverting to `/proc/self` fails there with exit `65`,
and one records that the host shell accepts both shapes and therefore
constrains nothing.

## Independent review and the blocking findings it closed

Independent adversarial review (Codex Luna, reasoning effort max, read-only
sandbox) judged eight claims. Root cause, fix correctness, completeness,
consumed-state accuracy and activation safety were confirmed; the write path
and the test fidelity were refuted, and the verdict was BLOCKING FINDINGS.
Its proportionality answer agreed that the shared root-health bytes must stay
unchanged for now. Two of its citations were over-broad and are corrected
below. Everything it blocked is closed in this unit.

**Write path (blocking).** `exec 4>` is a fresh write-mode open through procfs,
not reuse of the original open file description, and V1 proved only that the
read-only open succeeded. Because the marker intent was published before the
writer ran, a driver or procfs incompatibility would have consumed a second
marker action for nothing. V2 now runs one fixed write-path probe first: same
sysfs gates, same pin, `exec 4>` from the pinned descriptor, descriptor-4
verification, both closed, receipt `S20PMSG_PROBE_V1;returned=1;writable=1`,
and no byte written. `validate_trial` makes `probe-result` a prerequisite of
`marker-intent`, so no marker action can be consumed without that proof. The
marker write also gained an explicit failure exit so a write error cannot
precede a receipt.

**Test fidelity (blocking).** The dynamic tests no longer slice the script at
`exec 3<`: they execute the complete generated probe, writer and reader —
`set -eu` prelude and shared health guard included — through the target's own
mksh and toybox binaries under qemu, reusing the V1 suite's fixture for the
device-only inputs. The reader is now dynamically executed across exact,
duplicate, substring and missing records. Two shape guards and a new
PATH-resolution guard run unconditionally, so a clone without the private
extract still fails an exact `/proc/self` reversion.

**PATH resolution.** The review listed `printf`, `head`, `grep` and `wc` as
PATH-resolved. Only `printf` was: `head`, `grep`, `wc`, `stat` and `cat` were
already absolute. Every `printf` this runner generates is now
`/system/bin/printf`. The two remaining bare `printf` calls live in the shared
`health.ROOT_READ_SCRIPT`, whose pinned bytes are deliberately unchanged under
the proportionality finding and are recorded in the target contract.

**Documentation.** The contract's "no pstore operation occurred" was
over-broad; the readiness preflight does perform its declared bounded pstore
metadata reads. That sentence now says so.

Activation still requires a fresh independent review of this corrected V2 and a
fresh current operator request. V2 inherits no authority from V1's consumed
trial.

One observation left unchanged: the shared `health.ROOT_READ_SCRIPT` reads
`/proc/self/attr/current` through an external `cat`, which reports that
helper's context rather than the shell's. On this target no domain transition
occurs, so it reported `u:r:magisk:s0` correctly and the V1 trial's identity
predicates passed. It is shared with the root-health D0 lane and was not
touched by this unit.

## Evidence

Private reproduction harness and captures:
`workspace/private/work/s20plus-pmsg-v1-trial-failure-h0-20260905-mk57fd3/`.
Trial journal: `workspace/private/runs/s20plus-g986n-pmsg-warm-reboot-d1/trial/`
(`binding.json`, `marker-intent.json`, `failure.json`).
No firmware, raw device logs or identifiers are included in this commit.
