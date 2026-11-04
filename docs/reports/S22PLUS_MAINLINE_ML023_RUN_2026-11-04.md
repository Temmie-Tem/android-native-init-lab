# ML023: live Debian proof, host pre-spawn SSH failure, original Android healthy

Status: **CONSUMED / SSH NO_PROOF / ANDROID_CLOSED_HEALTHY**.

The S22+ FYG8 run obtained authenticated packaged-Debian RAM PID1 evidence
and sshd startup readiness, but the host stopped before launching its single
SSH client. The selected SSH milestone therefore remains unproved. Original
Android recovery and full final health completed with one N and one A transfer.

The operator returned the exact one-operation, 1800-second approval and
confirmed current attendance and usable Download recovery. The
[qualified candidate, independent review and backend V29](S22PLUS_MAINLINE_ML023_DEBIAN_SSH_RAM_H0_2026-11-04.md)
were unchanged. Because the previous readiness was approximately nine hours
old, the fixed seven-read Android health was refreshed and all raw captures
revalidated before arming the grant. No execution source changed during the run.

## Physical observations

N transferred once. Before the one phone-end replug cue, completed raw N
transfer, completed installation, the original observation window with
approximately 68 seconds remaining, and the latest complete ENOENT/no-child
USB census were checked. No endpoint, request, stop, return, terminal or
active transfer existed. The operator reported the instructed same-cable,
same-port, same-orientation replug complete. Its exact physical timing and
necessity were not measured.

The observer recorded **11 absent USB snapshots**, followed by one matching
endpoint, with no partial-enumeration sample. One connection and one nonce
request produced a complete **500,384-byte** authenticated response. Production
base rederivation and an independent request/response HMAC construction agree on:

- exact packaged Debian SysVinit as PID 1 and the exact observer as PID 70,
  PPID 1, at runlevel 2 with previous level N;
- the expected PID-namespace consistency, inittab, initrd, kernel release
  `7.2.11-g0q-ram-h0` and live device tree;
- one online CPU, zero block devices, uptime **66,971 ms** and a **20 ms**
  timer advance;
- the bounded positive sshd startup indication.

Initial namespace meaning also depends on the reviewed direct startup and
exact package/CPIO closure; namespace equality alone does not establish it.
The sshd indication checks the post-listen pidfile and executable. It does
not establish SSH authentication, command execution or continued availability.

## SSH host failure and bounded H0 diagnosis

The host captured the expected USB endpoint and a direct route through the
bound NCM interface, then durably wrote its single SSH intent. The producer
returned `returncode=null`, `producer_error_type=SessionError`, empty stdout
and stderr, and no timeout or output overflow. The unchanged producer can
receive this session exception from the pre-spawn callback; it occurs before
`Popen`. No SSH child was launched. No subsequent client invocation occurred.
The normal combined evidence record was not produced; terminal closure
retains the separately rederived base proof and `ssh_proved=false`.

The retained timing exposes a concrete prospective ordering defect:

| Recorded point | Remaining time / setting |
| --- | --- |
| SSH intent, original observation window | 26.502 seconds |
| Chosen SSH timeout | 20.000 seconds |
| Acquisition time after reserving four seconds | 22.502 seconds |
| Raw pre-spawn production elapsed | 3.558 seconds |
| Capture completion, original observation window | 22.935 seconds |
| Capture completion, acquisition deadline | 18.935 seconds |

`capture_ssh` chooses the timeout before its second full guard. Its callback
then requires the already chosen timeout still to fit before the acquisition
deadline. Validation and capture overhead can consume the small remaining
margin and reject spawn while useful time remains in the original window.

An isolated H0 reproduction used the unchanged `capture_ssh` and raw producer,
the recorded intent time, and the sealed endpoint/route inputs. A stubbed
successful second guard advanced the clock by the recorded 3.558-second raw
elapsed interval. It reproduced `SSH spawn would exceed original window`
before any `Popen` call. A zero-delay control reached an intercepted `Popen`
call. Neither case launched a process or opened a socket.

This establishes the ordering failure under that timing model. The original
raw stores only the exception type, not its message, and does not separately
measure guard time. The model assigns the complete raw elapsed interval to
that guard. Thus the specific budget predicate is a supported explanation,
not a recovered original error message or proof that all other effect-time
guard predicates passed. It supplies no evidence of a Debian sshd failure.

A prospective correction should allocate the effective budget after validation
or use the existing absolute acquisition deadline to bound the actual remaining
time. The original window, four-second settlement reserve, current binding
checks and single-invocation rule must retain their meaning. No producer,
capability or candidate was changed in this closure; any correction needs its
own scoped validation and independent review before a future run.

## Original-A recovery and closure

The completed replug acknowledgment was saved separately from the later actual
Download confirmation. The stopped original owner dispatched physical recovery
once and transferred its original A once. During first recovery-health
readiness, `wait-077-boot` returned exit 1, empty stdout and `error: closed` on
stderr. The failed raw capture and journal prefix were preserved. This does
not establish the transport cause or an additional Android boot.

After rederiving the completed A transfer, one health-only continuation
completed full final health and closed the original task. No further A
transfer, reboot, new grant, native replay or SSH attempt occurred. The owned
transient NetworkManager profile was removed, and later cleanup confirmed
absence. Expected profile-absence results are separate from acquisition errors.

One fixed post-closure D0 acquired the complete **2,097,136-byte** returned log
with successful producer status and empty stderr. Before/after health proves
the same returned Android boot. Production decoding and an independent HMAC
search agree on **zero loader-handoff and zero kernel-entry frames**, with no
damaged or foreign frames. The absent frames coexist with positive live Debian
evidence and identify neither a failed stage nor a historical failure cause.

An acquisition-blocked offline audit verified all **374** indexed task raw
captures, both real failures, expected profile absences, cleanup, base wire
proof, complete retention acquisition and closure. The task, grant, approval,
journals and terminal were unchanged. The timing reproduction separately
checked its original input records remained unchanged. Both private Python
auditors passed compilation and their focused assertions. This factual
documentation update changes no policy, evidence acceptance or execution code;
content, local links, privacy and scoped diff checks suffice for the commit.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-ml023-debian-ssh-h0-20261104-1/`,
including actual approval/physical statements, `task-1/closed.json`, canonical
timeline and journals, raw index, `retention-1/`, `run-audit-1.json` and
`ssh-budget-reproduction-1/result.json`. Source and artifact identities retain
their original preparation/execution bindings. No external model was called
during this execution-and-closure turn.

The candidate and grant are consumed. No F1 owner, successor or new grant is
armed; the next bounded unit is not selected. Persistent storage, installed
Debian, physical SSH, automatic recovery and replug necessity remain unproved.
A90 and S20+ were untouched; unrelated working-tree changes remain intact.
