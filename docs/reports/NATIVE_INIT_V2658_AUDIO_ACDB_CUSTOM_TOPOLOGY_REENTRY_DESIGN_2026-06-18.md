# NATIVE_INIT V2658 — ACDB custom-topology reentry design

## Scope

Host-only analysis/design after V2657. No Android boot, native replay,
`/dev/msm_audio_cal` ioctl, mixer write, PCM write, speaker playback, or raw ACDB
payload publication occurred.

This unit answers why the V2656/V2657 real-common custom-topology attempt emitted no
`AUDIO_SET_CALIBRATION` rows, and defines the next capture helper shape.

## Decision

`v2658-phase-aware-common-topology-reentry-design-host-only`

V2657 should not be retried unchanged. The next capture helper must be
**phase-aware**:

1. During `acdb_loader_init_v3()`, keep the pre-init common-topology hook, but
   **short-circuit init's call** and patch the initialized flag so init returns to
   the helper.
2. After init returns, call the real common-topology implementation from a new
   exported helper entrypoint, not by relying on the same exported symbol path that
   init uses.
3. While that real common function runs, treat any nested/preempted
   `acdb_loader_send_common_custom_topology()` entry as an expected dynamic-symbol
   reentry and return success (`0`) instead of the old `-92` sentinel, while logging
   the reentry.
4. Keep the V2630 fake-SET shim active: dump every `AUDIO_SET_CALIBRATION` arg
   byte-exactly and same-process dma-buf payload when present; fake-success all SETs;
   never pass a real kernel SET during capture.

Acceptance for the next live capture remains byte-exact fake-SET records for all
missing custom topology cal types: `10`, `14`, and `24`.

## Evidence

### V2657 reproduced the old `-92` frontier

V2657 reached the intended hook boundary but stopped before SET emission:

- `preinit_stages`: `entered_common_topology_hook`, `before_real_common_topology`,
  `real_common_topology_return`, `patch_initialized_flag_return`,
  `return_to_init_v3_no_arm_no_send`
- `real_common_return_codes`: `[-92]`
- `setcal_record_count`: `0`
- `custom_allocate_cal_types_seen`: `[10, 14, 24]`

That is useful frontier evidence, but not a payload capture.

### `-92` is our wrapper's reentry sentinel

The public source used by V2656/V2657 has an explicit guard in
`libacdb_preinit_no_send_v2608.c`:

```c
if (a90_in_hook)
    return -92;
```

The event `entered_common_topology_hook` is logged after the guard. Therefore a
nested entry can return `-92` without producing a second `entered...` event. V2657's
single visible hook entry plus `real_common_topology_return=-92` is consistent with
that silent reentry path.

### `libacdbloader.so` makes the symbol preemptable

The stock `libacdbloader.so` has an `R_ARM_JUMP_SLOT` relocation for its own default
visibility symbol:

```text
000172e4  R_ARM_JUMP_SLOT  acdb_loader_send_common_custom_topology
```

So calls through that dynamic-symbol path are preemptable by our preload. A helper
that exports the same symbol and then calls the real implementation can still be
re-entered by libacdbloader's PLT path. The current guard treats that as an error and
returns `-92`, which aborts the path before SET rows appear.

### The DB contains the relevant custom cal blocks

The fake-allocation trace from V2657 shows init allocated the custom topology cal
blocks:

| cal_type | meaning | observed as fake allocate |
| --- | --- | --- |
| `10` | ADM custom topology | yes |
| `14` | ASM custom topology | yes |
| `24` | AFE custom topology | yes |
| `39` | CORE custom topology | yes |

This makes the next problem a control-flow/interposition problem, not evidence that
10/14/24 are absent from the ACDB database.

### Contrast with V2581/V2582

The natural init path without the phase-aware real-common call reached a fake-success
`AUDIO_SET_CALIBRATION` for cal_type `39`, `cal_size=4916`, but did not reach the
missing subsystem custom topology records before the helper crashed or timed out.
That proves the fake-SET shim can observe real libacdbloader SET calls, but the
current entry point still does not carry us through 10/14/24.

## Next implementation design

Build a V2659/V2660 helper/preload pair with three explicit phases.

### Phase 1 — init short-circuit

`acdb_loader_send_common_custom_topology()` wrapper behavior during
`acdb_loader_init_v3()`:

- log `init_common_enter`;
- do **not** call real common topology;
- patch `acdb_loader_is_initialized` exactly as V2608/V2656 already does;
- return `0` to init, not `-92`;
- do not arm post-init SET replay yet.

Rationale: V2567 showed init's tail can crash before the helper regains control. The
short-circuit keeps this helper in control long enough to call the real path in a
bounded, observable phase.

### Phase 2 — post-init real common call

Add an exported function, for example:

```c
int32_t a90_run_real_common_topology_after_init(void);
```

The helper calls this after `init_v3` returns. This function:

- resolves the real `acdb_loader_send_common_custom_topology` via `RTLD_NEXT`;
- sets `a90_phase = A90_PHASE_REAL_COMMON`;
- calls the real implementation once;
- logs return code and whether nested reentries occurred;
- exits after capture success or a bounded timeout path.

### Phase 3 — nested reentry neutralization

Wrapper behavior when `a90_phase == A90_PHASE_REAL_COMMON` and a nested
`acdb_loader_send_common_custom_topology()` entry arrives:

- log `common_reentry_neutralized` with pid/tid and a sequence number;
- return `0`, not `-92`;
- do not recursively call the real function.

Rationale: the old `-92` guard is a useful discriminator but now blocks progress.
Returning success for nested reentry lets the outer real implementation continue to
its `AUDIO_SET_CALIBRATION` calls, if that is the only blocker.

### Capture boundary

Keep the V2630 fake-SET boundary unchanged:

- `AUDIO_ALLOCATE_CALIBRATION`: fake success;
- `AUDIO_DEALLOCATE_CALIBRATION`: fake success;
- `AUDIO_SET_CALIBRATION`: dump full ioctl arg bytes; if `cal_size > 0`, read the
  same-process dma-buf payload; fake success;
- all unrelated ioctls pass through;
- any real `AUDIO_SET_CALIBRATION` pass-through is a boundary violation.

## Success and branch table

| Result | Classification | Next action |
| --- | --- | --- |
| SET cal_types `10`, `14`, `24` captured | success | add records to private replay manifest before stream open; rerun native SET replay |
| only SET `39` captured again | partial, not dead retry | direct-lower-function RE for ADM/ASM/AFE custom topology send routines |
| nested reentry logged, no SET rows | informative partial | inspect real-common call graph/return path; do not rerun unchanged |
| no nested reentry, real common returns nonzero before SET | informative partial | map that return site in `libacdbloader.so`; do not assume DB absence |
| helper crashes after dumping any target SET | partial success if raw records are intact | preserve private run; classify based on dumped cal types |

## Hard stops retained

- No native replay in this unit.
- No real kernel `AUDIO_SET_CALIBRATION` during capture.
- No mixer writes, PCM playback, or speaker write.
- Raw payloads remain private only.
- Android handoff/rollback must use the checked helper and return to V2321 with
  `selftest fail=0` for any future live run.

## Validation

Host-only checks performed for this design:

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.
- Compared V2657 report/events against V2570, V2581/V2582, V2567, V2576, and V2577.
- Confirmed the V2608 source contains the `-92` reentry sentinel.
- Confirmed the stock `libacdbloader.so` exposes and has a JUMP_SLOT relocation for
  `acdb_loader_send_common_custom_topology`.
- Confirmed V2657/V2581 fake-allocation traces include custom cal types `10`, `14`,
  and `24` before the failed SET frontier.
