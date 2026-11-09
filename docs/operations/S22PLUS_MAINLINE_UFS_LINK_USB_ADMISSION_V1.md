# S22+ ML034 mainline UFS link with bounded USB admission V1

Status: **REVIEW_GATED_CAPABILITY**

On 2026-11-10 the operator requested Argon/Opus discussion of ML033's USB
`EBUSY`, correction and continuation through the next physical experiment.
This policy adopts one prospective ML034 scope, subject to independent review
of the actual implementation and the live conditions below. ML033's precise
rejecting branch remains unobserved; this change cannot establish its historical
cause. Consumed ML028 and ML030–ML033 keep their original records and cannot
be repinned or replayed.

## Exact bounded unit

Only the qualified ML034 four-package Debian RAM root, new mainline Image,
fixed late module and fresh observer identity on SM-S906N / g0q /
S906NKSS7FYG8 may use this scope. The retained DT, guest functional source,
power/clock/reset/PHY/UniPro operations and attach caller keep their original
provenance. Internal `ml030` symbols and wire magic identify the implementation
family; the new artifact closure, key and candidate identity select this run.

| Artifact | SHA-256 |
| --- | --- |
| Mainline Image | `6a6c1c65bc7a9ea1ae2121d72782f87e9149531e76fff3d8f857459f13b91e15` |
| Fixed g0q module | `d08217055d940bb55f330a63070eaad9827badfd47cffa8ea77fa13f9cd5002e` |
| Physical RAM archive | `3143c31b128a882dd66d08e9e565da480cac32357277801c6668554e2746e1a6` |
| uniLoader | `a8142f6b02db500b5901afc618c4a5ae5bad97468dd8134a54430dcfa31a2032` |
| Single-member boot-only AP | `727a6b936ddcddac70d5a83110fd2bb0dada8133b1758e217a81fe6c0014cdce` |

The complete [ML030 observation, dispatch and return conditions](S22PLUS_MAINLINE_UFS_LINK_V1.md#observation-dispatch-and-return)
apply to this distinct candidate with its own task, grant, consumption and
original-A history. This adopts those conditions, not prior artifact tables,
approvals or consumed authority. The incorporated common details retain the
closed hardware scope.

One separately returned finite approval permits one attended operation in
1800 seconds, one N and one original A total. First authenticated evidence
must arrive within 120 seconds of N launch. At least 300 seconds from sealing
it to the fresh same-socket challenge, the same boot/kernel/DT/PID1/observer,
at least 300 seconds of additional guest uptime and zero block devices precede
the separate one-shot module permit. The original 540-second host/guest
ceilings, 15-second module budget, six fixed local UniPro commands and at most
one DME_LINK_STARTUP remain unchanged.

## USB admission and its evidence

All existing USB controller/driver identity, runtime-active PM, ICC path and
request, and completed ordinary BCM vote predicates remain required. Coverage
never resumes a device, creates a vote, changes a command cache or issues an
ordinary RPMh request. The ordinary-request prohibition remains specific to
the module's issuing task; calling that prohibition as a diagnostic is forbidden
because it latches failure.

After the single original `g0q_rpmh_begin`, and before any overlay, rail
registration or hardware probe, only these unsuccessful trylocks may cause
another complete coverage attempt: the USB device lock, ICC bandwidth lock,
global BCM-voter lock and selected voter's lock. Every failed leaf releases
all locks and PM/device references before a sleep or retry. Every other
identity, path, driver, PM, pending-commit, unknown/value or run-state failure
ends coverage immediately. There is no hardware-command retry.

At most 25 complete attempts are admitted inside a 250-millisecond local
interval and the original absolute 15-second deadline. Sleep requests are at
most 10 milliseconds and clamped to the remaining interval/deadline. Both
limits are checked before each attempt and again after a successful coverage;
a late success releases its acquired references and admits no hardware action.
Scheduling may delay return, but does not extend admission. No second begin,
deadline reset, overlay retry, PM resume or vote submission is added.

The new module emits exactly 21 decimal fields in the existing authenticated
256-byte payload. The first 19 retain their meaning. Word 20 packs final reason
in bits 0–7, first observed retryable lock reason in bits 8–15, total attempted
coverage calls in bits 16–23 and zero in bits 24–31. Word 21 contains only the
final failure's fixed scalar detail, zero after successful coverage. Details
use fixed indices/flags, API returns and lock-protected BCM values clamped to
0, 1, 2 or at least 3; no address, pointer or unrestricted dump is included.
Zero attempts is valid only for a run-state/deadline rejection before the first
call. A successful coverage can still precede a stage-zero or later operation
failure and is never sufficient for link success or normal return.

The exact independently qualified AP selects version 2. Legacy candidates keep
their 19-field version 1; there is no length-based autodetection or fallback.
Load/read errors retain their original raw/errno path and are not invented
coverage reports. The unchanged guest forwards the bounded raw payload; the
host validates the reason, detail, retry history and full original link result.

## Return, recovery and attachment

Normal Download still requires the complete authenticated successful link
result, settled power commands and released USB reference, followed by the
fixed reboot-mode/SCM NODUMP/PSCI path and exact Download ticket. Normal and
physical recovery share one original A total. Physical Download, complete
rooted original-A health and settlement of the owned network profile remain
recovery and closure conditions. Uncertain writes, transfers and controls
never repeat. SCSI/media commands, fDeviceInit, LU/partition access,
media-backed filesystems, ICE/key effects, a general shell, installation and
unattended execution remain excluded.

The [ML033 prepared attach-caller conditions](S22PLUS_MAINLINE_UFS_LINK_TIMED_ATTACH_V1.md#prepared-use-of-the-retained-attach-caller)
apply unchanged to this owner. The exact absent-endpoint proof, current owner,
latest sealed census, source/artifact/raw-integrity checks, original time
window and operation-local physical interlock remain mandatory. Preparatory
timing aims grant no effect or deadline extension. Only a successfully recorded
cue is displayed, and the operator resolves it before separate physical
Download instructions. No cue, request, control or transfer is replayed.

## Implementation and activation

ML034's exact AP declaration joins its new Image/module, physical archive,
loader, independent H0 review, input/evidence pins and actual producer/consumer
qualification. The new machinery requires its own review; retained reviews
cover only unchanged named inputs. Unknown or mixed bundles are rejected.
The existing Session, `mainline-download`, one-shot permit and
`ml030-return-intent` stage are reused under this distinct owner.

The current capability receipt is
`workspace/public/src/device-action/bindings/s22plus_mainline_ufs_link_usb_admission_v1_review.json`.
It must be independently PASS_GO for the reachable owner, authority, decoder,
cue, normal-return and recovery closure. Only those reviewed exact sources may
publish and select a new immutable backend review. Candidate-only validation
and cue source stay excluded from original-A recovery and health-only
prerequisites. Old reviews, grants and journals are not repinned.

Fresh target/host/health/rollback checks, exact artifact admission, usable
Download recovery, the returned exact finite approval and current physical
attendance remain required before execution. Scope adoption, model advice,
preparation and PASS_GO alone create no grant or device proof. Another successor
requires its own scope and cannot inherit this grant.
