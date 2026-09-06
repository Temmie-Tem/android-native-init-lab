# S22+ P349 RAM workspace preparation

The operator authorized implementation and D0/D1 preparation through fresh F1
approval-code issuance. F1 execution still requires the separately returned
code. This unit selects only SM-S906N / g0q / S906NKSS7FYG8; P348 remains
consumed and closed, and A90/S20+ receive no command.

## Capability and proof scope

P349 adds one current-boot `/work` mount: 8 MiB, 256 inodes, UID/GID 65534,
nosuid/nodev. PID1 creates the fixed mount once before opening its listener and
never traverses caller-created files. Fresh isolated children can retain files
across actions and run a script through the fixed BusyBox interpreter. The rest
of the child filesystem stays read-only, with the inherited privilege drop,
seccomp, snapshot, descriptor and resource restrictions. This is not a root
shell. Only BusyBox script execution is qualified; arbitrary ELF execution is
unqualified and remains subject to the same syscall/privilege restrictions.

The new lease permits at most 3,900 seconds and 16 later actions. Initial
qualification retains six sessions / 18 commands and one 120-second clean
reopen. The ordered later sequence requires a checked snapshot, RAM creation,
cross-child modification, script execution, exit 7, timeout, cancellation,
post-cancel output, then 20/40/60-minute workspace witnesses. Each timed witness
must have a durable intent issued after its actual elapsed threshold relative
to lease opening. The consumer reopens authenticated raw frames and checks
command identity, fresh nonce and the same candidate boot. Delayed publication
cannot make an early intent satisfy the hour requirement.

Capacity exhaustion, cleanup and reuse are host-qualified only. The live hour
criterion is sampled residency and file retention, not continuous monitoring.
Functional evidence and exact Magisk rollback/final rooted FYG8 health remain
separate. No live P349 capability or hour proof is claimed by H0 preparation.

## H0 verification

- Five child tests passed, including actual Linux user/mount namespaces: fresh-child persistence,
  script execution, unchanged view/escape denials, capacity cleanup/reuse,
  exact later RAM command strings and AArch64 object/syscall-header checks.
- Four longevity tests passed, including a one-nanosecond-early intent with a
  late result and an out-of-order witness sequence.
- Two P349 raw receipt/owner-isolation tests passed; all 29 P348 regressions and
  29 common evidence tests passed.
- Four raw-first hostile tests passed. The full-tree raw-first audit passed;
  the only changed member of its old 49/129/133 inventories was the shared
  typed-evidence module. Counts and legacy membership were preserved.
- Reproducible A/B build and actual common bundle promotion rehearsal passed.
  The linked init is a static AArch64 ELF. Publication was rehearsed before any
  ready manifest or connected run was created.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| A/B candidate AP | 28631081 | `8ff751708347bbbb15278c6547cb1a46d34292ec01ce165c5541b4e35f2256af` |
| Linked init | 149456 | `d6fc40c9f03e12bf2c506baea80030b1fedc7438cae196ece9eab5fb4e9271e1` |
| Image | 41490944 | `de36995ad644cde3df79ea18a0ce1b0cc6ffac3aa8d0e6ec6532d5834cfe155d` |
| Build result | 92018 | `fc8ccb68a2c523543383313bfab663c2f799f7ae8c50a53df7eddb0f069e0aa5` |
| Exact Magisk rollback AP | 23367721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |

The retained construction base and consumed P345–P348 source templates remain
unchanged. New wrappers bind their exact template bytes; current raw-first and
live closures include the executed templates. Preliminary host failures were
an initial namespace fixture mount-point mismatch, x86-only legacy syscall
mapping and a missing fresh Image run-ID projection. Their corrections were
qualified before artifact derivation; no device effect was involved.

Private build and test evidence is under `workspace/private/outputs/` and
`workspace/private/outputs/s22plus_fyg8_p349/`. No firmware or raw device log is
published with this report.

## Review and connected preparation

Independent reviewer `p349_safety_design_review` returned **PASS_GO** for the
17 named current source/contract hashes and their execution-critical template
closure. It independently reopened the A/B build and found no remaining blocker.
The exact review record is private at
`workspace/private/outputs/s22plus_fyg8_p349/independent-review.json`. This is a
capability review, not F1 authority. The consumed build's
`lineage.behavior_delta` retains its old read-only lineage label; its explicit
boundary flags and RAM/runtime metadata define P349's changed behavior. The
legacy label is not a read-only-filesystem claim.

1. D0 `p349-ready1-prepared-20260906-1` stopped on retained evidence-family
   contamination. Its 2,097,136-byte EOF capture and typed stop were preserved;
   host reclassification reproduced the same rejection. Stop result:
   `3251B/98720dd5`. It did not satisfy clean baseline preparation.
2. The operator-preapproved unchanged P296/P320 ordinary-reboot primitive passed
   its self-test, then performed one reboot through a fresh private invocation.
   The boot ID changed and the exact target returned with completed Android,
   root, original boot/supporting hashes and no Download endpoint. D1 result:
   `2963B/4c1b745b`. No other target was commanded, and no partition transferred.
3. New D0 `p349-ready1-prepared-20260906-2` passed
   `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. F1 preparation then bound the
   current exact target/boot/topology, candidate, rollback, key, observer,
   recovery owner and 75 execution sources. The approval code was generated
   for this binding; no F1 execute was invoked. Actual `load_prepared` reopening
   passed against the final stored files and source closure.

| Retained preparation artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Ready manifest | 11798 | `37ee17337089053d9a19c3a90b9b6d451b707b85c92394e82b5b91889ccb8930` |
| D0 result | 3261 | `51a955d00e575c2388bd80f038cd00ec24dfe7ba88e34d95fadc626b958ac677` |
| Prepared binding | 43926 | `2035b2687b552c411834efba24392a0fde47ffacdb8df30d95a332c0b4e5e840` |

Prepared run:
`workspace/private/runs/device-action-f1-live-v2/p349-ready1-prepared-20260906-2`.
The eleven exact later command files are prepared privately, but none has run.
F1 will require the returned exact code and attendance through physical Download
rollback. The actual hour, live RAM behavior and P349 final rollback/health
remain unproved until that separate run completes.

## First approved invocation: host authentication stop

The operator returned the exact prepared approval. Fresh execute-preflight D0
passed and the journal recorded live-session start at
`2026-09-06T07:52:27.006733Z`. Before Download entry, the CDC observer's
ModemManager guard invoked the existing `pkexec` owner. Its fixed 30-second
arming window ended without a byte of output or an arm acknowledgement. The
retained capture records 30,090 ms, empty stdout/stderr and a still-pending
process return code at capture time. The caller performed its existing release
cleanup. Subsequent host inspection found no guard process or runtime udev rule.

Polkit's matching timestamp window records failed authorization for
`org.freedesktop.policykit.exec`. The evidence establishes incomplete host
authentication; it does not establish whether a dialog was seen or why the
operator did not complete it. No bypass or timeout change was made.

The journal terminated ABORTED/4 at `2026-09-06T07:53:07.210451Z`, with
`candidate_attempted=false` and `candidate_observer_arm_failed_before_candidate`.
The generic verdict is `FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD`; despite that broad
name, no Download request or candidate attempt occurred. Result:
`1351B/ca79a6d221bf88b3cd83e186314ee0716210aab5a05b49075cefd8fa0b41d26f`.
Actual `load_prepared` and `validate_live_result` reopening passed. Recovery was
not required and no rollback was sent. No campaign-closure row is appended
because there was no candidate transfer or CAMPAIGN_CLOSED event.

The original prepared run and approval remain aborted. Existing D0 authority
was used for a fresh read-only preparation, which passed and confirmed healthy
rooted FYG8. No additional reboot was requested. Replacement run:
`workspace/private/runs/device-action-f1-live-v2/p349-ready1-prepared-20260906-3`.
Prepared binding: `43926B/87367678f9960966dcf1a075f61e3da1c71460befcf4c939d866d4a2d4d7b0b2`.
D0 result: `3261B/dbd9a55cb9e86296925b332e125ca86010b47309f404868a3f22f9cd4f2750db`.
This new binding requires its own returned approval and successful host
privilege authentication. Candidate bytes, execution sources and the intended
actual-hour witness requirements remain unchanged. P349 RAM/hour proof is
still unproved. A90/S20+ were untouched.
