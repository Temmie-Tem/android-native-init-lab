# S22+ first native baseline roundtrip H0 — 2026-09-10

## Bounded result

Internal **P383 / v0.2.0-rc.1** implements the first attended qualification:
Android → N → Download → the same N → fresh native health → Download → A →
final rooted FYG8/original-partition Android health. The attempted roundtrip
is unproved after a host USB observation failure; A transfer and final rooted
Android/original-partition health are verified, with CLOSED/19 and no recovery required. No native baseline adoption is claimed. P382/v0.1.2 remains
consumed, closed and unchanged.

The [common exception](../operations/S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1.md)
expressly specializes the permanent same-candidate repeat rule for one declared
restoration role. Relabelling N as rollback would not have authorized it.
The change retains boot-only payloads, exact target/rollback identities,
physical attendance, private evidence and the permanent installation claim.

## Implementation

The existing F1 owner handles initial installation and Android cleanup. The
new `s22plus_native_roundtrip_owner_v1.py` binds the three roles before approval
and owns the single exceptional restoration, using the same boot-only archive,
Odin, endpoint and bounded raw/receipt machinery. The second arrival has its
own immutable intent/delivery, observer guard/raw streams, CONTROL intent and
Download window. It cannot become an independent ordinary candidate run.

A fixed native-health EXEC proves numeric root, PID1 parentage, real proc/sys/dev
mounts, complete binary stdout/stderr and terminal status, followed by idle
STATUS. The second authenticated kernel boot identity and challenge must both
change before its CONTROL. A new challenge alone is insufficient. CONTROL ACK
remains acceptance-only; exact timely Download is independently observed.

Recovery cannot invoke N restoration or reopen either native console. A failed,
missing or uncertain A result cannot consume another A attempt. Result validation
reopens the original claim, restoration intent/delivery/raw result, both native
health streams and both Download windows; its role timeline is separate from
the ordinary journal's timeline. Final ownership retirement follows that
validation. A complete native proof survives a later local publication cut;
recovery does not upgrade an incomplete or failed native roundtrip.

One H0 cut exposed a pre-install Download-recovery reporting mismatch: the
P383 native no-proof validator expected the full candidate timeline even though
no candidate intent existed. The P383-only branch now accepts the existing
exact request-cut recovery timeline only with `candidate_classification=not-attempted`.
It does not invent candidate events or relax other variants.

## Validation

- **23 focused tests PASS**, including real generated P383 C authentication,
  supervisor/fork/pipes, fixed health and raw replay, plus the joined three-role
  owner, actual bounded writers, current USB/Download producer and Android final
  consumer against explicit hardware/transport fixtures.
- Joined normal close performs exactly N installation, one N restoration and
  one A cleanup. The original consumed claim remains retained; CLOSED recovery
  reopens evidence without another transfer.
- Eleven publication cuts cover exception-claim publication, restoration
  intent/delivery/result, second raw receipt, complete native proof, A start/
  result and CLOSED result publication. No role is repeated. A intent without
  a result parks. Completed native proof is retained across later local cuts.
- Actual short restoration-intent writes preserve partial bytes and allow only
  the predeclared A recovery. Same-kernel second arrival stops before CONTROL.
  Failed or uncertain restoration and Android results are not retried.
- **77 existing common live tests PASS**. Ordinary release/attempt/recovery
  semantics remain unchanged outside P383; no global registry bypass is added.
- Actual A/B build passed with identical APs: size **31,150,121**, SHA256
  `16d723931a86bcb9efe894743995fde8d151991520bd2adbc0853bb71ab8b119`.
  Both `/init` outputs are static ARM64 ELF. The new Image is size **41,490,944**,
  SHA256 `776e5a2461b2c3260bf084ef30844628dcaf562d38f958433e3204b02899c4f4`.
  Its identity-only IKCONFIG transform preserves compressed length/layout.
- Generated native helper bytes normalize exactly to P382 after the declared
  identity substitution. The renderer change is the prospective version label.
  No numeric syscall flag, native ABI behavior or module algorithm changes.

Raw H0 logs, fixtures and A/B artifacts stay under `workspace/private/`.
The tests' UUID/root/mount/USB/Odin/ADB facts are fixtures, not live health,
flashed-image or physical-recovery proof. The failed first image-layout attempt
and its log are retained; only the fresh exact-length identity is qualified.

## Independent review and readiness

Independent **PASS_GO** covers the complete changed execution closure and the
common-boundary specialization. The reviewer independently ran all 23 focused
tests, checked all 348 build inputs, both APs/45 cpio entries, native source
normalization and all 54 current static source bindings. The prior static
metadata predating the final policy/target text is preserved privately; the
fresh canonical result binds the current reviewed bytes.

- Candidate static: size **38,959**, SHA256
  `fd2cc2a87320cd418ba34e926f41fc4fd40f44f2574a21a00ff9a92302327d54`.
- Initial independent review: size **14,919**, SHA256
  `ca3117e8682e48d8d9ab0cc18056c35e10a8335263a8ff2edcf3ac48135b143e`.
- Final binding-correction PASS_GO: size **14,606**, SHA256
  `7baa608b661a3133c382c37e789ef310b9046bc27fc655a304da8241c955f379`.
- READY manifest: size **6,703**, SHA256
  `0e8ad44a2dea05067247cd0d3bb85ff06b160cab23fe9de2f43865f5845f0b70`.
- Verified READY bundle:
  `a13d7843452b07dbd9eedc36c0c4538433f866144c0b532609d9a62784e0b027`.

The unchanged foreground-goal capability's review was refreshed only for
`f1_owner`, `common` and `target`; the other six sources and eight actions are
unchanged. This refresh opens or renews no grant. No previous token, session
grant, manifest or consumed candidate is reused.

The corrected connected preparation below was completed before the operator
supplied its exact finite attended Process-v2 approval for the recorded attempt. The first qualification ends in Android;
standing native-baseline adoption and future faster loops remain a separate
bounded unit.

## First preparation and host binding correction

The first connected preparation at `p383-ready1-prepared-20260910-1` completed
D0 with `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Its exact target,
Android/root/original hash and bounded observer evidence remain unchanged.
It performed no reboot, Download request, Odin invocation or partition write.
The later host binding construction stopped with `KeyError: member`, before
`prepared.json`, any approval token or F1 intent existed.

The real `core.verify_bundle` adds `member` only to the candidate AP receipt;
the old generic fixture also supplied it for rollback. P383 preparation now
reopens the exact hash-verified Android AP with the existing boot-only reader
and derives its member identity explicitly. Later observer/control/recovery/
result paths validate that sealed identity without reopening the Android AP;
pre-restoration artifact checks still compare its actual member with the seal.
The joined fixture now uses the actual rollback receipt shape. All five joined
normal/cut/failure tests and 77 common live tests passed after this correction.

The successful original D0 and pre-correction static/promotion/READY bytes are
preserved privately. Their bundle binding is not rewritten to fit changed
sources. Fresh coherent H0 metadata and exact connected preparation bind the corrected
execution closure; no candidate or device effect is replayed.

The actual existing A also requires the ordinary rollback reader's
`require_deterministic_metadata=False` at both pin and member parsing; N keeps
`True`. The regression fixture now uses nonzero A tar UID/GID/mtime and the
actual pinned receipt producer. Both actual APs pass member derivation, and
current `core.verify_bundle → prepare_plan → _binding` passed without a device
call or prepared/token publication. The closure/binding body is 36,848 bytes.
The final correction review confirms these exact bytes and all 54 current
static bindings, with no remaining finding. Only the foreground `f1_owner`
review pin changed after the earlier refresh; all eight actions remain fixed.

## Corrected connected preparation

`p383-ready1-prepared-20260910-2` completed the exact D0 preparation with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. It verified current rooted FYG8
Android health, exact original boot/supporting hashes, target continuity and
Download absence. At that preparation stage, no reboot, mode change,
candidate/restore/cleanup transfer, F1 transaction or exception consumption
had occurred.

The new approval binding is
`938a3f15bbd75b8a03db4ba70b6339365dcd280b714219b7e9cd34e1d7008b9f`.
The private preparation owns exactly N installation, one N restoration and one
A cleanup/fallback with the fixed native health profile. The additional-command
plan was empty. Execution required a fresh approval with physical ability to
perform the demonstrated Download recovery; that approval was subsequently
supplied as recorded below.

## Attended attempt and final Android health

The operator supplied the exact prepared approval token. One original execute
used `p383-ready1-prepared-20260910-2`; no execute replay occurred. Source version
is commit `58dd85ddb4`, with the 86 unchanged prepared execution-source receipts.

| Evidence | Retained result |
| --- | --- |
| N installation | Completed once; transfer receipt `6d27de4c817b38f32b1f0ad91780e28b34fe63cb605fed6b47fd0b69872ed2aa` |
| First native health | Fixed command, complete output, terminal and idle STATUS proved; observer receipt `cb85ec9e2af3587b75b7f95b91a748a9c7d7bc3a1d731f71cc6cde251b78fa26` |
| First Download return | Exact arrival within CONTROL window; receipt `2dd5f95ff9e60905d49c0ac9f9fff1319a6bcc9720be3640c9acc0733e87808f` |
| Same-N restoration | Completed once with the identical AP; receipt `40b8e1e2aac22e1b9a414f2a3a287a044392896c578db84694e9c64fc6e549fd` |
| Second native health | Not reached; no second observer receipt or CONTROL intent |
| A fallback | Exact AP transferred once; receipt `216afb59403ccf3c2be9234eb4a903200583d5aa5b26a9aba95b2cc6d1aa64aa` |
| Final Android health | Verified on unchanged recovery continuation: exact target, rooted FYG8, original boot/supporting hashes and Download absence; CLOSED/19 |

At 03:59:36.770122Z, the second arrival's first USB inventory acquisition stopped
with `UsbfsInventoryMembershipChanged` / `inventory-membership-changed` before
snapshot publication. Its raw diagnostic reports one removed former Download
node. Diagnostic size423/SHA256
`26558209d667efc9be3e9fc43e8c0b3d2d0494efe34f951599768b23ebe66936`
is retained in the child `odin-endpoints/diagnostics` directory with the raw
USB identity captures. A reboot/enumeration timing overlap is an inference;
this record does not establish a device boot failure. After the stop, the
operator initially reported booting/no bootloop, then clarified that the second
boot stayed at the boot screen and never showed the native screen. The clarified
physical observation supersedes any interpretation that native boot completed;
it does not locate the stopped execution stage.

The research stop was retained. No second console open, CONTROL or N retry was
issued. The separately preapproved recovery reidentified exact Download and
completed A once. Its first final Android wait expired with no online matching
ADB target. That invocation left ROLLBACK_FLASHED/15, without final-health proof.
The operator subsequently reported Android. A fresh bounded raw-first ADB
inventory found the expected model/device online; the unchanged recovery owner
then rechecked exact private target continuity and all final health predicates.
It resumed from ROLLBACK_FLASHED and performed no further transfer. At
04:17:46.471890Z the journal reached **CLOSED/19**, terminal verdict
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p383_root_console_unproved_rollback_verified`, `recovery_required=false`.
The installation and exceptional restoration claims remain consumed.

Terminal live-result size **43,004**, SHA256
`e98585dce243ffdd699c9e4ddc2fbaf2586221346a695fc4d7b11ccf1f2e118f`.
The final stock observer remains `NO_PROOF_OBSERVER`; successful Android
recovery does not upgrade native roundtrip or causal proof. The original
execute and first recovery errors are retained alongside the exit-0 recovery
continuation. No source change, ADB reconnect/server reset or added reboot was
used. The temporary offline state is observed; its underlying cause remains
unproved. It is separate from the earlier USB inventory acquisition failure.

The completed original canonical timeline contains:

| Event | UTC |
| --- | --- |
| live_session_start | 2026-09-10T03:58:47.432350Z |
| candidate_flash_start | 2026-09-10T03:59:05.185769Z |
| candidate_flash_done | 2026-09-10T03:59:06.819324Z |
| candidate_boot_ready | 2026-09-10T03:59:20.112952Z |
| rollback_flash_start | 2026-09-10T04:03:57.074857Z |
| rollback_flash_done | 2026-09-10T04:03:58.624435Z |
| rollback_boot_ready | 2026-09-10T04:17:46.450885Z |
| live_session_end | 2026-09-10T04:17:46.471890Z |

The linked restoration intent/delivery/result accounts for the additional N
transfer; the ordinary journal's candidate/rollback counters remain1/1.
There were three physical boot-only transfers in total. A90/S20+ were untouched.
No physical-input request or recovery action remains pending for this run.
No standing native baseline adoption or version promotion follows.

Reporting validation preserves every preexisting ledger byte and adds only the
three P383 attempt/recovery/close rows. Scoped diff/link/private-identifier checks
pass. The legacy ledger suite is blocked at existing log row547 (unknown evidence
outcome), reproduced identically from pre-change HEAD and the working ledger;
the methodology suite also retains a preexisting 54-versus-62 incident-count
mismatch. These unrelated historical checks are not reported as passing or
changed to qualify this run. No execution source changed during consumption or
recovery.

## Second-screen clarification and H0 control-flow diagnosis

The operator clarified that arrival2 remained at the boot screen, with no native
screen. No device action was performed for this follow-up. Reopening the current
P383 generated helper establishes the order: OPEN/AUTH and BOOT_ID frame,
return/root-work preparation, `rc1_console`, then `hud1_start`. The HUD is therefore
conditional on the host opening and authenticating the console; it is not an
autonomous pre-authentication boot witness. The source insertion is in
`s22plus_fyg8_p376_research_shell_runtime.py`; P383 retains that order through its
sealed predecessor projection. The current generated helper was inspected,
not merely the predecessor text.

The second host path stopped in USB inventory acquisition before opening its
observer, and no second authenticated stream exists. Consequently the host
failure prevented the required handshake for starting the HUD. This provides a
concrete explanation compatible with the unchanged boot screen even if native
PID1 had started. It does **not** prove that PID1 reached its listener, exclude
an additional kernel/native startup failure, or establish that fixing the host
race alone would make arrival2 healthy. There is no second-arrival kernel/PID1
trace to distinguish those cases. Same-AP transfer completion and first-arrival
success do not fill this gap. The earlier implication that the second native
boot was healthy was unsupported; the result remains NO_PROOF with Android
recovery independently verified.

## Structural coupling and follow-up scope

The original [P376 HUD contract](../operations/S22PLUS_FYG8_BOOT_HUD_V1.md#scope-and-ownership)
explicitly scoped the display to an authenticated console's status and excluded
a standalone boot UI. The [P376 report](S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md#result-and-limits)
records that same scope. Reusing console supervision, snapshots, deadline and
CONTROL cleanup is visible in the implementation; treating that reuse as the
original designer's primary motivation would be an inference. Rendering itself
does not require host authentication: the HUD child receives fixed local
snapshots and does not inherit the authentication key or USB console descriptors.

As the HUD became a system/boot-status display, its startup and lifetime remained
inside the authenticated console. This is a confirmed structural coupling that
limits boot diagnosis: host observation failure prevents starting the local
screen as well. Reusing earlier code is not itself the defect; retaining an old
execution dependency after the component's purpose expands is the issue here.
This finding does not establish a second-arrival kernel boot failure.

| Item | Current evidence and follow-up |
| --- | --- |
| HOST — second USB observation | Inventory membership changed before snapshot publication and authentication. Diagnose and exercise the actual reboot/enumeration transition before selecting a repair; a timing race is inferred, and no repair is implemented. |
| DISPLAY — host-dependent HUD | Generated control flow confirms authentication precedes HUD startup. Proposed follow-up: let PID1 supervise local display and authenticated console separately, provide a local waiting/failure indication, and keep command execution and CONTROL authenticated. Independent startup and safe lifetime/cleanup still need design and validation. |
| RETURN — temporary ADB offline | The first final-health wait expired; later online enumeration and exact health verification closed the same journal without another transfer. Underlying offline cause remains unproved; recovery completion is verified. |
| Second kernel/PID1 progress | No second authenticated or kernel trace establishes the reached stage. Preserve this as an evidence gap, not a confirmed boot defect. |

This update records findings and prospective work only. It changes no runtime,
reviewed HUD contract, consumed source binding or run result. The existing
[checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md) incorporates the
HOST, DISPLAY and RETURN lessons without adding a new execution gate. P383 stays
consumed, NO_PROOF and CLOSED/19 with verified Android recovery; v0.1.2 remains
the functional version. Screen separation and host repair are not implemented
or qualified by this documentation update.

Subsequent H0 work completed the [direct-source refactor](S22PLUS_FYG8_NATIVE_SOURCE_REFACTOR_1A_H0_2026-09-10.md),
[local display lifecycle](S22PLUS_FYG8_LOCAL_DISPLAY_REFACTOR_1B_H0_2026-09-10.md),
[compatible observer](S22PLUS_FYG8_LOCAL_DISPLAY_OBSERVER_1C_H0_2026-09-10.md)
and [completed-restoration arrival repair](S22PLUS_FYG8_RESTORATION_ARRIVAL_H0_2026-09-10.md),
each with independent PASS_GO. The table above records the original assessment.
These later implementations preserve this execution record and do not prove
the historical second boot, reopen consumed authority or explain ADB offline.
