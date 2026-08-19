# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. A90 identity, artifacts,
authority, evidence, transports, and commands remain separate.

## Current Frontier

P3.18 is the current closed live unit. Candidate and exact rollback transferred
once; the operator saw a normal boot without a loop and ACM `endpoint-timeout`.
Two final reads have clean Carrier framing/CRCs; the frozen decoder exposed `[valid, bad-body]` without proving terminal absence. Reviewed H0
recovers generation 47/stage `0x66`/item 38/failure `0x6010`: the latch shifted
`eud.ko` from 37 to 38 while its trigger stayed 37. Historical sweep proves
P3.10/11/13/14/17 kept both at 37; it adds no older reclassification, while
P3.10/14/17 frozen-Carrier agreement is now host-audited. Max77705
was never reached, so effective proof is `NO_PROOF_EXPERIMENT_PRECONDITION` and
historical close is `NO_PROOF_OBSERVER`. A reviewed finalizer used one fresh FYG8-health approval, no Download/Odin/transfer/replay, and advanced the journal from 15 at `ROLLBACK_FLASHED` to 19 records at `CLOSED`.
Terminal is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; exact transfers remain 1/1,
attempt 2 is absent, and `recovery_required=false`. A successor must derive the
EUD trigger from its effective plan, retain the decisive witness in the ring,
and keep ACM supplemental until a physical-device positive control qualifies it.
Reports: `docs/reports/S22PLUS_FYG8_P318_POSTROLLBACK_FINALIZATION_INCIDENT_H0_2026-08-17.md`
and `docs/reports/S22PLUS_FYG8_P310_P318_HISTORICAL_EUD_INDEX_SWEEP_H0_2026-08-17.md`.

P3.16 is the preceding closed live unit. Its distinct boot-only candidate and
exact Magisk rollback each transferred once, the journal closed, and rooted
boot-completed FYG8 health passed after rollback. Its retained observer was
sound but proved that the Max77705 experiment did not execute; the effective
class is `NO_PROOF_EXPERIMENT_PRECONDITION`. The immutable decoder spelling and
original append-only ledger row remain historical evidence.

P3.15 is the preceding closed cycle unit. Its distinct boot-only candidate and
exact Magisk rollback each transferred exactly once. The Process-v2 journal is
`CLOSED`; rooted boot-completed FYG8 Android, boot and supporting-partition
identities, stopped boot animation, and absence of Download mode passed with
`recovery_required=false`. The operator observed a normal candidate boot
without a loop. The consumed candidate is never replayable, and its prepared
binding grants no remaining authority.

The exact ACM observer timed out at zero bytes, but this was not an observer
no-proof. Two full-length, byte-identical retained reads contain one
integrity-clean, foreign-count-zero Carrier-v2 record with adjacent generations
106/107: A=`0x0d3f` records cycle-attempted, not-attached, speed UNKNOWN, and
B=`0x5064` records path-drift mask `0x04`. The candidate-side USB sidecar was
integrity-clean and observed no new candidate USB connection after Download
departure.

The exact materialized parser and frozen encoding make `0x04` the sole
`OUTER_WORK` bit. All ten functional pair counts were exact; pullup pairs were
zero; RUN_STOP pairs were two; gadget-start was one pair; QSCRATCH, state, and
event-config each appeared once; and the required resume nesting held. These
fixed contributions account for 33 records. Since the final parser accepts
only 41 clean or 49 bounded-drift records, the nonzero outer-work bit forces
the 49-record case and therefore eight complete `dwc3_otg_sm_work` pairs,
twice the source-derived expectation of four.

P3.15 therefore refutes the clean four-outer-work cycle model while proving
that the restart-side functional path, nested gadget-start/RUN_STOP, and
postcycle digital witnesses executed. The frozen Result Contract revokes a
cycle-causal claim on multiplicity/path drift, so neither the host silence nor
the not-attached/UNKNOWN result may be attributed to a clean cycle, and none
of this proves whether a USB2 pull-up reached the connector. The live decoder's
generic `cycle_causal_claim=true` default is not used to override that explicit
contract.

Post-live H0 corrects rather than upgrades the P3.15 result.
`p315_wait_restart_completion()` read one completion snapshot and accepted
exactly four complete outer pairs plus the single nested start-on pair. The
runtime then performed a distinct profile-bearing RESTART read. Its strict
parser accepted either 41 clean records or 49 bounded-drift records, but that
second snapshot's record count was not retained. The terminal eight-pair
result therefore proves only that four additional outer invocations completed
after the completion read and before the final snapshot. It does not place
their execution after the RESTART read, and their enqueue provenance may even
predate the completion read.

The reusable derived fact is correspondingly narrower: the restart completion
causal prefix reached the exact four outer pairs and one nested start-on pair,
and the final functional tuple proves the expected restart-side PHY, power,
gadget-start, RUN_STOP, QSCRATCH, state, and event-configuration witnesses.
Because every functional count stayed exact, the four additional completed
outer turns took none of those functional branches. The frozen P3.15 label
remains `REFUTED` and the multiplicity rule continues to forbid a clean-cycle,
connector, or pull-up claim.

The fixed wrapper has no inert-state self-loop: `dwc3_otg_sm_work()` requeues
itself only when `work` is true. Source-real external queue sources include
wrapper role/VBUS/ID notification, UCSI and Samsung notifier control planes,
resume work, PM completion, and power events. P3.15 retained neither the
completion-to-RESTART delta nor raw ordering, so the consumed run cannot
identify which source queued the four later completions. Provenance closure is
mandatory only for a successor that reuses the `none -> peripheral` cycle or
claims causality from it; it is not a prerequisite for an independent path
that does not inherit that cycle.

The forward frontier has moved off the connector-side Max77705 USB2 MUX discriminator to the role chain: role request, UDC bind, DWC3 pull-up/connect, physical host attach.
Stage A's first directory-only D0 requested zero attribute/I2C reads but the host parser discarded raw stdout before reporting a shape mismatch; the permanent D0/F1 raw-first handle boundary and granular Stage A parser then took independent H0 PASS_GO, and Stage B has since run and read CONTROL1 directly, so regmap presence and the Stage B target are proved rather than pending. An independent review demoted the MUX and 2026-08-19 host-only work supplied the structural ground: the P3.17 plan substitutes `s22plus_max77705_mux_diag.ko` for the stock driver on the same `maxim,max77705` compatible, so `max77705_muic_attach_usb_path` never runs on that candidate and its `0x3f`/`0x09`/`0x09` shows the command protocol reachable with CONTROL1 retaining `COM_USB` while saying nothing about the stock attach path. On the new frontier `B_SESS_VLD`, not `vbus_active`, gates `dwc3_otg_start_peripheral`, and a sticky `EUD_SPOOF_DISCONNECT` clears it while `mode` still reads `peripheral`.
The stopped D0 is `docs/reports/S22PLUS_FYG8_P319_MAX77705_ATTRIBUTE_STAGE_A_D0_OBSERVER_STOP_2026-08-17.md`; the raw-first H0 closure is `docs/reports/S22PLUS_FYG8_P319_RAW_FIRST_OBSERVER_BOUNDARY_H0_2026-08-17.md`; the host-only closure of the review's five ranked items is `docs/reports/S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md`; the source authority remains
`docs/reports/S22PLUS_FYG8_MAX77705_CONTROL_PLANE_SUCCESSOR_FEASIBILITY_H0_2026-08-11.md`.
It preserves the MUX as a source-real but causally unproven residual mechanism:
P3.15 omitted the exact GENI-I2C/MFD/PDIC producer closure that contains the
normal `COM_USB` transition, while its controller-side digital witnesses were
present and its same-session host USB sidecar remained candidate-silent.

The stock comparison keeps `ucsi_glink.ko` and adds six modules, taking the
61-module plan to 67. The pinned vendor ramdisk can rematerialize the complete
P3.15 base and all six stock additions with their recorded identities.
Cross-inventory comparison partitions those 67 names exactly into 37
first-stage names and 30 tracked `vendor_dlkm` names;
all 30 second-stage rows match the expected size/SHA-256 and are marked
byte-identical. Gate 0 is now closed host-side. A bounded streaming extractor
authenticated the complete pinned ZIP, sparse super, logical raw super, and
57,610,240-byte `vendor_dlkm` extent while retaining only that extent. F2FS
inode 144 yielded the exact 5,843-byte `modules.load`, SHA-256
`8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360`,
with 356 unique module lines. This removes the former D0 alternative and keeps
the 140-line first-stage, 446-line recovery, and 356-line second-stage
authorities distinct.

The recovered Android line order is not a direct `finit_module` recipe. Within
the selected 67 names it contains 126 dependency-after-consumer edges, while
the inherited P3.15 61-module sequence followed by
`msm-geni-se`, `gpi`, `i2c-msm-geni`, `spu_verify`, `mfd_max77705`, and
`pdic_max77705` has a complete dependency closure and zero forward edges.
That closes byte/order arithmetic; target-only override/bind timing, stage
capacity, and the stock-versus-custom choice remain open.

Stock and custom successor shapes are not interchangeable. The PASS5 stock
MFD invokes its updater on every successful probe; retained Android evidence
proves one healthy no-update execution and therefore reduces novelty, but the
source has a named updateward read-failure default: failed firmware/status
reads can remain zero and classify as old firmware or battery-only, while
reset/retry edges disable the voltage/TA guards after the first pass. Stock-67
is unadjudicated.

The preferred bounded shape is now machine-registered as 65 modules: the
P3.15 base plus exact stock `msm-geni-se`, `gpi`, and `i2c-msm-geni`
substrate modules and one purpose-built
`s22plus_max77705_mux_diag.ko`. It does not load stock or custom MFD/PDIC, and
it omits `spu_verify.ko`. Instead it binds the otherwise-unowned
`max77705@66` parent directly, creates only the `0x25` USBC/MUIC dummy client,
reads and retains the whole stale UIC latch once, performs pre and immediate
post1 `CONTROL1_R`, holds one exact 30-second host-correlation interval, and
performs terminal post2 `CONTROL1_R`. It conditionally performs one
non-retried `CONTROL1_W(0x09)` only when pre is not the full `COM_USB` byte.
The module must load only after the gadget path and host sidecar are ready, so
its bounded probe dwell needs no workqueue or writable trigger.

The exact 491-module audit still matters: it proves PDIC alone consumes the
three removable MFD updater exports and also records the much broader stock
PDIC/MUIC/CC/PD/alternate/AFC/QC/notifier/user-control surface. That former
full-PDIC custom-66 design is now rejected as disproportionate, not retained as
the preferred implementation. The v10 authority retains the corrected source
validator and fixes the logical
transaction shape: neither post value may be synthesized, both reads occur
outside the optional-write branch, post2 follows the exact retention dwell,
and any I2C call outside the registered call multiset is rejected. The initial
UIC read consumes every latched bit, not only `APCmdResI`; its raw byte and all
poll bytes must therefore be retained. PMIC compatibility now follows the stock
low-three-bit revision rule while retaining the complete raw revision byte, and
the cached terminal string is published through one release/acquire readiness
pair. A getter invoked through the pre-init sysfs exposure returns `-EAGAIN`
rather than an initial or torn result.

The interpretation ceiling is now explicit. Pinned source proves the opcode
ABI but not that `CONTROL1_R` senses physical analog contacts or that a cold
write engages them without prior classification. Thus post2 distinguishes an
observed late opcode-state reversion, but no host-silent tuple refutes physical
MUX continuity. Host attach/enumeration is the only independent physical-path
witness in this diagnostic.

The corrected source and linked-ABI H0 gate is closed. The final builder ran
`validate_diag_source_text()` before compilation, reconstructed the exact
P3.10 source/ABI closure, and produced two byte-identical 293,400-byte modules
with SHA-256
`4f4f485a35cdb12206b814390b56674ca6a6d691c9a1d7a29c97030053231849`.
The audit proves exact FYG8 vermagic, 15 imports, 16 matching modversions, CFI
callback jump-table relocations, registered call counts, and zero exports.
The current private contract receipt is
`custom-surface-authority-20260812-15.json`, SHA-256
`2da2f53c981440663a1626024125bcced789872f664b0f4c59b7b07b14ecc339`;
its embedded contract is
`eefe1890d72bb7a03fe979e6349b8d64195a6beec04b9606949b78b601e2b472`.
That receipt remains the source/linked predecessor; the P3.16 runtime and
boot-only package now extend rather than rewrite it. No module was loaded on a
device.

Runtime integration is now implemented and arithmetically fenced. The
generic early loop is exactly 64 entries (the inherited 61 plus three GENI/I2C
substrate modules); the diagnostic is the staged sixty-fifth payload but is
forbidden from that loop. The inherited 20-second bind gate must close after
gadget readiness and host-sidecar arming, before one dedicated late
`finit_module` call begins a lifetime of at least 31 seconds. Actual-C fixtures
execute the dynamic adapter scan, exact pre/post binding witnesses, dedicated
late-loader helper, final pipe drain, bounded abort/reap, and result-read
priority. They distinguish seven observer sites by seven normalized error
classes, preserve only site-authoritative binding fields, and keep helper
failure above loader deadline above result-read failure. The synchronous result
may be sampled while loading, but parse/classify/publish remain forbidden until
the helper proves successful `finit_module` return. A post-return claim-busy
`EAGAIN` remains a required negative invariant, not an observable terminal.

The retained-telemetry sub-gate is closed H0-side. One fixed 128-byte
Carrier-v2 envelope preserves both 64-byte request-v3 payloads without an Image
change. All nine terminal buckets, all five MUX result classes, and the complete
seven-site by seven-error observer matrix have retained preimages through the
real Process-v2 adapter; claim-busy has an empty decoder preimage and encoder
acceptance is a hard error. The native envelope fixture executes 64 rows: 49
observer rows, nine terminal rows, five MUX rows, and one overflow row. The
actual transformed C publisher also emitted 15 byte-exact v3
requests (1,500 bytes of host-only fixture output, not retained or device
footprint; SHA-256
`1200128d11c57bda9fdfa879fb3e592a1d368e0fc15a6bed255957678a136b2d`),
rejected five out-of-family details, and left the inherited v2 publisher
byte-identical. Oversized lossless poll evidence terminates in the ninth,
explicit payload-unrepresentable no-proof bucket rather than truncating or
inventing causality. Envelope v2 keeps the four per-command poll counts, total
raw count, SHA-256, per-command OR, poll0, nonzero count, and fixed
transaction/result fields in 44 bytes, leaving 32 bytes zero; it retains no raw
sequence and cannot recover MUX causality. Post2 `CONTROL1` crossed with post2
poll0 now yields four explicit retention rows. The `0x7b` detection mask and
`0x0a` DCD/charger-type subset prove only a retained event and temporal
correlation, never physical switch movement or causation.

The exact allocation-free PID1 result parser is H0-qualified and integrated by
the P3.16 materialized runtime. Its private receipt is
`runtime-parser-20260812-01.json`, SHA-256
`692325e9e16a600b8ca8f62d3196d8304a3dab24301f26a266096ec0288ff209`.
The actual C accepted four canonical module strings, rejected thirteen syntax
or semantic mutations, matched Python SHA-256/OR/poll0/nonzero summaries, and
compiled freestanding for AArch64 with the pinned Android clang. It performs no
I/O and names no sysfs path; the surrounding runtime owns all I/O and loader
lifecycle.

This closes schema, carrier, decoder, publisher geometry, the isolated result
parser, and the exact sysfs-inventory D0 gate. The bounded read-only D0 selected
one healthy `SM-S906N/g0q/S906NKSS7FYG8`, observed one Android `04e8:6860`
endpoint and no Download endpoint, and sent no command to any other target.
Its 16,542-byte private result has SHA-256
`5adbb80d5178b709097abc2f9bcc0d597fafeab72f904057d9f44dbca18ccdcf`;
an independent host reparse matched its 72,904-byte raw snapshot exactly.

Live geometry is exactly three QUPv3 wrappers, three GPI devices, and nine
GENI I2C controllers. The target triplet is
`9c0000.qcom,qupv3_0_geni_se`, `900000.qcom,gpi-dma`, and `994000.i2c`;
the remaining twelve exact names are now frozen by the authority report. All
fifteen stock devices had the source-expected driver, exposed
`driver_override`, and read `(null)`. This is stock evidence, not permission to
inherit a bound state in the candidate: the future runtime must still apply
and verify twelve sentinels before loading any substrate module. The live
stock path was `994000.i2c/i2c-57/57-0066`, with the parent bound to
`max77705`. Adapter number `57` and both `57-*` client prefixes are stock
registration-context observations, not candidate inputs. The successor must
resolve the unique adapter below `/sys/bus/platform/devices/994000.i2c/` and
then the unique `*-0066` client below that adapter; a literal bus number is
forbidden. The stock MFD-created dummy clients do not become part of the
custom diagnostic's pre-load geometry.

P3.16 now has one canonical H0 package and offline Process-v2 ready bundle. The
frozen intent, prepackaging, final qualification, and static-closure SHA-256
values are respectively `7ed7530597dee0064fd76ba698aca5230e7efe079b099e9c1799b902814040b5`,
`4068d8aefd49adb38ed12465508aefada5025a7a99efda5b19c27ca5b6c0cbf0`,
`25dc4066b4e49bed0b46e100753accd515b98021783aa8e4e0918d1df6cd11dc`,
and `0842f1efb5a51bc05117e499a45ac65592504b46eaa6c3750537f49a9de568b5`.
Independent regeneration reproduced all four byte-for-byte. Candidate A/B have
identical boot SHA-256
`7c6ee851196b7d604aff7a4ce81eba271adc52c5408de10a568b924e8c6f41c9`
and AP SHA-256
`59893227c4deccc107d2fc4469a882e44212e076a0c5c8e4072031b853a6c6f0`.
Offline promotion produced run-manifest SHA-256
`803d8c106e538302bc64c89294678e0efd9a56de96a6d8bd93e57a7e9d8f1c00`;
the canonical ready manifest and a non-creating rehearsal agree at SHA-256
`a9fb48065d717d47b0877d96f08b7d05974ac3a6a8f7b7dea4b17ba4cab4c533`.
Final independent review returned
`PASS_GO — S22PLUS_FYG8_P316_CUSTOM65_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1`
for this exact execution-critical closure.
All remain H0: `device_contact=false`, `live_authorized=false`, and no fresh
D0/F1 binding or approval exists. A standalone
connected stock-Android override write would be D1, but all twelve controls are
already bound there: it could prove only write/readback, not pre-bind
suppression, unless preceded by an out-of-scope unbind. No such low-value D1 is
planned. The suppression property must instead pass the pinned arm64 QEMU
platform-device control, while the planned in-candidate writes remain part of
the enclosing boot-only F1 and must not be split into a D1 pretest. No further
device action is needed for the sysfs-name gate. The pinned arm64 QEMU
suppression behavior and its raw-capture/replay schema are independently
qualified. Its
first two guest executions reached the same three-device transition but
exposed two distinct active-Rule-7 failures: host termination before a complete
terminal record, then rejection of a complete PL011 CRLF record by the LF-only
codec.
The former shared the terminal-framing invariant but not the latter's input
contract or causal mechanism, so the CRLF repair had one bounded corrected
execution available. That execution retained 1,463 exact raw bytes before
decoding, accepted the CRLF record, proved target-only bind followed by
clear-plus-reprobe recovery of both controls, and replayed the same raw SHA-256
through the identical codec/parser to the same PASS. The first two runs did
not preserve raw bytes and are not replay authority; named synthetic
representatives now preserve their truncation and CRLF failure contracts. The
three-device corpus does not cover the future 15-device candidate observer,
which must add its own negative corpus when its schema materializes. This
closes only the technical proof for generic platform `driver_override`
suppression. The first independent schema review correctly withheld `PASS_GO`
for weak manifest-authority validation, non-exact FAIL parsing, and a tail
append reopen. The scoped repair now requires the expected manifest hash,
validates the full source/clock/chunk schema, parses exact FAIL grammar, and
keeps one exclusive raw descriptor through tail drain; the original run-03 raw
passed that stricter replay without a QEMU rerun. The first re-review then found
a remaining manifest TOCTOU between path hashing and path reopening; replay now
hashes and parses one immutable byte object, with a switching-path regression.
Final independent re-review attacked those four findings and returned
`PASS_GO — S22PLUS_FYG8_MAX77705_DRIVER_OVERRIDE_QEMU_RAW_CAPTURE_REPLAY_SCHEMA_V1`
for closure commits `1024b095e8`, `2867a6df8c`, `17ae7a56fc`, and
`28408eecb9`. Actual S22+ path construction, the future 15-device negative
corpus, binding, I2C, and MUX behavior remain live-only unknowns. P3.16 now
materializes the 15-device path, negative corpus, package, and offline ready
closure; they do not create live authority.
The former
4,246,401,024-byte
workspace-capacity blocker is closed by the exact private S22+ cleanup
receipt: 68 superseded or invalidated
large payloads with 5,033,287,680 allocated bytes were removed only after a
reversible quarantine and focused regression, and the latest H0 `df -B1`
after the bounded Gate 0 output and diagnostic cleanup reported
51,230,306,304 bytes available. This does not waive per-operation
capacity proof: every extraction, build, or package must still derive its peak
working set plus margin and fail closed on ENOSPC, short write, unexpected
size, or hash drift. The old 86-module phone-VBUS closure remains forbidden
because it reintroduces the recorded debug-partition writer. No device action
or live authority follows from this H0 result.

## P3.15 Detailed Successor Design

P3.15 extends rather than rewrites the consumed P3.14 contract. The exact
P3.14 incident and design-requirements receipts remain historical authority.
The revised `s22plus_fyg8_p315_design_requirements_v3` contract registered the
additional obligations below. The realized prepackaging closure carries its
exact requirements hash and passes the real validator before package creation.

### Explicit phase geometry

The ten ordered pair classes are `start_off`, `start_on`, `child_suspend`,
`child_resume`, `phy_suspend_off`, `phy_suspend_on`, `power_off`, `power_on`,
`phy_init`, and `notify_connect`. P3.15 freezes three separate semantic
vectors:

- STOP: `[1,0,1,0,2,0,1,0,0,0]`, 14 clean records;
- RESTART: `[1,1,1,1,2,2,1,1,1,1]`, 41 clean records; and
- FINAL: `[1,1,1,1,2,2,1,1,1,1]`, 41 clean records, with 49 retained as the
  inherited bounded-drift ceiling.

RESTART and FINAL are equal values but distinct semantic contracts. The
materialized parser must select STOP, RESTART, and FINAL explicitly rather
than allowing RESTART to fall through an `else` branch. PARTIAL retains its
existing non-terminal behavior. Every unknown phase fails closed with the
already registered `0x6707`, `record-format-contradiction`; no raw or new
detail is introduced. Qualification must execute a real 41-record RESTART
fixture, reject each missing pair, and map each complete excess pair class to
the existing `0x6c01..0x6fff` mask.

The 41-record RESTART vector is not allowed to certify itself. The v2 contract
binds exact receipts for the fixed wrapper, DWC3 core, HS-PHY source, P3.14
materialized runtime, and 25-event descriptor. A dedicated source audit must
derive all ten pair counts from the actual `none -> peripheral` call chain.
The ten functional classes contain 12 complete pairs, or 24 records. It must
also derive four outer-work pairs, two RUN_STOP pairs, one gadget-start pair,
zero pullup pairs, and one QSCRATCH, state, and event-config singleton: another
17 records, for 41 total. Copying the expected vector into a fixture is not
source proof.

### Restart completion fence

The inherited restart readback is not a completion witness. `mode_store()`
calls `dwc3_msm_set_role()`, whose external-event path flushes old work but
queues the new `sm_work` and returns. Child and parent can both read `active`
near the beginning of `dwc3_otg_start_peripheral(1)`, before its notify,
QSCRATCH, gadget-start, RUN_STOP, and outer return records are complete.
Reading the strict RESTART snapshot immediately after those PM readbacks can
therefore reject a normal in-flight prefix.

P3.15 adds `p315_wait_restart_completion()` before the authoritative RESTART
snapshot. Its profile-free prefix parser may only decide ready, not-yet-ready,
or malformed; it makes no controller or cycle-causal claim. Readiness is an
independent control-flow fence: it requires a complete `start_on` pair nested
in its containing outer-work pair and the source-derived quiescent topology of
four complete outer-work pairs. It must not depend on child resume, PHY init,
power-on, gadget-start, RUN_STOP, QSCRATCH, state/config snapshots, or a total
41--49 record count. Four quiescent outer pairs without the required
`start_on` shape are completed malformed topology and map to the established
`0x6707`; an in-flight outer or `start_on` pair remains not-yet-ready. The
helper reuses the existing restart deadline and is additionally capped at 301
trace snapshots (one initial read plus 300 100-ms intervals). Trace-read
failure maps to `0x6704`; a worker or `start_on` pair that never completes,
deadline expiry, or attempt exhaustion maps to the registered `0x6718`. Only
after this fence may the profile-bearing authoritative RESTART snapshot run.

The authoritative snapshot first proves structural, profile, and ring
integrity, then classifies the nested resume path. Trace profile counters are
per event, not per decoded argument: `run_off` and `run_on` share event indices
19/20, while gadget-start uses indices 21/22. The clean stop prefix therefore
leaves one recorded/profiled `run_off` entry and return even when `run_on` is
absent. Absolute-zero run profile counts are forbidden as an absence test.

`0x671d` retains its P3.13 meaning only when gadget-start and decoded `run_on`
entry/return records are both absent and there is no relevant profile excess:
gadget-start profile and record totals are both zero, while each run profile
total exactly equals its cumulative recorded run total (the existing
`run_off` baseline). The DEVICE resume precondition or path was not
established. It is a terminal information result, not an observer timeout, and
does not continue to FINAL because the containing outer invocation has already
returned. A relevant profile count greater than its cumulative record count
maps to dedicated `0x6721`, `profile-only-nested-hit`, and cannot support an
absence claim; it is an attribution contradiction, not ring-loss proof. An
incomplete entry/return pair maps to `0x6713`.

The asymmetric case is deliberately separate. A negative gadget-start return
with no `run_on` preserves the existing controller-detail result. A positive
gadget-start return maps to the existing `0x6714` before any zero-return branch;
the zero branch must test `rc == 0` explicitly and may not use a nonnegative
fallthrough. A zero gadget-start return followed by no `run_on` maps to
dedicated `0x6722`, while `run_on` without gadget-start or after a negative
gadget-start maps to provenance contradiction `0x6723`. Neither is `0x671d`.
A recorded negative `run_on` return after a valid zero-return gadget-start is
the existing controller result (including measured `-ETIMEDOUT`). Only when
all required nested pairs are present does the parser enforce the full
source-derived 41-record RESTART geometry, the bounded 49-record drift shape,
QSCRATCH, state, and event-config requirements and continue the experiment.

The three new meanings occupy the already enumerated reserved contradiction
slots `0x6721..0x6723` within the inherited `0x6701..0x673f` terminal gate.
They do not add B outputs or change the 251,450-cell matrix count. The P3.15
decoder must replace only those three reserved names while historical P3.13
and P3.14 decoder meanings remain unchanged.

### Live snapshot invariant

One new helper, `p315_read_live_snapshot()`, owns both intermediate callsites.
It accepts only STOP or RESTART, calls
`p282_trace_read_snapshot(control, 1)`, maps every trace or profile read error
to the established `0x6704`, `trace-snapshot-read-failed`, and invokes
`p314_parse_live_snapshot()` only after that read succeeds. Parsing populates
`record_hits[]` before the valid `profile_hits >= record_hits` relation, and
ring statistics follow the profile relation. No raw errno may reach
`p313_cycle_fail()` from these callsites.

This restores an existing invariant rather than inventing one. The inherited
final and partial close paths already disable tracing, read trace plus profile,
parse, compare profile counts, check ring statistics, and map negative read
results to `0x6704`. They remain unchanged in P3.15. The three implementations
-- stop/restart helper, final inline, and partial inline -- are recorded as one
review set; changing one requires checking all three.

The six inherited `require_profile=0` sites are classified rather than
globally rewritten. STOP and RESTART leave that set and use the new helper.
Role retains its role-source contradiction normalization, legacy cycle refresh
retains its trace-incomplete warning, and bind plus direct remain intentional
bind-event-count no-ops that perform no file read. The one new profile-free
site is the bounded restart-readiness prefix read described above; it may not
feed a profile comparison or terminal cycle classification. Any other new
zero-profile site, or any downstream profile comparison after the five listed
sites, blocks packaging.

### Coverage and timing closure

The prepackaging artifact must bind each observer seam to the immediate caller
that establishes its inputs. This includes snapshot-to-helper,
parser-to-helper, profile-relation-to-parser, ring-check-to-parser, the two
live callers, and the inherited final/partial callers. The unverified
difference for changed functions and those immediate callers must be zero.

Function-symbol `(void)` references are not execution proof. The P3.14 runtime
fixture must actually execute `profile_from_result()` and
`p313_cycle_profile_relations()`. The older stop-localization audit may retain
its nine compile-only symbols only with the machine-recorded, scope-specific
reasons in the P3.15 contract. This is a bounded one-time sweep, not a global
call-graph coverage requirement.

The existing bounded waits remain 160 seconds inside the 300-second candidate
window. P3.15 adds one completion wait point but zero independent wait
seconds: it shares the already running 30-second restart deadline. Its explicit
301-snapshot cap bounds readiness trace reads to 19,726,336 bytes. The two
profile-bearing reads remain exactly two and add at most 131,072 bytes, for a
combined maximum added read extent of 19,857,408 bytes. Qualification must
recalculate materialized non-wait overhead and execute deadline, attempt-cap,
in-flight-prefix, outer-complete-without-`start_on`, nested-both-absent,
profile-only-hit, gadget-start-negative, gadget-start-positive,
gadget-start-zero-without-`run_on`, `run_on` provenance, exact-ready,
bounded-drift, and malformed-prefix fixtures.
The nominal 140-second subtraction is not itself proof. The reviewed
1,200-second host guard remains unchanged.

### Host observer and packaging closure

Device-side parser success alone is insufficient. The P3.15 overlay must be
selected by the real Process-v2 evidence and live paths, select Carrier-v2
semantics before decoding, preserve `foreign_count == 0`, and round-trip JSON
persistence. Fixtures must cover a clean adjacent pair, `0x6704` at both the
actual STOP and RESTART positions, `0x6705`, unknown phase `0x6707`, unknown or
mixed overlay rejection, completed outer work with the existing `0x671d`
resume-precondition result, the distinct `0x6721`, `0x6722`, and `0x6723`
branches, and the complete inherited A/B/pair-mask position matrix of at least
251,450 cells. A real ready-manifest rehearsal must select P3.15 and the
reviewed 1,200-second guard rather than fall back to P3.14 or a generic Carrier
decoder.

The contract maps the recurring observer classes, rather than only this run's
detail: materialized-source/position drift, live-caller input validity,
profile-versus-record semantics, Carrier decoder/persistence/overlay dispatch,
and declaration-versus-packaging wiring. Each class names one of the mandatory
proof artifacts below; prose closure is insufficient.

Four named prepackaging proof artifacts are mandatory: restart source geometry,
the actual runtime wrapper fixture, the real Process-v2 adapter/persistence
fixture, and packaging wiring. Each binds the v2 requirements hash plus its
producer and artifact hashes. The realized parent packager calls the real
prepackaging validator first; missing or mutated proof must yield zero
parent-packager calls and zero package output. A separate final-qualification
artifact binds reproducible packaging and the real ready rehearsal. The actual
builder call graph, negative package-blocking fixtures, and qualification
receipts satisfy the registered two-phase shape. None grants device authority.

P3.15 changes only generated userspace runtime and its host
design/fixture/closure/packaging validation. The fixed Image, kernel hooks,
5/15/25-event descriptors, module plan, 107 checkpoint positions, Carrier-v2
layout, rollback, transfer, recovery, and guard remain exact. It therefore
required a userspace rebuild, boot-only repackaging, fresh qualification, and
one focused independent review of the changed closure, but no Full-LTO. Those
H0 obligations passed and still grant no D0, D1, or F1 authority.

## P3.15 Implementation and Qualification

The frozen P3.15 intent contains 119 `SOURCE_KEYS` and run ID
`b9cc424d0d184f5accbce94a844e817d`. The prepackaging validator is invoked by
the actual builder before the parent packager and blocks missing or mutated
proof with zero package output. The restart source geometry, actual runtime
wrapper, Process-v2 adapter/persistence, packaging wiring, and final
qualification artifacts all passed. The 251,450-cell matrix covers all actual
A/B/pair-mask outputs at every retained generation position.

Two userspace builds and candidate A/B packages are byte-identical. The
qualified AP SHA-256 is
`11f77fa0225126749b471d1552dc8cedeb35ec9c18158f7c6096ab4bb2e078c7`
and its boot image SHA-256 is
`836eeb460030a5955bd4d99883ba80e81967823ff841aa0a5476e09c3572cc1a`.
Static artifact closure, Process-v2 promotion, the real offline bundle, and
ready-manifest creation all passed with `device_contact=false`.

The first two direct H0 executions exposed separate qualification incidents:
Python direct-script/canonical-import module duplication separated validated
prepackaging state from the late safety callback, and the P3.15 userspace
result initially omitted one inherited callsite-identity field required by the
static checker. Both failed before any device action; their private evidence
was preserved. The bounded repairs canonicalize direct-script module identity,
make the wiring audit enforce that ordering, restore the exact inherited field,
and add focused regressions. Independent review returned `PASS_GO` for the full
changed closure and each narrow repair.

## Completed P3.13/P3.14 predecessor evidence

P3.13 and P3.14 are consumed, closed predecessors; neither candidate may be
replayed. P3.13's two retained slots proved generation 96, stage `0x90`, item 3
parent-suspended progress followed by generation 97, stage `0x90`, item 4
terminal failure `0x6712`. Post-live source analysis showed that the
child and parent necessarily contribute two complete stop-side
`phy_suspend_off` pairs, so the original one-pair expectation was wrong.
The frozen live decoder also inherited P3.12 Carrier semantics and rejected the
valid P3.13 intermediate terminal. Those count-model and decoder incidents are
historical evidence, not grounds to relabel or replay the run.

P3.14 normalized the exact two-off/two-on source geometry, introduced
pair-specific `0x6c01..0x6fff` excess masks, executed the 251,450-cell
value-by-position matrix through the real Process-v2 adapter, and enforced
validator-before-packager wiring. Candidate A/B reproducibility, final
qualification, independent static closure, Process-v2 promotion, ready
rehearsal, and focused independent review passed without changing the fixed
Image or running Full-LTO.

The actual P3.14 F1 then stopped during the stop snapshot at `0x6705` because
the live caller requested a snapshot without profile data before invoking the
profile comparison. P3.15 repaired that live-caller seam, registered distinct
STOP/RESTART/FINAL geometry, executed the actual wrapper and inherited matrix,
and passed the packaged closure summarized above. The detailed immutable
authorities remain:

- `docs/reports/S22PLUS_FYG8_P313_POST_BIND_RESUME_CYCLE_DESIGN_H0_2026-08-10.md`;
- `docs/reports/S22PLUS_FYG8_P313_STOP_MULTIPLICITY_AND_CONTINUATION_GAP_H0_2026-08-10.md`;
- `docs/reports/S22PLUS_FYG8_P314_SOURCE_NORMALIZED_CYCLE_SUCCESSOR_DESIGN_H0_2026-08-10.md`; and
- the corresponding P3.13/P3.14 incident, implementation, and independent-review reports.

This compression changes no historical result, hash, authority, or
non-replayability rule.

## Authority and Target State

The Interim Fast-Loop trial retired at 2026-08-03T20:46:02Z after the first
`CAMPAIGN_CLOSED` rows for `s22plus-fyg8-p296` and
`s22plus-fyg8-p298`. It grants no standing D0, autonomy, or per-candidate
approval waiver. H0 implementation may proceed without device contact; any
future D0, D1, or F1 must satisfy the ordinary live common/target authority and
fresh exact binding requirements.

The exact S22+ is healthy at the P3.15 close. Physical Download recovery and
the exact Magisk rollback remain the required F1 recovery path. No candidate
may be written over an unhealthy or unverified device; rollback never waits
after candidate execution begins, and a consumed candidate is never replayed.

P3.13 is now consumed and closed. Its candidate and rollback each completed
once; a transient post-rollback host endpoint-evidence failure was recovered
from the durable rollback state without retransmission, and final health
passed. No live authority remains from its approval or prepared record.

P3.02 passive electrical attribution remains parked because no reviewed safe
inline breakout is available. P3.14 is now consumed and closed. Its candidate
and rollback each completed once; the retained observer contradiction was
recovered from two byte-identical post-rollback reads, and final health passed.
No live authority remains from its approval or prepared record. P3.15 is also
consumed and closed. Its candidate and rollback each completed once, its
integrity-clean retained pair proved outer-work-only path drift, and final
health passed. Its journal, approval, and prepared binding are historical
evidence only and grant no authority. P3.02 remains parked.

## Success and Stop Conditions

P3.13 implementation and its one live attempt are complete. The live result is
`NO_PROOF_OBSERVER`: the device published an information-bearing stop-side
multiplicity contradiction, but no final P3.13 pair or ACM banner. A successor
may not inherit a claim that restart was attempted. It must first distinguish
source-required pair geometry from unexpected multiplicity, define explicit
continue-versus-stop semantics, and exercise the complete runtime-authorized
value-by-position matrix through the actual Carrier semantic authority and
Process-v2 evidence path before any new device action. P3.14 satisfies those
host-side prerequisites without changing the fixed Image or candidate kernel;
it does not retroactively add restart evidence to P3.13. The consumed run
cannot identify the exclusive live pair vector and must not be presented as
doing so.

P3.14 implementation and its one live attempt are also complete. The live
result is `NO_PROOF_OBSERVER`: its clean 14-record stop snapshot was compared
against an unpopulated profile array and deterministically emitted `0x6705`
before restart. A successor may not inherit a claim that P3.14 attempted the
restart or refuted any remaining digital mechanism. It must close the actual
intermediate snapshot call sequence, not merely the lower-level parser or the
post-emission value-position matrix, before a new candidate is packaged.

P3.15 satisfies that successor boundary and its one live attempt is complete.
It produced a valid, information-bearing `REFUTED` result rather than an
observer no-proof: restart executed, but eight complete outer-work pairs
violated the source-derived clean expectation of four. All other encoded path
classes were exact and the sidecar remained candidate-silent. Because the
frozen Result Contract revokes cycle causality on multiplicity, this result
does not prove that the cycle caused the host silence or that a pull-up did or
did not reach the connector. A future cycle-reusing unit must first close the
unretained queue provenance; an independent natural-attach OTG unit does not
inherit that cycle and may instead proceed from its dedicated H0 design and
hazard review. No P3.15 candidate replay or inherited clean-cycle claim is
permitted.

P3.16 qualification and its one live attempt are complete. Candidate and exact
rollback each transferred once, the 19-record journal closed, and rooted
boot-completed FYG8 health passed after rollback. Two byte-identical,
CRC-clean retained reads decoded one authoritative `0x6708`
`exact_parent_unbound_after_sync_return` terminal: the exact Max77705 parent
existed unbound, the diagnostic module's synchronous `finit_module()` returned
success, but the parent remained unbound, no diagnostic `0x25` client existed,
and the result stayed `-EAGAIN`. The immutable decoder terminal is
`NO_PROOF_OBSERVER_DIAGNOSTIC_SYNC_CONTRADICTION`, but the observer itself did
not fail. It emitted the exact registered EAGAIN precondition row, so the
effective campaign class is `NO_PROOF_EXPERIMENT_PRECONDITION`: observer sound,
experiment not executed. No CONTROL1 or physical-MUX claim is permitted and
the P3.16 candidate is consumed without replay.

Post-live H0 localizes the dominant pre-probe mechanism. An exact-source
extractor proves that `pinctrl-0 = <0x7b>` and
`max77705,irq-gpio = <0x11 ...>` resolve to the same compatible owner,
`qcom,pm8350c-gpio`: two raw property reasons become one deduplicated
consumer-to-supplier edge. P3.16 omitted the full stock five-module provider
chain: `qti-regmap-debugfs`, `regmap-spmi`, `qcom-spmi-pmic`, `spmi-pmic-arb`,
and `pinctrl-spmi-gpio`. That omission exactly predicts successful driver
registration followed by an unbound client and an unpublished result. It
remains a strongest H0 localization rather than a unique device proof because
P3.16 did not retain `waiting_for_supplier` or the unresolved supplier
identity.

The P3.10-P3.16 proof audit is now fixed as four observer failures, one
experiment-precondition failure, and two conclusive `REFUTED` results. The
general `EXPERIMENT_EXECUTABILITY_CLOSURE` and its first exact-source family,
`FW_DEVLINK_DT_SUPPLIER_CLOSURE`, are registered in Process-v2. The host-only
28-row parser-table regression receipt is 14,680 bytes with SHA-256
`88b8247e48a1945c8a5f31544336f942c32f9604787e0cd46de0ba5f70f17609`.
The incident and successor design are in
`docs/reports/S22PLUS_FYG8_P316_MAX77705_SYNC_PROBE_CONTRADICTION_INCIDENT_2026-08-12.md`
and
`docs/reports/S22PLUS_FYG8_P317_EXPERIMENT_EXECUTABILITY_CLOSURE_DESIGN_H0_2026-08-12.md`.

The next host-only boundary review found two more non-symbol dependency
classes. Device instantiation is real beneath the derived PM8350C GPIO
provider: SPMI-controller registration enumerates the PMIC, and the PMIC driver
populates the GPIO child. But exact merged-DT reconstruction corrects the
initial QUP explanation. `9c0000` and `994000.i2c` are `/soc` siblings created
by default OF platform population; the wrapper's `of_platform_populate()` does
not create this controller. Instead the I2C driver parses the otherwise
unregistered `qcom,wrapper-core` reference and
`geni_se_resources_init()` returns `-EPROBE_DEFER` before adapter registration
when wrapper driver data is absent. The second and third registered families
are therefore `DEVICE_INSTANTIATION_CLOSURE` and
`DRIVER_CONSUMED_DT_REFERENCE_CLOSURE`. All three registered families now
iterate over every emitted exact node until a least fixed point, rather than
running as root-only or single-family passes. The reviewable must-bind proposal
still has three roots, three claims, nine claim-to-consumer counterfactuals,
and four explicit evaluability preconditions. The previous reviewed authority
hash `fd27d79883cbdc5e6daab937f0b24ab303fdd8a1c91cf63feb5789975e04c1d3`
is superseded because its wrapper-instantiation sentence was false; the
corrected reviewed claim-authority hash is
`49859c0957a15ef25cdad98137c5f178eb790f4689ddeb74553971d1a9ce3070`.
Machines prove coverage, fixed-point semantics, and source seams only. The
follow-up review approves the corrected causal authority, all three mutually
recursive relation families, and the exact `+5` module delta; no candidate
authority follows.

The exact mutually recursive H0 extractor now applies the active revision-12
overlay independently to both applicable pinned Waipio bases. Both produce the
same 23-node closure after five iterations, with 170 raw and 53 deduplicated
relations. Every frontier node enters all three families. The derived module
delta is exactly `spmi-pmic-arb.ko`, `pinctrl-spmi-gpio.ko`,
`qti-regmap-debugfs.ko`, `regmap-spmi.ko`, and `qcom-spmi-pmic.ko`. It preserves
all 64 predecessor early modules as an exact subsequence, inserts the five
before `msm-geni-se.ko`, and changes the effective count from `65 -> 70`
(69 early stock modules plus the inherited one late diagnostic). Specifically,
the generic early loop loads those 69 modules; the seventieth is
`s22plus_max77705_mux_diag.ko`, loaded exactly once by the dedicated synchronous
late `finit_module()` path after early-module completion, gadget readiness, and
sidecar arming. The private receipt is 496,664 bytes with SHA-256
`67042a70a6e023a5ea3382d4fd179fd04b6f0c111ff9430d5e5a1b9410b2a657`.
The reviewed must-bind receipt is 15,712 bytes with SHA-256
`bbb066b0dc8a7492db407a22f9cb1417773ee049a69b232a2ebc02d234418263`;
the fixed-point receipt SHA-256 is
`67042a70a6e023a5ea3382d4fd179fd04b6f0c111ff9430d5e5a1b9410b2a657`.
The superseded pre-correction must-bind receipt remains historical evidence at
SHA-256 `b9d8b967aed453ab006aa7532592f4fc6413131d775159df4f18daf96ec33334`;
the matching pre-correction fixed-point receipt was
`b4418d8cf0a8aedcb540e53d008720e31202ede823cc6064978463ef3b8d8f9c`.
Neither is the current packaging authority.

P3.17 H0 implementation now closes the remaining runtime and packaging
obligations. The materialized runtime retains effective fw_devlink policy,
three provider/binding witnesses, the three-state `waiting_for_supplier`
authority, supplier links, exact consumer binding, and diagnostic probe entry.
Envelope-v3 and the real Process-v2 adapter cover 107 unique retained
preimages, including all six observable EAGAIN generation paths. The separate
claim-busy negative fixture executes the inherited C policy rejection,
then executes a byte-identical copy of the materialized runtime
`p316_classify_eagain()` wrapper and its exact immediate-caller seam. Its
normalized `result-policy` / `io-format` output is the input to the actual
envelope, Carrier, and host decoder, where no claim-busy `eagain_row` survives.
The package
contains exactly 69 early stock modules plus the unchanged one late diagnostic;
two userspace and boot-only builds are byte-identical, with boot SHA-256
`068aa5337acdbe4c2a0dcf80241b7aa543600fdfdfc84bb0e74111542b76d18d`
and AP SHA-256
`ac0db3172cdc4dc9fe7991bf034e872f0d377a3fb175e61ff8cba0eb136c9f22`.
Final qualification, independent static reconstruction, Process-v2 promotion,
private ready exact-copy, and non-creating ready rehearsal pass. Canonical
manifest SHA-256 is
`5732cb44797f4a4aec3d5024796c80d6a771afa23ce4c1309300a5a23e2fccb3`.
Independent source-frozen regeneration reproduced intent-file `6d2cabac...`,
prepackaging `c4f6a928...`, userspace `1b00407b...`, qualification
`74becadb...`, and static closure `269a057f...` byte-for-byte. It also verified
the canonical/private ready copies, target, rollback, 300-second candidate
window, 1,200-second guard, and non-creating rehearsal. The capability verdict
is `PASS_GO — S22PLUS_FYG8_P317_CUSTOM70_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1`.
This is H0 capability qualification only: fresh live prerequisites and exact
authority remain mandatory, and actual provider binding, GENI/I2C transfer,
Max77705 retention, physical MUX conduction, and host attach remain device-only
unknowns. No device command, Full-LTO, kernel rebuild, live authority, A90
action, or S20+ device action occurred.

P3.17 live evidence localizes a topology-precondition failure without
rewriting the frozen campaign row. The sealed sidecar proves the exact
candidate enumerated high-speed at `3-1.3` under `0000:00:14.0`, with the bound
`04e8:6861` identity, candidate serial, `cdc_acm`, and `ttyACM0`. The frozen
observer required approved topology `2-1.3` under the different controller
`0000:00:0d.0`; it selected zero endpoints and never opened the TTY. The
operator confirms that the cable/dock connection was physically moved during
the run. The observer therefore behaved correctly, while the experiment lost
its frozen topology precondition. Its null endpoint identity and zero-byte raw
file mean “not selected,” not “opened and read nothing.” The P3.17 endpoint
sub-result is `exact-candidate-topology-drift`, with effective proof class
`NO_PROOF_EXPERIMENT_PRECONDITION`. This correction is P3.17-only and does not
reclassify earlier campaigns. The original multiplicity terminal remains a
separate observer limitation and the immutable F1 row remains unchanged.

The live diagnostic also crossed the P3.16 executability boundary: all three
providers were bound, `waiting_for_supplier=ZERO`, the diagnostic owned the
parent and one `0x25` client, all commands/responses completed, and CONTROL1
was `0x3f -> 0x09 -> 0x09` across the 30-second boundary with no post2
detection latch. Host enumeration proves only that the candidate enumerated on
the later physical connection. Because disconnect/reconnect and controller
movement are competing causes, it does not prove that CONTROL1 caused a
physical switch move or that the original connection conducted. Two identical
retained records still violate the single-result contract, and register
readback is not a physical switch witness. The operator reports a
physical-button misoperation that caused two actions, which is consistent with
two records but cannot supply the missing per-boot retained identity. The
official multiplicity no-proof and healthy 1/1 close remain unchanged.

P3.18 preserves the P3.17 result as
`NO_PROOF_EXPERIMENT_PRECONDITION`: the operator-moved `2-1.3 -> 3-1.3` pair is
incident evidence only, never selector authority. The permanent topology
boundary spans Download through rollback and final health. Drift parks until
an independently reviewed `recovery_rebound_exact`; normal rollback uses
`rollback_bound_exact`, and neither path may reclassify the experiment.

The host-only successor now includes the pre-gate evidence correction. An
early GPL module registers the exported `dwc3_event` tracepoint, masks the
exact DWC3 raw-word ABI, filters the source-bound `a600000.dwc3` UDC name, and
latches install plus the first post-gate RESET, CONNECT_DONE, or physical-EP0
SETUP event with `ktime_get_ns()`. One atomic state also saturating-counts
qualifying events that linearize before the write-once pre-UDC gate. Snapshot
v2 retains that count; both the gate parameter and snapshot derive readiness
from bit 30 of that same state with an acquire read, without a shadow ready
flag. Python snapshots require an explicit pre-gate count, and impossible
duplicate gate publication warns while remaining fail-closed. The runtime
reads back the gate before its sole reachable UDC bind. The late diagnostic uses the same clock for
pre/write/post1/post2. `install <= gate_write` is structural consistency, not
causal evidence; no-event interpretation additionally requires
`gate_write <= pre`, zero pre-gate events, and a complete no-endpoint host
receipt. Only masks `0xef`/`0xff` carry that authority; `0x6f`/`0x7f` do not.
The v4 `TIME_MASK=0xff` is fully allocated; a future timing witness requires a
new byte or reviewed Envelope-v5 and may not reinterpret an existing bit.

The bounded banner writer uses one absolute five-second deadline across
EINTR, EAGAIN, and short writes and retains written/deadline/errno/partial plus
the exact byte count. Envelope-v4 remains 128 bytes: a 29-byte prefix leaves
47 lossless poll bytes; overflow uses 73 bytes and requires three zero spare
bytes. Actual P3.17 poll evidence is 8 raw/9 PackBits bytes. The real C encoder,
Carrier, and host decoder cover the 47/48 boundary, nonzero-spare rejection,
all terminal preimages, and separate EAGAIN/EPIPE/ENODEV outcomes.

The frozen 42-`SOURCE_KEY` package contains the exact 69 P3.17 stock modules
plus one early latch (70 early) and one synchronous late diagnostic (71
effective); the old P3.17 diagnostic is absent. Two userspace and boot-only
builds are byte-identical: boot `0b74986f8531`, AP `129ad86b934c`. Independent
intent `d760c54dc01e`, prepack `594b02effd24`, userspace `a5bccc6edadd`,
qualification `c2453d656d10`, static `b5ddb3cacdfd`, Process-v2 run
`0c2fab45520e`, and process static `a26f0aa26507` match the canonical bytes.
Ready 4/4 exact-copy and noncreating rehearsal pass with manifest 2,778 bytes,
SHA-256 `79cf54d59171`; candidate observation is 300 seconds and the source-bound
guard is 1,200 seconds. Focused P3.18, common Process-v2, and standalone live
integration tests pass 114/114, 120/120, and 5/5.

The V1 and V2 implementation PASS_GO verdicts remain historical authority for
their exact old hashes only. Independent final4 changed-closure review matched
the canonical path byte-for-byte and returned:

`PASS_GO — S22PLUS_FYG8_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V3`

V3 qualifies only this exact H0 offline implementation and packaging closure.
It grants no D0, D1, F1, recovery, replay, or live authority; fresh connected
prerequisites and exact approval remain mandatory.

The latch identity is source-and-canonical-path frozen: qualified module
`27be8abfe121` embeds `dwc3-event-latch-build-20260814-01`, which is therefore
an execution-critical input. The source-identical `5f8bab654c41` build completed
normally under `dwc3-event-latch-build-followup-v3` but is ineligible only
because that embedded path changes its bytes. V3 does not claim path-independent
rebuildability; another output path requires a new identity and full qualification.
Detailed report:
`docs/reports/S22PLUS_FYG8_P317_CDC_ACM_ENDPOINT_SELECTOR_CORRECTION_H0_2026-08-14.md`.

The first P3.18 live-prerequisite D0 stopped on three residual P3.17 records;
its ledger row records that the unnormalized decoder left no result receipt.
The typed stop-result successor and downstream requalification now have
independent H0 `PASS_GO`; boot/AP are unchanged and ready is `082c046f9091`.
Fresh post-rotation P3.18 D0 passed: exact rooted FYG8 health and a clean
2,097,136-byte marker-free baseline; binding `fd68d3b4713d` is prepared, but F1/live remain unauthorized.

Stop on target ambiguity, missing rollback, a changed `SOURCE_KEY`, a forbidden
archive member, an unreviewed common receipt/schema change, an observer result
that cannot distinguish the declared branches, or any unexplained post-session
failure. Never trade a permanent safety boundary for speed.

## Archived History

The complete state through P3.12 and the frozen P3.13 design is preserved at
`docs/archive/roadmaps/GOAL_THROUGH_P312_AND_P313_DESIGN_2026-08-10.md`.
Earlier snapshots remain at:

- `docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`;
- `docs/archive/roadmaps/GOAL_THROUGH_P284_PM_ORDER_2026-07-29.md`; and
- `docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md`.

Archived text is evidence only and grants no authority. The append-only
campaign ledger and private Process-v2 evidence remain the authority for live
attempt and transfer history.
