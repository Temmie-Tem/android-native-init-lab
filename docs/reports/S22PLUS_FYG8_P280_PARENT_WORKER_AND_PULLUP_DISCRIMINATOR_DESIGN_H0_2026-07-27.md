# S22+ FYG8 P2.80 parent-worker and pull-up discriminator design

Date: 2026-07-27 KST
Tier: H0 host-only
Status: `DESIGN_COMPLETE_IMPLEMENTATION_PENDING`

## Verdict

`GO` for a bounded P2.80 implementation under H0.

P2.80 will not retry the role transition, add another USB stack, or infer
electrical attach from a successful sysfs write. It will observe two existing
boundaries in the exact P2.76 path:

```text
PID1 peripheral request
  -> parent dwc3_otg_start_peripheral(on=1)
  -> parent and child runtime-PM call results
  -> configfs UDC bind
  -> child dwc3_gadget_pullup(on=1)
  -> child dwc3_gadget_run_stop(on=1), when reached
  -> canonical UDC state and negotiated speed
```

The selected mechanism is a small, versioned tracefs kprobe-event set. It is
armed only around those two transitions and parsed into an exact retained
functional detail or progress warning. Instrumentation setup loss does not
block the primary E3 mission after verified clean ownership. Phase B trace loss
after its synchronous bind is also diagnostic-only. A specifically classified
Phase R post-action ambiguity may retain RAM-only probe state until the
mandatory reboot rather than risk unregistering an active kretprobe.

This design grants no build, D0, approval, transaction, reboot, flash, or
device-write authority.

## Preserved Contract

P2.80 preserves:

- the exact P2.76/P2.71 60-module closure and insertion order;
- E3 stages `0x88..0x8f` and terminal success stage `0x90`;
- every P2.60 configfs, gadget, `ttyGS0`, banner, role, UDC, and speed value;
- one PID1 write of `peripheral`, one configfs UDC bind, and no role retry;
- the exact boot-only candidate and Magisk rollback execution model;
- P2.48 regression/read-error semantics and all existing `0xaXX` details;
- the P2.74 host USB sidecar as mandatory evidence for a later F1; and
- Process v2 journaling, rollback, final-health, and fresh-approval rules.

P2.80 adds no checkpoint stage or retained-record field. It adds exact
structured details plus a versioned nonterminal progress-warning semantic at
the current frontiers only. Terminal success remains zero-detail.

## Adversarial Corrections

### A. External `vbus_active` producers

P2.79A excluded the Samsung notifier by module identity. P2.80 must preserve a
stronger symbol-level proof.

The FYG8 stock vendor modules were scanned for undefined references to:

```text
dwc_msm_vbus_event
dwc_msm_id_event
```

Only `usb_notifier_qcom.ko` imports those exported DWC3-MSM entry points. It is
not in the exact 60-module candidate closure. The exact closure also cannot
activate UCSI because its ADSP remoteproc owner and firmware path are absent.

The source's default-peripheral branch is inapplicable as well:

1. `usb_role_switch_register()` completes before
   `dwc3_msm_check_extcon_prop()`;
2. the default `vbus_active=true` assignment requires both
   `!mdwc->role_switch` and `!mdwc->extcon`; and
3. the registered parent role switch makes that predicate false.

Therefore the initial supported source model has no external DEVICE producer.
P2.76's explicit PID1 role write remains strongly source-deduced. P2.80 will
make that assumption executable: an initial `peripheral` or `host` value is a
model contradiction and stops before another role write.

This conclusion is limited to the inspected FYG8 source and exact module
closure. It is not a claim that undocumented firmware can never affect USB.

### B. Correct interpretation of stage `0x8e`

Stage `0x8e` proves more than a configfs string readback, but less than actual
controller RUN_STOP.

The exact UDC core:

1. initializes `udc->vbus=true`;
2. calls `usb_udc_connect_control()` while binding the gadget driver;
3. calls `usb_gadget_connect()` when VBUS is true; and
4. propagates a nonzero gadget-connect return through
   `udc_bind_to_driver()`.

Thus P2.76 stage `0x8e` proves:

```text
dwc3_gadget_pullup(on=1) returned 0 to the UDC bind path
```

It does not prove that `dwc3_gadget_run_stop()` executed. The exact pull-up
source has successful early exits when:

- `pm_runtime_get_sync()` returns zero after handling resume;
- `pullups_connected` already equals the requested state; or
- the run-stop helper itself sees the child runtime-suspended and returns zero.

Conversely, successful bind does not imply every nested run-stop returned
zero. `dwc3_resume_common()` discards `dwc3_gadget_resume()`'s return, so a
run-stop failure inside runtime resume can be swallowed before pull-up itself
returns zero.

The durable wording is therefore "pull-up API success", not "RUN_STOP
success". P2.80 observes both functions separately.

### C. Resume-time supplier failure

H11 is retained:

```text
probe-time dependencies were sufficient to bind;
role-time parent or child runtime resume can still fail or block.
```

The exact `dwc3_otg_start_peripheral()` calls parent and child
`pm_runtime_get_sync()` but ignores both return values. In the linked FYG8
module those wrappers compile to two calls to `__pm_runtime_resume`.

For the currently inspected module, the instructions immediately after those
calls are at function-relative offsets `+0x34` and `+0x450`. Those numbers are
evidence, not handwritten runtime constants. The P2.80 contract must derive
the two post-call sites from the exact module's relocations and disassembly,
then generate the runtime event definitions from that result.

A negative value captured at either post-call site directly supports H11.
Absence of a negative value does not prove that every clock, regulator, or
interconnect operation had its intended hardware effect.

### D. Independent adversarial review corrections

The first independent review returned `NO-GO` on the draft. Five findings were
resolved in the design before implementation:

1. The parent role write is synchronous and can block inside
   `flush_delayed_work()`. PID1 therefore delegates the one exact write to a
   child while retaining the absolute deadline and checkpoint control.
2. All probed `int` arguments and returns use explicit signed 32-bit fetch
   types.
3. The owned trace instance uses a globally ordered `counter` clock, and the
   Phase R parser requires one captured `common_pid`.
4. Missing synchronous Phase B returns and impossible propagated return
   combinations are trace/source contradictions, not USB states.
5. Phase B probes and its instance are removed before ordinary `0x8e`
   progress; only parsed values remain in memory.

The follow-up review found one remaining precedence gap: a negative helper
write result could otherwise drift into the no-entry deadline. The final
state machine now performs cleanup and preserves that existing errno before
evaluating any `0xb13` no-entry result.

The review's broader claim that every nonzero run-stop result contradicts a
successful UDC bind was rejected after a deeper exact-source check.
`dwc3_resume_common()` calls `dwc3_gadget_resume()` without propagating its
return. A nested `dwc3_gadget_run_stop()` failure can therefore be swallowed
by runtime resume, after which `dwc3_gadget_pullup()` can still return zero.
That source-valid outcome remains an exact P2.80 classification.

## Selected Observation Mechanism

### Why tracefs kprobe events

The exact rebuilt kernel enables:

```text
CONFIG_KPROBES=y
CONFIG_KRETPROBES=y
CONFIG_KPROBE_EVENTS=y
CONFIG_EVENT_TRACING=y
CONFIG_TRACING=y
CONFIG_DEBUG_FS=y
CONFIG_KALLSYMS=y
CONFIG_KALLSYMS_ALL=y
CONFIG_TRACEFS_DISABLE_AUTOMOUNT=y
```

The required built-in symbols are present in the exact `System.map`, including
`trace_clock_counter`, and the parent functions remain named local symbols in
`dwc3-msm.ko`. The same `System.map` contains `instance_mkdir`,
`instance_rmdir`, `trace_array_create`, and `trace_array_destroy`; tracing
instances are linked, not assumed from a newer upstream kernel.

Tracefs accepts entry and return probes by `[MOD:]SYM[+offset]`, supports named
fetch arguments and `$retval`, and permits selective removal. The upstream
interfaces are documented in:

- https://docs.kernel.org/6.12/trace/kprobetrace.html
- https://docs.kernel.org/trace/kprobes.html
- https://docs.kernel.org/trace/ftrace.html

The exact vendor module already registers kretprobes on
`dwc3_gadget_pullup()` and `dwc3_gadget_run_stop()`. Its existing handlers log
through the vendor debug path and are not retained proof. Their presence does
show that this FYG8 module was designed to probe these exact functions.
Upstream Kprobes explicitly permits multiple probes at one address.

Qualcomm IPC logging remains optional corroboration only. Low Samsung debug
can collapse its context to a dummy logger, so marker absence is not evidence.
The DWC3 `link_state` debugfs read remains excluded because it runtime-resumes
the controller and perturbs the state being diagnosed.

### Shadow Call Stack, pointer authentication, and CFI

An adversarial follow-up raised a valid failure-mode question: a silently
bypassed return probe would turn "return instrumentation did not fire" into a
false claim that the target did not return. Exact FYG8 source and linked-code
inspection rule out the proposed Shadow Call Stack mechanism.

The exact arm64 Kprobe core calls the return-probe entry handler and then
`arch_prepare_kretprobe()` before the target's first instruction.
`arch_prepare_kretprobe()` saves live `x30` and replaces live `x30` with
`kretprobe_trampoline`; it does not patch a saved return address on the normal
stack. The exact `dwc3_otg_start_peripheral()` body then executes:

```text
paciasp
str x30, [x18], #8
...
ldr x30, [x18, #-8]!
autiasp
ret
```

The substituted trampoline is therefore what pointer authentication signs and
what Shadow Call Stack stores. The exact arm64 trampoline later restores the
original return target into `lr`. SCS bypass of this return probe is
`RULED_OUT` for the inspected FYG8 source and object. This conclusion is
source/disassembly-specific; the generic QEMU control below does not claim to
validate S22+ SCS.

The event set already pairs every decisive return probe with its entry probe.
Its three states remain distinct:

- registration or exact readback failure before action is progress warning
  `0xb02` after clean ownership;
- registered but no decisive entry is a source-defined pre-entry outcome
  (`0xb12` or `0xb13` in Phase R);
- entry without its required return is `0xb14` in Phase R or progress warning
  `0xb03` after the synchronous Phase B bind and clean ownership.

Any nonzero missed count is `0xb03` in quiescent Phase B but terminal `0xb18`
after the asynchronous Phase R action. A separate live control return probe
would not prove that a different target returned and would enlarge the
instrumentation hazard, so P2.80 does not add one.

CFI symbols must be resolved by exact name and body address. The exact vendor
module contains the local body
`dwc3_msm_usb_role_switch_set_role` and a distinct global
`dwc3_msm_usb_role_switch_set_role.cfi_jt`; P2.80 does not probe either one.
Its parent target `dwc3_otg_start_peripheral` has one local body and no
same-name `.cfi_jt`. The three built-in Phase B targets likewise resolve to
exact local bodies without same-name `.cfi_jt` symbols. The site extractor
must reject a suffix match, a CFI thunk, an alias, or an address outside the
expected text section.

### Mandatory generic-arm64 mechanism control

The pinned Debian generic-arm64 guest enables Kprobes, Kretprobes, Kprobe
events, Ftrace, tracing, and full kallsyms. P2.80 adds a standalone control:

- `s22plus_fyg8_p280_kprobe_qemu_control.c`;
- `s22plus_fyg8_p280_kprobe_qemu_control.py`; and
- focused source/config mutation tests.

It hash-pins the guest kernel and config plus the QEMU binary/version, mounts
tracefs, creates one isolated instance and group, and registers one
entry/return pair on exact `__arm64_sys_close`. It filters to PID1, selects the
counter clock, invokes `close(-1)`, requires one ordered entry and return with
exact signed `:s32` value `-EBADF`, requires zero missed probes, removes both
events and the instance, unmounts tracefs, and verifies cleanup. Compilation,
archive construction, QEMU identity, and guest execution all have explicit
host deadlines.

This control is mandatory before Full LTO. It validates the tracefs ABI,
event syntax, return-value fetch, instance/filter behavior, profile parsing,
and cleanup path that P2.80 will reuse. It does not validate Qualcomm targets,
target SCS/PAC, DWC3 behavior, or physical USB enumeration; those remain
covered by exact source/object gates and, later, the bounded F1 observation.

### Tracefs ownership

Each phase has a separate complete ownership lifecycle. The candidate will:

1. mount `tracefs` at `/sys/kernel/tracing` when needed;
2. verify exact filesystem type `TRACEFS_MAGIC=0x74726163`;
3. require the exact control files used by the contract;
4. require a newly created tracing instance at `instances/p280`;
5. define only group `p280` with fixed event names, disabled globally;
6. enable those events only in the `p280` instance;
7. require `counter` in `trace_clock`, select it, and read back `[counter]`;
8. set that instance to a bounded 64 KiB-per-CPU trace buffer;
9. use the kernel-derived default `maxactive` for return probes rather than an
   arbitrary smaller cap;
10. remove only `p280` events and the owned instance, never clear another
   owner's events or global ring buffer;
11. require a zero missed count for every owned probe profile; and
12. verify full cleanup before ordinary progress from that phase.

Dynamic event definitions are globally visible even when enabled only in one
instance. Any pre-existing `p280` group or `instances/p280` directory is an
ownership conflict and fails setup. The candidate does not reuse or overwrite
it. A candidate-owned mount uses `nosuid,nodev,noexec`, is tracked explicitly,
and is unmounted after each phase's instance/event cleanup. A pre-existing
valid tracefs mount is never unmounted by the candidate. Phase B recreates the
same exact names only after Phase R has verified their absence.

Registration, readback, parse, missed-event, or overrun ambiguity is an
instrumentation failure. It must never be decoded as a USB hardware failure.
Setup failure before a phase action is fail-soft only after the candidate
proves that no owned event, instance, or mount remains. Phase B post-bind trace
loss is fail-soft only after its synchronous bind returned and cleanup passed.
The first diagnostic warning is propagated through later progress records.
If bounded cleanup itself cannot be verified on a quiescent path, the candidate
records `0xb04`, parks, and does not claim a clean instrumentation exit.

A Phase R deadline after a probe target entered is different: unregistering an
active kretprobe can itself wait. PID1 performs a best-effort disable, does not
attempt potentially blocking unregister, records the exact deadline detail,
and parks. The mandatory reboot/rollback clears that explicitly non-clean
RAM-only state.

### Exact event set

The contract descriptor, not handwritten C strings, generates the event set.
The intended semantic shape is:

```text
Phase R: parent role work
  start_in       dwc3_msm:dwc3_otg_start_peripheral, on=%x1:s32
  parent_pm_out  post-call site for parent __pm_runtime_resume, rc=%x0:s32
  child_pm_out   post-call site for child __pm_runtime_resume, rc=%x0:s32
  start_out      return from dwc3_otg_start_peripheral, rc=$retval:s32

Phase B: UDC bind and child pull-up
  resume_in      dwc3_runtime_resume
  resume_out     return from dwc3_runtime_resume, rc=$retval:s32
  pull_in        dwc3_gadget_pullup, on=%x1:s32
  pull_out       return from dwc3_gadget_pullup, rc=$retval:s32
  run_in         dwc3_gadget_run_stop, on=%x1:s32
  run_out        return from dwc3_gadget_run_stop, rc=$retval:s32
```

Phase B events are filtered to `common_pid == 1`. Phase R runs on the parent
workqueue, so its decisive entry is filtered by `on == 1` and correlated by
the `counter` trace clock. The parser captures `common_pid` at the first
`start_in(on=1)` and requires every decisive Phase R record through
`start_out` to have that same PID.

The parser does not require an exact total event count. Extra irrelevant
events are ignored. It requires only the ordered load-bearing boundaries,
their exact arguments, clean probe profiles, and unambiguous returns. This
avoids repeating the prior invalid "global cardinality must equal one" class
of contract bug. In Phase R, records before the first
`start_in(on=1)` are ignored; this permits the role write's initial
`flush_delayed_work()` to finish an older stop-side worker without confusing
it with the newly queued DEVICE worker.

The post-call probes fire before their target instruction executes, while
register `x0` still carries the inlined `pm_runtime_get_sync()` return. The
site extractor must verify this exact AArch64 dataflow, not merely locate a
nearby relocation. The explicit `:s32` fetch type preserves negative Linux
`int` results instead of treating AArch64 `w0` zero-extension as success.

Phase B parsing accepts only exact source-valid nesting. All records must have
`common_pid == 1`; a nested entry without its return, a nonzero pull-up return
after successful bind, or a negative runtime-resume return after successful
bind is a trace/source contradiction. A nonzero run-stop return is different:
it is valid only when nested in runtime resume, whose caller discards the
gadget-resume error before pull-up returns zero.

## Runtime State Machine

### Phase R: parent role work

1. Prepare tracefs and arm the four Phase R events before reading or writing
   the parent role. A pre-action `0xb01` or `0xb02` setup failure may continue
   only after verified cleanup. That path stores the first warning and uses the
   already exercised P2.60 final role/UDC predicate with a P2.80 exact-`none`
   precondition. It never accepts or writes from initial `host` and makes no
   trace-derived conclusion. Because arming failed before the role action and
   ownership cleanup passed, no P2.80 probe can be active. This degraded path
   intentionally does not prove parent-worker quiescence; it reuses the
   P2.76 ordering that already reached exact `0x8e` without a boot loop.
2. Read `/sys/devices/platform/soc/a600000.ssusb/mode` exactly.
3. Accept only exact `none`.
   - `peripheral` is an external-producer/model contradiction.
   - `host` is an unsafe topology contradiction; do not write HOST or continue.
   - malformed or unreadable data uses the existing exact errno behavior.
4. Clear the owned instance buffer and enable Phase R.
5. Start one absolute 30-second deadline before `fork()`. The child closes
   unrelated descriptors, performs the one exact `peripheral` write, reports
   its exact return through one fixed-size versioned pipe record, and exits.
   The record carries a magic, operation ordinal, signed syscall result, and
   exact byte count. It contains no text or identifier. The child does not
   retry, exec, sleep, checkpoint, or control tracing.
6. PID1 remains the control plane. It uses nonblocking child reaping and
   bounded instance snapshots until both the write result and the required
   trace outcome are known or the one deadline expires. The deadline is never
   reset by write completion or event entry.
7. A valid helper record with a negative write result stops waiting
   immediately. PID1 performs quiescent cleanup and fails at `0x8d` with that
   existing positive errno detail. Cleanup failure instead produces `0xb04`.
   A nonnegative result with a non-exact byte count is `0xb17`.
8. Require ordered `start_in(on=1)`, both PM post-call records, and
   `start_out(rc=0)` from one `common_pid`.
9. A negative parent or child PM return is a structured H11 result.
10. On a quiescent outcome, stop tracing, verify zero missed events, parse once
    more, and verify full event/instance/mount cleanup. Post-action malformed,
    missed, or source-incomplete Phase R trace is `0xb18` and does not continue.
11. Revalidate exact `peripheral`, exact `a600000.dwc3` membership, and all
    earlier E2 gates before publishing progress at `0x8d`, carrying the first
    diagnostic warning when the clean setup fallback was used.

If the child remains in the sysfs write at the deadline, PID1 sends one
`SIGKILL` and never performs a blocking wait. No `start_in(on=1)` classifies
the pre-worker/flush boundary; an entered but unreturned parent start
classifies the worker boundary. PID1 best-effort disables tracing but does not
unregister a possibly active return probe. It records the exact deadline
detail and parks for the already mandatory reboot.

`start_out(rc=0)` proves that the source's straight-line on-path returned
after the VBUS override, redriver/PHY connect notifications, DBM reset,
`in_device_mode=true`, and child DEVICE-role call sites. It proves those
operations were reached and returned; it does not prove their electrical
effect.

### Phase B: UDC bind and pull-up

1. Arm the six Phase B events and require their exact registration readback.
   A pre-bind `0xb01` or `0xb02` setup failure may continue uninstrumented only
   after verified cleanup.
2. Clear only the owned instance buffer and enable that instance.
3. Run the unchanged exact configfs UDC bind.
4. Disable tracing immediately after the synchronous bind returns.
5. Snapshot and validate the owned trace plus kprobe profiles.
6. Verify full Phase B event/instance/mount cleanup. Keep only the parsed
   bounded result in ordinary memory.
7. On bind error, fail at `0x8e` with the existing errno after cleanup.
8. On trace loss, missed events, or a source contradiction after the
   synchronous bind, store progress warning `0xb03` only after verified
   cleanup. Cleanup failure remains terminal `0xb04`.
9. On bind success and clean ownership, publish progress at `0x8e`, carrying
   the first diagnostic warning when one exists.
10. Preserve the parsed Phase B result while running the unchanged
   30-second configured/high-speed loop.
11. High-speed configuration remains normal success. Progress at `0x8f`
    propagates the warning before zero-detail terminal `0x90`. Configured at
    another speed remains `EPROTO`.
12. At timeout, revalidate earlier gates, re-read exact parent mode, UDC state,
    and speed, then select one exact P2.80 detail. A clean trace is mandatory
    for `0xb20..0xb22`; specifically, Phase B must be clean. A Phase R warning
    alone does not invalidate Phase B pull-up/run-stop evidence. If Phase B is
    not clean, `not attached` becomes `0xb27`.

Because the bind is synchronous, a successful `p260_bind_udc()` return closes
the Phase B trace interval. Missing nested returns are therefore
instrumentation failures, not proof that a synchronous kernel call remained
in flight. No probe remains through the configured wait, and no blind
post-bind dwell is added.

## Exact Structured Detail Contract

P2.80 reserves no broad `0xbXX` range. Only the descriptors below are valid,
and only for their listed outcome and stages.

| Detail | Outcome | Allowed stage | Exact meaning |
|---:|---|---:|---|
| `0xb01` | progress warning | `0x8d..0x8f` | tracefs or required control ABI was unavailable before action |
| `0xb02` | progress warning | `0x8d..0x8f` | exact probe registration/readback failed before action |
| `0xb03` | progress warning | `0x8e..0x8f` | Phase B trace was malformed, lost, missed, or source-contradictory after synchronous bind |
| `0xb04` | failure | `0x8d`, `0x8e` | quiescent-path trace cleanup could not be verified |
| `0xb10` | failure | `0x8d` | initial parent role was already `peripheral` |
| `0xb11` | failure | `0x8d` | initial parent role was `host`; candidate stopped before writing |
| `0xb12` | failure | `0x8d` | role-write helper missed the deadline before DEVICE start entry |
| `0xb13` | failure | `0x8d` | role write returned, but DEVICE start never entered by the deadline |
| `0xb14` | failure | `0x8d` | DEVICE start entered but did not return by the one deadline |
| `0xb15` | failure | `0x8d` | parent runtime-PM call returned a negative value |
| `0xb16` | failure | `0x8d` | child runtime-PM call returned a negative value |
| `0xb17` | failure | `0x8d` | helper/start return or ordering contradicted the exact source |
| `0xb18` | failure | `0x8d` | Phase R post-action trace could not prove quiescent worker completion |
| `0xb20` | failure | `0x8f` | pull-up returned zero without a run-stop call and state stayed `not attached` |
| `0xb21` | failure | `0x8f` | nested run-stop failed, error was swallowed, state stayed `not attached` |
| `0xb22` | failure | `0x8f` | run-stop returned zero and final UDC state was `not attached` |
| `0xb23` | failure | `0x8f` | final UDC state was `attached` or `powered` |
| `0xb24` | failure | `0x8f` | final UDC state was `default` |
| `0xb25` | failure | `0x8f` | final UDC state was `addressed` |
| `0xb26` | failure | `0x8f` | final state was `reconnecting`, `unauthenticated`, or `suspended` |
| `0xb27` | failure | `0x8f` | final state was `not attached`, but clean Phase-B trace evidence was unavailable |

The first warning class wins and is propagated through each later progress
slot. This keeps it in the older A/B slot beside either terminal `0x90`
success or a failure at `0x8f`. Because `0xb01` and `0xb02` are shared by both
phases, the retained warning does not identify its origin phase; the decoder
must report origin as `unknown`, not infer it from the propagated stage.
Terminal success remains zero-detail. A primary failure at `0x8d` or `0x8e`
remains authoritative even when a same-stage setup warning cannot also be
represented.

The descriptor must contain value, name, category, allowed outcomes, allowed
stages, event requirements, and optional canonical UDC state strings. It
generates:

1. runtime constants and classification tables;
2. userspace checkpoint validation;
3. kernel retained-writer validation;
4. host decoder names and categories;
5. linked-audit expectations; and
6. exhaustive plus mutation-test fixtures.

There must be no independent `0xb00..0xbff` maximum, duplicate state map,
handwritten event-name table, or separately maintained PM offset.

## Timeout Classification Priority

At `0x8f`, priority is:

1. any earlier E2 gate regression or read error;
2. exact configured/high-speed success;
3. configured at the wrong speed (`EPROTO`);
4. canonical bus-progress state (`attached`, `powered`, `default`,
   `addressed`, `reconnecting`, `unauthenticated`, or `suspended`);
5. Phase-B-diagnostic-incomplete `not attached` (`0xb27`);
6. nested run-stop failure swallowed by runtime resume;
7. pull-up zero with no run-stop boundary; and
8. run-stop zero with `not attached`.

Cleanup has passed before `0x8e` progress, and any diagnostic warning is
retained separately in the previous A/B slot. Physical UDC bus progress
therefore outranks trace quality. For `not attached`, only clean Phase-B trace
may identify the deepest software boundary; otherwise the result is `0xb27`.
A Phase R-only warning does not discard independently clean Phase-B evidence.

An unknown UDC state string is `EPROTO`, not an invented ordinal. Canonical
strings come from the kernel's `usb_state_string()` vocabulary.

## Observation Window

The 30-second parent deadline starts before the one role-write helper and
replaces the old role loop's maximum five seconds, adding at most 25 seconds.
It covers the synchronous sysfs write, its pending-work flush, and the newly
queued DEVICE worker. Trace setup and quiescent cleanup are separate control
operations; they do not reset the parent deadline or configured deadline.

The future ready manifest must be regenerated only after the exact
implementation emits a versioned timing receipt. The old planning value:

```text
observation.timeout_sec = 240
```

remains provisional and cannot be copied into a manifest by convention.

At least five clean cold executions must run a generic-arm64 build that
compiles the same P2.80 trace-control implementation and exact four-plus-six
event lifecycle as the candidate. Only its target descriptor may substitute
safe generic symbols and actions. It records Phase R setup and cleanup, Phase B
setup and cleanup, and action time separately from guest monotonic timestamps.
The existing one-pair Kprobe mechanism control remains necessary but cannot
qualify this two-phase lifecycle.

These samples prove shared control ordering and provide an implementation
sanity measurement only. They are not an FYG8 wall-time upper bound and are not
scaled into the manifest timeout. Guest boot and host QEMU startup are also
excluded. Every attempt is recorded; a timeout, mechanism failure, or unclean
teardown fails the gate rather than being discarded as an outlier.

The manifest budget instead uses contract maxima plus a separately reviewed
fixed trace allowance:

```text
contract_waits =
  120 pre-E3 + 5 tty + 5 banner + 30 parent + 30 configured = 190
trace_control_allowance =
  15 Phase-R control + 15 Phase-B control = 30
residual_margin = 20
selected_timeout =
  round_up_to_10(contract_waits + trace_control_allowance + residual_margin)
  = 240
guard_cap =
  floor_to_10(300 - max(conservative pre-observation overhead) - 30)
```

The 120-second term is the conservative retained-evidence baseline, not a
measured P2.80 timestamp. Each 15-second trace allowance covers only fixed-count
mount/setup/readback/disable/parse/cleanup work; parent action and configured
waits are already counted and must not be double-counted. The allowance is an
explicit planning bound, not a claim that QEMU proves FYG8 speed. Each clean
generic phase must finish its control-only work within five seconds or the
allowance requires re-review. The separate 20-second residual margin covers
the synchronous configfs UDC bind and other fixed operations without explicit
dwell; it is not reassigned to trace control.

The guard itself does not persist its arm timestamp. Do not invent one. For
each durable sample, derive a conservative pre-observation overhead from
existing evidence:

```text
observation_start =
  candidate_boot_ready timestamp - candidate-observer elapsed_sec
pre_observation_overhead =
  observation_start - live_session_start timestamp
```

`live_session_start` precedes guard arming, so this is at least as conservative
as the unavailable guard-arm-to-observation-start interval. A negative value,
missing event, noncanonical event order, or observer elapsed value outside its
bounded receipt rejects the sample.

The overhead maximum must come from every available durable transaction sample
matching one machine-checked compatibility key:

```text
target-profile SHA
F1 runner execution-closure SHA and runner version
observer source SHA and embedded guard-payload SHA
Odin binary SHA and version
Download identity/profile SHA
private stable host USB-controller/topology identity digest
one regular boot.img.lz4 member
historical boot.img.lz4 size >= current boot.img.lz4 size
```

Any missing or unequal identity field, smaller historical transfer member,
incomplete timeline, or non-successful candidate transfer rejects that sample.
At least one compatible sample is required; absence stops ready-manifest
generation and does not authorize a device run to manufacture timing evidence.
The final 30 seconds is a fixed guard-lifetime reserve for host scheduling,
udev processing, and guard release, not candidate runtime.

The timing receipt binds the compatibility key and accepted/rejected input
receipts, every QEMU attempt and raw phase sample, formula inputs and derived
values, tool identities, shared implementation hash, descriptor hash, and
runtime hash.

Qualification requires `selected_timeout <= guard_cap`. If it does not fit,
the line stops before a ready manifest; it must not silently extend the
300-second udev guard or clip the observation window. Changing that guard is a
separate reviewed observer unit. A versioned data-only ready-manifest builder
must consume and hash-verify the timing receipt, reproduce
`selected_timeout`, and reject a lower, stale, or manually supplied value.
An observer timeout still cannot prove a USB defect; it is a bounded no-proof
if target trace-control work exceeds the reviewed allowance. This later
manifest choice grants no authority by itself.

## Safety and Failure Containment

Dynamic kprobes are a new instrumentation hazard class. They temporarily
modify executable kernel text and route hits through probe handlers. Although
the kernel and vendor module already support this machinery, P2.80 requires
one independent safety review before a final candidate build.

Containment is:

- exact symbol or source-derived instruction site only;
- no handler supplied by the candidate, only tracefs's standard event path;
- at most ten fixed events, two short trace intervals, and bounded buffers;
- one forked helper for one exact pre-existing `peripheral` sysfs write, with
  PID1 retaining the deadline and no retry or exec;
- one isolated trace instance with no global tracer or ring-buffer reset;
- no register modification, fault injection, or mid-function control change;
- no new module, firmware, role producer, direct PHY write, power vote, or
  retry beyond the unchanged driver path;
- each phase is disabled, removed, and verified before normal progress;
- an active-probe deadline parks without potentially blocking unregister and
  records that non-clean state explicitly;
- setup failure before action continues only through the exact clean fallback;
- reboot clears all RAM-only trace state; and
- the permanent boot-only rollback envelope remains unchanged.

The remaining risk is a probe-related kernel fault or timing perturbation.
It must be stated in the later F1 safety review and cannot be dismissed merely
because another vendor kretprobe uses the same address.

## Versioned Implementation Closure

Implementation should add a new P2.80 versioned layer over P2.60, not edit
P2.60 in place:

- `s22plus_fyg8_p280_contract_spec.py`;
- `s22plus_fyg8_p280_source_contract.py`;
- `s22plus_fyg8_p280_e1_decoder.py`;
- one P2.80 native runtime include;
- one P2.80-only progress-warning publisher entry point, while the historical
  zero-detail progress entry point remains byte-identical;
- one runtime-authority descriptor plus exact artifact-safety selector;
- one exact module probe-site extractor/auditor;
- one generic-arm64 Kprobe mechanism control and runner;
- one shared four-plus-six-event generic lifecycle harness;
- one observation-budget calculator and hash-bound timing receipt;
- focused parser, contract, runtime, mutation, and decoder tests; and
- one selector registration.

The source adapter delegates unchanged P2.60 generation and performs bounded,
count-checked transforms. It adds the warning publisher only to P2.80 output;
P2.60 generated output, its zero-detail progress API, and historical decoder
behavior must remain byte-identical. The P2.80 decoder reads both valid A/B
slots and reports a progress warning separately from the active functional
outcome.

### Artifact-safety metadata gate

P2.80 adds runtime authority that P2.60's artifact-safety map does not describe:
an owned tracefs mount lifecycle, writes to the dynamic `kprobe_events`
interface and one isolated instance, and temporary standard Kprobe
instrumentation of exact source-bound sites. Reusing the P2.60 map would repeat
the P2.63 false-authority incident even if every runtime and linked test passed.

One P2.80 runtime-authority descriptor is the source of truth for the new
operations. The source contract verifies the runtime paths and operations
against it; the candidate builder's exact-contract selector renders its safety
fields; and the static checker consumes the builder selector. The selected
P2.80 map must preserve every P2.60 field and add exactly:

```text
userspace_tracefs_mount_scope =
  source-contract-bound-p280-mount-if-absent-owned-unmount-only
userspace_tracefs_global_event_scope =
  source-contract-bound-p280-exact-group-event-register-readback-and-remove
userspace_tracefs_instance_control_scope =
  source-contract-bound-p280-isolated-instance-create-remove-filter-enable-clock-buffer-trace-and-tracing-on
dynamic_kernel_text_instrumentation_scope =
  standard-tracefs-kprobe-events-at-exact-source-bound-sites
no_global_tracer_or_global_buffer_reset = true
```

Dynamic event definitions live in tracefs's global `kprobe_events` namespace;
instance isolation limits enablement and trace-buffer ownership, not event
registration. "Owned" therefore means exact source-bound group and event names
with readback and deletion, not a private kernel namespace.

It must not regain `no_userspace_sysfs_or_configfs_write`, claim no tracefs
write, or imply that a pre-existing tracefs mount is owned. The static checker
must consume the builder selector, not reproduce this map. The P2.80 source
receipt must bind the authority descriptor, selector, and all five exact
values.

Before Full LTO, complete-map fixtures must prove:

1. every P2.80 safety field fails independently when removed or mutated;
2. adding historical `no_usb_or_configfs` or
   `no_userspace_sysfs_or_configfs_write` fails;
3. E1, historical E2, and P2.60 maps remain exactly unchanged;
4. the builder call site still selects safety from the exact contract;
5. an independently fixed complete expected map catches coordinated
   builder/checker drift;
6. adding, removing, or changing a runtime mount, path, control write, event
   registration, or dynamic-probe operation without the matching authority
   descriptor change fails the source contract; and
7. a plausible broadening to a global tracer, arbitrary events, a global
   buffer reset, or unconditional unmount fails.

This is metadata truthfulness, not new device authority. Failure blocks intent
qualification and Full LTO.

The independent amendment review initially returned `NO-GO`: the first draft
understated global event registration, let builder and checker drift together,
and incorrectly scaled generic QEMU time into an FYG8 timeout. A second review
required instance create/remove authority and a machine-checkable historical
sample key. The corrections above separate all authority surfaces, add
runtime-operation mutations and an independent map, limit QEMU timing to a
sanity gate, derive guard overhead from existing durable events, and reject
incompatible samples. Final read-only re-review returned `GO`.

The new exact `0xbXX` whitelist changes the checkpoint validators and therefore
the final kernel image. A qualified P2.80 candidate requires one fresh
Full-LTO A/B build after every pre-LTO gate passes. Full LTO is not part of the
implementation loop.

## Static Validation Gate

Implementation is complete only when H0 validation proves:

1. P2.60 outputs, stage geometry, terminal `0x90`, and 60-module plan are
   unchanged.
2. The exact 60-module undefined-symbol scan independently excludes every
   caller of `dwc_msm_vbus_event` and `dwc_msm_id_event`.
3. The default-peripheral source branch remains excluded by registration
   order and exact DT role-switch topology.
4. Every event target resolves to one exact function body in the expected text
   section, not a suffix, alias, or `.cfi_jt`; it exists in the exact module or
   final `System.map`, is not a `NOKPROBE_SYMBOL`, and the linked image retains
   trace-instance support. Exact arm64 Kprobe source plus target
   prologue/epilogue disassembly must continue to prove that live `x30` is
   replaced before PAC/SCS stores and restored through the trampoline.
5. The two PM post-call sites are derived from exact relocations and
   disassembly; changing either call, order, or following instruction fails.
6. Runtime event strings, parser rules, detail whitelist, decoder, and linked
   audit all derive from one descriptor.
7. Only the listed `0xbXX` values are accepted for only their listed outcomes
   and stages; every reserved neighbor and outcome mutation is rejected.
8. Event registration/readback, clean fail-soft setup fallback, instance
   ownership, `TRACEFS_MAGIC`,
   `trace_clock=counter`, signed `:s32` fetches, filters, buffer bound,
   cleanup, default-maxactive use, and `nmissed` handling are mutation-tested.
9. The parser accepts irrelevant extra events but rejects missing, reordered,
   malformed, duplicate-conflicting, truncated, overflowed, cross-PID, or
   source-impossible required boundaries.
10. Phase B accepts only PID1 events. Phase R requires exact `on=1` and one
    captured `common_pid` through its decisive return.
11. The role-write helper is tested for exact success, errno, short/malformed
    report, pre-entry stall, post-entry stall, one `SIGKILL`, nonblocking reap,
    no retry, and terminal `0xb18` for post-action trace-quality loss.
12. Every quiescent exit performs ordered cleanup before ordinary progress;
    an injected cleanup failure produces `0xb04`. A simulated active-probe
    deadline never calls unregister and produces only its exact deadline
    detail.
13. Earlier E2 regression checks still win at the current frontier.
14. Canonical UDC-state fixtures cover every accepted state and reject unknown
    strings.
15. Phase B fixtures cover direct run-stop, no run-stop, run-stop nested in
    runtime resume, and swallowed nested run-stop failure. Missing synchronous
    returns and impossible propagated returns become `0xb03` only after the
    bind returned and cleanup passed.
16. Progress-warning fixtures prove first-warning propagation through `0x8f`,
    zero-detail terminal success, A/B retention beside success and failure,
    and `0xb27` instead of trace-derived `0xb20..0xb22` when Phase-B quality is
    not clean. A Phase R-only warning must preserve clean Phase-B
    classification. The decoder must report the origin phase of propagated
    `0xb01`/`0xb02` as `unknown`.
17. The exact-contract artifact-safety selector emits the five P2.80 trace
    authority fields from the runtime-authority descriptor, rejects every
    runtime-operation, field, and broadening mutation, and leaves E1,
    historical E2, and P2.60 maps unchanged. Builder and checker use the same
    selector while an independently fixed expected map catches shared drift.
18. At least five clean cold shared-control QEMU samples exercise the shared
    four-plus-six-event control lifecycle and keep each phase's control-only
    work below the five-second sanity threshold. A hash-bound budget receipt
    reproduces the fixed-allowance formula, rejects stale or lowered timeout
    mutations, and proves the selected value fits below the compatible
    300-second guard cap. It must not present QEMU time as an FYG8 upper bound;
    the existing one-pair control alone cannot satisfy this gate.
19. The runtime cross-compiles as static AArch64 and two links are
    byte-identical.
20. The hash-pinned generic-arm64 Kprobe control must pass one ordered PID1
    entry and return with exact signed `:s32` value `-EBADF`, zero missed
    probes, and verified full cleanup under bounded host commands. The
    existing generic-arm64 QEMU E3 path must also remain green. Neither result
    is labeled as S22+ SCS/PAC or Qualcomm USB proof.
21. The kernel patch applies cleanly and the generated exact detail table is
    present in the linked image.
22. A GNU `nm`/`objdump` linked audit passes on the controlled verification
    host; the prohibited high-RSS LLVM substitution is not used.
23. Independent safety review finds no widened device or partition authority
    and confirms the generated safety map describes every bounded runtime
    write and dynamic-instrumentation effect.

Only after all pre-LTO checks pass may one final source-bound Full-LTO A/B,
six-artifact equality, deterministic boot-only packaging, closure audit, and
offline Process v2 promotion begin.

## Result Interpretation

| Result | Supported conclusion |
|---|---|
| `0xb12` | role write remained before DEVICE start, including the pending-work flush |
| `0xb13` | role write returned, but parent DEVICE start was not reached |
| `0xb14` | parent DEVICE start entered and did not return by the absolute deadline |
| `0xb15` / `0xb16` | H11 is directly supported at parent or child runtime PM |
| `0xb18` | Phase R trace loss left asynchronous worker quiescence unproved |
| parent start returns | parent device-start call sites were reached, not electrically proved |
| `0xb20` | pull-up API returned zero through a branch that did not enter run-stop |
| `0xb21` | a nested run-stop failure was swallowed by runtime resume |
| `0xb22` | run-stop returned zero but no host bus state reached the UDC |
| `0xb23..0xb26` | electrical/protocol progress occurred; the final canonical state locates it |
| `0xb27` | E3 did not configure and no clean trace supports a software-boundary claim |
| configured/high-speed | E3 functional success, subject to exact host banner and rollback |

No trace event proves host enumeration by itself. A later F1 still requires
the armed host kernel/udev sidecar and exact ACM banner. If the sidecar is not
durably armed before candidate execution, the F1 must not start.

## Non-Goals

P2.80 does not add or perform:

- `none -> peripheral` retriggering or `soft_connect` retry;
- physical cable replug as a second intervention;
- ADSP remoteproc, PMIC firmware, PMIC GLINK, UCSI, Max77705, or Samsung USB
  notifier expansion;
- `link_state` polling, direct MMIO reads, register writes, or fault injection;
- another gadget function, NCM, ADB, shell, Debian, or supervisor work;
- a new F1 runner, manifest schema, checkpoint stage, or retained field; or
- any device action in this design unit.

## Proof Limits

- Tracefs observes control flow and return values, not analog PHY state.
- A returned parent start proves that its source path reached and returned
  from the listed calls; void helper return does not prove hardware effect.
- A zero run-stop return can still be the runtime-suspended early return.
- Absence is meaningful only with successful probe registration, clean
  profiles, no overflow, and an unambiguous bounded trace.
- `0xb01..0xb03` are diagnostic-quality warnings, not claims about USB target
  execution. The active functional result remains authoritative.
- A Phase R setup fallback proves only clean P2.80 probe ownership plus the
  later primary E3 result. It does not prove parent-worker completion before
  bind; that is the explicitly retained P2.76 ordering limitation.
- A Phase R deadline intentionally leaves possibly active RAM-only probe state
  for reboot rather than claiming verified cleanup.
- `SIGKILL` cannot promptly reap a child blocked in an uninterruptible kernel
  wait; PID1 never treats signal delivery as helper completion.
- The two PM call results identify runtime-PM failure, not necessarily one
  permanent missing supplier.
- This design applies only to the exact FYG8 source, module closure, and
  source-bound candidate.

## Decision

Proceed to P2.80 H0 implementation in small units:

1. descriptor, module-site extractor, parser, and mutation fixtures;
2. versioned runtime/source-contract/decoder integration;
3. static AArch64 and QEMU validation;
4. independent instrumentation safety review; then
5. one final Full-LTO A/B candidate qualification.

No device contact follows from this decision.
