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

**Current task: reserve 64 GiB for native-only persistent storage while
retaining Android.** The operator allows resetting current Android apps,
settings and user data. Existing boot-only recovery does not qualify GPT
restoration. The native census closed `NO_PROOF` with healthy DETACH; missing
native UFS initialization is a likely cause, not the proved failed guard.
The separately approved original-A return then completed one image transfer.
Its first Android health query returned ADB `error: closed`; after actual
attendance was confirmed, health alone resumed and passed. The task is closed
`ANDROID_CLOSED_HEALTHY`, with no repeated transfer or pending F1 owner.
The first foreground Android D0 obtained both GPT headers and the primary
table, but omitted the backup table and remains `NO_PROOF` with final health
proved. The observed array starts nine blocks from LU0's end. The fixed tail9
successor received independent `PASS_GO`, and all 68 focused tests pass.
Its pre-read extent guard excludes userdata. It is ready for one foreground
read; no new transition grant is needed. No partition write or format has occurred. See the
[result and Android successor](docs/reports/S22PLUS_ANDROID_STORAGE_CENSUS_H0_2026-09-15.md).

## Retained native baseline

**The clean V3 owner completed P393 bootstrap and P394 physical USB
reconnect N/E/N. P393 is admitted and retained `NATIVE_CLOSED_HEALTHY`.**
The actual attended grant covered 3600 seconds and three operations. Bootstrap
completed two P393 installations and four authenticated health sessions.
The following N/E/N operation completed fresh starting-N health, one P394
installation, E health/DETACH, actual cable departure and a new USB generation,
fresh same-boot E authentication/CONTROL, P393 restoration and one final
health/DETACH. All eight required native health observations passed.

The reconnect's authenticated ordinal advanced from one to two with a fresh
nonce and unchanged kernel boot identity. Physical departure and new USB
arrival were observed within the original 120-second window. This qualifies
the selected actual reconnect, not long-duration reliability or automatic
recovery from a stalled device. HUD was not requested. Original Android A
recovery was unnecessary; it was not exercised in this task.

Both operation terminals and their raw evidence rederive. The task is closed,
two operations are consumed, the unused third operation is retired and no F1
owner remains. P394 stays consumed; P393 retains its original V3 admission
and final tail. A later device operation requires its own current authority.
The five-file PC configuration remains installed as verified external
configuration. The operator reported the missing `rc.1` display suffix;
both qualified images display `v0.2.1`, and this presentation detail remains
recorded without changing consumed artifacts. See the
[live result and timeline](docs/reports/S22PLUS_NATIVE_SESSION_V3_LIVE_2026-09-15.md).

The [V3 implementation](docs/operations/S22PLUS_NATIVE_SESSION_V3.md) and
common/target adoption received exact-source independent `PASS_GO`.
Passing H0 runs cover 86 selected tests. P393 N and P394 E share the same
144-file native source closure and passed ARM64 A/B and AP/member
qualification. The installed polkit API correction passed actual
noninteractive host readiness before the grant opened. See the
[H0 result](docs/reports/S22PLUS_NATIVE_SESSION_V3_H0_2026-09-15.md).

The [validation proportionality audit](docs/reports/S22PLUS_VALIDATION_PROPORTIONALITY_AUDIT_2026-09-15.md)
identifies host authentication inside execution deadlines and pre-effect grant
consumption as the first workflow corrections. Retained-log and whole-policy
invalidation are narrower review candidates; relevant transport/ABI tests and
effect/recovery proof remain necessary. The audit changes no runner, grant or
host setting and does not renew P392.

## Earlier Android recovery and clean-baseline preparation

P392 / v0.2.1 implemented idle USB tty reacquisition on rc.9's thermal V3
baseline. Its first actual boot and two authentication sessions passed, but
the host's second `pkexec` prompt did not complete within the old guard's
30-second arm window. No second native transfer intent exists. Original A
fallback ran once and closed healthy Android. That grant is closed and P392
remains consumed, unadmitted and unavailable for replay. Its physical USB
reconnect trial never ran; the fresh P393/P394 V3 work above later qualified
the shared runtime. See the
[P392 H0 report](docs/reports/S22PLUS_NATIVE_USB_RECONNECT_H0_2026-09-14.md).

The separately approved physical-Download Android exit completed
`ANDROID_CLOSED`, with one exact original A transfer and rooted FYG8 health.
The approved P392 bootstrap then closed `ABORTED_NO_DEVICE_EFFECT` during its
Android D0: the complete retained log contains one valid P387 carrier record,
so the existing clean-baseline decoder correctly rejected it. Initial Android
health passed; no P392 Download request or transfer occurred. Both grants are
closed and their F1 owners released. P392 was still unconsumed at that point;
its subsequent single installation is recorded above.

The existing attended normal-reboot profile then completed one reboot with
changed-boot health `PASS`. Its code was unchanged; independent `PASS_GO`
refreshed only the common/target receipt bindings and reused the unchanged
25-test evidence. Fresh complete D0 now passes with a clean retained baseline,
zero evidence-family markers and exact current Android health. No F1 owner or
pending reboot remained. The separate one-operation/600-second request
`p392-bootstrap-20260914-2` was then approved and consumed as recorded above;
the first grant remains closed despite its zero image transfers.
Preparation, raw results and H0 replay are under
`workspace/private/outputs/s22plus-v021-live-prepare-20260914-1/`.
Existing P387/P391 admission and consumed records retain their meanings;
Samsung USB recovery and long-duration reliability remain unproved.

## Previously qualified proportional research amendment

**The operator-approved proportional research amendment is implemented and
H0-qualified with independent `PASS_GO`; all 46 selected tests pass.** Revision
11 updates the common contract and S22+ contract together. One finite scope can
admit spontaneous in-scope candidates without per-candidate human approval,
with reviewed read-only reobservation, prospective healthy-N-return repeats,
and explicitly selected attended or deferred physical recovery. Earlier
consumed images and grants retain their meanings. See the
[policy](docs/operations/S22PLUS_PROPORTIONAL_RESEARCH_V1.md) and
[H0 report](docs/reports/S22PLUS_PROPORTIONAL_RESEARCH_H0_2026-09-14.md).

The actual P391 terminal, P387 admission and all 121 P387 native inputs still
rederive unchanged. The old D0 stop can be read by the new exact-evidence
importer, but remains unresolved. No new grant, candidate build or physical
device action occurred during the amendment. Capability qualification does
not prove current USB response or authorize a new experiment by itself.

## Earlier unresolved observation before Android recovery

**The requested post-amendment D0 reobservation also ended
`NO_PROOF_NATIVE_RESPONSE_UNRESOLVED` at 2026-09-14 04:06 KST.** The reviewed
observer sent one 32-byte OPEN and received zero bytes during a **59.940-second**
capture. No AUTH, EXEC, CONTROL, DETACH or image transfer occurred; the guard
released. A passive check at 04:08 KST still matched the exact native USB and
tty identity. Current uptime, temperatures and authenticated native health
remain unverified; USB enumeration does not establish application responsiveness.
No second attempt or recovery followed. A90 and S20+ received no command.

The new failed attempt preserves the earlier D0 stop and its successor chain.
Its structured result has SHA-256
`b0641be6354a3fb63f7744ed8817330fbeec2c0256581ee109a43884181eaad2`;
the reviewed source commit is `bba51ac736db530594c30416883ff00f6d27ca83`.
Raw evidence and the close summary remain under the corresponding
`workspace/private/runs/s22plus-native-reobservation-v1/20260914-requested-status-1/`
and `workspace/private/outputs/s22plus-status-check-20260914-1/` directories.

### Earlier checkpoint and operator observation

**The requested resident D0 checkpoint stopped with
`NO_PROOF_NATIVE_RESPONSE_UNRESOLVED`; the operator observed continuing local
display and system sampling.** At 2026-09-14 01:22:44 KST the exact guarded
native tty accepted one valid 32-byte OPEN from the host. No response arrived
in approximately 59 seconds: retained RX is zero bytes, with no AUTH, EXEC,
CONTROL or DETACH. The aggregate capture lasted 60.465 seconds. Both current
ModemManager protection flags and the owner-only tty-holder check passed;
the guard released. No reboot, image transfer, recovery or native retry followed.

The operator's photo shows `v0.2.0-rc.5`, uptime **18:49:06**, `SYSTEM: FRESH`,
`SENSORS: FRESH`, system sample sequence **67,676** and sensor sequence **67,262**.
The operator explicitly confirmed that UPTIME and SYSTEM SAMPLE keep advancing.
This supports current local monitoring/display activity and long-duration
resident operation. The USB response failure does not establish device-wide
stoppage; its cause and complete interval health remain unproved. Current boot
identity and health were not authenticated through the USB observer.

H0 follow-up found a matching native USB disconnect/re-enumeration at
**2026-09-13 16:32:22–24 KST**. The source retains one tty handle and treats
pre-OPEN EOF/EIO as peer absence while continuing local service. The inspected
kernel's tty hangup behavior makes an unreopened hung-up handle the leading
explanation. This is a source-backed hypothesis, not a live handle trace or
proof of the disconnect cause. No device action followed this diagnosis.

The historical P391 terminal is unchanged. Its new explicit D0 successor
intent is consumed, so the old native predecessor cannot start another F1
operation. This failed checkpoint is not a healthy replacement terminal.
New state-changing native effects remain stopped. The reviewed fixed D0 path
preserves both failed attempts; H0 communication diagnosis may continue.
See the [D0 checkpoint and operator-observation report](docs/reports/S22PLUS_NATIVE_RESIDENT_D0_2026-09-14.md).
A90 and S20+ received no command.

## Previously qualified deferred physical capability

**S22+ deferred physical native-baseline mode is H0-qualified with current
source-bound independent `PASS_GO` and activated capability receipts.** The
operator-requested [policy change](docs/operations/S22PLUS_NATIVE_BASELINE_DEFERRED_RECOVERY_V1.md)
permits one explicitly selected native-origin N -> E -> N experiment without
attendance, with one reservation/600 seconds and an exact returned finite grant.
Failure stops further effects, retains ownership and leaves activity unknown
until later attended original-A recovery. It does not claim automatic failure
recovery. Existing absent-mode grants remain attended, and consumed runs remain
consumed. See the [H0 change report](docs/reports/S22PLUS_NATIVE_BASELINE_DEFERRED_RECOVERY_H0_2026-09-13.md).
No new candidate, request, grant or device action is part of this policy work.
All 26 selected tests passed; retained P391/P387 proof still rederives. The
capability definition does not grant a trial or resolve the later native D0
communication stop.

## Earlier closed P391 experiment

**P391 N -> E -> N is closed with `PASS_P391_N_E_N_NATIVE_CLOSED`;
CPU, GPU, DDR-region and board battery temperatures are observed.** One P391
installation and one normal P387 restoration completed under the separately
returned one-operation/600-second approval. All five authenticated health
sessions across three distinct native boots passed. Final DETACH/descriptor
close completed at **291.554 seconds**; Android transfers: **0**. The grant is
closed, the F1 owner released, and P391 is permanently consumed.

Latest retained E temperatures are **CPU maximum 26.3 C (12/13)**, **GPU maximum
26.3 C (2/2)**, **SoC DDR-region 26.2 C (1/1)** and **board battery sensor 15.3 C**.
All 16 mappings and both TSENS bank bindings passed. TRDY remained `[8,8]`, but
V3 performed the selected status reads and accepted each sensor's VALID bit and
temperature together. Retained frames 2..10 had **13/13** CPU coverage; only the
last retained frame 11 had `cpu-1-3` (bank 0 sensor 8) VALID clear and 12/13.
The operator photo's sample-8 values match retained frame 8 at 10.804 seconds.
The final zero placeholder is not a temperature or proof of a persistent sensor
failure. Why VALID cleared at that later read remains unproved. DDR-region is
not RAM-die temperature.

At that close, the healthy native snapshot was restored **P387 / v0.2.0-rc.5**,
with its 121 native inputs and original temperature limitations unchanged.
That operation terminal has SHA-256
`3baf937274fcf3965956dfa7bc4384296dcc6819dd928a7dd623d9ccdac3ecaf`;
the earlier P390 terminal's successor is consumed. The actual terminal,
experiment-outcome and admission readers rederive. Native close is past health
evidence, not continuous liveness or standing authority.

See the [P391 H0/live report](docs/reports/S22PLUS_NATIVE_THERMAL_V3_H0_2026-09-13.md)
and [thermal V3 profile](docs/operations/S22PLUS_NATIVE_THERMAL_V3.md). The
qualification includes 32 regression tests, six actual-artifact mutation tests,
real ARM64 producer/consumer and A/B package checks, plus independent PASS_GO
for both exact 211-source variants. All execution pins remained unchanged
through the run. The consumed request SHA-256 is
`156fc01de788ccdbf2a8a2fb02f6d9cf940a07c7782e3cedcc0e73ee4beb5cc7`.
Source commit: `91924d4a4d2047f3f8693867b848648b91440fc4`.

Latest sample/frame capture is complete and fresh within the software bounds;
complete history and hardware conversion age remain unproved. The later operator
photo provides a separate visual observation matching frame 8; the machine
observer's physical-visibility flag remains unchanged. No device transition or
read was repeated for reporting. A90 and S20+
were untouched. Any future experiment needs its own current authority and fresh
runtime binding; this completed run cannot replay.

## Earlier closed P390 trial

**P390 N -> E -> N is closed with `PASS_P390_N_E_N_NATIVE_CLOSED`; thermal
qualification remains partial.** One P390 installation and one normal P387
restoration completed under the exact returned 600-second request. Five
fresh authenticated health sessions across three native boots passed; final
DETACH/descriptor close occurred at **265.286 seconds**. Android transfers: **0**.
The grant is closed, the owner released, and P390 is permanently consumed.

The latest retained E sample proves board-ADC battery temperature **18.6 C**.
CPU **0/13**, GPU **0/2** and SoC DDR-region **0/1** remain `NO_PROOF`; zero
placeholders are not temperatures. This time all 16 mappings and both TSENS
bank bindings passed. Both acquired readiness words were `8`, whose bit 0 is
clear; the provider returned its own `-ENODATA` and read no sensor status words.
FYG8's source-selected v2 getter uses the per-sensor VALID field without that
extra TRDY precondition. P390 did not observe actual VALID bits/temperatures;
the cause of the low TRDY bit remains unproved. The separately qualified P391
successor above addresses the extra gate; P390 itself cannot replay.

At that close the healthy native snapshot was restored **P387 / v0.2.0-rc.5**,
with 121 native inputs unchanged. Its then-current P390 terminal had
SHA-256 `ad377de602a54ff20444da663f641f6192cc93d08b677d5930481be4a3ceb41d`;
the earlier P389 terminal's successor is now consumed. Native close is past
health evidence, not continuous liveness or standing authority.

See the [P390 H0/live report](docs/reports/S22PLUS_NATIVE_THERMAL_V2_H0_2026-09-13.md)
and [thermal V2 profile](docs/operations/S22PLUS_NATIVE_THERMAL_V2.md). Its
pre-run H0 qualification had independent PASS_GO for 207 execution inputs,
35 regression tests plus five actual-artifact mutation tests, and actual ARM64
IPC/A/B package qualification. The closed request SHA-256 is
`fe000f4e0fe1099900d32d408832a396bed7cb8cc9b36d5aae71b87ca5d6f21f`.
No candidate, normal N role, grant or device read was repeated after close.

The completed [thermal census and follow-up](docs/reports/S22PLUS_THERMAL_SENSOR_CENSUS_H0_2026-09-13.md)
remain separate evidence for the original CPU path defect and remaining
RAM/UFS/board questions. Exact UFS temperature support and RAM-die temperature
remain unproved. Additional ADC channels, UFS queries and PMIC/GPIO control are
outside P390.

## Earlier closed P389 trial

**P389 `N -> E -> N` is closed with `PASS_P389_N_E_N_NATIVE_CLOSED`;
temperature support is partial.** The latest retained P389 thermal HUD reports
fresh board battery temperature **17.3 C**, but CPU coverage is **0/13**:
CPU temperature remains `NO_PROOF`, not 0 C. See the
[thermal H0/live report](docs/reports/S22PLUS_NATIVE_THERMAL_H0_2026-09-13.md).

The exact returned request `23609ee53498286084ccc01ec44db7a4dbefc7c1cff2359c0737bb538f984ee4`
consumed one P389 E installation and one normal restoration of admitted P387 N.
All five authenticated health sessions passed across the starting N, E and
returned N boots. Final DETACH/descriptor close occurred 244.293 seconds after
the original grant start, within 600 seconds. Android transfers: **0**; no
research stop or physical fallback. The terminal rederives, the grant is closed,
and the F1 owner is released. P389 is permanently consumed and cannot replay.

That run ended in healthy P387 / `v0.2.0-rc.5`, whose 121 native
inputs remain unchanged. Its original temperature limitations remain expected.
The retained E HUD lacks CPU-bank diagnostic fields, so it cannot directly
distinguish probe rejection from readiness/status failure. The subsequent H0
path-defect reproduction above is separate from that live evidence; no further
device read or hardware-enable attempt occurred after close.
The historical P389 H0 qualification has 24 passing tests and independent
`PASS_GO` for its then-current 195-source capability. Any future E still needs
its own exact artifacts and current finite authority. A90 and S20+ were untouched.

## Baseline admission and earlier P388 roundtrip

**P387 bootstrap and the distinct P388 `N -> E -> N` roundtrip are COMPLETE:
`PASS_P387_BOOTSTRAP_AND_P388_N_E_N_NATIVE_CLOSED`.** Both exact returned
approvals completed within their separate one-operation/600-second grants.
Four native transfers and nine authenticated fixed-health sessions passed
across four native boots. P387 is admitted, P388 is permanently consumed, and
the final P387 boot closed in `NATIVE_CLOSED` with fresh health, clean
reauthentication and actual DETACH/descriptor close. Android transfers: **0**.
Both grants are closed, both F1 owners are released, `recovery_required=false`,
and neither operation has a research stop. A90 and S20+ received no commands.

The separately reviewed, intentionally uncommitted current-instance capability
receipt binds the unchanged 186-source working-tree variant. The committed H0
receipt is preserved; neither the reader nor unrelated S20+ work was changed.
See the [live qualification](docs/reports/S22PLUS_NATIVE_BASELINE_V2_H0_2026-09-12.md#live-bootstrap-and-experiment-roundtrip-2026-09-13-kst)
for exact source, request, terminal and admission evidence. A duplicate host
summary after the first complete native close exceeded its generic record cap;
the original terminal/admission/completion rederived unchanged, and only a small
host summary was written. No device transition or native role was repeated.
The final state is a past authenticated native snapshot, not continuous-liveness
or automatic-failure-recovery proof. Future experiments require a fresh declared
E and current finite authority; the consumed P388 may never replay.

## Completed H0 precursor

The completed [resident native baseline V2 H0](docs/reports/S22PLUS_NATIVE_BASELINE_V2_H0_2026-09-12.md) unit defines
normal `N -> E -> N`, with Android A for explicit exit or failure fallback.
The separate common-incorporated [V2 policy](docs/operations/S22PLUS_NATIVE_BASELINE_V2.md)
and shared owner bind proposed P387 N and distinct globally one-shot P388 E,
resident clean reentry without a normal lifetime ceiling, and finite attended
host authority. **H0 capability is complete with independent PASS_GO**:
58 distinct tests, 21 publication cuts, actual identical AArch64 A/B boot-only
APs, all 186 reachable execution sources, and full request/terminal reopening
under unchanged bounds. The public review binds this unit's selected commit
bytes; existing unrelated S20+ AGENTS changes remain outside that commit and
made the differing local working tree fail its capability source check at H0
close. That H0 unit made no device contact, grant, live bootstrap or admission.
Live N qualification and the distinct E roundtrip were unproved at H0 close;
the separately approved live results above now supply that bounded evidence.

## Earlier ordinary F1 result

P386 **READY2 is COMPLETE: `PASS_F1_V2_P386_ROOT_CONSOLE_AND_ROLLED_BACK`,
`CLOSED/19`, `recovery_required=false`**. Its separately returned attended
approval consumed one native installation and one exact Android return. Four
authenticated checkpoints and eight fixed commands passed across **1,825,019 ms
(30 minutes 25.019 seconds)**. Fresh system/gauge samples advanced beyond the
old 601-sample and 900-second limits. Final rooted FYG8, original boot/supporting
hashes, Android readiness and Download absence passed. The exact Download return
was inside the original CONTROL window with no physical-fallback prompt.

The original execute reached CLOSED but failed to publish its 67,863-byte
indented result under the 65,536-byte cap. Independently reviewed H0 finalization
used the unchanged original runtime and complete validator to publish the same
data as 38,437-byte compact JSON, then retired the F1 owner. All 2,076 original
run files retain their bytes and modes; no command, transfer, CONTROL or device
observation was repeated. The subsequent reviewed terminal-writer correction
keeps the same cap and journal encoding. Original preparation, source pins,
approval, failure output and consumed candidate claim remain unchanged.

CPU temperature was not observed: all four CPU sensor masks were zero. Physical
pixels, uninterrupted liveness between checkpoints, causal software return and
automatic failure recovery remain unproved. This ordinary F1 result creates no
native-baseline admission, same-N restoration role or standing device grant.
A90 and S20+ received no commands.

Earlier READY1 ended `ABORTED/4` before Download or either transfer because the
resident adapter accessed the guard through the wrong wrapper. Its guard cleanup
succeeded; the old run/token stays closed. The minimal guard-owner correction
passed independent PASS_GO and nine regressions before READY2 preparation and
its separate approval. Those original records remain unchanged; the later
READY2 installation has now consumed the candidate content.

Earlier P386 preparation used **one ordinary Android reboot**.
The D1 observer stopped when ADB was online but the successful property output
still had empty `boot_completed` with a running boot animation. Separate fixed
read-only reconciliation proved the changed healthy Android boot and cleared
pending recovery bookkeeping; the original D1 STOP and closed goal remain.
A narrow readiness correction now polls only that fixed nonroot property within
the original deadline before strict health parsing. Independent PASS_GO and
25 tests passed; the used source/review are preserved privately. That stopped
goal performed no second reboot, P386 connected preparation or F1 transfer.
Subsequent D0 preparation used fresh operator continuation and preserved
the closed goal, STOP and separately observed late health. Its one-reboot
allowance remains consumed.
See the [execution and preparation report](docs/reports/S22PLUS_P385_EXIT_P386_F1_PREPARATION_2026-09-11.md).

The [P385 exit / P386 resident observation](docs/reports/S22PLUS_P385_EXIT_P386_F1_PREPARATION_2026-09-11.md)
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
P386's later ordinary thirty-minute observation is complete as recorded above;
its consumed execution closure excludes the repaired native-baseline owner.
The stopped P385 grant supplied no P386 authority or further native role.

The [resident adoption H0 V1](docs/operations/S22PLUS_NATIVE_RESIDENT_ADOPTION_V1.md)
unit is complete with **PASS_RESIDENT_ADOPTION_H0 / independent PASS_GO for H0 only**.
P386 / v0.2.0-rc.4 connects the qualified resident runtime to a deterministic
boot-only AP, four authenticated checkpoints spanning thirty minutes, and the
ordinary one-N/one-A installation/return owner. Actual AP decoding, generated-C
integration, retained replay, full preparation/reopen and failure recovery pass.
The final review binds 157 static inputs and 176 unique execution sources.
No device contact, live activation, prepared run or grant occurred in that H0
unit. See the
[H0 report](docs/reports/S22PLUS_NATIVE_RESIDENT_ADOPTION_H0_2026-09-11.md).
The later P385 Android exit and separately approved P386 execution are recorded
above; neither completed run grants another device action.

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
