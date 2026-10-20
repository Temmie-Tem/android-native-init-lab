# S22+ P441: watchdog observations; no external access; Android healthy

Status: **CONSUMED; ANDROID_CLOSED_HEALTHY**.
The live-access terminal is **NO_PROOF**. Separate post-return evidence proves
installed Debian PID1 and partial rcS progress, with nine authenticated
watchdog observations. It proves neither completed rcS/services/SSH nor a clean
native shutdown or the cause of the watchdog failure.

The [later H0 analysis](S22PLUS_P441_WATCHDOG_FOLLOWUP_H0_2026-10-20.md) preserves
that strict result and authenticates an intact frame within the rejected line
in a separate forensic view: five TASK/WCHAN pairs. It also refines CPU time
as Linux-accounted runtime and records the unchecked pet-return limitation.

Only the operator-owned S22+ FYG8 was selected. A90 and S20+ received no command.
The [qualification](S22PLUS_AUTOBOOT_WATCHDOG_P441_H0_2026-10-20.md) and
[design](S22PLUS_AUTOBOOT_WATCHDOG_P441_DESIGN_2026-10-20.md) retain their scope.

## One approved operation and complete recovery

The operator returned the prepared exact attended 3600-second/one-operation
grant. Current source/artifact/recovery checks and fresh Android health passed.
One boot-only N transfer selected `cpuidle.off=1`, the bounded watchdog observer
and the exact P440-authenticated history. No N retry occurred.

The original 360-second observation window produced no matching NCM endpoint,
SSH evidence or health. The owner recorded `automatic observation window
expired`, returned `AWAITING_ATTENDED_RECOVERY` and retained ownership with
device activity UNKNOWN. The recorded stop follows N completion by 363.473
seconds; it does not establish a device-side stop at that time.

After the operator physically entered Download, the same owner performed one
original-A transfer and complete changed-boot Android32 health. Boot/root,
supporting partitions, GPT and reported capacity of 34,357,624,832 bytes passed.
No recovery read failed and no health-only continuation or additional transfer
was needed. Original A does not undo native_data writes or prove its consistency.

The H0 close rederived all 694 raw captures, both original transfers, initial
and final health, the candidate claim and the unchanged 14-row journal and
terminal, with process/device acquisition blocked. The one operation and grant
are closed; no F1 owner remains. Execution sources are preserved as 139 host
files plus their capability and 147 runtime files from the qualified working
tree at implementation commit `4cb3a3e0aba171b05f18cd74a44cf3757698843e`.

| Canonical event | Seconds from grant opening |
| --- | ---: |
| Live session start | 0.000 |
| Android Download request | 100.121 |
| Candidate flash start | 131.038 |
| Candidate flash done | 135.696 |
| Candidate boot ready / external health | Not proved |
| Rollback flash start | 540.910 |
| Rollback flash done | 542.301 |
| Rollback boot ready | 591.225 |
| Live session end / durable task close | 610.566 |

## First boot: admitted root and watchdog observations

The fixed post-closure D0 completed all 16 captures, including one bounded
2,097,136-byte `last_kmsg` read between health brackets on the same returned
Android boot. It made no device mutation. Reopening the raw capture reproduces
141 authenticated transition records, zero conflicts and one rejected
malformed frame. The 142 literal marker occurrences are not 142 proofs.

The first candidate boot contains 158 authenticated preparation records and
four diagnostic records. Preparation reaches `STORAGE_READY`. Its file worker
returns successfully from file/parent/root close, unmount, RO restoration,
clean-superblock/GPT checks and RAM receipt publication. The supervisor reports
successful settlement. The automatic entry records complete protected checks,
the admitted root, its writable activation and RAM witness; the installed hook
authenticates actual Debian PID1 at 6.508 seconds and runtime-file creation.
These are same-boot execution facts, not a later native_data readback.

The rcS fork, checked fork-record persistence, child descriptor cleanup,
exec attempt, first parent wait and first 10 ms sleep return are authenticated.
There is no authenticated rcS completion, successful child exec/reap, service
completion or runlevel-parent record. An exec-attempt marker is not exec proof;
the last progress record does not locate a stall.

Five watchdog task samples and four wait-symbol samples survive. They share
one authenticated task identity. The scheduling policy is FIFO and RT priority
99 in every task sample; the observations are not atomic.

| Acquisition BOOTTIME | Task state | CPU time ticks | Last CPU | Wait-symbol class |
| --- | --- | ---: | ---: | --- |
| 6.539 s | S | 0 | 2 | `qcom_wdt_kthread` |
| 9.006 s | S | 0 | 2 | `qcom_wdt_kthread` |
| 10.003 s | S | 0 | 2 | `qcom_wdt_kthread` |
| 11.009 s | R | 80 | 7 | zero/running/unavailable/hidden |
| 12.006 s | R | 179 | 7 | No authenticated sample |

`R` means running or runnable; the increasing CPU counter establishes consumed
CPU time between samples. It does not identify a loop, timer/IPI/SMC phase,
watchdog renewal or a failed CPU. Zero wchan does not identify an instruction.
The producer's bounded reads may perturb timing. Complete surviving records
report no prior logging error/loss, but the malformed frame and missing later
records prevent a complete-log claim.

## Reset context and distinct second boot

Both kernel spans contain the actual `cpuidle.off=1` command line and the
cpuidle driver registration rejection. The first span contains gh-watchdog
RT throttling at 11.984759 seconds, followed by a warm-reset firmware span
whose diagnostic is `TZBSP_ERR_FATAL_NON_SECURE_WDT`, then a second candidate
kernel boot. These kernel/firmware lines are retained context, not MAC records.
Unlike P437, this capture has no explicit bark/bite timestamp; none is inferred.

The second boot has a distinct authenticated identity, 156 preparation records
ending at `ufs_qcom` BEGIN, one diagnostic START and no authenticated transition
records. Its missing return does not prove an internal UFS stall. Its writes,
safe rejection, shutdown and native_data consistency remain unproved. The two
boots do not represent two host N transfers.

The selected cpuidle setting therefore did not resolve this bounded startup
failure. The new evidence narrows the watchdog lead to a task that wakes and
consumes CPU before reset; it does not establish the missed-renewal cause or
eliminate every idle-related hypothesis. No further device effect or storage
retrieval is authorized by this consumed grant.

## Checklist and evidence

The [11-item checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md) was
rechecked against the actual path. ABI/ARTIFACT now include the live command
line; IO/WIRE preserve nine valid watchdog observations and reject the malformed
frame; SEMANTIC/AUDIT separate boot identities, authenticated progress, reset
context and absent external proof. PERSIST/ROUTE include reopened source/raw/
journal/terminal/close records, while current native_data consistency stays
unknown. HOST/RETURN have exact original-A and final Android health; DISPLAY
remains inapplicable. No new gate or replay authority is introduced.

Private evidence is under
`workspace/private/outputs/s22plus-autoboot-watchdog-p441-h0-20261020-1/`:
the operation journal/raw captures and task close under `connected-prepared-1/`,
`source-snapshot/`, the fixed `retention-1/` capture and original projection,
and `retention-audit.json`. The H0 audit reruns the strict projection and
separates both authenticated boot epochs without acquisition or original-file
mutation. Its initial literal-count assumption was rejected and preserved;
the correction compares decoded records while retaining the malformed input.
