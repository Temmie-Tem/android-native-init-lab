# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This goal reports state, never device authority. The binding layers are
`AGENTS.md`, `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Select only
`SM-S906N/g0q/S906NKSS7FYG8`; A90 and S20+ remain isolated.

## Current bounded unit

Changed-path regression reference: [past failure checklist](docs/operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md).

P366 reporting is complete. One candidate, one CONTROL and one exact Magisk
rollback were consumed; rollback transfer completed and Android return was
observed by the operator and host. The experiment remains NO_PROOF: the native
return consumer required a missing legacy P318 producer record. Recovery-only
rebinding preserved the lost physical continuity and original evidence.

Automated terminal publication is incomplete: the journal remains
ROLLBACK_FLASHED/15, with no CLOSED/19 or terminal live-result. A raw-capture
filename collision and then a separate device's Download endpoint blocked
final validation. This does not undo the completed rollback. Report the
retained health evidence without claiming a full final-health PASS. At the
operator's direction, finish reporting with no additional device action or
request to disconnect another device. No candidate, CONTROL or rollback replay
is permitted; no next F1 is active. See the [P366 incident report](docs/reports/S22PLUS_FYG8_P366_NATIVE_USB_DEPARTURE_PREPARATION_2026-09-08.md).

P365 is consumed and CLOSED/19 after one candidate and one exact Magisk rollback.
Its corrected ARM64 flags passed all preparation stages: 46 authenticated progress
records, ten swap submissions and accepted Download CONTROL were retained.
The operator reported changing screen output, then screen-off and automatic
Download entry without physical intervention. This is operator observation;
the machine's bounded Download-arrival proof remains unproved.

The original execution stopped during initial USB inventory after CONTROL
acceptance; its original inner exception/path was not retained. Same-journal
rollback-only recovery verified exact rooted FYG8, original hashes, Android
health and absent Download. Verdict `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`,
recovery_required=false. The 40,414-byte live state and 45,270-byte result were
published without a persistence repair. No candidate or CONTROL replay occurred.
See the [P365 report](docs/reports/S22PLUS_FYG8_P365_ARM64_AND_PERSISTENCE_PREPARATION_2026-09-08.md).
The consumed successor is [P366](docs/reports/S22PLUS_FYG8_P366_NATIVE_USB_DEPARTURE_PREPARATION_2026-09-08.md): preserve initial-inventory failure classes and
observe the exactly bound outgoing native USB node before unchanged strict Odin
arrival checks within the same 30-second window. P365's historical inner cause
remains unproved. A/B build, static/bundle checks, independent boundary
and artifact reviews, 22 new tests and 77 regressions passed. Fresh D0 passed
without D1 reboot; the 32,823-byte preparation reopened against the real bundle.
The preparation was consumed by the P366 execution described above.
A90/S20+ received no command from this unit.

P364 is consumed and CLOSED/19 after one candidate and one exact Magisk rollback.
Verdict `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, proof class `NO_PROOF_OBSERVER`,
recovery_required=false. Final rooted FYG8, original boot/supporting hashes,
Android health and absent Download were verified. A90/S20+ received no command.

The new diagnostic channel retained 28 authenticated progress frames: the first
four module file checks/insertion/close calls returned zero, then the SDAM
provider checker (stage 30) returned -22/EINVAL and a signed terminal repeated
that error. The diagnostic frame itself does not identify an inner syscall. Renderer creation and
Download CONTROL were not reached; no visible display or native return is
claimed. Physical Download entry enabled the exact preapproved rollback.

Final result publication initially rejected the deliberately shared P363-named
return-state fields. A reviewed CLOSED-only host repair revalidated the original
prepared closure and raw evidence, preserved all 7,119 existing run files and
published the terminal result without a device action or changes to live-state
or append-only journal-record contents. Later audit found that the repairing
reopen replaced the same-byte journal-head index; metadata was not preserved.
The reusable validator now admits only the three exact shared names for native
return owners; other foreign names remain rejected. Consumed pins are unchanged.
Completed H0 analysis found an ARM64 open-flag ABI mismatch in the transferred
binary: directory literal 0200000 means O_DIRECT, which sysfs rejects with
EINVAL. The unchanged ARM64 function reproduces the first-open failure; changing
only to target O_DIRECTORY=040000 makes the host fixture pass. The same old
source passes on x86. Module literal0400000 also omitted the intended ARM64
O_NOFOLLOW=0100000 protection; no symlink substitution was observed. Earlier
host stubs ignored these flags. The analysis preserves the frame's lack of an
inner-syscall witness and does not prove later preparation or display/return.
No next candidate, active lease or new F1 authority exists. A successor requires
target-correct directory/no-follow flags, real ARM64 behavior checks and its
existing changed-closure review/qualification. Consumed sources remain frozen.
Report: [P364 preparation diagnostics](docs/reports/S22PLUS_FYG8_P364_PREPARATION_DIAGNOSTICS_2026-09-08.md).

The historical-failure applicability audit found a further current persistence
issue: a representative state with validated success projections is 37,750 bytes
and the actual 32-KiB state writer rejects it. This is a hybrid sizing fixture,
not a complete successful terminal run. A successor needs success/late-failure
producer-to-writer roundtrips and a scoped persistence correction in addition
to the ARM64 flag repairs. Earlier pipe, timing, numeric identity and host-first
OPEN corrections remain present.
Report: [Historical failure applicability audit](docs/reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md).

## Completed P363 post-run analysis

Post-run H0 analysis and two exact root D0 metadata invocations are complete.
The bound raw prefix replays successfully through authentication, kernel boot
identity, parent identity and the full sequence-4 display-frame host write.
The failure is the later readiness wait, not failed authentication. Actual C
and the transferred init disassembly confirm that a preparation error is
silently parked before renderer creation. Two injected errors reproduce the
365/208-byte exchange shape and timeout; neither identifies the original errno.
Current stock provider paths/module presence and candidate debugfs support were
checked, with exact same-boot health before/after D0. The first failing native
call remains unproved because no preparation-stage/error witness was retained.
The next bounded requirement is a fixed stage/errno witness before terminal park;
no successor runtime or F1 is activated and the renderer remains unchanged.
Report: [P363 preparation-path analysis](docs/reports/S22PLUS_FYG8_P363_POSTRUN_PREPARATION_PATH_ANALYSIS_2026-09-08.md).

P363 is consumed and CLOSED/19 after one candidate and one exact Magisk
rollback. Verdict `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, proof class
`NO_PROOF_OBSERVER`, recovery_required=false. The operator reported no pattern,
only a black screen or logo; repeated display and native Download remain
unproved. The authenticated exchange ended after about 60 seconds without a
completed session, durable CONTROL intent or ACK. Its return-window record is
`not-requested`; no successful native return is inferred.

The original execute then stopped at USB snapshot23 with
`usbfs-endpoint-departed` before a snapshot was published and before rollback
intent. Physical cause remains unproved. The operator entered physical Download;
one same-journal rollback-only recovery completed exact Magisk rollback and
final rooted FYG8/original boot/supporting hashes/Android health/absent Download.
The live result is 20,832 bytes, SHA256 prefix `b1d4dbe1`. Candidate, display and
control were never replayed. No active lease, successor F1 or automatic recovery
is authorized. A90/S20+ received no command from this task.

The completed H0 qualification remains distinct from the failed live proof.
Its exact five stock reason/provider modules, retained ten-swap renderer and
kernel boot identity do not establish runtime module preparation, visible
output or native return. The FULLDUMP initialization window and stock NVMEM
error hazard remain documented. Any follow-up begins with the preserved raw
observer evidence and actual consumer; no next device experiment is selected.

Preparation's preceding ordinary-reboot D1 also retains its separate
240-second healthy-return timeout and STOPPED/consumed NO_PROOF result.
Independent late D0 and fresh preparation established then-current health,
not bounded D1 return or automatic recovery. Neither failed invocation is
reclassified or replayable.
Report: [P363 native return control result](docs/reports/S22PLUS_FYG8_P363_NATIVE_RETURN_CONTROL_PREPARATION_2026-09-08.md).

## Completed P362 investigation

P362 reboot/Download investigation is complete at H0 plus one fixed D0 module
census. Healthy Android contains the Samsung reboot-reason/provider modules
missing from the P361 native plan; the current Image has a confirmed PSCI reset
handler. Both applicable DT bases across all 11 overlays preserve enabled reboot
nodes. A90 source illustrates native-owned reboot/recovery calls, not transferable
Download proof. P361 has no post-display command receive path and its renderer
lacks reboot capability. Native normal reboot and Download remain unproved.

Follow-up narrowed the candidate addition to five modules: sec_reboot_cmd,
sec_qc_rbcmd, sec_qc_qcom_reboot_reason, qcom-dload-mode and
nvmem_qcom-spmi-sdam. Their 87-module union has 4,532 imports and zero H0
resolution/CRC failures. Runtime probe/return remain unproved. Command-table
registration is asynchronous; module presence alone is insufficient. The
existing wire boot_id is a native-generated token, so a new restart qualification
must explicitly bind kernel boot identity. Ordinary same-PID1 reboot remains
an intentional separate control action from Download/rollback.

P362 itself changed no production runtime or automatic F1 policy and performed
no new D1/F1 effect. Normal reboot would keep the candidate boot installed.
Its D0 preserved exact same-boot
rooted FYG8/original hashes/Android health; A90/S20+ were not commanded.
Report: [P362 reboot and Download analysis](docs/reports/S22PLUS_FYG8_P362_REBOOT_DOWNLOAD_PATH_ANALYSIS_2026-09-07.md).

## Consumed P361 repeated display

P361 is consumed and CLOSED/19, recovery_required=false. One CACHED ABGR8888
repeated-frame candidate and one exact Magisk rollback transferred. The operator
reported repeated alternation and final first-pattern hold normal without
corruption. This qualifies bounded operator-observed repeated display; exact
count/cadence, pixel readback, redraw and PID1 heartbeat/HUD remain unproved.

Machine verdict `PASS_F1_V2_P361_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`
remains dispatch/rollback evidence. Live result `22803B/7c571019`. Original
execute stopped after observation, before rollback intent, on measured USB
endpoint evidence: snapshot103, usbfs-endpoint-departed, no snapshot persisted.
Its physical cause remains unproved. One same-journal rollback-only recovery
completed exact Magisk rollback and final rooted FYG8/original hashes/Android
health/absent Download. Candidate and observation were never replayed.
No active lease remains. A90/S20+ received no command from this task; no successor
F1 or standing native runtime is granted.
Report: [P361 repeated-frame result](docs/reports/S22PLUS_FYG8_P361_REPEATED_FRAME_PREPARATION_2026-09-07.md).

## Consumed P360 transition

P360 is consumed and CLOSED/19, recovery_required=false. One CACHED ABGR8888
two-frame candidate and one exact Magisk rollback transferred. The operator
reported both frames normal and transition to the numeral 2. This qualifies the
bounded operator-observed first-to-second transition without reported corruption;
it does not prove pixel-exact readback, panel timing or repeated/general flips.

Machine verdict `PASS_F1_V2_P360_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`
remains dispatch/rollback evidence. Live result `22805B/7bd7c40c`; original
execute completed without recovery re-entry. Final rooted FYG8, original boot
and supporting hashes, Android health and absent Download passed. No active
lease remains. Candidate and observation are never replayable. A90/S20+ received
no command from this task; no successor F1 or standing native runtime is granted.
Report: [P360 two-frame result](docs/reports/S22PLUS_FYG8_P360_TWO_FRAME_PREPARATION_2026-09-07.md).

## Consumed P359 pattern

P359 is consumed and CLOSED/19, recovery_required=false. One CACHED ABGR8888
RGB/grid/edge candidate and one exact Magisk rollback transferred. The operator
reported the pattern and border normal without breakup and supplied a photograph
corroborating correct RGB positions, regular grid and white perimeter. This
qualifies the bounded operator-observed static pattern; photographic evidence
is not pixel-exact readback or cache-causality proof.

Machine verdict `PASS_F1_V2_P359_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`
remains dispatch/rollback evidence. Live result `22805B/686a99f7`; original execute
completed without recovery re-entry. Final rooted FYG8, original boot/supporting
hashes, Android health and absent Download passed. No active lease remains.
Candidate and observation are never replayable. A90/S20+ received no command
from this task; no successor F1 or standing native runtime is authorized.
Report: [P359 pattern result](docs/reports/S22PLUS_FYG8_P359_CACHED_PATTERN_PREPARATION_2026-09-07.md).

## Consumed P358 comparison

P358 is consumed and CLOSED/19, recovery_required=false. One CACHED ABGR8888
ordinary-buffer candidate and one exact Magisk rollback transferred. The operator
reported **full clean magenta**, whereas WC P356/P357 were corrupt. This is the
first clean ordinary-buffer observation in this comparison; it supports the
CACHED path but does not isolate cache coherency from mmap/DMA-map timing.

The machine verdict is `PASS_F1_V2_P358_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`;
it proves dispatch and rollback, not visible output. Live result is
`22805B/f6467449`. Original execute stopped on measured USB endpoint evidence
while awaiting physical Download after observation, before rollback intent. One
same-journal preauthorized recovery completed the exact rollback and final rooted
FYG8/original hashes/Android health/absent Download checks. The initial error
remains unexplained; candidate and observation were never replayed.

No active lease remains. P358 is never replayable; A90/S20+ received no command
from this task. A next bounded patterned-frame comparison using CACHED is a
possible follow-up, not an activated successor or proof of a general display
runtime. Historical WC failure evidence and source closures remain intact.
Report: [P358 clean cached-buffer result](docs/reports/S22PLUS_FYG8_P358_CACHED_FRAMEBUFFER_PREPARATION_2026-09-07.md).

## Consumed P357 comparison

P357 is consumed and CLOSED/19, recovery_required=false. One opaque ABGR8888
ordinary-buffer candidate and one exact Magisk rollback transferred. The original
execute completed without recovery re-entry; final rooted FYG8, original
boot/supporting hashes, Android health and absent Download passed. No active
lease remains. P357 is never replayable; A90/S20+ received no command.

The operator reported magenta with stripes/corruption. **Clean framebuffer output
was not achieved.** The format/opaque-alpha change alone did not resolve the
observed issue; cache, mapping, scaler, bandwidth and timing causes remain
unproved. P355 hardware fill was clean, while P356 and P357 ordinary buffers
were corrupt. Machine verdict
`PASS_F1_V2_P357_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK` proves dispatch and
recovery only. Live result is `22805B/a653d9f9`. No next experiment is activated.

During recovery, byte-preserving sparse conversion of four owned P357 packaging
intermediates reclaimed 228,515,840 bytes; space afterward was about 402 MiB.
Retained artifacts/evidence were not deleted.
Report: [P357 opaque ABGR result](docs/reports/S22PLUS_FYG8_P357_ABGR_FRAMEBUFFER_PREPARATION_2026-09-07.md).

## Consumed P356 comparison

P356 is consumed and CLOSED/19, recovery_required=false. One ordinary-buffer
magenta candidate and one exact Magisk rollback transferred; final rooted FYG8,
original boot/supporting hashes and absent Download pass. The machine verdict
is `PASS_F1_V2_P356_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`, proving dispatch
and recovery, not clean visual output. Live result is `22804B/5669fe05`.

The operator and private photo show magenta with horizontal dark breaks and
severe lower-area corruption. **Clean ordinary-buffer magenta was not achieved.**
P355 hardware fill was clean; P353/P354 patterned buffers and P356 constant
buffer were corrupt. A supplied Android-boot carrier-logo photo lacks the same
conspicuous breakup. This supports H0 comparison of the native buffer/display
setup with Android; cache, format, mapping, scaler and timing causes remain
unproved. No next candidate or new device action is authorized by this finding.

The original execute stopped on measured USB endpoint evidence while awaiting
physical Download after observation, before rollback intent. One same-journal
preauthorized recovery completed exact rollback and health without candidate or
observation replay. The error remains unexplained. The separate earlier D1
ADB-timeout start and missing success result also remain intact; manual USB
restoration and late health never rewrote that result. No active lease remains,
and A90/S20+ received no command. P353 through P356 are never replayable.
Report: [P356 framebuffer magenta result](docs/reports/S22PLUS_FYG8_P356_FRAMEBUFFER_MAGENTA_PREPARATION_2026-09-07.md).

## Consumed P355 comparison

P355 is consumed and CLOSED/19, recovery_required=false. Candidate
`30965801B/d100d9bc` and exact Magisk rollback `23367721B/d2373bf8` transferred
once each. Final rooted FYG8, original boot/supporting hashes and absent Download
pass. The machine verdict is `PASS_F1_V2_P355_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`;
it proves authenticated host dispatch and rollback, not internal display state.
Live result is `22805B/0fcd7a1e`.

The operator reported a full magenta field with no visible corruption and
supplied a corroborating private photo. The prior horizontal speckles and
lower-area breakup are absent in that image. **Clean magenta was observed with the solid-fill candidate**, while P353/P354's ordinary pattern-buffer output was corrupt.
The same 30HS mode and noise disable were retained. This narrows further H0
investigation toward the normal buffer-fetch/format/scaler path; it does not
alone establish a cache fault or exclude every downstream contribution, because
solid fill also changes internal format/scaler/source geometry. Machine proof
and operator/photo evidence remain distinct. Supplemental Carrier is ambiguous
and supplies no causal proof.

The original execute invocation stopped on measured USB endpoint inventory while
awaiting physical Download, before rollback intent/transfer. One same-journal
preauthorized recovery completed the exact rollback; candidate and observation
were never replayed. The original failure is preserved and its cause remains
unproved. No active native shell or standing device authority remains. P353,
P354 and P355 are never replayable; A90/S20+ received no command.
Report: [P355 clean magenta and recovered close](docs/reports/S22PLUS_FYG8_P355_HARDWARE_SOLID_FILL_PREPARATION_2026-09-07.md).

## Consumed P354 comparison

P354 is consumed and CLOSED/19, recovery_required=false. Candidate
`30965801B/bc48a71f` and exact Magisk rollback `23367721B/d2373bf8` transferred
once each in the original execution, without replay or a recovery restart.
Final rooted FYG8, original boot/supporting hashes and absent Download passed.
The machine verdict is `PASS_F1_V2_P354_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`;
it establishes authenticated host dispatch and rollback, not pixel fidelity.
Live result is `22805B/ab4ff2f3`.

The same P353 pattern/buffer/30HS candidate with explicit `noise_layer_v1=0`
showed the same corruption to the operator. The private photo again shows the
recognizable red/blue/green/black-cross pattern, horizontal speckles and extensive
lower-area corruption. **No visible improvement was observed.** This does not
establish the property's runtime execution or exclude every noise-related cause;
post-dispatch execution telemetry remains absent. Clean image quality and the
failure mechanism remain unproved. Supplemental Carrier is ambiguous and supplies
no causal proof. Operator/photo evidence does not promote the machine receipt.

The bounded run is complete. No active shell or standing device authority
remains. P353/P354 are never replayable; A90/S20+ received no command. A further
comparison would use the previously qualified hardware magenta solid-fill design
in a fresh successor to help distinguish the buffer-fetch path from remaining
display processing. It is not implemented or authorized by this goal.
Report: [P354 noise-disable comparison and closed result](docs/reports/S22PLUS_FYG8_P354_NOISE_DISABLE_H0_2026-09-07.md).

## Consumed P353 and H0 diagnosis

P353 is consumed and CLOSED/19, recovery_required=false. Candidate
`30965801B/a4515202` and exact Magisk rollback `23367721B/d2373bf8` transferred
once each in the original execution, without replay or a recovery restart.
Final rooted FYG8, original boot/supporting hashes and absent Download passed.
The machine verdict is `PASS_F1_V2_P353_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`;
it proves authenticated host dispatch and rollback, not pixel fidelity.

The operator saw the unique red/blue/green and black-cross pattern replacing
the boot logo and supplied a photo. The photo also shows unintended horizontal
speckles and substantial lower-area corruption. The narrow first-image
observation is supported **with visible corruption**; clean image quality and
its failure mechanism remain unproved. Actual paint code contains only uniform
fills and solid regions, with no noise generation. Photo and visual statements
are private; machine evidence was not promoted by the operator witness.

Supplemental Carrier is ambiguous (`P320 Carrier generations differ`) and
supplies no causal proof. Live result is `22804B/eb437b9a`. No active shell or
standing device authority remains. A90 and S20+ were untouched. Any follow-up
starts from H0 diagnosis of image corruption and requires a fresh candidate
binding for another experiment; this goal grants no device authority.
Report: [P353 static image and closed result](docs/reports/S22PLUS_FYG8_P353_STATIC_FIRST_FRAME_PREPARATION_2026-09-07.md).

The subsequent H0 corruption audit runs the exact consumed AArch64 renderer in
user-mode QEMU: all 10183680 paint bytes match an independent rectangle oracle,
including row padding. Source and consumed-module checks agree on linear format,
pitch and WC mapping; actual WC visibility and hardware state remain unproved.
The operator confirms the corruption was visible to the naked eye. Retained
Android underrun text is not candidate causal evidence. No root cause or repair
is established. Four exact source-function H0 cases qualify the proposed
hardware magenta `color_fill` branch as a discriminator only; a clean result
would not by itself prove a cache fault.
Report: [P353 image-corruption H0 analysis](docs/reports/S22PLUS_FYG8_P353_IMAGE_CORRUPTION_H0_2026-09-07.md).

Subsequent web and exact FYG8 vendor-image analysis identifies a smaller first
comparison: the shipped SDM/DRM path handles disabled noise with an explicit
`noise_layer_v1=0`, whereas P353 omits the property. Exact library disassembly
and three source-function cases establish the difference, not its live cause.
Prefer a fresh same-pattern, same-30HS successor with only that explicit disable;
the magenta discriminator remains the fallback. P354 above implements this
comparison in H0; no device effect is authorized. Thirty-nine firmware files, 22 DT combinations and
historical Android 120HS/60PHS mode text were examined. The normal Android photo
does not identify its active mode or exclude a condition-dependent physical fault.
Report: [Android firmware display comparison](docs/reports/S22PLUS_FYG8_P353_ANDROID_DISPLAY_COMPARISON_H0_2026-09-07.md).

## Consumed P352 and source investigation

P352 is CLOSED/19 and consumed with
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, recovery_required=false.
Candidate `30965801B/6cda084d` and exact Magisk rollback `23367721B/d2373bf8`
transferred once each. Final rooted FYG8, original boot/supporting hashes and
absent Download passed. Actual prepared/result and failed-session reopening
passed; live result is `21491B/ea7e19e6`.

Qualification passed 1/3 sessions. All twelve insertions and fresh readiness
passed, followed by the actual `msm_drm` name, thirteen returned modes and one
exact 30HS match. The display child exited 1 at 200 ms at `competing-plane`,
before buffer allocation or frame submission. Its conflicting plane's exact
ID/CRTC/FB state was not logged; do not infer its owner from the selected IDs.
The operator observed only the retained boot logo. Visible output is UNPROVED.

Physical Download entry and exact rollback completed in the original execute
invocation, without a recovery restart or repeated effect. P352 is never
replayable. No active shell or standing device authority remains. The source,
artifact, raw capture and journal are retained; any successor must address the
observed initial-plane condition under a fresh binding. A90/S20+ were untouched.
Report: [P352 closed result and timeline](docs/reports/S22PLUS_FYG8_P352_SOURCE_BOUND_DISPLAY_H0_2026-09-07.md).

H0 initial-plane investigation now confirms a vendor splash producer can expose
CRTC-nonzero/FB-zero attachments that trigger the guard; the actual failed tuple
is still absent, so live splash causality is unproved. Exact consumed module
disassembly also confirms that first atomic duplicate callbacks change old
splash bookkeeping before allocation, including on a TEST_ONLY path. P352
stopped before that path. Eight bounded source-function cases and independent
analysis review passed; full handoff remains unqualified. Early A90 SETCRTC
history does not bypass this S22+ atomic machinery.

The operator narrowed the next functional proof to the boot logo changing into
one identifiable static image, followed by operator-entered Download and exact
rollback. Repeated frames, completed display disable and post-display USB are
not that visual proof's success criteria. Follow-up source and exact-module
inspection now support one WC buffer and one blocking atomic commit, with a
complete initial snapshot and explicit inherited-plane handling in the same
transaction. The real commit retains internal validation without a separate
TEST_ONLY. CRTC stage/CTL replacement provides the proposed mechanism for
excluding the old composition; actual flush and latch remain unproved.
Per-plane disable callbacks are not guaranteed. Nine bounded H0 cases and independent
design review pass; ioctl success alone still does not prove visible output.
That H0 investigation led to the P353 implementation and scoped qualification
reported above, including resource ownership during the attended observation
window and matching contract/observer criteria. P352 consumed artifacts remain
unchanged; the investigation itself involved no device action.
Report: [Initial-plane source and binary investigation](docs/reports/S22PLUS_FYG8_P352_INITIAL_PLANE_INVESTIGATION_H0_2026-09-07.md).

## Consumed P351

P351 is CLOSED/19 and consumed with
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, recovery_required=false.
Candidate `30965801B/f9e2783f` and exact Magisk rollback `23367721B/d2373bf8`
transferred once each. Final rooted FYG8, original boot/supporting hashes and
absent Download passed; actual prepared/result reopening passed.

Qualification passed 1/3 sessions. The authenticated display child returned
exit 1 at 200 ms. All twelve module insertions and two fresh readiness snapshots
passed: exact bus/PMIC bindings, four rails and DRM `226:0`, at elapsed 2 ms.
It then failed `driver-name` with errno 71, before DRM master or frame submission.
The bound vendor source declares `msm_drm`, while the renderer and original fake
DRM fixture expected `msm`; a source-informed H0 fixture reproduces the failure.
The actual returned name was not logged. Visible P351 output remains UNPROVED.

USB endpoint evidence failed while waiting for physical Download, before
rollback transfer. One same-journal recovery completed the exact rollback and
final health. Candidate and observation were never replayed. The operator
reported no normal-boot response during the candidate phase; do not promote
that report into a precise screen-output claim.

The bounded run is complete. No active shell or new device authority remains.
P351 source, artifact, capture and journal bytes are preserved. Any next display
attempt needs a fresh successor correcting the exact driver-name binding and
its source-informed fixture; P351 is never replayable. A90/S20+ received no command.
Report: [P351 result and timeline](docs/reports/S22PLUS_FYG8_P351_DISPLAY_READY_H0_2026-09-06.md).

## Previous consumed display attempt

P350 is CLOSED/19 and consumed with
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, recovery_required=false. Candidate
`30822441B/41b9272b` and exact Magisk rollback `23367721B/d2373bf8` transferred
once each. Final rooted FYG8, original boot/supporting hashes and absent Download
passed; actual prepared/result reopening passed.

Qualification passed 1/3 sessions. The fixed display child returned exit 1 at
101 ms after all nine module insertion calls returned success, then failed
opening `/sys/class/drm/card0/dev` with errno 2. No frame submission occurred.
The first live probe stop remains unproved. H0 analysis now confirms missing
S2DOS05 regulator and i2c-gpio bus providers required by the selected panel;
module softdeps and DT named-supply/instantiation dependencies were omitted from
the prior symbol-only graph. USB inventory failed
during physical Download waiting; one ordinary same-journal recovery completed
the exact rollback. Candidate and observation were never replayed.

The operator did not observe the screen; this is not a blank-screen claim. They
requested a larger, white-background display after inadequate pre-run guidance.
A pure H0 white-background layout and actual C preview are now implemented:
550-pixel central counter, large lower green block, footer run ID. P351 now
packages that layout. All eleven DTBO definitions require the same four
S2DOS05 rails. Exact source-body host checks and independent review confirm the
missing prerequisite; waiting alone is insufficient. Provider H0 assessment now
passed: three additions including pmic_class, 91 imports with no CRC errors, and
a built/reviewed i2c-gpio variant restricted to display bus i2c@50 before pinctrl.
Stock generic GPIO-I2C would bind four buses and is not the selected artifact.
P351 above completes provider/readiness and white-renderer integration in a
fresh H0-qualified successor; this does not authorize a device effect.
Report: [Display provider H0 assessment](docs/reports/S22PLUS_FYG8_DISPLAY_PROVIDER_ASSESSMENT_H0_2026-09-06.md).
No new device effect is authorized by this goal. P350 is never replayable.
Report: [P350 result and timeline](docs/reports/S22PLUS_FYG8_P350_NATIVE_DISPLAY_PREPARED_H0_2026-09-06.md).

## Paused P349 unit

P349 device work is paused pending operator attendance. Independent capability
review returned PASS_GO; A/B candidate, static promotion, 73 focused tests and
raw-first audit passed. Candidate AP is `28631081B/8ff75170`; exact Magisk
rollback is `23367721B/d2373bf8`. This is a UID/GID 65534 current-boot RAM
workspace, not a root shell: `/work` is 8 MiB/256 inodes, with fixed BusyBox
script execution and fresh children across actions.

The 65-minute/16-action lease requires initial six-session/120-second reopen
proof, eight ordered functional actions and 20/40/60-minute authenticated
same-boot workspace witnesses. Durable intent timing must satisfy each actual
elapsed threshold. Capacity tests remain host-only. Actual P349 hour/live RAM
behavior and rollback/final health are still UNPROVED; no F1 transfer occurred.

First D0 preserved a retained-family baseline stop. One preapproved ordinary
reboot D1 passed with changed boot ID and healthy rooted FYG8 return, then new
D0 and preparation initially passed in `p349-ready1-prepared-20260906-2`.
The returned approval then reached an observer-guard host authentication failure:
`pkexec` supplied no arm response within 30 seconds, and polkit logged failed
authentication. The run is ABORTED/4 before any Download request or candidate
attempt, with result `1351B/ca79a6d2`; actual result validation passed. No flash,
rollback or native session occurred, and the old approval cannot be replayed.

Fresh preparation `p349-ready1-prepared-20260906-3` also passed D0, but its
returned approval encountered the same host-authentication timeout. It too is
ABORTED/4 before Download or candidate transfer; result `1351B/c1cb7925`.
The operator then confirmed they were away and could not authenticate. Both
approval bindings are terminated; no replacement is currently prepared.

The latest execute-preflight recorded healthy rooted FYG8. No device transition
followed it, and no native shell is active. The candidate remains untransferred;
P348 remains closed/consumed. Resume only when the operator can complete host
authentication and physical Download recovery, with fresh exact preparation and
approval. P349 remains paused; separate H0 display build work is described below.
A90/S20+ receive no command.
Report: [P349 capability and preparation](docs/reports/S22PLUS_FYG8_P349_RAM_WORKSPACE_PREPARED_2026-09-06.md).

## Separate H0 display investigation

The operator requested a visible indication that native PID1 is running,
distinct from the retained boot logo. [Initial display research](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_RESEARCH_H0_2026-09-06.md)
selects DRM/KMS as the preferred source-investigation path; current framebuffer
support is disabled and the USB plan omits the vendor display module. Actual
native display output remains unproved. This H0 work does not alter P349 or
activate a device lane. [Follow-up research](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_FOLLOWUP_H0_2026-09-06.md)
found the retained panel-selection parameter, checked 50 modules/2,965 imports
against the exact Image within their declared graph, and identified a WC buffer
route. Stock display/debug providers also have persistent-write paths, including
probe and diagnostic-read triggers. [Minimal-build research](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_MINIMAL_BUILD_RESEARCH_H0_2026-09-06.md)
identified paired diagnostic gates and forced make/header configuration; public
KMS/modetest examples support renderer design but do not qualify FYG8.
[Consolidated H0 result](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_CONSOLIDATED_H0_2026-09-06.md):
isolated vendor-module Full-LTO/CFI build succeeded with known display persistence
paths and POC/SPI implementations excluded. Final combined graph: 82 modules,
4,391 versioned imports, zero unresolved/ambiguous/CRC-mismatched providers.
This qualifies a host build and symbol graph, not runtime ABI, safe probe,
transitive absence of persistence, screen output or recovery. The P350 unit above
adds a qualified host renderer/packager and fixed observation sequence. Runtime
probe and visible output remain unproved. P349 remains unchanged.

## Latest completed P348 unit

P348 is CLOSED/19 and consumed with
`PASS_F1_V2_P348_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`.
Candidate `28631081B/5dde2320` and exact Magisk rollback `23367721B/d2373bf8`
each transferred once. Six initial sessions / 18 commands, 120-second idle and
clean reopen passed, followed by all five retained-shell acceptance actions:
checked snapshot, exit 7, timeout, authenticated cancel and post-cancel success
with complete 120,017-byte output. Final rooted FYG8 Android, original
boot/supporting hashes and absent Download passed. No active native shell remains.

**One-hour stability is UNPROVED.** The last successful later action was
390.137 seconds after lease opening; the one-hour setting was only an upper
bound. Recovery was requested at 453.389 seconds. Future full-hour validation
needs a separately qualified successor with explicit timing and witness criteria;
this consumed candidate and lease must never be replayed or renewed.

Run `p348-ready1-prepared-20260906-2` has live result `42728B/97915e02`,
recovery_required=false. Actual prepared/result reopening passed. A host command
file mode rejection preceded any action intent; its corrected first execution
was ordinal 1. USB identity evidence failed while awaiting physical Download,
before rollback transfer. Same-journal recovery after operator Download entry
completed the exact rollback once. Original failure evidence is preserved and
its cause remains unproved. A90/S20+ received no command.
Report: [P348 result and timeline](docs/reports/S22PLUS_FYG8_P348_RETAINED_SHELL_PREPARED_2026-09-06.md).

## Latest completed bounded unit

P347 is CLOSED and consumed with
`PASS_F1_V2_P347_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`. Candidate
`28631081B/02c5d905` and exact Magisk rollback `23367721B/d2373bf8` each transferred
once. All five same-FD qualification sessions passed: numeric read-only canary,
exit 7, 15,156-ms timeout, authenticated cancel and all 120,017 final output bytes.
Final rooted FYG8 Android health, original boot/supporting hashes and absent
Download passed. No later shell lease or standing command authority exists.

Run `p347-ready1-prepared-20260906-3` is CLOSED/19, recovery_required=false;
live result `33570B/9e2db4b7`, observer raw `124676B/20f67548`. Actual prepared/
result reopening and append-only campaign-ledger closure passed. The first
execute-preflight host ADB startup-stderr stop is preserved separately; it
preceded target-specific commands and transaction creation. Candidate and
observation were never replayed, and no recover invocation was needed.

The approved bounded unit is complete. Any new candidate requires its own
qualification, current exact binding and fresh approval; P347 is never replayable.
A90 and S20+ received no command.
Report: `docs/reports/S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md`.

## Consumed P346 and diagnosis

P346 is CLOSED and consumed after the operator returned its exact F1 approval.
Candidate `28631081B/ad6a84ef` and exact Magisk rollback `23367721B/d2373bf8`
transferred once each. Final rooted FYG8 health, original boot/supporting hashes
and absent Download passed. Journal CLOSED/19; formal result
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, `25665B/7d28bfa7`, with recovery not required.

The fixed read-only child canary and expected exit-7 session passed (2/5).
Session 3 failed expected timeout-outcome validation after a complete exchange;
authenticated cancel and post-cancel pipeline were not attempted. Raw evidence
is preserved. This is partial functional evidence, not complete qualification.

A host USB inventory failure after observation stopped the initial runner before
rollback transfer. One ordinary journal-based recovery completed exact rollback
without candidate or observation replay. Its precise cause remains unproved.
The earlier baseline D1 return timeout also remains preserved; late exact healthy
return and fresh ordinary D0 subsequently passed without repeating that reboot.

The approved bounded execution is complete. Any next work is H0 diagnosis of the
session-3 outcome and inventory failure using retained evidence. Do not replay
P346, widen its child filter, or start another candidate under its consumed approval.
Report: `docs/reports/S22PLUS_FYG8_P346_PREPARATION_AND_D1_RETURN_STOP_2026-09-06.md`.

H0 sleep diagnosis reproduced the failure: the exact candidate BusyBox calls
`clock_nanosleep(115)`, which the consumed filter denies with `EPERM`; BusyBox
then exits zero without waiting. The retained sequence-4 EXIT is zero/empty at
101 ms, consistent with the supervisor's 100-ms polling. Real-filter/C-supervisor
H0 reproduction agrees; no wait/reporting defect was found. Two new diagnosis
tests and nine child-boundary tests passed. Historical filter input is frozen
in `tests/fixtures/p346/readonly_child.inc.c`.

A private minimal relative-CLOCK_REALTIME-only correction passed H0 normal,
nonzero, cancel, 15-second timeout and next-pipeline tests, negative controls,
AArch64 compilation and independent review. That diagnostic proposal was not applied to P346:
the earlier no-widen question was subsequently resolved by the operator's
P347 preparation request. The historical P346 source stays unchanged; the new
version belongs only to P347. Full diagnosis evidence is in the report above.

## Adjacent H0 audit

The follow-up audit reproduced an additional output-integrity defect: a
120,000-byte BusyBox awk output (below the 128-KiB cap) yielded only 65,536 bytes
with exit 0, flags 0 and `ok`. Real-filter C/Python framing and exact candidate
BusyBox nonblocking-pipe tests cover the mechanism. Separately, denied
`prlimit64`/`sysinfo` queries let ulimit/uptime/free emit untrusted values with
exit 0; usleep shares the clock_nanosleep failure. Pipeline/substitution status
masking is a shell-semantics limitation, not a newly invented proof of failure
in the existing fixed canary. Independent review agrees.

These findings led to the separately qualified P347 successor above. The audit
itself applied no production fix or device action and remains the causal record.
Report: `docs/reports/S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md`.

## Latest completed evidence

P345 is CLOSED/19 and consumed: candidate `28631081B/7ee59a13` and Magisk
rollback `23367721B/d2373bf8` each transferred once, with final rooted FYG8
health and original boot/supporting hashes verified. The qualification accepted
0/5 sessions; retained raw `670B/a8d28dc6` is partial evidence only. Terminal-only
metadata normalization published `15689B/039bcb3f`, verdict
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p345_readonly_research_shell_unproved_rollback_verified`, recovery not required.
No journal, state, raw capture or prepared binding was rewritten.

H0 repair `4a8c6d8b0d` shares numeric parent-ID checks, separates child numeric
UID/GID queries, normalizes JSON metadata and excludes P345 from incompatible
P328 receipt fields. Independent review passed for code repair only. P345
43/46 host tests passed; three historical build reopenings reject changed source
identity. Shared exchange 8/8 and common F1 live 74/74 passed. Historical pins
remain unchanged; this does not qualify a fresh candidate.
Report: `docs/reports/S22PLUS_FYG8_P345_SHELL_QUALIFICATION_NO_PROOF_2026-09-06.md`.

P344 proved the bounded five-query named read-only exploration workflow:
initial four sessions/twelve commands and 120-second idle reuse, then successful
kernel/processes/mounts/memory/usb-state actions with published results and no
failed/pending action. Candidate/rollback 1/1, CLOSED/19 and final rooted FYG8
health passed. Verdict `PASS_F1_V2_P344_NAMED_EXPLORATION_AND_ROLLED_BACK`;
result `38199B/aba403cc`. The device returned to Android; all actions are consumed.
Report: `docs/reports/S22PLUS_FYG8_P344_NAMED_EXPLORATION_PREPARATION_2026-09-05.md`.

Earlier native-PID1 evidence includes P325 ACM arrival, P326 fixed bidirectional
USB/BusyBox shell, P327 framed fixed-command execution, and P335 authenticated
three-session command execution. None establishes unrestricted shell, interactive
PTY, indefinite residency, persistent installation, shell reboot/Download control,
autonomous recovery or Max77705 causal behavior. P343 and earlier NO_PROOF results
retain their original classifications and no-replay status.

## Archive and continuing boundaries

The complete previous 899-line goal was preserved byte-for-byte at
`docs/archive/roadmaps/GOAL_THROUGH_P345_H0_REPAIR_2026-09-06.md`.
Its completed history and earlier archive links are evidence only. The private
append-only campaign ledger and run journals remain authoritative for effects.

Never prepare a new experiment over unhealthy or uncertain state. Preserve exact
target, current boot, candidate/rollback, topology, source and journal bindings.
An unexplained device-session failure stops the experiment; retain raw evidence
and continue only allowed observation and preauthorized recovery. A consumed
candidate is never replayed, and a reporting failure never repeats a device effect.
