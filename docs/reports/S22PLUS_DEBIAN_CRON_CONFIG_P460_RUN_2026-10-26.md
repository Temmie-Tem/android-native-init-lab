# P460: persistent cron configuration consumed after Debian reboot

Result: **PASS_TWO_DEBIAN_BOOTS_SSH / ANDROID_CLOSED_HEALTHY**. The exact
cron configuration is **preserved across reboot, consumed by packaged cron,
and retired successfully**. One second-boot workload creates its exclusive
512-byte report. One N, one ordinary reboot, one final shutdown and one original
A were used. The task and candidate are consumed. A90, S20+ and server work
were untouched.

The operator approved the prepared one-operation/3600-second scope and
explicitly confirmed attendance through Android return and usable physical
Download. The selected task and verbatim replies were saved before the single
dispatch. Current source, image, original-A and demonstrated recovery checks
passed. The [physical preparation](S22PLUS_DEBIAN_CRON_CONFIG_P460_PREPARE_2026-10-26.md)
provides the fixed clean M=26 baseline, A/B-identical candidate, 49 ARM64 cases,
boot-only package, independent review and actual-entry qualification. Those
preparation results remain distinct from this physical execution.

## Physical functional proof

First boot creates the exact **185-byte cron.d configuration** after the
reviewed daemon/process settlement. File and parent synchronization, close and
full readback succeed. Authenticated records bind its contents, inode and
nanosecond timestamps. First-boot invocations cannot claim a job intent or
create the report; successful first-boot evidence confirms those outputs are
absent. This does not assert that cron never dispatched a process.

One ordinary reboot produces a different authenticated kernel boot identity,
the same pinned SSH key and one installed boot-count increment. Both complete
second-boot protected admissions require the exact retained configuration and
first-boot evidence. The second-boot record joins the unchanged first creation
metadata and content hash, rather than learning a new identity.

The real packaged cron then launches the selected job through its permitted
cron/PAM/shell ancestry. It hashes the pinned cron and sshd programs and writes
one exclusive **512-byte report**, with checked synchronization and completion
publication. The job starts **44,845 ms after arming**; executable hashing takes
12 ms. That is hashing time only, not the entire durable-write duration. Two
permitted intermediate ancestors join the original daemon.

After successful worker settlement and the service window, the observer
acquires the fresh RAM revocation claim, stops the daemon, verifies settled
cron processes and the exact held configuration, and unlinks that file once.
Parent synchronization, name absence and zero links on the held inode are
checked before cron restarts with full identity checks. Authenticated retirement
is recorded at **136,725 ms of second-boot BOOTTIME**. The report is retained;
the configuration is not left installed.

| Measurement | First boot | Second boot |
| --- | --- | --- |
| Installed boot count | 6 | 7 |
| Initial and installed Debian PID1 | PASS | PASS |
| Complete protected root admissions | PASS | PASS |
| Local 120-second service evidence | PASS | PASS |
| Interval between same-boot SSH responses | 120,970 ms | 120,810 ms |
| Persistent configuration | Created; no job report | Exact retention, scheduled consumption and retirement |

The SSH samples prove access across those intervals, not a continuous
connection. Four selected RW lifetimes advance the sealed mount count from
M=26 through M+4=30. Clean post-reboot admission is proved. Final native_data
consistency after the last shutdown, or post-Android rereading of the final
report/configuration absence, was not separately measured. Package installation,
general configuration management and unattended recovery are not established.

## Original-A return and health continuation

After the second functional observation and fixed shutdown request, the
original owner paused for physical Download. The operator confirmed entry.
The sole normal-return connector call reported an uncertain backend response.
Its original backend remained active and later published one continuation
intent; the request was not repeated. The original owner transferred A once.

The first post-A health bracket stopped on an ADB `device not found` read.
The original raw transfer consumer independently rederived the completed A
transfer with device acquisition disabled. The existing health-only continuation
then ran once and completed changed-boot rooted original-A health and exact
Android32/GPT geometry. It sent no partition payload. The recovered terminal
reflects that health branch, not an additional A transfer. The uncertain reply
and failed read remain preserved; their cause was not changed or assumed by
this run.

## Closure evidence

H0 closure rederives **693 raw captures**, both functional proofs, configuration
continuity/consumption/retirement, the N claim and unique A/final-health sequence.
Device acquisition, process launch and sockets are denied. The **24-row journal**
and terminal remain byte-identical; frozen source snapshots verify and no F1
owner remains. Actual connector status reports start, normal continuation and
health continuation as **CLOSED_BY_ORIGINAL_OWNER**. General recovery was not
dispatched.

Of 105 nonzero captures, 101 are retained bounded Debian evidence observations,
one is the stopped post-A read, and three are NetworkManager queries reporting
an absent temporary connection profile. The corresponding cleanup records are
two `ALREADY_ABSENT` results and one `REMOVED` result. Accepted functional and
health evidence is rederived through the original consumers; capture integrity
alone does not turn a nonzero result into success.

| Canonical event | Seconds from original grant |
| --- | ---: |
| Live session start | 0.000 |
| Android Download request | 110.518 |
| N transfer start / completion | 123.745 / 125.322 |
| First boot fully proved | 284.961 |
| Original-A transfer start / completion | 675.594 / 677.017 |
| Final Android health complete | 806.633 |
| H0 task closure | 971.989 |

The ordinary reboot intent/step completion occurred at 285.322/286.309 seconds;
second-boot proof completed at 447.815 seconds. The final shutdown intent/step
completion occurred at 448.811/458.094 seconds. Control acknowledgement does
not substitute for a separate post-shutdown filesystem observation.

The exact task, human replies, approval, raw captures, source snapshots,
append-only journal, transfer proofs, uncertain reply and closure audit remain
private under
`workspace/private/outputs/s22plus-debian-cron-config-p460-h0-20261025-1/`.
No new device operation or repeat of this consumed candidate is authorized.
