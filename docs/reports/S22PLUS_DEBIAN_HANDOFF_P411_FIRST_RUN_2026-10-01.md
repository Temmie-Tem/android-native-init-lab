# P411 first run: dirty-root rejection and healthy Android recovery

Date: 2026-10-01 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Candidate: P411 `v0.4.0-rc.11`, [handoff V2](../operations/S22PLUS_DEBIAN_HANDOFF_V2.md).

## Result

P411 authenticated its native boot and retired the native workers, then
rejected native_data before mounting it because ext4 required journal recovery.
It did not activate a writable root or execute installed Debian init.
Scientific result: **NO_PROOF Debian PID1; protected dirty-root rejection
proved**. This attempt did not test the later same-gadget correction on Samsung.

Original Android was restored once and fully checked. Terminal:
**`ANDROID_CLOSED_HEALTHY`**, `recovered=true`. The one-operation/3600-second
grant and candidate are consumed and closed. The F1 owner is absent. A90 and
S20+ received no command or transfer.

## Exact admission evidence

The 867-byte authenticated preparation log records:

```text
RI1_BIND exact=1
RI1_BLOCK_RO partition=1
RI1_SUPER clean=0 state=1 recover=1 orphan=0
RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1
RI1_RESULT complete=1 stage=10 errno=0 cleanup_errno=0 partition_ro=1 clean=0 mounted=0 unmounted=0
```

The superblock's clean-state bit alone was insufficient: `recover=1` made the
combined clean predicate false. The inspector completed its protected negative
result and cleanup without mounting, running the filesystem checker or
comparing installed files. The parent then emitted authenticated STOP
`errno=71`, last completed transition stage 2 (`workers-settled`). No
root-admitted, writable activation, witness or installed-init stage followed.

The host sent no init continuation, START or release. There was no NCM/SSH
attempt and no Debian shutdown command. The terminal's `persistent_writes=true`
field describes the selected writable capability; it is not proof that this
attempt reached that phase. The authenticated phase/log evidence establishes
the pre-mount rejection independently.

The [P410 writable lifetime and forced return](S22PLUS_DEBIAN_HANDOFF_P410_FIRST_RUN_2026-09-30.md)
made a dirty filesystem a known possibility. P411 establishes the actual
journal-recovery flag at this observation, not a complete diagnosis of the
filesystem's contents or a causal explanation for every prior shutdown event.
Its clean-root guard was retained and worked as qualified.

## Recovery and observation limits

The operator reported native appearance and requested software Download entry
and recovery. A bounded host USB observation found the same P411 native
identity. ACM had not been unbound in this attempt, so that observation cannot
prove a new native boot or reset. No later authenticated kernel boot identity
or reset-cause evidence was collected.

The host did not dispatch a new native Download command or reopen the consumed
native session. The reviewed recovery owner waited for and bound the exact
Download endpoint, then dispatched the sole original-A transfer. The record
does not prove the mechanism that caused that Download entry.

The first final-health bracket failed on an ADB `device not found` read after
the A transfer had already completed. Its raw capture was preserved. The next
invocation reconstructed the completed A from its original evidence and
performed only remaining health reads; it sent no second image. Full numeric
root, original boot/supporting partition hashes, a distinct Android boot,
matching GPT and Android32 total capacity passed. The native partition remained
present. Android health does not establish repaired or clean native_data.

## Canonical timeline

Elapsed seconds are measured from the original grant opening. No deadline or
operation budget was renewed.

| Seconds | Durable event |
| ---: | --- |
| 9.481 | Fresh operation preflight completed |
| 9.656 | Original Android Download intent |
| 22.213 / 23.729 | Sole N transfer intent / completion |
| 48.659 | Compound Debian handoff intent after native authentication/health |
| 49.058 | Research stopped after protected dirty-root rejection |
| 335.946 | Original-A recovery preparation started |
| 378.804 / 380.190 | Sole A transfer intent / completion |
| 380.202 | First final-health bracket started; one later ADB read failed |
| 463.382 / 467.249 | Health-only continuation / successful final health |
| 676.320 | H0 evidence audit and explicit finite-grant closure |

## Retained evidence and validation

Private run root:
`workspace/private/outputs/s22plus-debian-handoff-p411-live-20261001-1/`.
The task/operation is under `connected-preparation-1/task/operation-0001/`.

The H0 closure audit verified both raw streams for **1,436 operation captures**,
the original and final health projections, exact N/A transfers, global consumed
claim and all **261 frozen source files**. It rederived the terminal with device
command production blocked and proved the terminal and all 16 journal rows
unchanged. The earlier 19-capture connected preparation and the bounded recovery
USB observation are retained separately. No executable or policy changed during
the run; source commit was `efa61ed3cc4b7677bf4a89b2f3acd322786c7926`.

| Record | SHA-256 |
| --- | --- |
| Task | `4dba33825c8cea17463266ac2e1e8b3591a45641ed68a2fb1caa5dc93f696aa9` |
| Pre-effect source closure | `2750bb4d16e3b2dd41b2a62c9b7686f6de9d63cf2bdebc53b6cad8a3337a04e9` |
| Authenticated preparation log | `9059fc70a7e0ebefec3b7f8252da4e5ea1205651b0c633c277715ebbc398e244` |
| Terminal | `f242ef98cb3158a2785b149d4364bc026d390094481e74eab0fb0eafe532e303` |
| Closure audit | `a8d4e16e59e1b6d9ad7402fc0a976d9eb93b23bd5697aa87cb6fe8326745975f` |
| Closed grant/task | `af659ad9fe0ec25b7a8e93c249db3768dcac99f406bddd8b200583f5a46833cc` |

## Next boundary

P411 cannot repair or replay the journal, reinstall the root or run again.
Any filesystem recovery requires a separately scoped design/review and explicit
write authority, followed by protected current-root qualification and a fresh
candidate. The bounded mutable-data allowance does not waive clean ext4.
The 120-second Debian observation, NCM/SSH and later package/service/persistence
milestones remain open. The H0 same-gadget qualification and P410's older
installed-init proof retain their separate meanings.
