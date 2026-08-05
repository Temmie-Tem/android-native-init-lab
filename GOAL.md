# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and the selected
shared process documents. A90 state and authorization remain separate.

## Current Frontier

P3.06 is the latest closed live unit. After one retained-baseline stop and one
attended normal-reboot rotation, its distinct boot-only candidate and exact
Magisk rollback each transferred once. The operator observed one normal
candidate boot with no loop. Final rooted FYG8 Android health passed, the
transaction is `CLOSED`, `recovery_required=false`, and A90 received zero
commands. Its integrity-clean adjacent generations 106/107 are `0xD79` then
`0x42D6`. The candidate saw B-session-valid set, inputs BSV, start-gadget,
and peripheral in
the required order, with each count in the 2--3 bucket. It also saw BSV clear
and undefined-without-BSV, but no core-init-failed or no-pullup marker. The
expected candidate ACM endpoint still timed out and the same-attempt host
sidecar was integrity-clean. This refutes absence of the wrapper BSV and
start-gadget/peripheral sequence as the current stop; the remaining boundary
is after that sequence and before candidate enumeration reaches the host. The
earlier `0xD00` proves only the in-window software guard saw
`clocks_enabled=true`; it does not retroactively prove that the discarded
initial hardware clock returns were zero.

Post-P3.06 H0 narrows the boundary further. The `peripheral` IPC marker is the
state-machine name emitted on its next invocation; it is not an aggregate
success receipt. `dwc3_otg_start_peripheral()` discards several returns and
always returns zero. Nevertheless, P2.98 separately proves the later configfs
bind path reached `__dwc3_gadget_start()==0`, both EP0 enable calls, and
`dwc3_gadget_run_stop(true)==0` with RUN_STOP set, DEVCTRLHLT clear, and PRTCAP
DEVICE. P2.80 and P2.92 reached the same not-attached boundary through nested
and direct run-stop paths, so another role-cycle reshaping is not selected.
P3.01-r1 then saw only one pre-configuration SUSPEND device event and no RESET
or CONNECT_DONE. The remaining frontier is the digital-to-physical handoff,
not wrapper-state or generic gadget control flow.

Repeating the full Type-C producer stack is also not selected. The exact
`usb_notifier_qcom` peripheral callback only calls `dwc_msm_vbus_event()`, while
the explicit mode path already creates the same wrapper BSV/start-peripheral
state. More importantly, historical S7A2 already loaded the Max77705 producer
chain with its GENI I2C transport and still produced no host-visible attach.
That stack may still matter as part of Android coordination, but module
presence alone is already refuted as a sufficient fix.

Two exact live predicates remain unproved and can share one narrow successor
without rebuilding Image or any module. First, the existing twelve
immediate-post-call HS-PHY clock probes must arm after module index 55
(`phy-msm-snps-hs`) and before index 58 (`dwc3-msm`), because the first PHY
init occurs synchronously during the latter probe. The full 28-event cycle
descriptor cannot simply move earlier because it also names not-yet-loaded
DWC3 symbols; use a clock-only descriptor and the already-audited offsets.
Second, the exact `dwc3-msm.ko` has the wrapper HS-PHY-control readback in
`w21` immediately before `dwc3_otg_start_peripheral+0x4cc`; one exact
module-offset probe can retain `UTMI_OTG_VBUS_VALID` bit 20 and, as a sidecar,
`SW_SESSVLD_SEL` bit 28 after the write.

The selected next H0 unit is therefore a userspace-only dual observer: arm the
clock-only set in the index-55/index-58 gap, then arm the single wrapper
readback probe after index 58 and before the first role request. Any negative
initial clock return or a cleared bit 20 localizes the failure. Twelve zero
returns plus bit 20 set closes both remaining digital gates; bit 28 alone is
not causal without a working-stock comparator. Only that nominal result moves
the frontier to candidate-specific Type-C/CC/mux or PHY-output state. No new
module stack, log-level change, role retry, or physical-line manipulation is
part of this unit.

P3.04 is the preceding closed live unit. After one pre-candidate host-observer
arm stop with zero transfers, a new prepared run transferred its distinct
boot-only candidate and exact Magisk rollback once each. Final rooted FYG8
Android health passed and its consumed candidate remains non-replayable.

The two byte-identical final retained reads contain generation 68 at
`stage=0x7B`, `item_index=59`, `PROGRESS`, followed by generation 69 at
`stage=0x7C`, `item_index=0`, `FAILURE`, detail `0xC5E`. Post-live H0 source
reconciliation proves that this does not report a notifier-module load failure.
The progress record was published only after exact stock
`usb_notifier_qcom.ko` loaded and the 60-module `/proc/modules` prefix verified.
The next `ucsi_glink.ko` load and 61-module prefix verification also returned
zero. Its subsequent progress publication requested `stage=0x7C/item=60`, but
the inherited position table still expects `stage=0x7C/item=0` as the first
bind gate. The publication therefore returned `-EINVAL`; `quiet_park()` then
published the allowed fail-closed `0xC5E` at that expected gate position.

P3.04 is consequently `NO_PROOF_OBSERVER`: it proves the added notifier bridge
can load in the exact candidate closure, but the stale 60-module checkpoint
schema parked PID 1 before bind gates, trace setup, USB configuration, or the
notifier hypothesis could be tested. The consumed P3.04 candidate must never be
replayed.

P3.03 is the preceding closed live unit. After one pre-candidate host-observer arm
stop with zero transfers, exact read-only D0 restored a durable `HEALTHY`
barrier. Host-only `pkexec` preauthorization then allowed a new run to arm the
unchanged observer and execute normally. The candidate and exact Magisk
rollback each transferred once, the operator observed one normal candidate
boot with no loop, final rooted FYG8 Android health passed, the transaction is
`CLOSED`, and `recovery_required=false`. A90 received zero commands.

The two byte-identical final retained reads contain one exact P3.03 pair.
Generation 106 is detail `0xD00`: `msm_hsphy_init()` entered and returned zero,
the exact callsite probes were armed, but all twelve `clk_prepare`/`clk_enable`
sites missed. Generation 107 is detail `0x4001`: candidate `/dev/kmsg`
collection was sequence-complete, saw the normal HS-PHY path, and saw zero
reset failures and zero `msm_usb_write_readback ... FAILED` records. With no
working-stock boot-head pair, the log result is deliberately non-causal. The
same-attempt host sidecar was integrity-clean and the exact candidate ACM
observer timed out; no candidate identity appeared at the host.

H0 source ordering explains the missed clock branch without treating it as
return zero. The candidate loads `phy-msm-snps-hs.ko` at module index 55 and
`dwc3-msm.ko` at index 58, while the cycle callsite probes arm only after the
module load loop. The initial `dwc3_msm_core_init()` therefore calls
`usb_phy_init()` before those module-offset probes exist and sets
`clocks_enabled`; the later measured init re-entry is expected to skip the
clock block. P3.03 consequently closes logged reset/readback failure only and
does not decide the initial clock returns. It is closed as
`NO_PROOF_OBSERVER`, not relabelled as a PHY success or failure.

P3.01-r1 remains the preceding closed event-subtype unit. Its narrow userspace
correction derived the expected final detail from the canonical P3.00 encoder as `0xE02`,
kept the fixed P3.00 Image and 15-probe descriptor unchanged, and produced
byte-identical one-member candidate A/B packages. The static checker, 33/33
focused regressions, immutable-source recheck, package binding, and narrow
independent check all passed before device contact.

The first connected preparation stopped on the prior retained P3.01 marker.
One attended normal Android reboot rotated that baseline and restored exact
rooted FYG8 health; the next connected D0 was clean and created approval binding
`71faac9b...`. The P3.01-r1 candidate and exact Magisk rollback then each
transferred exactly once. Candidate ACM observation timed out. After rollback
had already transferred successfully, one final USB endpoint inventory read
failed; durable `--recover` resumed only final observation and did not repeat
either transfer. The transaction is `CLOSED`, `recovery_required=false`, exact
rooted FYG8 Android health passed, and A90 received zero commands.

The two byte-identical 2,097,136-byte post-rollback reads contain one exact,
integrity-clean P3.01-r1 pair. Generation 106 is detail `0xD70`, proving the
probes armed, `__dwc3_gadget_start()` returned zero, both EP enable calls ran,
trace/profile loss stayed zero, cleanup passed, one or more non-RESET/
non-CONNECT_DONE device events reached raw dispatch, and sampled link state was
zero. Generation 107 is detail `0x40CD`: exactly one recognized other-device
event was `SUSPEND`, its first `event_info` was `3`, no unknown subtype was
seen, and the final tuple remained the expected
`not attached/UNKNOWN/COREIDLE=1/SUSPHY=0`. The subtype objective is therefore
proved despite the non-authoritative ACM timeout.

The source-level interpretation is narrower than the encoded label alone.
`core.h` maps link-state value 3 to U3/HS SUSPEND, and the configured-state
handler would mask `event_info` into that enum. This run was not configured,
however, so that handler never consumed the value. The actual pre-configuration
branch explicitly treats SUSPEND as expected and only requests a 2 mA current
budget. It is therefore a format decode, not a new cause or a runtime proof
that the driver acted on U3.

The integrity-clean same-attempt host sidecar closes the missing host axis. It
captured the initial Android removal, Download-mode addition, candidate flash,
and Download-mode removal. From that final removal through the complete
300-second candidate window it recorded zero kernel lines and zero udev lines:
no new USB device, descriptor retry/error, add, bind, change, expected-PID
event, or exact candidate identity. The start/end snapshots retain the same
unrelated pre-existing same-PID device, so VID/PID alone is not candidate
identity evidence; the exact serial/topology observer also timed out.
Thus the host did not detect an attach from this candidate. This does not yet
distinguish an unasserted device pull-up from a blocked analog/mux/cable path or
a host-port failure. Likewise, absence of `ERRATIC_ERROR` proves only that the
controller emitted no such event; it does not close every analog PHY failure
that could prevent attach detection. The external P3.02 observer is parked
because no safe inline breakout is available. Do not replay the consumed
P3.01-r1 candidate.

The selected P3.03 unit instead tests the silent HS-PHY initialization boundary
that the vendor driver already exposes. Reset and register-readback failures
are logged but not propagated, while all six `clk_prepare_enable()` operations
discard both their prepare and enable returns and then mark clocks enabled.
P3.03 combines a bounded candidate-window `/dev/kmsg` observer with twelve
exact immediate-post-`bl` return probes in the existing vendor module. It does
not rebuild the kernel or inject a module.

## Closed Bounded Unit: P3.03 HS-PHY Silent-Failure Attribution

The exact FYG8 `phy-msm-snps-hs.ko` has SHA-256
`22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94`,
Build ID `cdb249f9a7599440ca66208f02caec0a6601bc03`, and no out-of-line
`msm_hsphy_clocks()` helper. `msm_hsphy_init()` contains twelve ignored return
sites: prepare and enable for `ref_clk_src`, `ref_clk`, and `cfg_ahb_clk` in the
EUD and normal paths. Each selected offset is the instruction immediately
after a relocation-bound `bl` to `clk_prepare` or `clk_enable`; that instruction
is the first `cbz/cbnz w0` consumer. This is not the P3.00-rejected epilogue
offset pattern: there is one named call edge and one ABI-defined return register,
not several path-dependent register states converging at an epilogue.

The exact callsite audit is a hard gate. All twelve offsets must retain the
named preceding call and immediate `w0` consumer in the exact module receipt.
The candidate must also prove the on-device module hash before F1. A missed
callsite is never decoded as return zero. In particular, detail `0xD00` means
that `msm_hsphy_init()` entered and returned zero while all twelve clock
callsites were missed; it permits no clock-return conclusion and instead asks
why `clocks_enabled` was already true. Missing init entry/return or a nonzero
init return is a contradiction family, not the same result.

Ordinal 105 uses the already compiled exact PROGRESS rules `0xD00-0xDA2` for
clock reach and errno buckets. Ordinal 106 uses FAILURE `0x4001-0x4800` for
the candidate-window log summary: first write-readback offset, count bucket,
and reset-failure mask. The observer opens `/dev/kmsg` at the current end before
module loading, requires sequence-complete collection, and requires the normal
HS-PHY path marker. When a complete working-stock log pair is available it is
normalized into the same log domain. A candidate signature equal to working
stock cannot be attributed as the cause; without that pair, candidate log B is
supplemental and explicitly cannot carry causal attribution. Clean
reset/readback logs do not prove the unlogged clock path.

The two clean builds are byte-identical. Each boot image is 100,663,296 bytes
with SHA-256
`434a4075532ac4c35ec5068aaa56da441322f63e5e342fa22f6ee8f62ad52b68`;
each one-member AP is 27,105,321 bytes with SHA-256
`f2cb42b88276dd5c2793d2583308bff60c15e6a7dcf9bb3531b4a6d33f236ad2`.
They retain the fixed P3.00 Image, inject zero modules, and differ from the
parent only in the static userspace observer. The 12-file source intent remains
exact, the artifact/static closure and Process-v2 offline promotion pass. After
the optional-baseline execution closure passed focused independent review, the
clock-only canonical manifest was created at 2,780 bytes with SHA-256
`9188960230eecb7d85bf83c828cea55ea3563a5bd06809e680bcbc4f257b9c83`.
P3.03 completed one distinct candidate attempt and exact rollback at transfer
accounting 1/1. Its result is the valid `0xD00/0x4001` pair described above;
the campaign is closed and the candidate must never be replayed.

The working-stock boot-head log proved unavailable under the healthy D0
contract. Even when the second attended baseline rotation was chained directly
into the read, the retained ring began at 17.431607 seconds and contained zero
normal HS-PHY markers; `/proc/last_kmsg` retained only a prior-boot tail starting
after 4434 seconds. Repeating reboots cannot make this observation complete, so
it is no longer a live gate. The ready contract accepts either no stock pair or
one exact pair. If absent, it records `available=false` and
`causal_attribution_permitted=false`; the twelve clock callsite hit/return
results remain the primary objective. If supplied later, both artifacts must
still cover the boot window, bind exact target/module/campaign identity, and
pass the original strict comparison. One-file and unbound inputs remain
fail-closed. The exact S22+ returned rooted FYG8 health after the second
rotation, A90 received zero commands, and no additional baseline reboot is
planned.

The first Process-v2 connected preparation then stopped before any target
command because the shared D0 adapter still required one total ADB row and saw
both S22+ and A90. That empty run is closed and will not be reused. The narrow
execution repair advances D0 to v2-2 and the live adapter to v2-5: both derive
`SM-S906N/g0q` from the validated profile, match the ADB-normalized
`SM_S906N/g0q` row, permit unrelated rows without commanding them, and pin the
selected serial plus inventory row count before every subsequent target read.
Duplicate or replacement S22+ rows stop before topology/properties. The legacy
unscoped client keeps exact-one behavior. D0/live regressions pass 64/64 and a
focused independent review returned `PASS_GO`; the next preparation must use a
new private run directory and this changed execution closure. The successful
live run did so.

## Closed Bounded Unit: P3.04 Stock USB-Notifier Bridge Attempt

The exact FYG8 stock module `usb_notifier_qcom.ko` is present at 26,344 bytes
with SHA-256
`73f937efc9302d5fa8c2758b5e71b80f52063141d72c063bfe73b1583c781ccb`.
Its declared direct dependencies are `vbus_notifier`, `usb_typec_manager`,
`usb_notify_layer`, `dwc3-msm`, and `common_muic`; all are already in the
candidate closure before the proposed insertion point. The stock recovery
module list includes the module, while the current 60-module candidate plan
does not.

Source gives this bridge unique diagnostic weight. With
`CONFIG_USB_NOTIFIER`, the DWC3 wrapper's extcon registration returns early.
`usb_notifier_qcom` supplies `qcom_set_peripheral()` and calls the sole external
`dwc_msm_vbus_event(enable)` entry, which updates `vbus_active`, queues the OTG
resume work, and permits `B_SESS_VLD` to be set. The minimum P3.04 change is to
add this exact stock module after `dwc3-msm.ko` and before `ucsi_glink.ko`,
preserving the fixed Image, boot-only transfer, exact rollback, and same host
USB sidecar. No EUD write, module rebuild, kernel rebuild, or new transfer
machinery is selected.

The H0 candidate closure is now complete. Two clean builds are byte-identical;
each one-member AP is 27,105,321 bytes with SHA-256
`72ab3644e4db1e1eee609e9ffa28bc39da2c8a177414f0bcf1b7f91a3e9f8258`.
The effective rootfs contains exactly 61 stock modules, with the exact
26,344-byte notifier once at index 59 between `dwc3-msm.ko` and
`ucsi_glink.ko`. The seven byte-affecting P3.04 SOURCE_KEYS still match their
frozen intent, and the inherited P3.03 telemetry and fixed Image are unchanged.

Process-v2 promotion and the canonical 2,767-byte ready manifest pass at
SHA-256
`2ae39774786a35c7d6e5d1fee252e46aa515b55c809b6f7be220cf43eb719c7e`.
The first independent review correctly blocked one execution-binding gap: the
P3.04 61-module runtime closure adapter was imported by evidence validation but
not directly receipted. The exact P3.04 branch now adds that adapter as the
315th execution-critical receipt. Focused post-repair regressions pass 11/11,
independent `verify_bundle()` passes, and the rereview verdict is `PASS_GO`.
No candidate byte or ready-manifest byte changed during the repair.

The first fresh connected preparation stopped read-only because the retained
baseline still contained a prior candidate marker. It created no prepared
record and did not arm F1. One attended normal Android reboot then changed the
boot ID and restored exact rooted FYG8 health without Download, Odin, payload,
or transfer. A second prepared run stopped before candidate intent when its
host guard did not arm; transfer accounting remained 0/0 and the run was not
reused. Host preauthorization and a fresh exact-S22 D0 then produced a third
prepared run binding the same candidate, exact rollback, sidecar, and reviewed
execution closure.

That third run completed candidate and rollback transfer accounting 1/1. The
candidate observer timed out and the physical recovery transition caused one
transient measured-USB inventory failure, but durable recovery sent the exact
rollback only once and resumed final observation without replay. Final rooted
FYG8 health passed and the transaction closed with recovery not required.

The retained `0x7B/0xC5E` pair exposes an H0 contract defect in this candidate,
not a rejected USB-notifier hypothesis. The runtime loop was expanded to 61
modules, but `k_p248_e2_steps[]` retained only module indices 0-59 before the
first gate. Index 59 `usb_notifier_qcom` loaded and verified successfully.
Index 60 `ucsi_glink` then also loaded and verified, after which its
`stage=0x7C/item=60` progress publication conflicted with the inherited
`stage=0x7C/item=0` gate entry and fell into `0xC5E`. No bind gate or later USB
observer ran. P3.04 is closed as `NO_PROOF_OBSERVER`, its candidate is consumed,
and a distinct corrected candidate is required.

## Parked Bounded Unit: P3.02 Passive Pull-Up Electrical Attribution

The distinct P3.02-M0 carrier is complete without a kernel rebuild, module
injection, telemetry change, or Full-LTO rebuild. It reuses the exact P3.01-r1
behavioral bytes and fixed Image; only `/init` gains one inert, non-allocating
`.p302_identity` section containing `P302_ELECTRICAL_CARRIER_V1`. The hardened
verifier keeps every program header, allocated section, existing non-allocated
section, program byte, and otherwise unclaimed ELF padding exact. It permits
only the three section-table locator fields that necessarily change, then
checks the identity, section-name table, section order, and final file layout
exactly. Tampering with GNU-stack flags, section flags, `.comment`, `.bss`, or
non-loaded padding is rejected.

Two clean packages reproduce the same 100,663,296-byte boot image with SHA-256
`dec54b94d84e42d69b3589219c5b43992cf78894f19fd4d591ab2f66ac9509c4`
and the same one-member AP with SHA-256
`f2c55ed945d54ce3db71bdd2e2e6cc3517557601d018a95ad1dd27cdbf48e33a`.
Process-v2 now binds both the inherited nine-file P3.01 overlay and eight-file
P3.02 overlay, preserves the P3.01 decoder, restores all inherited module
globals, and passes an actual same-process P3.01-r1 promotion regression. The
latest offline promotion and ready-manifest rehearsal passed; the rehearsal
reported `created=false`, `manifest_created=false`, and no device contact.
Independent review returned `PASS_GO` for this exact H0 capability after
11/11 focused and 92/92 common regressions.

This does not satisfy the physical observer prerequisite. No public P3.02
manifest exists, F1 is not armed, and live preparation remains blocked until
the exact pass-through board passes pin/short checks and a host-confirmed
`12M` or `1.5M` device proves a known-High data line through that same path.

The next live electrical question is whether the candidate exposes a USB2
device pull-up at the host-visible cable path. The selected observer is a
passive USB-C USB2 inline breakout and high-impedance DC meters; it does not
enable charger detection, drive D+/D-, access MMIO, or change the F1 runner or
telemetry schema. This observer may accompany only the next distinct qualified
candidate. It does not authorize replay of the consumed P3.01-r1 artifact.

Before device contact, H0 must bind the exact male-female pass-through board
and prove unpowered continuity for VBUS, ground, D+, D-, and CC, with no
forbidden cross-short. A known Full-Speed or Low-Speed control device must then
enumerate through the same board and cable at an exact host-reported `12M` or
`1.5M`. The correct D+ or D- line must also measure High. A High-Speed or
SuperSpeed device is not a valid voltage control; failure to prove this
known-High result is `KNOWN_HIGH_CONTROL_INVALID` and stops before S22+ F1.

All breakout leads are fixed before power is applied. No live-board probing,
resistance/continuity mode, or current mode is allowed. A separate camera
records the meter displays and a visible timestamp so the attended operator
remains free for the required Download/recovery action. Raw video remains
private and voltages are transcribed only after rollback. Record VBUS, D+, and
D- at the earliest safe candidate point, then approximately 5, 15, and 30
seconds, and every 30 seconds through the fixed 300-second window. If fewer
than three meters are used, VBUS remains continuous and the prewired D+/D-
channels are selected only away from the energized breakout.

The result contract evaluates VBUS before either data line:

- `VBUS_ABSENT_ALL_WINDOW`: VBUS is absent at every sample. D+/D- are not a
  pull-up verdict; continue in the Type-C/CC/PD/session-valid branch.
- `VBUS_TRANSITION_IN_WINDOW`: VBUS changes between absent and valid. Retain
  direction and first-transition time; D+/D- are subordinate observations.
- `VBUS_VALID_DP_HIGH`: VBUS remains valid and D+ is stably High with D- Low;
  the device pull-up reaches the host-visible measurement point.
- `VBUS_VALID_LINES_LOW`: VBUS remains valid and both data lines remain Low;
  no candidate pull-up reaches the host-visible measurement point.
- `ANALOG_INDETERMINATE`: intermediate, unstable, contradictory, or incomplete
  voltages. Do not relabel this as a USB cause.

The candidate-flash Download enumeration and post-candidate rollback Download
enumeration are already mandatory parts of Process-v2. They are functional
before/after controls for the breakout, cable, CC path, and host and add no
device transition or separate action to the F1 procedure; their post-enumeration
D+ voltage is not a Full-Speed voltage reference.

Only `VBUS_VALID_LINES_LOW` selects a later FSVPLUS observer. That observer
must retain `0x24`, `0x7c`, `0x40`, PHY power, clocks, and charger-detection
state. External High with simultaneous FSVPLUS Low would prove only that
FSVPLUS is unsuitable as a passive detector under those conditions, not why.
External High otherwise skips that additional F1 entirely.

## Closed Bounded Unit: P3.00 Event-Ingress/IRQ Attribution

The source and existing Full-LTO evidence close the design question. The
actual P2.98 A/B `vmlinux` pair is byte-identical and keeps
`dwc3_interrupt`, `dwc3_thread_interrupt`, `dwc3_process_event_buf`,
`dwc3_process_event_entry`, and `dwc3_check_event_buf` out of line. Linked
control flow directly connects top-half return `w0`, threaded processing, raw
event dispatch, and the RESET/CONNECT_DONE handlers. The inlined
`dwc3_gadget_interrupt` helper is explicitly not a probe target.

P3.00 will add one noinline built-in snapshot beside the existing successful
run-stop snapshot. Its eight arguments carry the exact `dwc` and event-buffer
pointers, DEVTEN, GEVNTSIZ, GEVNTCOUNT, and the event buffer's length, count,
and flags. The readback is immediate rather than terminal: count zero means
only zero at that instant, while count nonzero plus no top-half proves a
strictly narrower IRQ-delivery boundary.

The exact Waipio tree has one `dwc3@a600000`, so entry/return pairing may rely
on strict nonnesting only while every later pointer matches that one snapshot.
The P2.98 A/B `vmlinux` contains several generic role/VBUS helpers, but the
active S22+ `vbus_active` and notifier state lives in external `dwc3-msm.ko`.
None is a sound 16th event in the candidate window, so one slot remains spare.
Before a future type-C/extcon/PHY follow-up, H0 must first prove its exact target
is built into `vmlinux`; otherwise it repeats P2.94's pre-device delivery stop.

The H0 implementation and static validation now pass. The fresh
transform/schema/streaming parser/decoder/source contract preserves every
inherited P2.98 payload source byte. Its host C fixtures execute the generated
setup, trigger, recording-window, cleanup, pointer, raw-mask, line/header
parser, and profile-relation paths. Ring-stat parsing, final aggregate stream
counts, and profile `nmissed` readback are source-order and integrated-compile
validated but are not claimed as executed fault branches. The generated patch
clean-applies to the exact inherited source and two static AArch64 `/init`
links are byte-identical. The
verdict is `PASS_P300_EVENT_INGRESS_IRQ_IMPLEMENTATION_HOST_ONLY` and the
focused telemetry verdict is
`PASS_P300_EVENT_INGRESS_IRQ_TELEMETRY_CLOSURE_HOST_ONLY`.

The first independent pass found and stopped an unclosed profile/recording
window plus preliminary build adapters whose qualification module did not yet
exist. The window now opens and closes without a probe-active/tracing-off gap
on the no-cutoff path, its cutoff-close race states are fault-tested, and the
preliminary candidate/build/package adapters were removed from this core
closure. The final independent review returned `PASS_GO` for the exact
remediated core. It qualifies this unchanged observer capability rather than a
candidate run and is reusable while its execution-critical bytes and hazard
assumptions remain unchanged; it is not a per-candidate review gate.

The candidate/build/qualification and exact same-attempt USB-sidecar closure
are now complete. Canonical Tier-1 intent remains unchanged at 159/159 source
keys. Two clean Full-LTO builds reproduce the exact Image and linked vmlinux,
and two boot-only packages reproduce an AP containing only `boot.img.lz4`.
The candidate AP SHA-256 is
`1d80017becd5974f9c64e25ecd8b9d800d001a49e165e6949822d692b58d8d7b`;
the exact Magisk rollback AP SHA-256 is
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The changed Process-v2/live-sidecar capability passed independent review at
bundle SHA-256
`633483479729112c46fc3bee404707957868b2a482b8c3454c6c68822f6e8a8c`
and execution-closure SHA-256
`1edd315f40bd6148e99203cbd2f49131a65f76eb0d21827821067583b20d6166`.
Its fault closure proves that observer witness or shutdown failure cannot block
the mandatory rollback, and interrupted observer descendants are reaped before
another attempt.

The first connected preparation stopped before F1 arm on a historical retained
marker. One attended normal Android reboot rotated that baseline and returned
the exact rooted FYG8 health. A fresh D0 then passed with zero candidate-family
markers and created the reopened prepared binding
`1ec284f2213a71c56de2afa1c202864cef8fa6638348f2f63a03d4dc563d8ad1`
under
`workspace/private/runs/device-action-f1-live-v2/p300-ready1-prepared-20260804-2`.
That exact binding has now completed one attended Process-v2 transaction. The
operator observed a normal candidate boot with no loop. Candidate ACM timed
out, but the two retained slots are valid and byte-identical across both final
reads. Generation 106 reports `DEVICE_OTHER_ONLY` at link state 0 with exact
probe setup, gadget-start return zero, two EP0-enable hits, verified streaming,
zero ring loss, zero missed return probes, and no RESET or CONNECT_DONE.
Generation 107 remains not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0.

The host USB sidecar is `UNKNOWN` and is not used for a host-visibility
conclusion. H0 replay shows that both monitors were alive before the requested
stop, captured without truncation, and then exited zero after handling SIGTERM;
the reviewed verifier overconstrained clean shutdown to return code `-15`.
This host-only mismatch does not invalidate the device-retained result and does
not justify another F1.

Post-live H0 source analysis proves that P3.00 discarded the exact subtype:
the raw trace carried it, but the parser folded every non-RESET/non-CONNECT_DONE
device event into one bit. A bounded live prerequisite then read
`GSNPSID=0x33313130`; its high half is the exact `DWC31_IP` value `0x3331`.
Consequently the DWC3-only pre-2.50a predicate is false, LINK_STATUS_CHANGE is
not enabled, and the DWC3-only pre-2.30a predicate is also false so SUSPEND is
enabled. The unresolved set is exactly DISCONNECT, WAKEUP, SUSPEND,
ERRATIC_ERROR, CMD_CMPL, and OVERFLOW. DISCONNECT is the best-fitting
hypothesis, not a proof. CMD_CMPL is source-disfavoured because the exact
device-generic-command writer polls `DGCMD.CMDACT` without setting
`DGCMD.CMDIOC`. EventOverflow, if present, is separate from the already-proved
zero ftrace-ring loss and must be reported as controller-event incompleteness.

## Closed Bounded Unit: P3.01 Subtype Refinement Attempt

P3.01 is a userspace-only subtype refinement over the
exact qualified P3.00 kernel Image and unchanged 15-probe descriptor. The fixed
Image accepts wide details only as `FAILURE`, excludes `0x4000`, `0x5000`, and
`0x6000`, and becomes terminal after the first non-progress write. It separately
contains all 176 exact progress rules at `0xD00-0xDAF`; the later false tuple
stub does not make those earlier exact rules unreachable. P3.01 must therefore
keep A as the existing 11-family/link progress detail and use B as the terminal
wide-band detail, not the reverse.

For an integrity-clean `DEVICE_OTHER_ONLY` repetition with the inherited exact
final tuple, B uses `0x4001 + (((mask - 1) * 16 + first_info) * 4 + bucket)`.
The six-bit nonzero mask has 63 values, `first_info` is the first other device
event's low nibble, and `bucket` is `1`, `2-3`, `4-7`, or `8+`; all
`63 * 16 * 4 == 4032` values occupy exactly `0x4001-0x4FC0`, leaving 63 valid
codes in that band. This family itself implies the inherited
not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0 final tuple. A changed valid final state
instead uses an exact 132-value `0x5001 + state_index` family and intentionally
does not claim a subtype; observer contradictions use the `0x6001` band. This
preserves information on drift without pretending that two retained slots can
carry both full Cartesian products. DEVTEN is now fixed by measured DWC31, and
the three immediate queue booleans are not retained in P3.01.

This requires reproducible userspace/boot-only packaging, not another Full-LTO
A/B. Bundle the future-only clean-zero sidecar shutdown correction into the same
implementation/review unit so it cannot consume a separate F1.

The P3.01 H0 implementation now satisfies that contract. Generated payload
comparison changes only `p290_e3_runtime_include`; the candidate patch,
checkpoint client, 15-probe descriptor, and exact qualified P3.00 Image remain
byte-identical. Runtime and schema hard-bind A to ordinal 105 with outcome
`PROGRESS`, verify the 105 -> 106 -> 107 checkpoint transition, and reserve
`0x4FC1` for any undefined/disabled device-event subtype before the guarded
`mask - 1` arithmetic. Types 8 and 12, a known/unknown mixture, all four count
buckets, a synthetic zero-mask contradiction, and wrong starting generations
104/106 execute in the generated-C closure.

Nine P3.01 payload `SOURCE_KEYS` were printed and hashed before the overlay
intent. The intent preserves the Image-bound P3.00 run ID and no key changed
afterward. Two static userspace links and two complete candidate packages are
byte-identical. The candidate AP SHA-256 is
`35a1621716702ef553c2db83b8fbb075543c37a4b56507b1fa0c4ef86668c41b`;
it contains only `boot.img.lz4`, injects zero modules, and reuses fixed Image
SHA-256 `01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f`.

The shared sidecar verifier now accepts direct SIGTERM death or clean zero
exit after the recorded SIGTERM request while retaining every prior
alive-before-stop, ownership, no-error, no-truncation, receipt, and same-window
requirement. Focused independent review returned `PASS_GO` for the exact
current P3.01 overlay, decoder/model, boot-only packaging, and sidecar change
set. Process-v2 candidate/static/live binding remains; the artifacts and
capability review alone grant no F1 authority.

One later adversarial review found that the P3.01 static checker could accept a
self-consistent substituted P3.00 result and the same A build in both slots.
The repaired checker now pins the exact 80,509-byte parent result and exact
125,025-byte pre-LTO qualification, requires the canonical A/B directories,
distinct directories and artifact inodes, and validates the complete
byte-identical, linked-audit, adapter, build-header, and qualification
identities. The reproduced bypass is rejected. Nine focused tests, the full
static replay, and ready-manifest rehearsal pass; static output remains
`de4e3b7e...` and the ready manifest remains `eb536d44...`. Independent
rereview returned `PASS_GO` with no residual blocker.

The exact firmware metadata used to derive the candidate plan was also
rechecked against stock. The planner already pins and parses first-stage
`modules.load` (140 rows), recovery `modules.load` (446 rows), and
`modules.dep` (441 rows), recursively closes hard and soft dependencies, and
uses stock order only as a tie-break. A fresh exact-device D0 found a distinct
356-row late `/vendor` list and 482 currently loaded stock modules; every one
of the candidate's 60 runtime names was loaded in stock. Stock also loads
`usb_notifier_qcom`, but the inherited explicit `mode=peripheral` path already
proves `vbus_active`, `B_SESS_VLD`, start-peripheral, and HS-PHY notify-connect
without that automatic Type-C bridge. No module-plan change is selected.

The P3.01 candidate and exact rollback each transferred once. The transaction
is durably `CLOSED`, final rooted FYG8 health passed, recovery is not required,
the sidecar left zero owned processes, and A90 received zero commands. The
retained pair is `0xD70/0x5003`: it repeats integrity-clean
`DEVICE_OTHER_ONLY` at link zero, then records the established not-attached
final tuple as drift because this implementation incorrectly selected `0xE06`
rather than P3.00's exact `0xE02` as its subtype precondition. No exact subtype
is claimed from this run.

The full design and limitation statement is recorded in
`docs/reports/S22PLUS_FYG8_POST_P298_EVENT_INGRESS_IRQ_ATTRIBUTION_H0_2026-08-04.md`.
The implementation receipts and remaining gates are recorded in
`docs/reports/S22PLUS_FYG8_P300_EVENT_INGRESS_IRQ_IMPLEMENTATION_H0_2026-08-04.md`.
The reusable capability-review receipt is recorded in
`docs/reports/S22PLUS_FYG8_P300_EVENT_INGRESS_IRQ_INDEPENDENT_REVIEW_2026-08-04.json`.

## Closed Bounded Unit: P2.98 Live Attribution

P2.98 is the fresh successor contract
`s22plus-fyg8-p298-gadget-start-event-attribution-v1`. Its host implementation
and canonical Tier-1 intent are complete. The reproducible static userspace
also passes. Pre-Full-LTO qualification now passes on the qualified build host:
the focused closure is 130/130, the shared Process-v2 regression is 110/110,
and 33,662,164,992 bytes physical RAM, 12,884,893,696 bytes swap, and
37,085,384,704 bytes free disk satisfy the mandatory resource predicates. The
receipt has SHA-256
`f3533d20ef3edc5c4feaf410296492820138dcd2c56861ee81be02fca78b89eb`
and recorded `full_lto_started=false` before either build. Independent
execution-code rereview returned `PASS_GO` for the exact Tier-2 repair with no
finding, and the current common-policy and S22+ document receipts were rebound
before build.

Two clean Full-LTO builds now close the host unit. Both produced the same
41,490,944-byte `Image` at SHA-256
`689d71487788777e28efbdb48eb783462dde271f5af5a8ba0d2aa6348541ce87`
and the same 476,979,440-byte `vmlinux` at SHA-256
`3067680949754f7c5bd418136bc8c21cc9522f55aa8394a666fa0b21e1a2968d`.
The official result is
`PASS_P298_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY`: all six compared
artifacts are byte-identical, random and absolute host clang paths are absent,
and 138 clang-resource paths are mapped beneath `/private-repo`. No device
action is part of this bounded unit.

This continues the **Gadget-Start Return Host Implementation (H0)** lineage:
the entry plus signed `$retval:s32` pair remains subject to a mandatory
post-Full-LTO A/B disassembly audit, now extended with EP0 and event
attribution.

The bind descriptor now contains 12 events: the inherited seven, one
`__dwc3_gadget_start()` entry/return pair, one entry-only
`__dwc3_gadget_ep_enable()` event, and controller-attributed RESET and
CONNECT_DONE handler entries. The parser requires the exact PID/counter order,
the exact controller pointer, zero missed events, and exact equality between
trace records and per-event profile hits.

The result contract is information-bearing on every valid observer outcome:

1. A negative gadget-start return plus one EP-enable entry proves the EP0-OUT
   command boundary; the same return plus two entries proves EP0-IN. The exact
   source restricts expected errno to `-EINVAL`, `-EAGAIN`, or `-ETIMEDOUT`.
2. A zero return is accepted only with exactly two EP-enable entries. The
   observer stays active through final sampling so the same run records RESET
   and CONNECT_DONE presence plus the link state.
3. The final A/B family itself implies successful probe setup, one returned
   gadget-start call, `start_rc == 0`, two EP-enable entries, exact read/profile
   agreement, and verified cleanup. Earlier setup checkpoints may be overwritten
   safely by the adjacent two-slot terminal publication.
4. Registration failure, no reach, no return, positive return, hit-count
   contradiction, parse/readback failure, cleanup failure, and profile mismatch
   remain distinct retained details.

P2.96 is the explicit historical no-probe behavioral control. Do not spend a
dedicated F1 control unless unexplained prefix/tuple drift, probe-provenance
contradiction, a new health anomaly, or a new hazard class reopens that choice.
Probe installation is evidence of installation only; it does not by itself
exclude observer effect.

The mandatory linked proof disassembles both actual Full-LTO images. It must
show all four probe targets out of line, two ordered and checked EP-enable
calls, the pullup caller discarding gadget-start `w0` before direct run-stop,
and the resume caller immediately testing the signed return. Inline, clone,
tail-call, missing, return-consuming, or A/B-divergent forms fail closed.

The pre-intent freeze covers 136 Tier-1 source keys and reports
`CHANGED_KEYS=[]`. The one canonical intent and static AArch64 userspace are
derived. Two independent links reproduce the 66,384-byte `/init` at SHA-256
`e35e2a1d978d2c9f4af0d6b3ac254239324c6f503312107b1a5a89c91f702daa`
and the 720-byte child at SHA-256
`9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`.
The final direct P2.98 suite passes 20/20 and the whole focused closure passes
130/130. A read-only audit of the historical P2.96 A/B pair passes the
new six-function call-shape checks. The fresh P2.98 A/B pair independently
passes the mandatory linked proof: all probe targets remain out of line, the
ordered two-call EP0 enable chain is retained, pullup discards gadget-start
`w0` before direct run-stop, and resume immediately tests the signed return.

## Ordered Execution

1. Keep every P2.96 `SOURCE_KEY` immutable and retain P2.96 as the historical
   behavioral baseline.
2. Freeze the complete P2.98 Tier-1 set before deriving its one canonical
   intent. Do not edit a Tier-1 byte afterward.
3. Reproduce the static AArch64 userspace, replay inherited focused gates, and
   bind the exact linked-audit metadata into pre-Full-LTO qualification.
4. Apply the runbook's physical-RAM, swap, disk, toolchain, source, and clean
   worktree gates before Full-LTO A/B. The qualified build host and shared
   110-test regression now pass; retain their exact receipts and never bypass
   either gate.
5. Retain the fresh independent `PASS_GO` for the exact reviewed
   trace/schema/parser and postbuild closure only while its named hashes remain
   unchanged. Fresh Full-LTO closure is complete. A later unit must
   independently satisfy package, exact rollback, D0, attended F1, recovery,
   and final-health gates. Never reuse the consumed P2.96 run.

Trial policy adds no per-candidate approval, but the legacy runner still
requires its fresh immutable token until aligned. The consumed P2.96 token,
prepared binding, journal, and candidate attempt are never reusable.

## P2.98 F1 Execution Result

P2.98 passed the last read-only boundary before F1. The new
Process-v2 promotion and ready-manifest adapters passed an exact nine-file
independent review after two fail-closed findings were repaired. The immutable
ready manifest is
`workspace/public/src/device-action/manifests/s22plus_fyg8_p298_process_v2_ready_1.json`
at SHA-256
`369b9037dd394bdea36bec7d1a207ac425c416cb46a83572d2f1562c3e5a7130`.

The first connected preparation correctly stopped on one historical retained
long-family record. One reviewed, attended D1 normal reboot then rotated that
baseline exactly once and returned exact rooted FYG8 health with a changed
boot ID. It issued no Download transition, Odin call, payload, partition
transfer, or command to A90.

The fresh production `--prepare` passed with a 2,097,136-byte clean
`/proc/last_kmsg` read, zero related-family records, and exact candidate,
rollback, target, manifest, and execution-closure binding. The prepared run is
private under `workspace/private/runs/device-action-f1-live-v2/`; its approval
binding SHA-256 is
`34df56c1527aafec28b4ef5e933661c89aa3e255a1daa4dd91c68639569d2613`.
The attended F1 consumed that binding exactly once. Candidate observation timed
out without an ACM endpoint, then the physical Download handoff encountered a
transient USBFS re-enumeration identity failure. Durable recovery continued
without candidate replay. Exact rollback transferred once; a second transient
host endpoint measurement failure occurred after the durable rollback. A final
recovery reopen performed only the remaining health and retained-evidence
reads, never another transfer.

The durable transaction is `CLOSED`: candidate/rollback transfer accounting is
1/1, `recovery_required=false`, and exact rooted FYG8 final health passed. The
two final 2,097,136-byte retained reads are byte-identical and prove
`start_rc=0`, two EP-enable entries, event mask zero, link zero, then
not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0. A production reopen validates the
complete journal, transfer receipts, timeline, final health, and retained
semantics. A90 received zero commands.

The downstream H0 design is now complete and selects P3.00 event-ingress/IRQ
attribution. Do not claim a specific run/connection, PHY, or VBUS cause from
that design. No device attempt follows until its new host implementation,
fault closure, independent review, qualification, and Full-LTO A/B proof are
complete.

## Evidence That Remains Binding

- The nonzero-detail retained-state `-ESTALE` defect is repaired in P2.92;
  accepted states must remain resumable through the whole declared sequence.
- Four pre-P2.92 runs establish a stable generation-88 prefix; P2.92 extends
  the live stable prefix through generation 106.
- The 45-byte two-slot retained ABI is unchanged. A and terminal B must be
  adjacent on every materialized execution path.
- P2.64 Stage C separates payload identity from qualification/evidence and
  live closure. Verifiers and documents may stay outside identity only when
  the contract declares that split and the approval bundle binds exact bytes.
- P2.84/P2.86/P2.88/P2.90/P2.92/P2.94/P2.96 are historical and immutable. Do
  not replay or silently repair them.

Load-bearing reports:

- `docs/reports/S22PLUS_FYG8_P292_F1_FINAL_NOT_ATTACHED_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P292_POST_RUN_STOP_BOUNDARY_AND_VALUE_TELEMETRY_H0_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P294_MODULE_DELIVERY_STATIC_STOP_H0_2026-08-02.md`
- `docs/reports/S22PLUS_FYG8_P294_DWC3_VALUE_TELEMETRY_IMPLEMENTATION_H0_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P296_F1_BUILTIN_DWC3_REFUTED_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_POST_P296_GADGET_START_RETURN_ATTRIBUTION_H0_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_P296_EXECUTION_CRITICAL_INDEPENDENT_REVIEW_2026-08-03.json`
- `docs/reports/S22PLUS_FYG8_P298_GADGET_START_EVENT_IMPLEMENTATION_H0_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_POST_P298_EVENT_INGRESS_IRQ_ATTRIBUTION_H0_2026-08-04.md`
- `docs/reports/S22PLUS_FYG8_P298_EXECUTION_CRITICAL_INDEPENDENT_REVIEW_2026-08-03.json`
- `docs/reports/S22PLUS_FYG8_P302_MEASUREMENT_CARRIER_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The full preceding working history is archived at
`docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`.
Archived text is evidence only and grants no authority.

## Success and Stop Conditions

The current device is healthy and the P3.00 campaign is closed at transfer
accounting 1/1. P2.98 refuted gadget-start or EP0-enable failure; P3.00 now
proves that the raw device-event boundary is reached but sees only another
device event, not RESET or CONNECT_DONE. H0 has exhausted that retained result:
the exact subtype was compressed away and cannot be recovered statically. The
next unit is the userspace-only subtype-retention and future-only sidecar fix
described above. Do not rerun unchanged P3.00 merely to repair the
non-authoritative host axis. Symbol-only proof, stock-path observation,
implicit success on an invalid trace, or a resource-gate bypass remains
insufficient for a successor.

Stop on a repeated material pre-session failure, any post-device-session
unexplained failure, target ambiguity, missing rollback, forbidden archive
member, source mutation after intent, external-module dependency, or evidence
that cannot distinguish the declared USB link-state branches. Never trade a
permanent safety boundary for speed.
