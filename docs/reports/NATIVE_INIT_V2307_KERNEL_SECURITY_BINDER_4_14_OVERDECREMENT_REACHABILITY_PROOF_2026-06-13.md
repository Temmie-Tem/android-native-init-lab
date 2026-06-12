# V2307 Kernel Security Recon: Binder 4.14 over-decrement reachability proof (host-only)

Date: 2026-06-13
Scope: host-only source analysis. No device action, no flash, no devnode, no
ioctl, no `mmap`, no Binder transaction, no trigger. This report answers one
question by reading the local stock 4.14 Binder source: **does the
CVE-2023-20938 / CVE-2023-21255 `binder_transaction_buffer_release`
over-decrement premature-free actually reproduce on this device's kernel tree?**
Baseline: resident rollback checkpoint `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Why this report exists

The Binder Stage-B branch reached a live milestone at V2306: the full *normal*
transaction path is reachable end-to-end on v2237 (uid-1000 context-manager
registration, two-process handle-0 delivery, `BR_TRANSACTION` received). The only
remaining step toward the CVE-class UAF was BB3 (a malformed transaction hitting
the failed-cleanup path). Before any BB3 trigger or any `slub_debug` reflash,
two facts forced a host-only proof first:

1. Public analysis (Android Offensive Security) establishes the bug is a
   `struct binder_node` **refcount-mismatch premature-free** that is **not
   re-accessed within a single transaction** — observing it needs
   free → heap-reclaim → subsequent-use, i.e. exploitation technique, not a
   crash-only one-shot. So a one-shot BB3 (with or without `slub_debug`) cannot
   confirm it.
2. The public CVEs target GKI **5.4 / 5.10**. This device is **4.14**. V2285 only
   proved the July-2023 full-mitigation marker (`binder_release_entire_buffer`)
   is absent — which proves *pre-mitigation*, **not** *exploitable*.

V2307 resolves (2): whether the over-decrement primitive is reachable at all on
this 4.14 tree. It is a free, zero-risk step that can close the track without any
device work.

## External references (bug nature)

- Android Offensive Security, "Attacking Android Binder: Analysis and
  Exploitation of CVE-2023-20938":
  <https://androidoffsec.withgoogle.com/posts/attacking-android-binder-analysis-and-exploitation-of-cve-2023-20938/>
- Carlos Llamas (patch author), "[PATCH v2] binder: fix UAF caused by faulty
  buffer cleanup" (the CVE-2023-21255 full mitigation, commit `1ca1130ec62d`):
  <https://lore.kernel.org/all/20230505203020.4101154-1-cmllamas@google.com/>
- NVD CVE-2023-21255: <https://nvd.nist.gov/vuln/detail/CVE-2023-21255>
- GitHub Advisory GHSA-5852-j2m5-mf5f (CVE-2023-21255):
  <https://github.com/advisories/GHSA-5852-j2m5-mf5f>

Authoritative root cause (both CVEs, one mechanic): commit `44d8047f1d87`
("binder: use standard functions to allocate fds") changed
`binder_transaction_buffer_release()` to **release all objects in the buffer when
`failed_at == 0`**. When a transaction buffer is released on failure with no
objects processed (`failed_at == 0`), that is misinterpreted as "release the
entire buffer," decrementing victim `binder_node` refs that were never
incremented → premature free. CVE-2023-20938 (Feb 2023) was the partial fix;
CVE-2023-21255 (July 2023, `1ca1130ec62d`) is the full fix, which renames
`failed_at` → `off_end_offset` and pre-computes it. The public trigger uses **≥2
`BINDER_TYPE_BINDER` objects** + an **unaligned `offsets_size`** to reach the
`failed_at == 0` failure cleanup. The secondary "buffer not zeroed between
ioctls" phrasing seen in some write-ups is imprecise; the patch author's root
cause is the `failed_at`-zero semantic mismatch above.

## Local 4.14 source facts

Source: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c`.

### 1. The cleanup bound has no fall-through to `full`

`binder_transaction_buffer_release()`:

```c
off_start_offset = ALIGN(buffer->data_size, sizeof(void *));      // :2399
off_end_offset = is_failure ? failed_at :                         // :2400
                off_start_offset + buffer->offsets_size;          // :2401
for (buffer_offset = off_start_offset; buffer_offset < off_end_offset; ...)  // :2402
```

This is `is_failure ? failed_at : full` — **not** the vulnerable
`is_failure && failed_at ? failed_at : full`. When `is_failure == true` the bound
is `failed_at` **even if `failed_at == 0`**. There is no path where a failure
cleanup silently expands to the full object range.

### 2. `failed_at` is always the live acquired-object boundary

The single failure call site passes the live loop cursor as `failed_at`:

```c
err_translate_failed:
err_bad_object_type:
err_bad_offset:
err_bad_parent:
err_copy_data_failed:
	binder_transaction_buffer_release(target_proc, t->buffer,
					  buffer_offset, true);              // :3712
```

`buffer_offset` is **initialized to 0** at function scope:

```c
binder_size_t buffer_offset = 0;        // :3076
```

and is only assigned the loop base immediately before the translation loop:

```c
buffer_offset = off_start_offset;       // :3452
for (buffer_offset = off_start_offset; buffer_offset < off_end_offset;
     buffer_offset += sizeof(binder_size_t)) {                    // :3458
```

### 3. The unaligned-`offsets_size` check fires before the loop, with `buffer_offset == 0`

```c
if (!IS_ALIGNED(tr->offsets_size, sizeof(binder_size_t))) {       // :3431
	... return_error = BR_FAILED_REPLY; ...
	goto err_bad_offset;                                          // -> :3708 -> :3712
}
```

At line 3431 the translation loop (3458) has not run, so `buffer_offset` still
holds its init value `0`. The two pre-loop `copy_user_to_buffer` failures
(`err_copy_data_failed` at :3415 and :3429) and the extra-buffers size check
(:3439) are likewise reached with `buffer_offset == 0`.

## Reachability conclusion

Match the **acquired** set against the **released** set on every single-
transaction failure path:

| Failure point | `buffer_offset` (= `failed_at`) | Objects acquired | Cleanup range `[off_start, failed_at)` | Balance |
| --- | --- | --- | --- | --- |
| unaligned `offsets_size` (:3431) | `0` | 0 (loop not entered) | empty (`x < 0` never true) | balanced |
| pre-loop copy failure (:3415/:3429) | `0` | 0 | empty | balanced |
| in-loop failure at object N (:3481/:3497/:3513/:3529/:3556) | `off_start + N*8` | objects `0..N-1` | objects `0..N-1` | balanced |

The loop increments `buffer_offset` only at the end of each iteration (:3458), so
a failure while processing object N leaves `failed_at` pointing at object N's
offset; cleanup releases exactly objects `0..N-1`, which are exactly the objects
whose refs were acquired by `binder_translate_binder/handle` before the failure.
Acquire and release are also symmetric in type and proc: translation writes the
post-translation object back into the buffer
(`binder_alloc_copy_to_buffer`, :3499/:3515/:3533), and the cleanup re-reads the
same buffer via `binder_get_object` on the same `target_proc`, so the release
decrements the same ref class it acquired.

Therefore:

> **The CVE-2023-20938 over-decrement variant is NOT reachable on this 4.14 tree.**
> The vulnerable `&& failed_at` fall-through is absent (`is_failure ? failed_at`),
> and the `buffer_offset = 0` init at :3076 makes every pre-loop error path clean
> zero objects. No single-transaction failure path decrements a `binder_node`
> ref that was not first incremented.

## Residual (CVE-2023-21255) is the same mechanic, and is also closed

The follow-up CVE-2023-21255 is **not** a separate "buffer not zeroed" mechanic.
Per the patch author (Carlos Llamas), it is the **same `failed_at`-zero
over-release** as CVE-2023-20938 — the Feb-2023 fix was incomplete and the July
fix (`1ca1130ec62d`) fully resolved it. So closing the `failed_at` mechanic on
this tree closes both CVEs. Two independent properties of this tree close it:

**(a) the predicate is `is_failure`, not `failed_at`.** The bug requires
"`failed_at == 0` ⇒ release all." This tree's bound (:2400) is
`is_failure ? failed_at : full` — when `is_failure == true` and `failed_at == 0`
it releases **zero**, not all. The `failed_at`-zero-means-all interpretation is
absent.

**(b) there are exactly two callers, both balanced:**

```c
// failure path
binder_transaction_buffer_release(target_proc, t->buffer, buffer_offset, true);  // :3712
// normal BC_FREE_BUFFER path
binder_transaction_buffer_release(proc, buffer, 0, false);                        // :3995
```

- `:3712` is the only `is_failure == true` caller, and it passes
  `failed_at = buffer_offset` = the live acquired-object boundary (never exceeds
  the acquired set).
- `:3995` is the only caller passing `failed_at == 0`, and it passes
  `is_failure == false`, so the bound is the **full** range — correct, because a
  normally-freed buffer had all its objects acquired.

The dangerous combination the CVEs need — `is_failure == true` **and**
`failed_at == 0` ⇒ release all — is produced by no caller. This tree also carries
both the fd-allocation refactor lineage (`task_fd_install`/`__fd_install`, :2706)
**and** the `is_failure` disambiguation parameter (:2385), i.e. whatever
ambiguity commit `44d8047f1d87` introduced is already resolved here.

No separate async-buffer-reuse or "not zeroed" path reopens it: `binder_get_object`
bounds every read by `buffer->data_size`, and the acquire and release passes read
the same offsets array from a buffer that neither participant can modify between
the two (target maps it `PROT_READ`, sender does not map it), so the released set
always equals the acquired set.

## Correction to V2285

V2285 classified Binder as
`binder-cve-2023-21255-public-fix-marker-absence-confirmed` and ranked it as a
candidate on that basis. V2307 refines: fix-marker absence proves the tree is
*pre-full-mitigation*, but the **over-decrement primitive itself is not present**
in the synchronous cleanup of this 4.14 source. This is consistent with the
project's standing rule that *fix-marker absence ≠ exploitability* (the same
caveat applied to the FastRPC triage). The Binder candidacy is downgraded
accordingly.

## Consequence for the Stage-B-Binder track

- **BB3 one-shot has no over-decrement to hit.** A malformed ≥2-node /
  unaligned-`offsets_size` transaction on this tree takes the balanced
  `failed_at`-bounded cleanup; it does not free a still-referenced
  `binder_node`.
- **`slub_debug` reflash (path C) is moot for this variant** — there is no
  premature free for poisoning to detect, and (per the public analysis) no
  in-transaction re-access even if there were.
- The Binder UAF track is therefore closed at the **host-only-proof boundary**,
  analogous to FastRPC closing at the DSP-channel-down boundary (V2291): the
  candidate is reachable up to the failure-cleanup edge, but the vulnerable
  primitive is absent on this kernel.

## Decision

Classification:

> `binder-cve-2023-20938-and-21255-overdecrement-not-reachable-on-4.14`

Recommended next: **stop the Binder trigger path; the Binder UAF track is
closed.** Both CVEs share the one `failed_at`-zero over-release mechanic, and this
tree provably does not produce the dangerous `is_failure==true && failed_at==0 ⇒
release-all` combination from any caller. The non-destructive, non-exploit
evidence is now complete and consistent:

- normal transaction path reachable end-to-end (V2306);
- July-2023 full-mitigation marker (`binder_release_entire_buffer`) absent
  (V2285) — but neutralized by the earlier `is_failure` disambiguation;
- the over-decrement primitive proven absent for both CVE-2023-20938 and
  CVE-2023-21255 (V2307).

No `slub_debug` reflash and no BB3 trigger is warranted: there is no premature
free to detect. The residual is closed on paper; no remaining Binder unit is
worth chartering.
