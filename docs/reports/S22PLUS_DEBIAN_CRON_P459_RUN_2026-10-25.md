# P459: actual packaged cron work retained across Debian reboot

Result: **PASS_TWO_DEBIAN_BOOTS_SSH**, with **cron_workload_proved=true**,
**cron_exact_retention_proved=true** and **ANDROID_CLOSED_HEALTHY**. One fresh N,
one ordinary Debian reboot, one fixed final shutdown and one original A were
used. The task and candidate are consumed. A90, S20+ and server work were
untouched.

The operator returned the exact prepared task's 3600-second, one-operation
attended grant and confirmed physical Download/original-A availability. The
reviewed entry was dispatched once. Its
[H0 and physical preparation](S22PLUS_DEBIAN_CRON_P459_H0_2026-10-25.md)
qualified the fixed M=22 baseline, identical A/B image, all 45 ARM64 cases and
the actual ordinary host entry. Capability and prepared-entry reviews passed
independently. Those qualifications are separate from the physical evidence
reported here.

## Physical functional proof

First boot ran the installed packaged cron service's stop, start and restart
once each. The previous daemon disappeared and the new daemon identities passed
the pinned executable, root, PID/start-time and descriptor checks. Packaged
cron then launched the fixed workload through its actual PAM/shell ancestry.
The job hashed the installed cron and sshd programs and created its one
exclusive 512-byte native_data report, with checked file/parent synchronization
and a completion receipt. The sequential observer also required settlement of
the winning job and its recorded intermediate processes.

The job began 45,026 ms after arming; hashing took 12 ms. The latter is hashing
time only, not synchronization duration. Two permitted intermediate ancestors
join the actual restarted cron daemon. Direct helper invocation is not used
as scheduled-work evidence.

One ordinary reboot led to a different authenticated kernel boot identity,
the same pinned SSH key and exactly one installed boot-count increment. Both
second-boot protected admissions authenticate the first report, and the host
compares its bytes with the acknowledged first-boot snapshot. The report and
its complete decoded proof remain identical; no second cron report is created.
The final first-boot early/runtime pair is also retained exactly.

| Measurement | First boot | Second boot |
| --- | --- | --- |
| Installed boot count | 4 | 5 |
| Initial and installed Debian PID1 | PASS | PASS |
| Complete protected root admissions | PASS | PASS |
| Local 120-second service evidence | PASS | PASS |
| Interval between same-boot SSH responses | 121,240 ms | 123,220 ms |
| Cron report | Actual workload completed | Exact first report retained |

The SSH responses prove sampled access across those intervals, not a continuous
connection. The selected four RW lifetimes remain sealed from M=22 through
M+4=26. Clean post-reboot admission is proved; final native_data consistency
after the last shutdown and post-Android retention of the second pair/report
were not separately measured. The schedule is a RAM overlay. Package
installation, persistent configuration, DNS and general Debian compatibility
are not established by this run.

## Original-A return and health continuation

After both functional observations and the fixed shutdown request/departure,
the original owner paused for physical Download. The operator performed that
action. The sole normal-return connector call reported an uncertain backend
response after its reply deadline. The original backend continued, published
one continuation intent and retained its process/result ownership. The call
was not repeated; one original A then transferred successfully.

The first post-A health bracket encountered one raw ADB `device not found`
read failure and stopped. With device acquisition and process launch denied,
the original transfer consumer rederived the unique completed A transfer.
The existing health-only continuation then ran once, with no transfer, and
completed changed-boot rooted original-A health and the exact Android32/GPT
geometry. The terminal is marked recovered because health finished through
that branch. Reply latency and the post-A read race remain separate host
follow-up topics; neither permits a repeated control or transfer.

## Closure evidence

H0 closure rederived all **683 raw captures**, both functional proofs, the N
claim and the unique final A/health sequence with process/device acquisition
disabled. It preserved the **24-row journal** and terminal byte for byte,
verified the frozen source snapshots and found no remaining F1 owner. Of 106
nonzero captures, 105 belonged to the original bounded Debian observation
loops and one was the stopped post-A read. Original consumers rederived all
accepted evidence. No new device command was issued by closure.

| Canonical event | Seconds from original grant |
| --- | ---: |
| Live session start | 0.000 |
| Android Download request | 110.889 |
| N transfer start / completion | 124.502 / 126.074 |
| First boot fully proved | 287.638 |
| Original-A transfer start / completion | 780.420 / 781.866 |
| Final Android health complete | 941.021 |
| H0 task closure | 1141.473 |

The ordinary reboot request/departure completed at 288.537/297.011 seconds;
second-boot proof completed at 465.687 seconds. The final shutdown request and
departure completed at 471.137/515.592 seconds. These events do not substitute
for a separate post-shutdown filesystem observation.

The exact task, returned approval, physical-action reply, raw captures, frozen
source snapshots, append-only journal, terminal, reply uncertainty and original-A
proof are retained under
`workspace/private/outputs/s22plus-debian-cron-p459-h0-20261025-1/`.
The connector reports the dispatch and both used continuations as
`CLOSED_BY_ORIGINAL_OWNER`. The current proof scope is the real cron workload,
exact ordinary-reboot data retention and healthy Android return. No new device
operation is authorized.
