# S22+ FYG8 P3.00 Event-Ingress/IRQ Implementation H0

Date: 2026-08-04
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N`, `g0q`,
`S906NKSS7FYG8`)
Tier: H0 only
Result: `PASS_P300_EVENT_INGRESS_IRQ_IMPLEMENTATION_HOST_ONLY`

## Outcome

The P3.00 host implementation now materializes the event-ingress/IRQ observer
selected after P2.98. It preserves every inherited P2.98 payload source byte,
changes only the four generated artifacts required by the observer, cleanly
applies the generated kernel patch to the exact inherited source contract, and
links the generated static AArch64 `/init` reproducibly twice.

The focused telemetry closure returns
`PASS_P300_EVENT_INGRESS_IRQ_TELEMETRY_CLOSURE_HOST_ONLY`. This is an H0
implementation result, not a linked-kernel qualification, candidate package,
manifest, or F1 authorization. No device or transfer session was opened.

## Closed review corrections

### Trace integrity and `nhit`

The implementation does not interpret kprobe profile `nhit` as having a
filter or trigger cutoff. Kernel source establishes that `kprobe_dispatcher()`
increments `nhit` before the trace filter and before
`trace_trigger_soft_disabled()`. Consequently:

- only events with neither a filter nor a cutoff require profile-hit equality;
- the filtered raw-dispatch event uses its profile/record delta only when the
  CONNECT_DONE cutoff did not fire;
- the conditional post-trigger is exactly `traceoff:1 if type == 2`;
- setup opens the recording window in `tracing_on`, group-enable, trigger-arm
  order;
- finalization reads the remaining count, removes the trigger, reads the final
  tracing state, disables the group, and only then turns tracing off;
- the close-race where CONNECT_DONE fires between count read and trigger
  removal is accepted only with final tracing state zero and the retained
  CONNECT_DONE record;
- the trace is consumed by a bounded streaming parser rather than the old
  fixed 64-record array; and
- per-CPU overrun, commit-overrun and dropped counters, explicit overwrite
  state, parsed-record count, and every kretprobe `nmissed` value are separate
  fail-closed predicates.

The cleanup command is the exact inverse
`!traceoff:1 if type == 2`. A trigger firing may weaken only the declared
filtered raw-event profile relation; it cannot relabel ring loss, a parser
shortfall, missed return instance, or failed trigger cleanup as a USB result.
Every exact no-cutoff profile comparison additionally requires the proved
closed-window state. This removes both the pre-recording and post-recording
`nhit`-without-record gaps found by the first independent review.

### Return-probe capacity

The unfiltered top-half return probe is fixed as:

```text
r32:p282/irq_out dwc3_interrupt $retval:s32
```

The value 32 is explicit rather than inherited from the tracefs default. It
matches the exact P2.98 A/B `CONFIG_NR_CPUS=32` bound. The audited function is
nonrecursive and nonsleeping; the target has one DWC3 controller and the
pending-resume path disables its IRQ while directly invoking the handlers.
Every accepted result still requires `nmissed == 0`, so capacity exhaustion is
an observer failure rather than a device conclusion.

### Exact terminal space

P3.00 reserves exactly `0xD00-0xDAF`, or 176 values, as eleven 16-value
families. The low nibble is the inherited link-state value. The high family is
one of:

1. `NO_TOP_COUNT_ZERO`
2. `NO_TOP_COUNT_NONZERO`
3. `TOP_NONE_ONLY`
4. `HANDLED_NO_WAKE`
5. `WAKE_NO_THREAD`
6. `THREAD_EMPTY_PASS`
7. `THREAD_NONDEVICE_ONLY`
8. `DEVICE_OTHER_ONLY`
9. `RESET_NO_CONNECT_DONE`
10. `CONNECT_DONE_NO_RESET`
11. `RESET_AND_CONNECT_DONE`

RESET presence is therefore mandatory information in every CONNECT_DONE
result; it is not an optional sub-bit. The range is disjoint from the existing
`0xE00-0xE83` final family. New observer failures occupy exactly
`0xF73-0xF7F`.

### Controller and non-device semantics

The Waipio source tree has one `dwc3@a600000`. The runtime nevertheless
requires every observed controller and event-buffer pointer to agree with the
immediate built-in snapshot and rejects nested or unmatched IRQ entry/return
sequences. The return event therefore needs no additional pointer field.

`dwc3_process_event_entry` is filtered to device-event records. Its unfiltered
profile `nhit` minus recorded device entries becomes a non-device-entry count
only when no cutoff fired. This closes the former empty-versus-endpoint
ambiguity without falsely naming all non-device union members as endpoint
events. The accepted name is `nondevice`.

### Future same-F1 host sidecar and spare slot

The existing passive `device_action_usb_trace_sidecar_v1.py` remains Tier 3
and is named by the P3.00 result contract for the eventual same-F1 window. The
current result explicitly records `binding_complete=false`: no runner or
manifest yet binds campaign ID, attempt ID, candidate hash, and the durable
journal interval. That integration remains a pre-F1 H0 gate and does not
create a new authority tier. Once complete, host visibility and device raw
ingress form the intended two-by-two diagnostic matrix in one candidate boot.

The actual P2.98 A/B configuration and symbol tables were audited for a useful
16th event. Generic built-in role/VBUS helpers exist, but the active
`qcom,dwc-usb3-msm` wrapper's `vbus_active`, notifier state, and
`dwc3_msm_notify_event()` live in external `dwc3-msm.ko`. The boot-only lane
injects no module. No built-in symbol was proved both semantically sufficient
and executable in the candidate bind-to-final window, so P3.00 deliberately
uses 15 of 16 slots. Any future connector/type-C/PHY successor must first
prove both exact `vmlinux` linkage and window reachability or stop at H0.

## Generated identity

- contract:
  `s22plus-fyg8-p300-event-ingress-irq-attribution-v1`
- payload source keys: 154
- identity descriptor SHA-256:
  `625a481fbc0dd0d3922ff24c85a9f9c6ca0c723e02c20118895ab0b9a9805953`
- telemetry descriptor SHA-256:
  `5432418016c36f0ae923b99609d5e0e0a3844ef5572b7376fdc2850c299a9009`
- generated patch: 36,900 bytes, SHA-256
  `8a574983e461cb66c392a40a64fb786e11b27b3fdf3cc224a83ce0a6c01c56f2`
- generated runtime wrapper: 27,866 bytes, SHA-256
  `cea5fe4482d27695b944a0a3f378b95aa34c9e3553c6cc305a8a8cc6d3a016f0`
- generated P3.00 runtime include: 141,397 bytes, SHA-256
  `d60542fa1ee0c89a47df4125b3ca5854697ed2e1fc6ae005ab691dd83c00aa5a`
- generated trace descriptor: 21,748 bytes, SHA-256
  `ac7a41f43a49e73b363fb93e0b67bc7fdf1b846f23d338e5ab019e5d1d62586c`
- generated checkpoint client: 35,086 bytes, SHA-256
  `6d109e6d634eb7dda13fde1630271e0b43e90effa5733f6b8f89fee9ba811475`
- reproducible static AArch64 `/init`: 78,672 bytes, SHA-256
  `65076de96a0df47f828c6105dbc9bbae8cd8c291b1e9d9e07421b97b7bf3f64c`

The descriptor has 107 positions, a terminal generation of 107, two retained
slots, 15 bind events, eleven ingress classes, 176 ingress/link terminal
values, 629 exact detail rules, and thirteen newly allocated observer-failure
values.

## Fault and build validation

The closure compiles and executes host C fixtures covering all eleven ingress
classes, IRQ entry/return pairing, unmatched and nested returns, the exact
return domain, both valid empty threaded-pass shapes, raw masks, duplicate
CONNECT_DONE, foreign pointers, filtered-profile relations with and without a
cutoff, trace header syntax, duplicate headers, PID 0 IRQ records, signed
returns, unknown and duplicate fields, trigger lifecycle, both valid
cutoff-close race states, and missing window-close proof.

A dedicated tracefs-state fixture compiles and executes the generated
`p282_trace_setup()`, `p300_trigger_arm/remove()`,
`p300_close_recording_window()`, and `p282_trace_cleanup()` bodies themselves.
It covers normal no-cutoff close, prior cutoff, close-time cutoff race,
impossible state, arm/remove/readback failures, and zero residual
trigger/group/tracing/instance/mount state. This is a one-time capability
qualification for unchanged execution bytes, not a new per-candidate gate.

Evidence is deliberately narrower for three paths: per-CPU ring-stat parsing,
the final aggregate `entries-in-buffer/entries-written/parsed-records` check,
and `p282_profile_clean()` rejection of nonzero `nmissed`. The closure proves
their exact generated code and call order and compiles them in the integrated
static AArch64 image, but does not claim that a host C fault fixture executes
those branches. They remain fail-closed observer predicates rather than USB
conclusions.

It also:

- clean-applies the patch to the exact inherited DWC3 source;
- proves that no external-module source is patched;
- builds two identical static AArch64 userspace images with `-Werror`;
- verifies the exact 15-event descriptor and `r32` return probe;
- proves all 176 accepted terminal values imply probe setup success,
  gadget-start return zero, two EP0-enable hits, verified streaming, zero ring
  loss, and zero missed return probes; and
- reruns the inherited P2.98 focused regressions in split groups without
  changing a P2.98 source path.

Focused P3.00 Python results are 6/6 contract tests and 5/5 telemetry tests
passing. The integrated implementation and runtime-closure tests were run
separately so their external compiler work could not be hidden by a harness
timeout. The unchanged passive sidecar also passes 5/5 focused tests.
`py_compile` and `git diff --check` also pass for the selected paths.

The first independent pass correctly stopped two scope defects before
qualification: the profile/recording window was not closed around probe
activity, and preliminary candidate/build/package adapters named a pre-LTO
module that did not exist. The window implementation above closes the first
defect. The five preliminary adapters were removed from this core closure;
candidate and qualification machinery will be introduced together as a later
reviewed H0 unit rather than represented by dangling code.

## Promotion and live readiness

The trace/schema/parser/trigger/built-in-helper core retained its independent
`PASS_GO`. The subsequent candidate/build/qualification and exact same-attempt
sidecar unit is also complete. Canonical Tier-1 intent remains unchanged at
159/159 source keys; two clean Full-LTO builds and two boot-only packaging runs
are reproducible. The AP contains only `boot.img.lz4` and is paired with the
exact preapproved Magisk rollback.

The Process-v2 sidecar integration records an exact durable observation
witness, rejects early source exit and duration expiry, reaps an interrupted
sidecar process group and its descendants, and converts observer failures to a
host-axis `UNKNOWN` without blocking the mandatory rollback. Focused
sidecar/P3.00 regression passed 21/21. Independent review returned `PASS_GO`
for bundle
`633483479729112c46fc3bee404707957868b2a482b8c3454c6c68822f6e8a8c`
and execution closure
`1edd315f40bd6148e99203cbd2f49131a65f76eb0d21827821067583b20d6166`.

The first connected D0 stopped before preparation on a historical retained
marker. One reviewed attended normal Android reboot rotated it and returned
exact rooted FYG8 health. Fresh D0 then passed and the prepared record reopened
under
`workspace/private/runs/device-action-f1-live-v2/p300-ready1-prepared-20260804-2`.
The exact attended Process-v2 transaction is now complete. The operator saw a
normal candidate boot with no loop. Candidate ACM timed out, while the retained
P3.00 pair passed its device-side integrity contract and reported
`DEVICE_OTHER_ONLY`, link 0, no RESET, and no CONNECT_DONE, followed by the
inherited not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0 final state.

The USB sidecar remains `UNKNOWN` and contributes no host-visibility claim.
Both sources were alive before requested shutdown, untruncated, and returned
zero after handling SIGTERM; the verifier required only `-15`. This is a
future-only host verifier repair, not grounds for another candidate boot.

Candidate and rollback transfers are exactly 1/1. The durable transaction is
`CLOSED`, exact rooted FYG8 final health passed, recovery is not required, and
zero owned sidecar processes remain.

## Post-live `DEVICE_OTHER_ONLY` reduction

H0 source analysis closes the interpretation limit of the live result. The
event-buffer setup reprograms the buffer and writes zero to `GEVNTCOUNT`, but
the driver later acknowledges consumed bytes by writing the nonzero consumed
count to that same register. Source alone therefore does not prove that the
zero write clears an older count. The prior core soft reset and the exact
immediate `GEVNTCOUNT` value were observed, but P3.00 did not publish that
numeric value. H0 cannot place the event more narrowly than the candidate bind
window. The exact driver enables DISCONNECT, RESET, CONNECT_DONE, WAKEUP,
ERRATIC_ERROR, CMD_CMPL, and OVERFLOW, adds LINK_STATUS_CHANGE only for a
DWC3-IP revision before 2.50a, and adds SUSPEND whenever that DWC3-only prior
predicate is false for 2.30a. P3.00 already excludes RESET and CONNECT_DONE.
HIBER_REQ, SOF, the reserved type, and the vendor-device-test type are not
enabled by this path.

The runtime-IP prerequisite is now measured rather than inferred. One exact
S22+ D0 first proved `SM-S906N/g0q/S906NKSS7FYG8`, the selected USB realpath,
completed Android boot, and active parent/child runtime-PM state. debugfs was
not mounted. The register read therefore used one attended D1 transaction:
mount debugfs read-only, read one `GSNPSID` line while both runtime-PM nodes
remained active, unmount through the exact return path, and verify
Android-complete plus controller-active health. It returned
`GSNPSID = 0x33313130`, unmounted cleanly, and left no second attached target.
The high half `0x3331` equals `DWC31_IP`.
Three draft wrapper invocations had first failed closed on host predicates: one
before device contact on ADB's `SM_S906N` inventory spelling, then two after
read-only identity calls on noncanonical bootloader/PID1 assertions. The
corrected D0 uses the repository's incremental-build identity field. None of
those stops changed device state or contacted A90.

`DWC3_VER_IS_PRIOR(DWC3, 250A)` and
`DWC3_VER_IS_PRIOR(DWC3, 230A)` both require `dwc->ip == DWC3_IP` (`0x5533`).
They are therefore false on this measured DWC31 controller. ULSTCNGEN is not
set, while the negated 2.30a predicate sets U3L2L1SUSPEN. The exact unresolved
set is six types: DISCONNECT (0), WAKEUP (4), SUSPEND (6), ERRATIC_ERROR (9),
CMD_CMPL (10), and OVERFLOW (11). LINK_STATUS_CHANGE (3) is excluded.

CMD_CMPL is source-disfavoured: every exact device-generic-command call polls
`DGCMD.CMDACT`, and the exact DGCMD write omits `DGCMD.CMDIOC`. This is the
device-generic command layer, not endpoint `DEPCMD.CMDIOC`; the event remains
enabled by `DEVTEN.CMDCMPLTEN`, so omission of CMDIOC is not promoted to a
hardware impossibility proof.
DISCONNECT is the strongest current hypothesis because its handler explicitly
sets not-attached and UNKNOWN speed, and the supporting host capture saw no
intended candidate ACM enumeration. It is still not proved: those values also
describe the untouched initial state, and the host sidecar remains
non-authoritative.

The subtype is irrecoverable from the retained P3.00 bytes. The trace record
contained the raw 32-bit event and exact type, but the streaming parser reduced
all types other than RESET and CONNECT_DONE to one `other_device_seen` bit.
The numeric DEVTEN and event records were validated in memory and then not
published. Static source cannot choose among the remaining types.

OVERFLOW must be a distinct successor result. P3.00's zero ring-loss predicate
proves the ftrace observer ring did not lose records; it does not negate a DWC3
hardware EventOverflow device event, which would make earlier controller-event
completeness unknown.

The proportional successor is userspace-only telemetry refinement over the
unchanged P3.00 probes and exact already-qualified Image SHA-256
`01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f`.
It needs no new kernel probe and no new Full-LTO build.

The fixed-Image ABI imposes four non-negotiable facts:

1. a wide detail is accepted only with outcome `FAILURE`;
2. each apparent 4K band excludes its base, so `0x4001-0x4FFF` contains 4095
   values and `0x4000` is rejected, with the same holes at `0x5000` and
   `0x6000`;
3. the first non-progress write makes the checkpoint terminal, so a wide-band
   A cannot be followed by B; and
4. the exact compiled rule table contains every ordinal-105 progress tuple from
   `0xD00` through `0xDAF` before the later always-false tuple stub. Those 176
   values are reachable and are not dead text.

P3.01 therefore preserves A exactly as P3.00's eleven family plus four-bit link
state progress detail in `0xD00-0xDAF`. B is the terminal failure detail. For
an integrity-clean `DEVICE_OTHER_ONLY` repetition whose final state equals the
inherited not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0 tuple, define mask bits in
the fixed order `{DISCONNECT, WAKEUP, SUSPEND, ERRATIC_ERROR, CMD_CMPL,
OVERFLOW}` and encode:

```text
index  = (((mask - 1) * 16 + (first_event_info & 0xf)) * 4) + count_bucket
detail = 0x4001 + index
```

The nonzero mask has 63 values. `count_bucket` is `0=1`, `1=2-3`, `2=4-7`,
or `3=8+` raw other-device records. Thus `63 * 16 * 4 == 4032` occupies exactly
`0x4001-0x4FC0`, with no base hole and 63 valid codes left in the first band.
An accepted subtype detail itself implies the exact inherited final tuple.

If the final state changes, retaining an exact drift is more honest than
silently attaching the old final-state meaning to a subtype code. A changed
valid final state instead uses `0x5001 + state_index` for all 132 existing state
indices and intentionally makes no subtype claim. Non-other P3.00 branches are
already retained by A and can use the same exact-final-state family. Observer,
parse, or state contradictions use named values beginning at `0x6001`.

The measured DWC31 identity removes the earlier three-way DEVTEN class. The
three immediate queue booleans are deliberately not retained: preserving them
alongside the complete subtype mask, first info nibble, four count buckets,
P3.00 branch/link, and exact drift state does not fit the fixed two-slot ABI.
This is a proportional scope choice, not an implicit zero or an unproved timing
claim.

The future-only sidecar shutdown correction should travel in that same H0
implementation unit: accept both signal termination and a monitor's clean zero
exit after the recorded SIGTERM request, while retaining the existing
alive-before-stop, untruncated, no-error, bounded-window, and ownership checks.
One focused review is required for the changed telemetry/schema and host
verifier. The unchanged kernel Image and probe machinery do not justify a new
Full-LTO A/B or a second review ceremony.

The concurrent A90 worktree paths were not read as authority, edited by this
unit, staged, or used; A90 received zero commands.

The review-time receipt and its reuse boundary are recorded in
`S22PLUS_FYG8_P300_EVENT_INGRESS_IRQ_INDEPENDENT_REVIEW_2026-08-04.json`.
