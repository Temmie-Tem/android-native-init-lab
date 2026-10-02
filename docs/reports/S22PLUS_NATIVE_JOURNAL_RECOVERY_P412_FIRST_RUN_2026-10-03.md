# P412 first run: clean-root proof and healthy Android closure

Date: 2026-10-03 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Candidate: P412 `v0.4.0-rc.12`, [journal recovery V1](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md).

## Result

One attended operation completed **PASS_JOURNAL_RECOVERY_OBSERVED /
PROVED_CLEAN_ROOT**, then returned normally to original Android. Terminal:
**ANDROID_CLOSED_HEALTHY**, `recovered=false`. The single-operation/1800-second
grant and candidate are consumed and closed; the F1 owner is absent. Exactly
one N and one original A were transferred. A90 and S20+ received no command
or transfer.

The native result proves clean protected-root admission after the strict
writer. It does not prove Debian init, services, NCM, SSH or shutdown. No
installed executable or Debian handoff was selected.

## Native filesystem evidence

The authenticated observation recorded these ext4 states:

| Phase | clean | state | recover | orphan |
| --- | ---: | ---: | ---: | ---: |
| Before strict recovery | 0 | 1 | 1 | 0 |
| After strict recovery | 1 | 1 | 0 | 0 |

The writer completed stage 5 with zero logical/I/O errors, two writes and
5,120 bytes. These are the two successful journal/primary-superblock
finalization writes; the accounting contains no additional home-block replay
write. This run therefore does not establish restoration of particular file
data from committed journal payloads.

The writer child was conclusively reaped and settled. The parent restored
native_data RO, the separate `e2fsck -fn` completed successfully, and protected
`ro,noload,nodev,noexec,nosuid` inspection passed. All **8,969 expected entries**
matched, with zero missing/content/metadata findings, exact bounded mutable
state and no extra entry. Installation start/complete/witness records passed.
Unmount, helper cleanup, post-replay superblock preservation and unchanged
GPT checks completed. Original pre-recovery evidence remains separate.

The observer completed authenticated DETACH and descriptor close. A fresh
same-boot native health session then issued the fixed Download control, proved
departure and bound the Download endpoint before the sole A transfer.

## Final-health consumer incident and H0 correction

The original-A transfer completed before the first final Android health read.
That read acquired complete rooted-health brackets, GPT and storage-stat
captures, but its projection raised `Android complete GPT bytes differ`.
The existing recovery path reconstructed the already completed A and performed
one health-only observation. The same projection error occurred; A was not
transferred again. The runner exited with its original traceback retained.

The cause was a missing `journal-recovery` registration in
`s22plus_native_gpt_android_v1.projection`. Its copied protected-operation list
fell through to the GPT reservation consumer, which selected historical
`original` layout because this operation correctly had no GPT-write intent.
P412 instead requires the retained `proposed` Android32 layout. This was a
wrong comparison basis, not an observed GPT mutation or failed health producer.

Both saved observations independently prove full **61,440-byte GPT equality**
with the sealed proposed layout, unchanged exact target, one new Android boot
relative to preflight, root and original boot/supporting partition hashes.
They agree on the same Android boot, native_data presence, 32-GiB userdata
extent and **34,357,624,832-byte** reported F2FS capacity. All raw producer
captures completed without timeout, truncation or nonzero status.

The minimal correction derives protected operations from the existing shared
session declaration. It changes no GPT, target, health or capacity assertion.
A real subprocess/raw regression exercises journal recovery through the
retained Android32 basis, verifies H0 reconstruction without I/O and still
rejects the wrong historical GPT. The focused health suite passed **9 tests**;
the owner/closure suite passed **21 tests**, and touched Python compiled.

Independent review returned **PASS_GO_H0_CLOSURE_ONLY**, covering the exact
source/test correction, private closure script, preserved sources and raw
health evidence. The existing `Session.repair_close` ran with command
acquisition blocked. It validated all six normal steps and appended only the
missing `android-final` completion, then published the normal terminal and
task closure. All original 19 journal rows, including the stop and subsequent
health start, remain byte-identical. A second H0 derivation reproduced the
terminal and complete 20-row journal unchanged. No additional device command
occurred during diagnosis or correction.

This follows the [V3 raw-proof publication rule](../operations/S22PLUS_NATIVE_SESSION_V3.md#effects-closure-and-recovery).
The retained live source, capability review, task and grant were not repinned.
The correction review authorizes H0 closure only; future execution requires
a current source binding and its own selected grant.

## Canonical timeline

Elapsed seconds are from the original grant. No budget or deadline was renewed.

| Seconds | Durable event |
| ---: | --- |
| 6.139 | Fresh rooted original-A preflight completed |
| 6.381 / 10.017 | Android Download intent / completion |
| 19.742 / 21.249 | Sole N transfer intent / completion |
| 34.431 / 38.546 | Journal-recovery pre-EXEC intent / complete native proof |
| 40.290 / 40.900 | Fresh same-boot return CONTROL intent / departure proof |
| 47.389 / 48.985 | Sole original-A transfer intent / completion |
| 49.000 / 97.139 | Final-health acquisition started / wrong-layout projection stop |
| 97.236 | Automatic health-only recovery observation started; same projection error |
| 469.552 | H0 rederivation appended missing final-health completion |
| 470.548 | Evidence audit and explicit finite-grant closure |

## Retained evidence and validation

Private run root:
`workspace/private/outputs/s22plus-journal-recovery-p412-live-20261003-1/`.
The operation is under `connected-preparation-1/task/operation-0001/`.
The audit verified both streams of **630 operation captures**, all **252 frozen
source files**, exact N/A transfers and the permanent consumed candidate claim.
The only current production-source difference was the separately reviewed H0
projection correction; its own frozen copy and review are retained. Device
execution used source commit `7e5bb2e1490001a51e8498e1bc3b230895649b34`.

| Record | SHA-256 |
| --- | --- |
| Task | `ac27dff2ef793ed5196247f5b6195f15b9938a124a64e8aeaa603e509a576cc1` |
| Pre-effect source closure | `b88cf431f8314f918056a11ece1a54d9b7ae1c5f0910791cb1728143ed9e8401` |
| Independent H0 closure review | `93d51143a84ab088e418c95f2ec33243a6390d6c27aa336fb1e4ce28b9f10e8e` |
| Terminal | `25cfbabc6511a65304b9095805a57e3e366a26b390a17bcc195487e16e95d220` |
| Closure audit | `1af8e62a6afd587d869378fea8e00cd7174bdcf1058f845be6de5db98ebdccfb` |
| Closed grant/task | `398cfe3f6d20e48af52339b4ac0a0e62daf8c961989cb0a025447d32c793981f` |

## Next boundary

P412 removes the dirty-root admission blocker observed by P411. A fresh Debian
handoff candidate may now be prepared under its own current qualification,
source binding, health/root admission and finite grant. P411/P412 cannot be
replayed. Clean ext4, Debian PID1, service progress, SSH and Android closure
remain distinct claims. Debian service progress and SSH remain open.
