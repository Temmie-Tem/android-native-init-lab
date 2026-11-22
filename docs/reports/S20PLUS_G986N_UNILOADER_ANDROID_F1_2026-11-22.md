# S20+ UniLoader Android F1 owner

The corrected candidate AP transferred once on the exact
`SM-G986N / y2q / G986NKSS8IYC2`. Candidate Android and its FDT
marker remained unproved after the bounded observation. The operator
entered physical Download and the owner restored the original Magisk
boot. Fresh rooted Android passed, with its FDT marker absent.
The terminal is `NO_PROOF_UNILOADER_ORIGINAL_ROOT_RETURNED`.
[Binding target section](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-uniloader-android-compatibility-attended-f1)

The [owner](../../workspace/public/src/scripts/revalidation/s20plus_g986n_uniloader_android_f1.py)
uses the retained S20+ Android-return engine, boot-only transport, target
lease, process cage and current global content claim. The namespace supplies
the exact historical capture and transport bytes to the engine. The source
changes are isolated from the consumed P0, P1 and P2 owners. The first
TWRP observation and original candidate/rollback AP identities are in the
[preparation report](S20PLUS_G986N_TWRP_OBSERVE_SOURCE_VIEW_2026-11-22.md).

The attended trial starts from a fresh, healthy original Magisk Android
boot joined to the demonstrated physical Download path. The owner checks FDT marker
absence there, then prepares one journaled Download entry. The candidate
proof requires its completed boot transfer, a fresh exact Magisk boot and
matching marker bytes on that boot. Root, serial, topology and boot identity
are checked around each marker read. After candidate intent the original
Magisk AP is the mandatory rollback. The owner closes only when the original
boot transfer is proved and a fresh healthy rooted Android boot proves the
marker absent. Uncertain transfer and incomplete read evidence preserve the
original owner. Each effect is one-shot.

## Review and activation

Independent review returned `PASS_GO` with zero open findings.
The review corrected candidate boot freshness matching, root producer status
checks, and the namespace's handling of compact core journals and retained
cgroup parents. All 18 focused tests passed. Actual host validation checked
both APs, the registry and process cage with zero device commands.

| Reviewed input | SHA-256 |
| --- | --- |
| Dormant owner | `d25a7002000f285bca7e2618ef08cb59712fee70aebe55f3a004c8d58d31a9e1` |
| Active owner | `9dde49d716902bc3089bd14c63176496e0f0afa29b01333c19e3cbe1d044a630` |
| Focused test source | `0f15216f75a23e65109be34f6f12585b1ae561e1d664d0fa4c609210aeea7145` |
| Host closure | `bccbab266270a9929f9988f37d244699d7dab825cc56ddb4b164bdb2432b0707` |
| Private activation record | `6958ecbef229bc4ddf68980112d5eae8b7c9f808c307b7b37afc5cd7be8c70e2` |

The only activation edit changed `ACTIVE` from `False` to `True`.
The installed owner and record passed `--validate-active` with zero device
commands. The mode-0400 activation record is in
`workspace/private/runs/s20plus-g986n-uniloader-android-f1/`.

## First physical preparation attempt

The operator reported physical Download entry and disconnected USB while
holding that state. The existing attended D1 exit lane recorded an empty
Odin device list. After the operator confirmed reconnect and payload-free
return, the lane stopped before dispatch when the Odin list did not have one
entry. Its private journal recorded zero effect commands and released the
guard. The reason distinguishes neither absence from ambiguity nor their
underlying cause. The initial read proves neither a current usable Download
endpoint nor a return to the original Magisk boot.

This first attempt issued no prepared F1 approval or candidate transfer.
No command was addressed to S22+ or A90.

## Reuse of demonstrated physical recovery

The successor revalidates the [closed P2 physical recovery](S20PLUS_G986N_P2_RAM_SNAPSHOT_H0_2026-09-23.md#recovery-and-final-state)
from its exact retained close record. Its empty and single-endpoint Odin
listings, the matching physical Download session and original fingerprinted
Magisk AP, the successful raw rollback capture, verified process quiescence,
and the healthy TWRP terminal were checked from their retained bytes. The
current S20+ uses the same exact serial and USB topology. The owner's own
rooted Android, same-boot FDT marker absence and Download arrival checks
remain required for a new approval.

The independent successor review returned `PASS_GO` with zero open findings.
The host validation and 37 focused tests passed. The reviewed active owner
SHA-256 is
`debc851f0af6036e2c6133132d41a00250e473317ca7f161a1d0a2e991e596bf`.
The new mode-0400 activation record SHA-256 is
`9e02a70c06b5b571c9cc5c52844f3bbd0fdaab87a921addb1c8aab71a0f05d8e`.
The earlier activation and P2 journal remain preserved.

## Prepared attended session

The owner verified the exact current Magisk Android boot with root UID 0
and Magisk 30.7. The fixed FDT marker was absent on that boot. One ADB
Download control completed and the fresh single endpoint matched the
retained physical recovery topology. Preparation completed at 22:35:13
KST on November 22. The prepared record SHA-256 is
`9af1931bae2641b78ec28d679dcc25790c396d1bd7f61cba70c4a5ce4e64f68a`.

The operator confirmed attendance and returned the exact approval before
expiry. The executed source and activation remain bound to this journal.

## First run result

| KST on November 22 | Observation |
| --- | --- |
| 22:36:07 | Odin returned 1 with `md5 fail` and `Fail parse` for `candidate.AP.tar.md5`. No USB session or candidate transfer started. |
| 22:36:08 | The owner recorded `NO_PROOF`. Candidate Android and FDT observation were never reached. The global claim was released through the certified pre-session local-parse lane. The run remains closed to replay. |
| 22:37:37 | One proved transfer of the bound original Magisk AP on the same already-present Download session. Temporary target-lease contention was resolved before confirmation. |
| 22:38:13 | Fresh exact Android boot completed with Magisk 30.7, UID 0, and SELinux Enforcing. |
| 22:38:15 | The same returned boot proved the FDT marker absent. The owner published the terminal and released the S20+ guard. |

The terminal SHA-256 is
`5a3caf769f23bdd4dd291414af4059cb8226906adf4d6a4c3f906be08c20cf78`.
The rollback transfer record SHA-256 is
`6b5f80b2d0649603d2653295ac9e9dc714fc926aa76afd6c12574b3665249853`.
Candidate and rollback transfer completions are zero and one respectively.
Other-target commands and recovery-partition operations are zero.

## Candidate AP filename correction

The AP byte digest and TAR MD5 trailer were correct. In a host namespace
with the USB device tree and network hidden, the pinned Odin binary
reproduced the parse failure for `candidate.AP.tar.md5`. The same bytes
under `AP.tar.md5` passed parsing and reached the intentionally absent USB
endpoint. The corrected packager writes `AP.tar.md5`; a fresh package
compared byte-for-byte equal to the original candidate and kept the
same decoded boot, FDT marker, and original rollback AP identities.
The corrected pair has SHA-256
`efd21f4e630cbed0131c92f5bed7ef95703bcfe1ec0e93869531d649abc73bfc`.
It requires a fresh preparation and approval because the absolute AP path
and pair receipt are part of the binding.

The corrected binding received independent `PASS_GO` with zero findings.
All 38 focused tests passed. The successor active owner SHA-256 is
`5a8d865ccac1d4c1dde94088fb2ea0550a0d0b80727d4d7e9d6da9b20fe53d42`.
The separate activation record SHA-256 is
`f5c4dd1fdcfc510a388b003dd278f9d4733459e7d5365609208dab980eba5cee`.
Activation and artifact validation sent no device commands. The first
run's original AP, source activation, and journal remain preserved.

## Corrected AP preparation

The original Magisk Android preflight passed on the exact current S20+.
It proved UID 0, Magisk 30.7 and absence of the fixed FDT marker on
that boot. The owner revalidated the successor activation and both APs,
issued one journaled ADB Download request and qualified the new endpoint
on the demonstrated recovery topology at 22:40:38 KST on November 22.
The new prepared record SHA-256 is
`cf8a28aa76e192e49fcf98a1f36107470fec31242bac0757c2f8dc5b0aa50b36`.
The session held the shared action guard while awaiting its own attended
approval. The operator returned the exact token before its 22:55:38 KST
expiry.

## Corrected AP result

| KST on November 22 | Observed transition |
| --- | --- |
| 22:41:28 | Odin completed one boot-only transfer of the corrected candidate. Process quiescence passed. |
| 22:44:30 | The 180-second candidate readiness window closed as `NO_PROOF`, with no qualified Android ADB, root capture, or FDT marker capture. The boot stage remains unknown. |
| 22:50:36 | After the operator entered Download, the owner proved the exact endpoint on the prepared physical topology. |
| 22:50:43 | Odin completed one transfer of the original Magisk AP. |
| 22:51:30 | A fresh exact Android boot passed with Magisk 30.7, UID 0, and SELinux Enforcing. |
| 22:51:32 | The same returned boot proved the FDT marker absent. The terminal was published and the shared S20+ guard released. |

The candidate transfer SHA-256 is
`6c5104ef742f935b55deef426184e6bd7caf65dd10ccf52288d95aeb985efef1`.
The original rollback transfer SHA-256 is
`f72afa1db597042c5a5b73d646722f3a835eb4735fab7f2b0be1fda94157d309`.
The terminal SHA-256 is
`76bd800582989b93bcd4b8404a901f62379a6a649a11a90f9e512fea2870d0e3`.
The private close record SHA-256 is
`850b288d571e609acebe82a7769e4a57f84b91fd8472197c92a52531f29a60bc`.

Candidate and rollback transfer completions are one each. The exact
candidate content claim remains consumed. Both transfer replays are
forbidden. Recovery-partition operations and commands to other targets
were zero.
