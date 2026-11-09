# ML032: prospective UFS link candidate with a refreshed attach census

Status: **H0 PROPOSAL — NOT ADOPTED FOR DEVICE EXECUTION**.

ML032 is a fresh successor to consumed ML030 and ML031. Both old operations
remain `NO_PROOF / ANDROID_CLOSED_HEALTHY`; their approvals, artifacts and
journals cannot be repinned or replayed. This proposal supplies one concrete
candidate and corrected attach caller for independent review. It does not
change common/target authority, select a live bridge review or open a grant.

## Candidate and unchanged effect limits

The unchanged producer generated new physical and VM authentication keys and
candidate identities. The observer, canonical RAM archive, loader and boot-only
AP are new. The Image, DTB, fixed module and four signed Debian packages retain
their original reviewed bytes and provenance. Internal `ml030` names and wire
magic still identify the retained implementation family.

| Artifact | SHA-256 |
| --- | --- |
| Retained mainline Image | `19fc260fc880731167d3612804e34a0ea64c48efb1a46bdf7aee803d35a2bc3c` |
| Retained fixed g0q module | `7859073e9abfef8cb93202683046bec2878b3210c4703fc36eb6a1474a6615f8` |
| Retained physical DTB | `f918d3094e31428fa3f44fcc919934dbbcd819e48020c2bd129d952fb21346a0` |
| New physical observer | `131f92f1a6cc8217dafabed08b22d852016668cc48f53f133c4d4f802d47d763` |
| New physical RAM archive | `0ab1ba484aba5dffa171c963feb9718824eee46c726576ef8bfa5999d44c2808` |
| New uniLoader | `b15aeab452d4c88345f13b92cc9c50865906c10359af49a2d96e0f40f7ba066f` |
| New single-member boot-only AP | `797e10947ba7706367bc04ff0ab170fe808956839235420505ddc42fa2a04f92` |

If separately adopted, this exact SM-S906N / g0q / S906NKSS7FYG8 candidate
would retain the closed [ML030 hardware and observation scope](../operations/S22PLUS_MAINLINE_UFS_LINK_V1.md)
and [ML031 followup limits](../operations/S22PLUS_MAINLINE_UFS_LINK_FOLLOWUP_V1.md):
one attended operation of at most 1800 seconds, one N and one original A,
first authenticated evidence within 120 seconds, then at least 300 seconds
from sealing it to the fresh same-socket challenge. The second witness must
join the same boot/kernel/DT/PID1/observer, at least 300 seconds of additional
guest uptime and zero block devices before the separate one-shot module permit.
The original 540-second host/guest ceilings and 15-second module submission
budget remain unchanged.

Only the fixed late power/clock/reset/PHY preparation, six local UniPro commands
and at most one newly issued DME_LINK_STARTUP are proposed. Fresh completion,
result zero and device-present transition remain separate from issuance.
Normal Download requires the complete authenticated successful link result,
settled power commands and released USB reference. Physical Download and one
original A total remain the recovery route, followed by complete rooted Android
health and settlement of any owned network profile. SCSI/media commands,
fDeviceInit, LU/partition access, media-backed filesystems, ICE/key operations,
general shell, installation and unattended execution remain excluded.
Uncertain writes, transfers and controls never repeat.

## Corrected attach caller and prepared use

The [fixed caller](../../workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py)
retains the existing operation-local interlock and physical condition: one
phone-end detach for about three seconds, then one reconnect with the same
cable, host port and orientation, without buttons. It reads existing sealed
evidence only; it adds no device acquisition, background observer, lease or
observation-window extension.

Both existing owner/source/artifact guards complete before selecting the
latest complete census. After the second guard, the caller rechecks journal
and forbidden states, selects and fully validates the current sealed census,
then performs the short final journal/state, latest-census, raw-integrity and
remaining-window checks. A newer census during that final check still refuses
issuance. Present, partial, failed, changed or other-topology evidence cannot
fall back to an older absence. The change removes the requirement that an
ordinal stay fixed during the expensive guard; it preserves the final latest
and integrity requirements.

Raw-complete N and completed installation, the active original window with
more than 60 seconds left, exact ENOENT/no-child evidence, no selected endpoint
or request, no stop/return/terminal/active transfer, and matching current
grant/consumption/F1 owner remain mandatory. Neither USB absence nor a cue
proves health or recovery. Arrival can still race the physical action.

Before any future N, load the CLI and prepare its exact approved operation
path and private, non-overwriting stdout/stderr destinations. Capture both
streams and exit status before interpretation. A refusal emits
`CUE_CALL_REFUSED` with its phase, error and selected/latest census paths when
available. This diagnostic does not prove that publication never happened.
Use the existing journal/window promptly after N; do not spend its observation
window building the caller or loading policy.

Display only `CUE_RECORDED_DISPLAY_NOW`, immediately while more than 60 seconds
remain. `CUE_RECORDED_DO_NOT_DISPLAY`, a nonzero exit or an output failure must
not produce an instruction or an automatic retry. Preserve any durable cue;
do not delete, republish or assume non-delivery. Record only the operator's
actual completion/cancellation through the original `resolve` interlock.
Silence is not resolution. Resolve any issued cue before a separate physical
Download instruction; a cable response is not a Download confirmation.

## Adoption boundary

Current common/target delegations and exact image admission name ML030 and
ML031 only. The current image validator deliberately rejects this new AP.
ML032 requires its own reviewed common/target scope adoption, explicit exact
candidate admission and current owner/bridge source review before preparation
as a live task. Fresh target/health/rollback checks, usable Download recovery,
the returned exact finite approval and current attendance remain required.
H0 qualification and independent PASS_GO alone grant no physical action.

This unit ends with corrected caller behavior, the fresh candidate, H0 evidence
and independent review. It changes no consumed record or other target.
