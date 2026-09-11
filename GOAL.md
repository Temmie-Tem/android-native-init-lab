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

P386 connected preparation is **COMPLETE, awaiting exact attended F1 approval**.
Fresh operator continuation authorized only the remaining fixed D0 preparation.
Exact S22+ rooted FYG8/original hashes, same-boot continuity, clean 2,097,136-byte
retained-log baseline and Download absence passed. The actual 64,024-byte
prepared record reopens through `load_prepared`; all 176 execution sources match
the qualified closure, and the candidate remains unconsumed. This step performed
no reboot, device write, Download transition or partition transfer. The next
approved F1 unit is one P386 installation, four authenticated checkpoints over
at least thirty minutes, one exact Android return and final health.

Earlier P386 preparation used **one ordinary Android reboot**.
The D1 observer stopped when ADB was online but the successful property output
still had empty `boot_completed` with a running boot animation. Separate fixed
read-only reconciliation proved the changed healthy Android boot and cleared
pending recovery bookkeeping; the original D1 STOP and closed goal remain.
A narrow readiness correction now polls only that fixed nonroot property within
the original deadline before strict health parsing. Independent PASS_GO and
25 tests passed; the used source/review are preserved privately. That stopped
goal performed no second reboot, P386 connected preparation or F1 transfer.
The later D0 preparation above used fresh operator continuation and preserved
the closed goal, STOP and separately observed late health. Its one-reboot
allowance remains consumed.
See the [preparation report](docs/reports/S22PLUS_P385_EXIT_P386_F1_PREPARATION_2026-09-11.md).

The [P385 exit / P386 F1 preparation](docs/reports/S22PLUS_P385_EXIT_P386_F1_PREPARATION_2026-09-11.md)
has completed P385's exact attended Android exit: **ANDROID_CLOSED**, one A,
zero N, `recovery_required=false`, F1 owner released. Final rooted FYG8/original
partition hashes, same-boot target continuity and Download absence passed.
The first two health attempts stopped because the owner incorrectly required
a clean pre-candidate retained-log baseline during final recovery health.
A narrowly reviewed final-health producer/reader repair passed twelve tests;
fresh read-only health then closed the completed A without another transfer.
The original request, grant, A evidence and both D0 STOP results are unchanged;
`research_stopped=true` remains. All 472 pre-repair files were verified unchanged.
P385's historical native qualification, admission and consumed installation
remain intact. Its consumed host review is not repinned after this repair.
P386's ordinary thirty-minute observation remains host-qualified; its execution
closure excludes the repaired native-baseline owner. Connected preparation is
complete; its separately returned ordinary F1 approval remains pending. The stopped P385
grant supplies no P386 authority or further native role.

The [resident adoption H0 V1](docs/operations/S22PLUS_NATIVE_RESIDENT_ADOPTION_V1.md)
unit is complete with **PASS_RESIDENT_ADOPTION_H0 / independent PASS_GO for H0 only**.
P386 / v0.2.0-rc.4 connects the qualified resident runtime to a deterministic
boot-only AP, four authenticated checkpoints spanning thirty minutes, and the
ordinary one-N/one-A installation/return owner. Actual AP decoding, generated-C
integration, retained replay, full preparation/reopen and failure recovery pass.
The final review binds 157 static inputs and 176 unique execution sources.
No device contact, live activation, prepared run or grant occurred. See the
[H0 report](docs/reports/S22PLUS_NATIVE_RESIDENT_ADOPTION_H0_2026-09-11.md).
The later P385 Android exit and P386 connected preparation are recorded above;
P386's own returned attended F1 approval remains required.

The completed [native resident runtime H0 V1](docs/operations/S22PLUS_NATIVE_RESIDENT_H0_V1.md)
has no normal PID1/local-service 15-minute cap, while
individual command sessions remain finite and uncertainty latches command
admission stopped. Separate system/hardware workers, bounded HUD diagnostics,
64-bit counters and CPU temperature with sensor coverage passed actual C/PTY/IPC
tests, 100,000 samples per collector, 1,001 renderer frames, accelerated day/month
boundaries and AArch64 A/B builds. The [H0 report](docs/reports/S22PLUS_NATIVE_RESIDENT_H0_V1_2026-09-11.md)
preserves the distinction between these fixtures and unproved target soak,
sensor exposure, physical display and recovery. Live resident adoption is a
separate later reviewed capability/approval. At that H0 close, all 160 P385 reviewed
source inputs matched their retained identities. This adoption changes exactly
three host inputs; all 112 native inputs remain unchanged. The original P385
review no longer matches the current host closure and was preserved together
with its consumed records and native artifacts. No device was contacted.

The completed predecessor is [bounded attended native baseline V1](docs/operations/S22PLUS_NATIVE_BASELINE_V1.md),
P385 / v0.2.0-rc.3: an exact qualified native image with clean DETACH and same-boot
reauthentication, finite normal baseline restoration, and distinct healthy native
or exact Android terminals. The then source-qualified capability, ARM64 A/B/AP
checks, 38 final owner/protocol/legacy tests and independent common/target review
passed with **PASS_GO**; see the [H0 qualification report](docs/reports/S22PLUS_FYG8_NATIVE_BASELINE_V1_H0_2026-09-10.md).
The separately approved `p385-bootstrap-20260910-1/operation-01` live bootstrap
completed **NATIVE_CLOSED** on 2026-09-11. Its one reservation/600-second grant
is consumed and closed. One N installation and one same-N restoration completed;
Android A was available and was not transferred. Each boot passed two fixed
authenticated health checks with clean descriptor detach/reopen, same-boot fresh
nonce and cached second preparation. The boots differ. First normal Download
return passed its original window; final clean DETACH ACK and actual close passed.
The exact P385 image/physical target is admitted, its original installation claim
remains consumed, and the F1 owner is released. The actual terminal/raw/admission
readers rederive the result with `recovery_required=false` and no research stop.

The device's last observed state is the healthy native snapshot at this close.
Six authentication admissions and 893.438 seconds of original native lifetime
remained then; this is not a current-health assertion or a renewed deadline.
Later native-origin operations or Android exit need fresh finite authority and
current binding. The next owner's present-native guard is H0-qualified but has
not yet been exercised in a separate live operation. Unattended recovery,
unlimited native service, persistent data work and a v0.2.0 release remain unproved.

The completed follow-up is the separately incorporated
[P384 native roundtrip V2](docs/operations/S22PLUS_NATIVE_ROUNDTRIP_FOLLOWUP_V2.md):
one N installation, one same-N restoration and one exact A cleanup/fallback,
with 1,800 seconds total and two 60-second native observations.
The attended `p384-native-roundtrip-v2-prepared-20260910-4` run is consumed and
**CLOSED/19**, with `PASS_F1_V2_P384_ROOT_CONSOLE_AND_ROLLED_BACK` and
`recovery_required=false`. Both authenticated native health checks pass, with
different kernel boot identities and nonces. Both exact Download arrivals were
observed inside their original 30-second CONTROL windows. Installation,
exceptional same-N restoration and exact Android cleanup each transferred once;
the original execute completed without a recovery invocation or repeated effect.
Final exact-target rooted FYG8/original boot and supporting hashes, completed
Android boot and Download absence pass. Terminal validation reopens both raw
native sessions, all three role results and the final health evidence.

Each arrival also returned five valid HUD frames with matched flip observations
and fresh gauge/memory/CPU samples. Physical pixels, continuous liveness,
pre-authentication display timing and software-causal Download attribution
remain unproved. Supplemental stock evidence remains NO_PROOF_OBSERVER.
This qualifies this bounded attended roundtrip, with the N installation and V2
claims retained. It creates no standing native baseline, reusable budget,
unattended recovery or v0.2.0 release. That P384 transaction returned the device
to healthy Android before P385.

The first approved invocation in `p384-native-roundtrip-v2-prepared-20260910-3`
ended **ABORTED/4 before any Download request, guard arm or partition transfer**.
Fresh execute D0 passed exact rooted FYG8/original hashes/Android health; the
actual observer factory then raised AttributeError because P384's direct
artifact object lacks the legacy credential-reader interface. Counts are
0 N installation / 0 N restoration / 0 A for that invocation. Its approval/run
cannot be reused and its original result remains unchanged.

H0 reproduced the actual entry failure before guard invocation. The reviewed
host-only fix selects the existing strict fixed-key reader and retains the
prepared P384 digest check. Actual ordinary/V2 factory construction, invalid
key rejection and pre-effect abort/no-replay tests pass; the prior fixture had
substituted key reading and missed this connection. All 108 candidate inputs
and the AP remain unchanged. Fresh read-only preparation, full reopen and the
actual fixed-key/factory entry preceded the separately returned finite approval
for prepared-4. Its actual privileged guard and complete execution now pass.

The earlier baseline-negative D0, one ordinary-reboot STOP with later read-only
healthy reconciliation, prepared-record size repair and actual prepared reopen
remain separately recorded. Neither later health nor a host repair upgrades
those original outcomes. P383's V1 policy, consumed budget and NO_PROOF records
are unchanged. See the [V2 report](docs/reports/S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md).

The H0 **v0.2.0-rc.2 / P384 local-display adoption** is complete after
the component refactor. It connects the direct local sources, fresh
candidate identity, authenticated observer and ordinary one-N/one-A F1 owner.
ARM64 A/B init/renderer/AP builds and actual AP decoding pass. The new owner
passes real generated-C/raw-reopen tests for optional HUD success/failure/skip,
post-observation recovery without replay and corrupt wire NO_PROOF with rollback.
Source binding includes dynamically loaded image and codec dependencies.
See the [adoption contract](docs/operations/S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_V1.md)
and [H0 report](docs/reports/S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_H0_2026-09-10.md).
That ordinary adoption opened no device grant, live prepared run or public READY
activation. The separately selected V2 graph above does not renew P383's consumed
same-N restoration exception and still requires its own exact approval.

**Functional version v0.1.2 — gauge HUD and lossless bounded console output**
maps to the identical successful **v0.1.2-rc.5 / run-001 / P382** artifacts.
The attended run is consumed and CLOSED/19 with
`PASS_F1_V2_P382_ROOT_CONSOLE_AND_ROLLED_BACK`, recovery_required=false.
All six fixed qualifications and three planned commands passed with zero dropped
output. The ordinary OBSERVED transition serialized to 1,100 bytes; exact
Download arrival was observed inside the sealed CONTROL window without a
physical fallback prompt. One candidate and one exact rollback completed,
followed by verified rooted FYG8/original hashes/Android health and Download absence.
Original execute completed without recover or replay.

The retained AP is `c417ab34f492ad7a50fb0950a62593c8ecb78d5925003333251b25934df514ef`;
no rebuild, artifact rename or new tag is needed for this functional mapping.
The five matched HUD records include four BUSY frames and fresh gauge proof.
Two complete bounded memory snapshots remain observations, not reclaimability
or leak-absence proof. The operator photograph shows the rc.5 gauge/status HUD
with SOC 99.9%, 4.337 V and +548.4 mA as physical OBSERVED evidence; it is not
cryptographic frame attribution or continuous-liveness proof.
Supplemental stock NO_PROOF_OBSERVER and causal software-return UNPROVED remain;
timely exact arrival is separate evidence. No standing native lease, unattended
recovery or native baseline adoption follows. See the [rc.5 execution report](docs/reports/S22PLUS_FYG8_JOURNAL_CLOSE_RC5_H0_2026-09-10.md).

The v0.1.2 bounded unit is complete. The attended **v0.2.0-rc.1 / P383**
first native-baseline roundtrip is **NO_PROOF, consumed and CLOSED/19**.
In `p383-ready1-prepared-20260910-2`, N installation, first authenticated native
health/idle STATUS and exact timely Download passed. The same N transferred
once more, but the second arrival's USB inventory changed before snapshot
publication; no second console/health/CONTROL was reached. The operator clarified
that the second boot remained at the boot screen with no native display. The
generated HUD starts only after host authentication and console entry, which
the failed host observation never initiated. This explains absent HUD without
proving where kernel/PID1 execution reached; second native boot remains unproved.

The preapproved exact A fallback transferred once. Its first 420-second final
health wait expired with ADB offline. After the operator reported Android and
fresh bounded enumeration found ADB online, unchanged recovery resumed from
ROLLBACK_FLASHED without another transfer. Exact target continuity, rooted FYG8,
original boot/supporting hashes and Download absence passed; the journal closed
at 04:17:46.471890Z with `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` and
`recovery_required=false`. Installation/exception claims remain consumed.
Counts are one installation, one exceptional N restoration, one A transfer.
Native roundtrip and supplemental stock proof remain unproved; the transient
ADB failure's cause is not established. No standing native baseline or v0.2.0
promotion follows. See the [execution and recovery record](docs/reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md#attended-attempt-and-final-android-health).

The current follow-up is documented in the
[structural assessment](docs/reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md#structural-coupling-and-follow-up-scope)
and [failure checklist](docs/operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md):

- HOST: the empty-child USB inventory transition is reproduced and repaired in
  H0. Exact completed-restoration context seeds the first comparison; unrelated
  inventory changes still fail. Independent review returned PASS_GO.
- DISPLAY: `local-display-v1` now implements PID1-owned local HUD lifetime
  before host authentication. H0 validation and independent PASS_GO are
  complete. Existing live candidates do not adopt the profile.
- RETURN: retain the temporary ADB offline incident with unknown cause and the
  verified recovery continuation. Second kernel/PID1 progress remains an evidence
  gap rather than a confirmed boot defect.

The [phase-1 refactoring preparation](docs/plans/S22PLUS_FYG8_REFACTOR_PHASE1_PREPARATION_2026-09-10.md)
now maps the latest native generation, host observation and recovery structure.
[1A is implemented and independently reviewed PASS_GO](docs/reports/S22PLUS_FYG8_NATIVE_SOURCE_REFACTOR_1A_H0_2026-09-10.md):
the direct common generator matches actual materialized C, ARM64 init/renderer,
module plan and both P383 AP packages. Twelve direct-source tests and four
additional backpressure checks pass. Historical generators and all 86 consumed
prepared execution-source bindings remain unchanged; the new path is H0 only.
The deeper platform envelope/compiler still binds the same run identity.
Display/console lifetime separation is complete as **H0 phase1B** under
[Local Display Lifecycle V1](docs/operations/S22PLUS_FYG8_LOCAL_DISPLAY_LIFECYCLE_V1.md).
Its explicit profile starts local ownership before boot-ID read and OPEN/AUTH at
that boundary, with authenticated command/CONTROL semantics and bounded cleanup.
[Implementation and H0 validation are complete](docs/reports/S22PLUS_FYG8_LOCAL_DISPLAY_REFACTOR_1B_H0_2026-09-10.md):
42 tests pass, including 916 renderer frames and real C backpressure; static
ARM64 A/B component builds match. Independent review returned PASS_GO.
No current live candidate or device capability is activated. The separate
[phase1C observer](docs/reports/S22PLUS_FYG8_LOCAL_DISPLAY_OBSERVER_1C_H0_2026-09-10.md)
now implements compatible H0 observation: fixed native health first, optional
local HUD collection, owned CONTROL and exact retained replay. Eleven new tests
and 15 shared health/wire tests pass; independent review returned PASS_GO.
Historical observer semantics remain unchanged.
The separate [host-arrival repair](docs/reports/S22PLUS_FYG8_RESTORATION_ARRIVAL_H0_2026-09-10.md)
is implemented and independently reviewed PASS_GO, with 197 passing host tests.
It validates the restoration's original claim/intent/delivery/complete transfer
and exact Download identity before the child's first measured snapshot. The
child keeps its own lease and sequence0. Remaining-node replacement is rejected.
Current execution sources changed and require future fresh bindings; consumed
P383 records/pins remain unchanged. The second device boot is still NO_PROOF.
The bounded refactor follow-up is complete in H0. Broad F1/evidence rewrites,
other-target changes and fresh live adoption remain outside this completed unit.

**v0.1.2-rc.4 / P381** is consumed and CLOSED/19 with exact rollback and final
rooted FYG8/original health complete. All six functional qualifications and three
planned commands passed with zero dropped output; the operator photograph shows
SOC/voltage/current. Two complete memory observations confirm369 files retained
on RAM with55.988MiB allocation metadata, not reclaimability.
The host's full OBSERVED journal record exceeded32KiB after observation. One
unchanged recovery resumed from durable evidence without candidate/CONTROL
replay, but timely software-return observation was missed. Formal NO_PROOF is
preserved; rc.4 did not confirm v0.1.2. The [compact journal H0 repair](docs/reports/S22PLUS_FYG8_OBSERVED_JOURNAL_H0_2026-09-10.md)
is implemented and independently reviewed PASS_GO: full proof input is retained,
OBSERVED stores state/receipt hashes, and normal/cut recovery passes with the
actual rc.4 receipt as common-path input under unchanged 32/64 KiB bounds.
The [native baseline roundtrip design](docs/plans/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_DESIGN_2026-09-10.md)
now has a bound first-qualification owner under the separate common exception;
H0 completion does not activate a device grant. No native rollback identity is changed. No file deletion,
RBIN/CMA change or standing native lease follows.
See the [rc.4 report](docs/reports/S22PLUS_FYG8_OUTPUT_MEMORY_RC4_H0_2026-09-10.md).

Previous candidate **v0.1.2-rc.3** (P380) is consumed and CLOSED/19 with one
exact rollback and final rooted FYG8/original health complete. The gauge HUD
subproof passed with three fresh SOC/voltage/current samples; overall console
qualification failed on 1536 dropped output bytes (queue pressure), so all
three planned commands stayed unexecuted. Formal NO_PROOF is preserved.
Two native meminfo observations identify an 800 MiB RBIN reservation component
in the ~1054 MiB HUD accounting difference; separating it leaves ~254 MiB,
not reclaimed RAM. The command output loss leaves the full process census unproved
and does not establish absence of a leak. No replay/native lease remains; v0.1.1 is retained and
image publication deferred. Follow-up Android D0 observed RBIN800MiB with7MiB
allocated/793MiB free/zero cached, and CmaTotal444MiB. Source verification found
the camera-named RBIN/gen_pool/cleancache implementation; reusable alone is not
proof of automatic reuse or safe release. Further H0 verified the historical
A90 281MiB arithmetic, but not its historical kernel/RBIN accounting. Reducing
the real S22+ reservation is a worthwhile design candidate, distinct from
changing the HUD calculation; no release or new device run is qualified.
The [H0 memory source review](docs/reports/S22PLUS_FYG8_MEMORY_SOURCE_REVIEW_H0_2026-09-10.md)
prioritizes RBIN ownership and Shmem/slab attribution. The adjusted254MiB
includes about32MiB of net availability-estimator gap; enabled diagnostic
options alone do not prove their runtime memory cost. No settings were changed.
Further H0 includes the vendor ramdisk: combined file data rounds to77.672MiB,
with55.988MiB in369 module files outside the current explicit load plans.
This is a RAM-file retention design candidate, not measured reclaimability.
Both applicable merged DTs explain CMA444MiB across13 areas and carry kasan=off;
final native filesystem/slab attribution and effective boot arguments remain open.
See the [rc.3 close and memory report](docs/reports/S22PLUS_FYG8_GAUGE_MODEL_MEMORY_RC3_H0_2026-09-10.md).

Previous candidate: **v0.1.2-rc.2 gauge diagnostics** (P379), consumed and CLOSED/19.
Formal result is NO_PROOF with one exact rollback and final rooted FYG8/original
health complete; no replay or native lease remains. Authenticated diagnostics
localize root-model allowlist rejection (stage7/ENODEV), before binding or any
I2C read. Units were not reached. Later probe checks remain untested.
Diagnostic localization succeeded; v0.1.2 remains unconfirmed and v0.1.1 retained.
Post-close bounded Android D0 observed root model `Samsung G0Q PROJECT (board-id,12)`
and retained meminfo; Android values do not decompose the prior native 1053 MiB.
This is the concrete rc.3 identity-check input. HUD image publication remains
deferred until rc.3 shows actual gauge data. See the [close report](docs/reports/S22PLUS_FYG8_GAUGE_DIAGNOSTICS_RC2_H0_2026-09-10.md).

Previous candidate: **v0.1.2-rc.1 — restricted gauge telemetry HUD**, consumed.
The attended `p378-ready1-prepared-20260909-1` run closed
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`: the gauge HUD qualification failed,
all three planned console commands remained unexecuted, and one exact rollback
plus final rooted FYG8/original-hash health completed. CLOSED/19,
`recovery_required=false`; no replay or standing native lease remains.
The photograph and retained HUD records show memory/CPU but gauge SOC, voltage,
current and gauge age N/A. Module insertion return does not prove child binding
or reads; the retained evidence cannot localize that failure. **v0.1.2 is not
confirmed.** See the [run report](docs/reports/S22PLUS_FYG8_GAUGE_HUD_V012_RC1_H0_2026-09-09.md).

Previous functional version: **v0.1.1 — system-status HUD**, mapped to successful
v0.1.1-rc.1 / run-001 (internal P377) without rebuilding or renaming artifacts.
The attended run passed all six fixed qualifications and three planned commands,
then one exact rollback and final rooted FYG8/original-hash health. CLOSED/19,
`recovery_required=false`; no replay or standing native console/HUD lease remains.

The operator photograph shows the grid-aligned text, memory/CPU and version/
purpose footer without visible clipping. Physical output is OBSERVED. Memory
and CPU are machine-qualified; battery capacity/charge/temperature show N/A and
remain unmeasured in native boot. Supplemental stock proof stays NO_PROOF_OBSERVER.
See the [status HUD report](docs/reports/S22PLUS_FYG8_STATUS_HUD_V011_RC1_H0_2026-09-09.md)
for the exact artifacts, photograph metadata, canonical timeline and limits.
This bounded unit is complete; any next candidate needs its own current authority.

Previous functional version: **v0.1.0 — root console and minimal HUD**, mapped to the
unchanged P376 artifacts and completed run. New experiments use the
[version/candidate/run naming convention](docs/operations/S22PLUS_FYG8_VERSIONING.md).
This mapping changes no internal identifier, consumed evidence or device authority.

P376 minimal HUD plus root console is complete. The attended run
`p376-ready1-prepared-20260909-1` closed with
`PASS_F1_V2_P376_ROOT_CONSOLE_AND_ROLLED_BACK`: all six fixed qualifications and
three planned commands passed. Matched HUD updates continued during console
work, and the operator reported seeing the text and increasing UPTIME.
Physical output is OBSERVED; machine pixel proof is not claimed.

One candidate and one exact rollback completed. Final rooted FYG8 Android,
original partition hashes and Download absence passed; CLOSED/19 with
`recovery_required=false`. No recover invocation, replay or standing console/HUD
lease remains. Supplemental stock evidence is still NO_PROOF_OBSERVER.
See the [P376 report](docs/reports/S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md)
for the canonical timeline, evidence hashes and limits. Any next candidate
requires its own current binding and authority.

P375 root console implementation, independent review and one attended live run
are complete. Run `p375-ready1-prepared-20260909-1` closed with
`PASS_F1_V2_P375_ROOT_CONSOLE_AND_ROLLED_BACK`: five fixed qualification commands
and three sealed plan commands passed; one candidate and one exact rollback
completed, followed by verified rooted FYG8 Android and original partition
hashes. The journal has 19 records, CLOSED, `recovery_required=false`.

The proved capability is repeated root BusyBox `sh -c` execution supervised by
native PID1 over one authenticated transport, real proc/sys/dev, same-boot RAM
state, bounded stdout/stderr, STATUS and cancellation. CONTROL acceptance and
observed exact Download rollback remain separate evidence. The supplemental
stock projection remains `NO_PROOF_OBSERVER`; it provides no causal stock proof.
No standing shell or replay authority remains. Any next run needs its own
current binding and authority. See the [P375 report](docs/reports/S22PLUS_FYG8_P375_ROOT_CONSOLE_H0_2026-09-09.md)
for the canonical timeline, evidence hashes and limits.

The preceding reviewed attended batch used three fixed display-step candidates:
P372 queues one fixed pattern; P373 queues two fixed patterns in order; P374
exits its display child after a fixed request starts, before completion. Shared
PID1 supervision must retain CONTROL independently of child work. Queued,
started, completed, child-failed, Download arrival, rollback and final health
remain separate evidence. Pixel output remains operator observation unless
independently proved.

Implementation, strict ARM64 A/B builds, candidate-static/common checks and one
shared independent review are complete. All three READY manifests and the
source-bound attended-session capability review are published; 142 changed-path
tests plus two activation-gate tests passed. See the [shared H0 report](docs/reports/S22PLUS_FYG8_DISPLAY_STEP_SESSION_H0_2026-09-09.md).

The attended P372/P373/P374 session is complete. Each candidate ran once,
rolled back once and closed PASS/CLOSED19 with recovery_required=false and
validated rooted FYG8/original hashes/Android/Download absence. P372 completed
one fixed request; P373 completed two in order. P374 started one request but
completed none, exited its display child with code7, and retained STATUS/CONTROL
with the signed pending/failed state. The declared child failure is the intended
negative display outcome. Original execute completed each run without a recover
invocation. P372's temporary final-health ADB offline resolved within the existing
wait; the operator separately observed Android.

All three reservations are consumed and the grant is closed. No active native
session or replay authority remains. P375 does not reuse that grant.
Visible pixels, continuous liveness, child/kernel/PID1 stall recovery and
unattended operation remain unproved. The shared report preserves exact results,
source qualification, evidence limits and canonical timelines.

P371's separately approved third preparation is consumed and CLOSED/19 with
`PASS_F1_V2_P371_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK`, recovery_required=false.
Two fixed STATUS replies after planned handoff passed, with signed native
spacing 2121 ms and the expected unreaped-child/wait facts. CONTROL, exact
Download, one candidate/rollback and final rooted FYG8/original hashes/Android
health passed. No native session or replay authority remains. Earlier ABORTED/4
and cold-ADB preparation records are preserved; no continuous-liveness/pixel/
kernel-stall or unattended claim follows. See the [P371 report](docs/reports/S22PLUS_FYG8_P371_FIXED_STATUS_PREPARATION_2026-09-09.md).


## Archive and continuing boundaries

The previous 799-line goal, including P371 closure and earlier archive links,
is preserved byte-for-byte in [the completed-history archive](docs/archive/roadmaps/GOAL_THROUGH_P371_2026-09-09.md).
That history is evidence only. Private append-only campaign records and run
journals remain authoritative for effects. Consumed candidates are never replayed.

Never prepare a new experiment over unhealthy or uncertain state. Preserve exact
target, current boot, candidate/rollback, topology, source and journal bindings.
An unexplained device-session failure stops the experiment; retain raw evidence
and continue only allowed observation and preauthorized recovery. A reporting
failure never repeats a device effect. A90 and S20+ are outside this unit.
