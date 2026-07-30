# S22+ FYG8 P2.86 early-restart trace load-bearing audit H0

Date: 2026-07-30 KST

Status:
`PASS_P286_EARLY_RESTART_TRACE_CLASSIFICATION_ONLY_H0`

## Verdict

The two trace snapshots surrounding P2.86's PERIPHERAL helper are not
load-bearing for dispatch, the write deadline, or the successful restart
path. They exist only to refine a bounded helper timeout into trace-derived
subclasses.

The pre-dispatch snapshot freezes one value:

```text
residual_outer_open = cycle->observed.outer_open
```

That value is consumed only inside the helper classifier's `timed_out` branch
to prefer `residual-outer-tail-timeout`. The immediate post-helper snapshot
supplies `restart_worker.entered/returned`, which are also consumed only in
that timeout branch to distinguish `start-peripheral-no-return` from
`peripheral-flush-timeout`.

Neither snapshot changes whether `p286_run_cycle_role_helper()` is called.
For a non-timeout result, none of those three trace fields affects the helper
classification. The final cycle capture later reads and parses the cumulative
trace again, so the immediate post-helper snapshot is not needed to preserve
successful-path trace evidence.

The cheapest successor order is therefore:

```text
exact parent suspended; publish 0x8f
run bounded PERIPHERAL helper immediately
classify parent-owned helper fields without a trace read
  failure -> publish exact stage-0x90 failure before trace cleanup
  success -> continue without either early snapshot
perform any later trace enrichment only outside this failure-publication path
```

This removes both early unbounded tracefs syscalls rather than marking them.
It needs no retained-slot expansion. A successor must use an honest generic
PERIPHERAL-helper-timeout detail instead of calling a no-trace timeout a
`flush-timeout`; preserving the P2.86 `c57/c58/c59` subtype split is not worth
placing an unbounded trace read before durable failure evidence.

This is a paper design result only. It changes no P2.86 source, selects no
P2.88 implementation, and grants no device authority.

## Frozen state

The audit began from clean HEAD
`b20ef54315bd33f88ce4672d6c0a43d3af967b99`. The exact P2.86 current and
intent source receipts remain:

```text
CURRENT_SOURCE_KEYS 70
INTENT_SOURCE_KEYS 70
CHANGED_KEYS []
```

The load-bearing sources are:

- `workspace/public/src/native-init/s22plus_fyg8_p286_e3_runtime.inc.c`,
  SHA256
  `5b113ba31b162230656fd405c9ca060f54e3d9f7534db033abd51dc4dcd6ed16`;
- `workspace/public/src/native-init/s22plus_fyg8_p286_classifier.inc.c`,
  SHA256
  `14b82ca22e307708cc412b29fa2b7e4784dc791348298c376ab3d8bc4d66d09e`;
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contract.py`;
  and
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_contract_spec.py`.

No payload, verifier, decoder, packager, manifest, or private evidence byte
was changed.

## Parent-suspended correction is already current

`GOAL.md` and the corrected F1 report already record the stronger P2.86
meaning of `0x8f/detail=0xc18`.

The runtime order is:

```text
p282_wait_exact_value(parent runtime_status, suspended)
p286_classify_parent_status()
failure -> p282_cycle_abort()
success -> p282_publish_classification(stage 0x8f)
```

The exact source is
`s22plus_fyg8_p286_e3_runtime.inc.c:2697-2724`. Therefore this P2.86 tuple,
unlike the byte-identical P2.84 tuple, proves the exact parent-suspended
readback. It remains non-proof of outer-work return or electrical rail
collapse.

## Pre-dispatch snapshot data flow

The restart function currently executes:

```text
:2757-2759  p282_cycle_refresh(RESTART)
:2760       residual_outer_open = cycle->observed.outer_open
:2762-2766  p286_run_cycle_role_helper(PERIPHERAL_WRITE)
```

Between the first refresh and helper dispatch, the only
`cycle->observed.*` read is `cycle->observed.outer_open`. The local
`residual_outer_open` has exactly two uses in the function: its initialization
and its later assignment to `helper.outer_open`.

`p286_classify_helper()` reads `observation->outer_open` exactly once, at
`s22plus_fyg8_p286_classifier.inc.c:81`, under:

```text
if (observation->timed_out) {
    if (observation->outer_open)
        residual-outer-tail-timeout;
    ...
}
```

It is ignored for dispatch failure, unreaped child, malformed completion,
write error, successful completion, and every non-timeout result.

The refresh itself returns zero even when snapshot read or parse fails; it
only records a trace-incomplete warning and drops trace authority
(`runtime:2478-2493`). It cannot veto helper dispatch except by blocking
inside the tracefs syscall. Thus its only intended contribution is diagnostic
classification, while its failure mode can prevent the operation it is trying
to diagnose.

The exact P2.86 source contract confirms that intent. It names the token
`pre-dispatch-residual-outer-snapshot` and requires:

```text
pre-dispatch refresh < residual_outer_open freeze < helper dispatch
```

at `s22plus_fyg8_p286_source_contract.py:297-314`.

## Immediate post-helper snapshot data flow

The current second snapshot is:

```text
:2770-2772  p282_cycle_refresh(RESTART)
:2773       helper.start_entered = observed.restart_worker.entered
:2774       helper.start_returned = observed.restart_worker.returned
:2777-2789  classify and publish helper failure
```

Those two `cycle->observed` fields are its only immediate consumers.
`start_entered/start_returned` are read only in the classifier's timeout
branch. When the parent-owned helper fields show success, the classifier
ignores them and returns zero.

Intermediate snapshot reads do not consume or clear the trace:

- the trace is cleared once during setup at `runtime:667`;
- `p282_trace_read_snapshot()` only reads the instance's `trace` file
  (`:1063-1079`);
- `p286_cycle_capture()` later disables tracing, reads the full snapshot and
  profile, and reparses the cumulative result (`:2496-2518`).

Consequently successful-path trace evidence does not depend on the immediate
post-helper read. It can be omitted from this corridor without erasing later
restart-worker, resume, PHY-init, power-on, or notify-connect records.

## Minimum successor ordering

The bounded helper already returns all fields needed for a trace-independent
first classification:

- `dispatched`;
- `record_complete`;
- `write_completed`;
- `timed_out`;
- `unreaped`;
- `malformed`; and
- `result`.

The correct minimum transformation is not to add a second post-helper
snapshot. It is:

1. delete the pre-dispatch refresh and `residual_outer_open` freeze;
2. run the existing bounded helper immediately after the parent gate;
3. classify the parent-owned fields immediately;
4. on any failure, publish through the existing publish-before-cleanup abort
   path before any trace operation; and
5. on success, omit the current immediate post-helper refresh because final
   capture can reconstruct the cumulative trace.

The existing classifier mechanically maps a timeout with all trace-enrichment
fields zero to `0xc57`. A successor must not retain the misleading
`peripheral-flush-timeout` name for that no-trace observation. Use one
versioned generic timeout semantic, such as `peripheral-helper-timeout`, and
retire the early live routing to the more specific `c58/c59` classes.

This preserves the 45-byte record layout, stage sequence, generation count,
and two-slot commit protocol. It changes candidate semantics and therefore
still requires a fresh versioned contract and intent; it is not an in-place
P2.86 edit.

## Slot expansion decision

The condition for evaluating a 2-to-6/8 in-place slot expansion is not met.
The two proposed early markers become unnecessary because both early
unbounded operations can be removed from the critical corridor.

No raw-ring headroom calculation is performed in this bounded unit. The
append design remains rejected, and the in-place expansion remains an
unselected fallback only if a future source-complete design proves an
unbounded operation cannot be removed, reordered, or isolated.

## Remaining limits

This result closes the cheapest design question, not the entire restart
evidence problem.

- `p282_wait_exact_value()` still performs a blocking sysfs read before its
  userspace deadline check.
- The later restart-worker polling refresh and final capture are still
  unbounded tracefs operations.
- A successful helper has no durable success marker before those later
  operations.

Those later boundaries should first be removed from the decisive path or run
behind a bounded parent/child isolation boundary. Slot or stage expansion
should be considered only after those cheaper structural options are proven
insufficient.

## Host validation

Focused H0 validation established:

- current/frozen source receipts `70/70`, changed keys `[]`;
- exact parent gate before the P2.86 `0x8f` publication;
- one and only one pre-helper observed-field consumer: `outer_open`;
- exactly one classifier consumer of `outer_open`, under `timed_out`;
- only `restart_worker.entered/returned` consumed after the second refresh;
- trace clear occurs at setup, not during snapshot reads;
- final capture reads and parses the cumulative trace again; and
- the existing AArch64 classifier fault-partition test passes under QEMU.

No D0, D1, F1, candidate/kernel build, image mutation, transfer, reboot, or
live action was performed. The only compilation was the existing focused
AArch64 classifier test in a temporary directory.
