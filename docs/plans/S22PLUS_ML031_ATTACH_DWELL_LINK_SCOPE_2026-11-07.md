# ML031: prospective attach-prepared five-minute UFS link candidate

Status: **H0 PROPOSAL — NOT ADOPTED FOR DEVICE EXECUTION**.

The operator requested a new successor after ML030, with the cable instruction
prepared before execution, H0 qualification and independent review. This
proposal records that exact successor. It does not reopen ML030, change the
common or target contract, select a live bridge review, or create a grant.
ML030 remains consumed and closed `NO_PROOF / ANDROID_CLOSED_HEALTHY`.

## Candidate and retained scope

ML031 uses a new random key and derived candidate identity. The physical
observer, canonical RAM archive, loader and boot-only AP are new artifacts.
The Image, DTB, fixed module and four signed Debian packages retain their
reviewed bytes and original provenance. Internal `ml030` symbol/module names
and protocol magic identify the retained implementation, not a reused grant.
Candidate authentication uses the new key and identity.

| Artifact | SHA-256 |
| --- | --- |
| Retained mainline Image | `19fc260fc880731167d3612804e34a0ea64c48efb1a46bdf7aee803d35a2bc3c` |
| Retained fixed g0q module | `7859073e9abfef8cb93202683046bec2878b3210c4703fc36eb6a1474a6615f8` |
| Retained physical DTB | `f918d3094e31428fa3f44fcc919934dbbcd819e48020c2bd129d952fb21346a0` |
| New physical observer | `83b329bf70ee06cae2a4653a6629d3a149b8f04953e960c70b0abda023b1d499` |
| New physical RAM archive | `c911585477282395579c4d21067baf1ff8b3c6d4aed6107dfb8040f12f4388db` |
| New uniLoader | `752a05d99cf7a9ec9f3a16b12d102bf22ce5537f02bbb741c0b39389e9d85e24` |
| New single-member boot-only AP | `64131da9daa9358009065f998748a56c7b24a607f5a028ee990cd7c2660027a3` |

If separately adopted, the proposed hardware scope is the same closed scope
as [ML030](../operations/S22PLUS_MAINLINE_UFS_LINK_V1.md): exact S22+ FYG8,
one attended operation of at most 1800 seconds, one N and one original A,
initial authenticated evidence within 120 seconds, then at least 300 seconds
between the sealed first response and the fresh same-connection challenge.
The second witness must prove the same boot/kernel/DT/PID1/observer, at least
300 seconds of additional guest uptime and zero block devices before the
separate one-shot module permit. Original host/guest 540-second ceilings and
the module's 15-second new-submission budget are retained.

The fixed late power/clock/reset/PHY preparation, six local UniPro commands
and at most one new DME_LINK_STARTUP are unchanged. Fresh completion, result
zero and the device-present transition remain the link criterion. Normal
Download requires the entire authenticated result, settled power commands
and released USB reference. Physical Download/original-A recovery and full
rooted Android health remain the fallback and closure requirements.
SCSI/media commands, fDeviceInit, LU or partition access, media-backed
filesystems, ICE/key operations, persistent installation and unattended
execution remain outside this proposal. No write or control may replay
after consumption or uncertainty.

## Prepared physical attach instruction

The separate fixed
[cue caller](../../workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py)
reuses the existing operation-local interlock and sealed records. Its imports,
actual raw-transfer consumer and fixed fixtures are checked before any future
N launch. It does not acquire USB/ADB evidence, create a background observer,
take the executing owner's target lease or alter its observation deadline.

The proposed physical condition remains one phone-end detach for about three
seconds and one reconnect using the same cable, host port and orientation,
without buttons. An instruction requires raw-complete N and its completed
step, the active original observation window with more than 60 seconds left,
the latest complete sealed ENOENT/no-child census, no selected endpoint or
request, no stop/return/terminal, and no active transfer. Actual identity,
grant, consumption and F1 owner must match. Arrival can still race the human
action; this procedure does not freeze USB or authorize a retry.

After a future approved launch, inspect the existing journal/window promptly
using the already prepared command. Do not spend the observation window
loading policy, finding modules or writing a caller. `check` reads existing
evidence; `issue` rechecks it under the existing local lock and durably records
the cue before returning an instruction. Display only
`CUE_RECORDED_DISPLAY_NOW`, immediately after another current-window check.
A delayed publication or post-publication exception returns
`CUE_RECORDED_DO_NOT_DISPLAY` with the retained cue and no instruction.
That record is never deleted or republished. An output/channel failure after
display begins is uncertainty, not proof that the operator saw nothing.

Record only the operator's actual completion or cancellation through
`resolve`. Silence and elapsed time are not a resolution. An unresolved cue
remains subject to the original interlock and deadline. Resolve it before a
separate physical Download instruction; a cable response is not a Download
confirmation. No additional readiness receipt or human approval gate is added.

## Adoption boundary

The present ML030 live validator deliberately rejects this new AP. The
existing common exception and target adoption still name ML030 alone.
Before ML031 can be a live task, its exact scope must be incorporated through
a separately reviewed common/target adoption and explicit candidate admission,
with the actual owner/bridge source closure reviewed for those changes.
Only then may fresh health/rollback checks and a returned exact finite attended
grant authorize execution. H0 candidate qualification and review alone do not.

The present work stops at the new candidate, prepared cue caller, H0 evidence
and independent review. It leaves all consumed ML030 artifacts, approvals,
journals and closure, as well as A90 and S20+, unchanged.
