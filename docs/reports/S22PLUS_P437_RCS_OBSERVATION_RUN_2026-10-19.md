# P437 physical rcS observation and healthy Android return

The fresh attended P437 operation completed one candidate N transfer and one
original-A transfer, then closed **ANDROID_CLOSED_HEALTHY**. The corrected host
transfer path passed on the physical S22+ FYG8. No qualified NCM endpoint or SSH
proof arrived within the original 360-second observation window; the live
terminal remains **NO_PROOF** for the composed Debian/SSH objective.

A separate, authorized same-returned-boot retained-log D0 authenticated **132
transition records from all seven actors**, with no rejected records or
contradictions. They prove installed Debian PID1 and progress through the rcS
fork, checked fork record, first nonblocking wait and first successful sleep.
They do not prove rcS completion, services, SSH or a clean native shutdown.
A90 and S20+ were untouched.

## Exact scope and execution

The operator returned the prepared one-operation/3600-second attended grant
and confirmed usable physical Download/original-A recovery. This was a new
operation, bound to the [reviewed host correction](S22PLUS_P437_TRANSFER_GUARD_H0_2026-10-19.md)
and the unchanged qualified P437 image. The earlier
[pre-transfer attempt](S22PLUS_P437_PRETRANSFER_STOP_2026-10-19.md) remains closed
with its original N=0/A=1 result and unrecovered exception detail.

Current source, artifact, rollback, target and health checks passed. The actual
N transfer crossed the unchanged 10-second endpoint revalidation window and
completed once. The owner then exhausted its existing read-only observation
window and recorded `SessionError: automatic observation window expired`.
It issued no SSH shutdown. Missing external access did not prove that the
automatic local workload was inactive.

The operator entered Download for the original recovery. One original A
completed. The first post-A health read returned ADB device-not-found; its raw
capture was retained. The existing owner rederived A completion and continued
health only, without another image transfer. Final changed-boot rooted
Android health, original boot/supporting digests, complete GPT and Android32
capacity of 34,357,624,832 bytes passed. The task is consumed and closed, and
no F1 owner remains. Android return does not establish native_data consistency.

## Authenticated progress and limits

| Observation | What the returned records establish |
| --- | --- |
| Early file preparation | Worker success, checked receipt publication and successful supervisor settlement |
| Root transition | Actual installed-init checks and runtime-file initialization succeeded |
| rcS fork | Parent and child identities join the successful fork |
| Fork-boundary file record | Write returned 128 bytes; fsync, readback verification and close returned success |
| Child descriptors | close_range succeeded; fd 3 was absent with the expected EBADF |
| Child execution | `/etc/init.d/rcS` exec attempt was observed; completion is unproved |
| First parent wait | WNOHANG wait returned 0: the child was not reaped at that poll |
| First sleep | nanosleep returned success after an observed 10 ms |
| Later lifecycle | No authenticated first heartbeat, child reap, rcS completion, service or SSH proof |

Installed-init validation completed at about 6.145 seconds of the candidate
boot. The child exec attempt was recorded at about 6.173 seconds, and the first
sleep returned at about 6.185 seconds. These are observed timestamps, not a
claim that execution stopped at 6.185 seconds. The first heartbeat is scheduled
only after the existing 10-second interval; missing later records cannot
locate a stall or distinguish execution failure from lost retention.

Successful syscall returns carry an errno snapshot of 9 in several records;
that stale errno is not an error result. The explicit fd-3 probe returning
-1/EBADF is the expected success predicate. No authenticated error/STOP explains
the later absence. In particular, the first fork-record write/fsync/verification/
close and the first wait/sleep are now observed to return; they must not be
reported as unproved or as the specific blocking calls in this run.

The projection has no sequence/source/boot conflicts. Observed records report
zero prior logger losses and at most 17 ms of prior logging budget use; this
only describes the retained prefix. Child exec success and rcS completion are
not inferred from the lack of an exec RETURN. No native_data reader, journal
replay, repair, new workload or second host candidate transfer was performed.

## Canonical host timeline

Times are seconds from the original finite grant opening.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Android Download intent | 95.430 |
| Candidate N transfer intent | 124.310 |
| Candidate N transfer complete | 128.512 |
| Live Debian/SSH ready | Not proved |
| Observation stop | 491.5 |
| Original-A transfer intent | 529.405 |
| Original-A transfer complete | 530.796 |
| Final Android health complete | 615.114 |
| Audited task closure | 684.030 |

## Retained evidence

Private records are under
`workspace/private/outputs/s22plus-p437-transfer-guard-h0-20261019-1/`:
`physical-authorization-1.json`, `physical-grant-1.json`, the execution/recovery
logs, `ready-1/task/operation-0001/`, `ready-1/task/closure-audit.json`,
`ready-1/task/closed.json`, `retention-1/` and `physical-evidence-summary-1.json`.
The closure rederives 400 bounded raw captures, including the one failed health
read; the subsequent D0 has 16 successful captures and matches the same returned
Android boot. The original journal and terminal remain unchanged by H0 audit.

Execution uses the frozen sources of commit `e87f565fc7` plus the preserved
unchanged preexisting workspace inputs. The pre-effect host source snapshot
and original manifest remain intact. A canonical historical snapshot wrapper
was added after return, copying the exact task-bound review receipt and
explicitly recording that timing; it does not relabel the original manifest.
The original P437 runtime build/41-case VM evidence remains unchanged.

The bounded experiment is complete. The candidate is now globally consumed.
Any prospective change must preserve these results and separately resolve its
current-root admission and execution authority; this run grants no replay.

## Subsequent H0 raw-log analysis

The [boot-requirements audit](S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)
subsequently separated two candidate boot identities in this same preserved raw
capture. The first boot's kernel-log tail records watchdog bark/bite and warm
reset at about 12.739 seconds; the first parent heartbeat was only due at about
16.175 seconds. The later 317-second kernel messages belong to the second boot.
This adds a concrete system-failure observation without changing the original
transition projection, terminal, transfers, grant consumption or Android health.
The missed-pet cause, rcS completion and second-boot writes remain unproved.
