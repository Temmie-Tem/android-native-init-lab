# S22+ FYG8 retention discriminator feedback reassessment

Date: 2026-07-22 KST
Scope: H0 host-only report, source, checker, Git-history, and retained-artifact
review
Status: documentation correction and design decision; no build, device access,
candidate generation, or live authority

## Verdict

The feedback has the right strategic conclusion: do not spend another F1 run
on a carrier whose all-zero result still merges candidate nonselection,
eligibility refusal, and later retention loss. Its proposed chronology and
73-byte window model are not correct for the current repository, however, and
two proposed remedies would weaken the safety model.

No Process v2 or candidate code change follows from this reassessment. The next
unit remains H0 discriminator design.

## Point-by-point disposition

| Feedback item | Disposition | Repository-backed reason |
|---|---|---|
| E0 remained host-only and was never flashed | `REJECTED_STALE` | E0 later completed exactly one candidate transfer and one rollback transfer; two complete retained reads contained zero E0 carrier bytes and final health passed. |
| Add a heartbeat before every guard | `PARTIAL` | Separating reachability from later progress is useful, but a physical write before target/layout/magic validation is unsafe and absence on the same channel remains ambiguous. |
| Force saturation with `printk` padding | `REJECTED` | The native candidate does not load `sec_log_buf.ko`; ordinary `printk` therefore does not deterministically advance this Samsung retained ring. Loading the owner creates the live writer that the frozen-cursor design excludes. |
| Use an unqualified fixed reserved offset | `REJECTED` | The inspected 2 MiB range is a Samsung circular log, not proven owned scratch. Its stock snapshot visibility is cursor-dependent. |
| Add a `<=73` static window-fit gate | `REJECTED_WRONG_MODEL` | R4W1-B's 73 bytes were the first fragment of a 99-byte boundary-crossing append. D/E/E0 use non-wrapping pre-cursor placement, and E already checks 173-byte fit and observer truncation. |
| Reconstruct exact geometry host-only | `ACCEPTED_COMPLETED` | The reconstruction below rules out the proposed monotonic 73-byte-window explanation without contacting the device. |
| Use two short non-overwriting tokens | `DEFERRED` | This can encode two states only after entry eligibility is independently proven. It creates new geometry and does not fix an all-zero result caused before either token. |
| Include an Image-derived nonce | `PARTIAL` | It strengthens positive identity, as the existing candidate-bound IDs already do, but cannot identify which branch produced an absent token. |
| Require a three-way discriminator before another F1 | `ACCEPTED` | This matches `GOAL.md` P2.17 and the existing gap analysis. |

## Live chronology correction

The complete current sequence is:

1. R4W1-E E1 used a 173-byte entry-plus-A/B-slot carrier. Process v2
   transferred the exact candidate once and the exact rollback once. Both
   retained reads were complete and byte-identical, but entry-family and slot-
   magic counts were zero. Verdict:
   `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.
2. R4W1-E0 was then designed and built host-only with the D-sized 45-byte slot.
   That was an intermediate state, not its final disposition.
3. E0 subsequently passed D0 preparation and completed its own exact candidate
   and rollback transfers. Its two complete byte-identical retained reads had
   zero ENTRY, USERSPACE, and family bytes. Verdict:
   `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

Git history records the E0 live close in `4e7d565a`. The authoritative result is
`S22PLUS_FYG8_R4W1E0_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`. A statement
that E0 is still draft-host-only describes the repository before that close.

## Geometry reconstruction

The Samsung region is `0x200000` bytes including a 16-byte header, leaving a
payload of `0x1ffff0` bytes (2,097,136 bytes).

R4W1-B appended a 99-byte record at the cursor and advanced the index. The live
snapshot contained the first 73 bytes followed by later boot text instead of
the final 26 bytes. That observation reconstructs the crossing case as:

```text
cursor = payload_size - 73 = 0x1fffa7
first fragment = 73 bytes
wrapped fragment = 99 - 73 = 26 bytes
```

This is a circular-write boundary result. It does not imply that only the final
73 bytes of the 2,097,136-byte snapshot survive.

The successor layouts do not append across that boundary:

```text
if cursor >= region_size:
    position = cursor - region_size
else:
    position = payload_size - region_size
write payload[position:position + region_size]
do not publish a new index
```

At the illustrative B cursor, the resulting physical intervals are:

| Carrier | Size | Interval | Wraps |
|---|---:|---|---|
| D | 45 | `[0x1fff7a, 0x1fffa7)` | no |
| E | 173 | `[0x1ffefa, 0x1fffa7)` | no |
| E0 | 45 | `[0x1fff7a, 0x1fffa7)` | no |

The exact candidate-time cursor was not captured for E or E0. That missing fact
does not change the static non-wrapping property: both branches of the placement
formula select one contiguous physical interval.

The completed private retained reads were also rescanned without modification:

| Candidate read | `ScmArmV8ExitBootServicesHandler` | Following evidence | Next `PM: Driver Init` |
|---|---:|---:|---:|
| D | 1,650,052 | `[[S22P1D` at 1,650,110 | 1,650,154 |
| E E1 | 1,636,595 | intact `Exit EBS` at 1,636,663 | 1,636,697 |
| E0 | 1,652,478 | intact `Exit EBS` at 1,652,546 | 1,652,580 |

These are offsets in the exported, rotated snapshot, not physical ring cursor
values. They reproduce the published D-versus-E0 differential and weaken a
random partial-overwrite explanation, but they cannot bind the candidate Image
or reveal the candidate-time header/index gate.

The E host checker and kernel patch already enforce the relevant fit contract:

- `REGION_SIZE = 45 + 64 * 2 = 173`;
- reject `REGION_SIZE > payload_size` in the host model;
- reject `sizeof(*region) > payload_size` in the kernel;
- place exactly one contiguous pre-cursor region; and
- reject a decoded observer region that runs past the captured payload.

A second generic Process v2 `<=73` check would duplicate the wrong abstraction
at the wrong layer. Geometry belongs to the candidate-specific static contract;
Process v2 binds and transports the artifact and validates its declared typed
observer.

## Heartbeat and saturation analysis

The diagnostic objective behind a heartbeat is sound: preserve evidence that
the post-exec call site was reached even if a later proof condition fails. The
proposed "before every guard" placement is not acceptable.

The current guards have different roles:

- exact init path and PID 1 bind the semantic event;
- target, physical layout, and magic prevent writes into an unknown structure;
- saturation is an inherited visibility precondition; and
- unchanged header values protect the frozen-cursor update.

The path/PID, target/layout, and magic checks cannot be bypassed merely to gain
telemetry. A same-ring heartbeat written after them but before saturation could
help distinguish a saturation refusal only if unsaturated stock snapshot
behavior and its placement are first proven. It would still not distinguish
candidate nonselection from bad magic, and its absence would not prove that the
call site was not reached.

`printk` padding does not remove this problem. `sec_log_buf.ko` is the owner that
registers the vendor log hook and publishes `/proc/last_kmsg`; it is deliberately
not loaded in checkpoint-bearing native candidates. Loading it or directly
advancing the two-megabyte ring would introduce a writer, mutate shared
metadata, overwrite prior evidence, and invalidate the current no-index-
mutation contract. A fixed offset in the same ring is likewise not an
independent carrier.

## Requirements for the next H0 design

A useful discriminator must satisfy all of these conditions before candidate
construction:

1. preserve exact target, layout, and magic validation before any physical
   retained-memory write;
2. bind any positive record to the exact candidate identity;
3. report enough state to separate at least saturation refusal from a completed
   ENTRY store, without calling a same-channel zero result independent proof;
4. model stock snapshot visibility for both saturated and unsaturated indices;
5. keep the carrier contiguous and candidate-specific geometry checks outside
   the generic Process v2 transport core;
6. avoid loading `sec_log_buf.ko`, changing the retained index, padding the full
   ring, or claiming ownership of an unproved fixed offset; and
7. keep F1 inactive until the changed execution-critical closure receives its
   required independent review.

An actually independent candidate-selection witness would be stronger than any
same-ring reason code. Until such a channel is found, an all-zero retained read
must remain explicitly ambiguous.

## Evidence used

- `GOAL.md`
- `docs/reports/S22PLUS_FYG8_R4W1B_LIVE_NO_PROOF_MAGISK_RECOVERY_PASS_2026-07-19.md`
- `docs/reports/S22PLUS_FYG8_R4W1D_CONTIGUOUS_PROOF_HOST_DESIGN_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_R4W1E_E1_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_R4W1E0_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`
- `workspace/public/src/patches/s22plus_fyg8_r4w1b_direct_pid1_witness.patch`
- `workspace/public/src/patches/s22plus_fyg8_r4w1d_compact_pid1_witness.patch`
- `workspace/public/src/patches/s22plus_fyg8_r4w1e_runtime_checkpoint.patch`
- `workspace/public/src/patches/s22plus_fyg8_r4w1e0_pid1_userspace_proof.patch`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1d_witness_contract.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1e_checkpoint_contract.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1e0_pid1_userspace_proof.py`

## Boundary

This reassessment used only local tracked sources, Git history, reports, and
private retained artifacts already collected by completed runs. It performed no
build, image operation, connected read, reboot, flash, or device action. It does
not authorize a new F1 run.
