# S22+ FYG8 P2.88 generation-88-to-89 corridor and reset reason H0

Date: 2026-07-30 KST

Status:
`PASS_P288_ASYNC_RESET_REJECTED_AND_CORRIDOR_REATTRIBUTED_H0`

Tier: H0

> Current split verdict, 2026-07-31:
> `PASS_P288_ASYNC_RESET_REJECTED_H0`;
> `REFUTED_P288_GEN88_TO_GEN89_CORRIDOR_ATTRIBUTION_H0`. Reset-reason evidence
> remains valid. The missing generation 89 is now fully explained by the
> active-slot `PROGRESS/detail=0xc18` reconstruction mismatch, deterministic
> pre-mutation `-ESTALE`, and `quiet_park()`. The unresolved publisher/gate
> corridor below is superseded. See
> `S22PLUS_FYG8_P284_P290_ACCEPT_TO_RESUME_HISTORY_ERRATUM_H0_2026-07-31.md`.

Correction: the reset-reason result and exact 12-gate materialized count remain
valid. The causal treatment of returned gate failures and the proposed
close-error client-divergence model are superseded by
`S22PLUS_FYG8_P288_NO_SILENT_PARK_AND_LINKED_VALIDATOR_H0_2026-07-30.md`.

## Result

P2.88's live run added no surviving pair-indexed coordinate after generation
88. The intended live localization therefore failed: all 15 new positions
are beyond the opaque generation-88-to-89 corridor.

Post-live H0 nevertheless closes one major alternative. The first retained
firmware stream after the candidate record is the operator's later physical
Download entry, classified by XBL/PMIC as a `PS_HOLD` warm reset. There is no
earlier watchdog, panic, oops, or reset boot between the candidate record and
that operator action. An asynchronous SoC reset during the candidate run is
therefore rejected.

The remaining attribution corridor is wider than the initial source-level
count of one return, one call, and one `clock_gettime`. The first P2.88 marker
wrapper runs the exact candidate's 12-gate sysfs revalidation before it writes
generation 89. The missing generation 89 therefore cannot distinguish:

1. the generation-88 publisher's post-commit return/error tail;
2. the straight-line returns and direct `clock_gettime` syscall;
3. a non-returning syscall in the hidden 12-gate revalidation; or
4. the generation-89 checkpoint publication itself.

An ordinary returned gate failure is not an independent recordless cause:
`p260_revalidate_or_fail()` calls `fail_at()`, which attempts a generation-89
`0x800+index` or `0x900+index` failure. The priority unresolved class is now
publication non-return or primary-plus-fallback publication failure. No
successor F1 should be requested until that no-silent-park gap and the intended
adjacent position placement are both handled.

## Exact retained and reset evidence

The two retained reads are byte-identical:

```text
SHA256 34f5df7414b0c1f992372abe1c68e3d026da92d30e8a636e12ad3403998a4a34
payload size 2,097,136
record start 1,649,792
record size 45
record end 1,649,837
first following XBL marker 1,649,874
gap 37
```

The first following firmware segment says:

```text
XBL: warm reset, valid magic
PM: Reset by PSHOLD
PM: Reset Type: Warm Reset
PM: PS_HOLD warm reset
FAULT2: RESTART_PON
POFF: PS_HOLD
ON: WARM_SEQ
WARM: PS_HOLD
Detect S2 Reset from PM Log
```

That first segment contains no `Watchdog`, `WDOG`, kernel panic, or panic
reason. Later XBL segments correspond to Odin and rollback; they are not
candidate-run reset evidence.

The Process-v2 timeline independently orders the 300-second bounded observer
before physical rollback Download and rollback transfer. The first new
Download endpoint appears only after the observer has closed, and the first
firmware stream after the record is the matching physical `PS_HOLD`/S2 reset.

The earlier raw-ring audit also proved there are zero Samsung kernel timestamp
prefixes after the candidate record and before this firmware stream. A
candidate-time oops would have produced an indexed kernel log, and a watchdog
or panic reboot would have produced an earlier first-next-boot XBL/PMIC reset
segment. Neither exists.

This rejects an asynchronous candidate-time SoC reset, watchdog bite,
panic/oops reboot, or PID1-exit-induced reboot. It does not reject a PID1
userspace hang, raw evidence park, or another non-resetting stall that lasts
until the operator enters Download.

## Position placement is exact but on the wrong side

The P2.88 position sequence is internally correct:

```text
index 87 / generation 88 = (0x8f, item 0)
  inherited_generation_088
index 88 / generation 89 = (0x90, item 0)
  restart_helper_dispatch
```

The runtime's first new symbolic call follows `p282_deadline_after()` inside
`p282_cycle_restart()`. There is no ordinal or pair mismatch. The prior
concern that the pair-aware model might reject an incorrectly numbered first
publication did not occur.

But the symbolic call is not the durable write boundary. Its wrapper is:

```c
next_stage = s22_p288_checkpoint_next_stage(...);
p260_revalidate_or_fail(next_stage);
s22_p288_checkpoint_progress_position(...);
```

`p260_revalidate_or_fail()` runs all 12 bind gates:

- the first 11 gates perform `newfstatat` plus `readlinkat` against sysfs
  driver links; and
- the final UDC gate opens `/sys/class/udc`, loops through `getdents64`, closes
  it, then performs `newfstatat` and `readlinkat` for the exact UDC.

Every syscall is before the generation-89 checkpoint write and has no
userspace-preemptive deadline. P2.88's static source-order gate proves only the
order of the `p288_progress_position()` call sites. It does not prove adjacency
between the preceding operation and the durable checkpoint inside that
wrapper.

But a returned error from any gate routes through `fail_at()` and attempts a
generation-89 failure publication. The gate scan is therefore an attribution
surface only for a non-returning VFS operation or for a subsequent publication
failure. A normal returned mismatch cannot alone explain the retained
generation 88.

Thus the name `restart_helper_dispatch` is aspirational at generation 89: a
surviving record would prove the pre-dispatch revalidation and publication
returned, still before helper dispatch. Its absence does not prove entry into
the helper or even completion of the gate revalidation.

## Exact generation-88 publisher tail

Generation 88 is emitted through:

```text
p282_publish_classification()
  -> p282_progress()
     -> p260_revalidate_or_fail(0x8f)
     -> s22_r4w1e_checkpoint_progress_detail()
        -> p288_publish_next()
```

The kernel writer clears the target CRC, writes the six-byte slot body,
commits and flushes the CRC, verifies the header and committed slot, advances
its in-kernel generation, then returns the request size.

The userspace client then:

1. returns from `sys_write`;
2. calls `sys_close`;
3. validates the write length and close result;
4. advances its own stage/item/generation state; and
5. returns through `p282_progress()`, `p282_publish_classification()`, and
   `p282_cycle_suspend()`.

A CRC-valid retained generation 88 proves the kernel commit, but not every
later item in that return path. Exact common-kernel source rejects the earlier
close-error counterexample: `filp_close()` gets a nonzero return only from
`file_operations.flush`, while the procfs regular operations have no
`.flush`, and this checkpoint proc entry has no custom release.

The kernel writer can instead return `-ESTALE` after committing the target CRC
but before advancing its in-kernel generation. There is no error return after
that state update. In the post-commit-error case the kernel and userspace both
still target the same next generation, so the fallback is not sequence-stale.
If it succeeded, it would replace the target with an unclassified failure.
The retained progress generation 88 proves only that no such fallback
successfully committed.

The concrete limitation of the “publication-dominated park” claim is simpler:
the generic wrapper discards the fallback return and raw-parks even when both
the primary and fallback publications fail.

## Corrected corridor

The exact unresolved corridor is:

```text
kernel generation-88 CRC commit
  -> kernel post-commit verification/state update/sys_write return
  -> userspace sys_close/result checks/local-generation update
  -> p282_progress return
  -> p282_publish_classification return
  -> p282_cycle_suspend return
  -> p282_cycle_restart entry
  -> direct CLOCK_MONOTONIC clock_gettime syscall
  -> first position wrapper entry
  -> 12-gate sysfs revalidation
  -> generation-89 checkpoint open/write/close
```

The direct `clock_gettime` path is a single non-sleeping time read and is a
lower-priority block candidate. A gate syscall that never returns remains
possible, but gate 0 through 10 perform link metadata operations and gate 11
enumerates `/sys/class/udc`; none reads a runtime-PM device attribute. A
returned gate error attempts a classified record. Publication acceptance,
return, and fallback failure are therefore the priority unresolved region.

Consequently the live F1 produced zero new coordinate-level discrimination.
The reset-reason H0 and wrapper expansion, however, reject asynchronous reset
and replace the earlier incomplete two-hypothesis model with the exact
remaining producer corridor.

## Successor placement rule

The next design must enforce:

> The first new subposition follows the last live-proven publication return in
> straight-line code, and its publication path contains no unrelated
> revalidation, cleanup, readback, or trace operation before the checkpoint
> write.

A useful sequence remains:

```text
(0x8f,1) immediately after generation-88 publication returns,
           before p282_cycle_suspend returns
(0x8f,2) immediately after p282_cycle_suspend returns in the caller
(0x8f,3) at p282_cycle_restart entry, before p282_deadline_after
(0x8f,4) immediately after p282_deadline_after returns
(0x90,0) immediately before the helper boundary
```

The adjacent marker should use a versioned direct position publisher without
the inherited `p260_revalidate_or_fail()` preamble. That placement correction
is necessary but not sufficient. The publisher cannot prove its own persistent
failure, and the current unclassified fallback silently discards its error.
Absence of `(0x8f,1)` would therefore still cover both publisher non-return and
primary-plus-fallback failure; presence would reject those earlier paths and
advance the boundary.

The static gate must inspect the full marker wrapper and the code between the
last proven publication and the first new durable write. Counting symbolic
call sites alone is insufficient. It must also distinguish “publication was
attempted” from “a durable publication was confirmed before raw park.”

## Intentional P2.88 behavior change confirmed

P2.88 was not instrumentation-only. Its selected design explicitly removed
both early classification-only trace snapshots:

- the pre-helper refresh and `residual_outer_open` freeze were deleted; and
- the immediate post-helper refresh and
  `restart_worker.entered/returned` enrichment were deleted.

`residual_outer_open` was not moved. Its only purpose was to route helper
timeouts among retired details `0xc57/0xc58/0xc59`. P2.88 replaced those with
the generic `0xc5d/peripheral-helper-timeout`.

A later refresh loop still exists, but only after helper classification,
helper-returned publication, child-active readback, parent-peripheral
readback, and exact-UDC readback. It preserves later cumulative trace
classification and is not the removed immediate snapshot.

The actuation helper itself and its parent-owned timeout/reap behavior remain
the P2.86 implementation. The intentional behavior change was removal and
deferral of diagnostic trace reads, not a change to the PERIPHERAL write.

## Generation-87 semantic rendering correction

The bound P2.88 model and validator correctly accept generation 87 as:

```text
stage 0x8e, item 0, progress, detail 0
```

The bound decoder then rendered detail zero through the failure-detail
taxonomy, yielding `detail_kind=invalid`. That was a presentation error, not
a record-validity or live-verdict error.

The approval-bound P2.88 decoder remains byte-for-byte untouched. A new
post-live-only v2 renderer now maps:

- progress/detail zero to
  `progress-no-diagnostic-detail`; and
- terminal success/detail zero to `terminal-success`.

Nonzero details, the decoded record, active generation, slot validity, and
formal F1 verdict are unchanged. The exact retained P2.88 record now renders
generation 87 as ordinary progress while generation 88 remains
`suspended-power-helper-off-zero`.

## Validation and identity

Focused validation passes:

```text
py_compile: pass
post-live decoder/corridor tests: 5/5 pass
applicable inherited P2.88 contract tests: 19/19 pass
current P2.88 SOURCE_KEYS: 83
frozen P2.88 SOURCE_KEYS: 83
changed source receipts: []
missing source receipts: []
extra source receipts: []
```

The historical
`test_pre_intent_freeze_is_git_derived_and_exact` is intentionally
inapplicable after intent, build, ready-manifest, F1 report, and this H0. It
correctly rejects those later Git paths as outside the old pre-intent declared
window. The frozen declaration must not be expanded to make a historical gate
pass after the fact.

The v2 renderer, its test, this report, and `GOAL.md` are outside the 83
candidate SOURCE_KEYS. P2.88 run ID, intent, Full-LTO pair, ready bundle, and
closed F1 evidence remain immutable.

No device was contacted. No new F1 authority exists.
