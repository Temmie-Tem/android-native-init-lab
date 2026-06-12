# V2308 Kernel Security Recon: KGSL CVE-2023-33107 SVM range-wrap reachability (host-only)

Date: 2026-06-13
Scope: host-only source analysis. No device action, no flash, no devnode, no
ioctl, no `mmap`, no GPU command, no trigger. This report finishes the last open
candidate from V2285 by reading the local stock 4.14 KGSL source: **is the
CVE-2023-33107 SVM `gpuaddr + size` range-wrap primitive present, and is it
reachable, on this device's kernel tree?**
Baseline: resident rollback checkpoint `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Why this report exists

V2291 (FastRPC) and V2307 (Binder) closed the two strongest UAF candidates
non-destructively. KGSL CVE-2023-33107 was ranked #2 in V2285 (fix-marker absent)
but never finished: V2287 found `/dev/kgsl-3d0` open-blocked under native init, so
no live work was done. This report resolves KGSL on paper so the kernel-security
recon phase has no loose ends.

Unlike the other two, KGSL turns out to be the candidate where the vulnerable
**primitive is genuinely present and source-reachable**; it is closed for a
different reason (runtime environment + exploitation-step), not because the bug is
absent.

## External reference

- Project Zero "0-days in the wild" RCA, CVE-2023-33107 (KGSL `kgsl_iommu_set_svm_region`
  SVM range wrap): <https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2023/CVE-2023-33107.html>

Public root cause: in the SVM range/overlap check, `gpuaddr + size` can overflow
(wrap past `U64_MAX`), so an out-of-range/wrapping region is accepted as
"in SVM range." The public fix computes `end = gpuaddr + size` and rejects
`end <= gpuaddr` (wrap) in `iommu_addr_in_svm_ranges()`.

## Finding 1 — the wrap primitive is present (fix-marker absent)

`drivers/gpu/msm/kgsl_iommu.c`:

```c
static bool iommu_addr_in_svm_ranges(struct kgsl_iommu_pt *pt,
	u64 gpuaddr, u64 size)
{
	if ((gpuaddr >= pt->compat_va_start && gpuaddr < pt->compat_va_end) &&
		((gpuaddr + size) > pt->compat_va_start &&        // :2584  unguarded add
			(gpuaddr + size) <= pt->compat_va_end))       // :2585
		return true;
	if ((gpuaddr >= pt->svm_start && gpuaddr < pt->svm_end) &&
		((gpuaddr + size) > pt->svm_start &&              // :2589  unguarded add
			(gpuaddr + size) <= pt->svm_end))             // :2590
		return true;
	return false;
}
```

There is **no** `end = gpuaddr + size; if (end <= gpuaddr) return false;` wrap
guard — the public fix marker is absent. The downstream overlap walk in
`kgsl_iommu_set_svm_region()` repeats the unguarded add:

```c
if (gpuaddr  + size <= start)        // :2618  unguarded add
	node = node->rb_left;
else if (end <= gpuaddr)             // :2620  (this 'end' is the rbtree node end, not a wrap guard)
	node = node->rb_right;
...
ret = _insert_gpuaddr(pagetable, gpuaddr, size);   // :2626
```

So the wrap primitive is present: a `gpuaddr` inside an SVM range plus a `size`
large enough to wrap `gpuaddr + size` back below `svm_end` passes the range check,
and the region can be inserted. **Primitive: present** (contrast Binder V2307,
where the primitive was absent).

## Finding 2 — source-reachable via the explicit-useraddr map path

Two callers reach `set_svm_region`:

- **mmap / get_unmapped_area path** (`_gpu_set_svm_region`, kgsl.c:4633): `addr`
  comes from `_cpu_get_unmapped_area` → `vm_unmapped_area` (kernel-chosen CPU VA,
  `< TASK_SIZE`) and `len` is bounded by the search window. `addr + len` cannot
  reach a `U64_MAX` wrap. **This path cannot trigger the wrap.**
- **explicit user-address path** (`kgsl_setup_anon_useraddr`, kgsl.c:2504, from
  `IOCTL_KGSL_MAP_USER_MEM`):

  ```c
  if (size == 0 || offset != 0 || !IS_ALIGNED(size, PAGE_SIZE))   // :2512  only these checks
      return -EINVAL;
  ...
  ret = kgsl_mmu_set_svm_region(pagetable,
      (uint64_t) hostptr, (uint64_t) size);                       // :2523  user hostptr + user size
  ```

  `hostptr` and `size` are user-supplied; the only guard is `size != 0`,
  `offset == 0`, and page-alignment of `size`. There is **no `hostptr + size`
  overflow guard** before `set_svm_region`, and the wrap check inside
  `iommu_addr_in_svm_ranges` is the one that is missing. This is exactly the
  pre-fix shape the public CVE describes.

So in source the wrap is **reachable** via `IOCTL_KGSL_MAP_USER_MEM` with a
crafted `hostptr`/`size`. (A fully rigorous reachability proof would also trace
`hostptr` canonicalization in the ioctl entry; the missing wrap guard plus
user-controlled inputs and the absent fix marker place this at "present and
source-reachable, pre-fix.")

## Finding 3 — why KGSL is nonetheless closed here

Two independent blockers stop this from being a non-destructive result on this
device, both outside the justified scope:

1. **Runtime device-open is blocked under native init (V2287).**
   `open("/dev/kgsl-3d0", O_RDONLY)` did not return and required a serial cancel —
   `devnode-materialized-open-blocked`. The wrap is only reachable through the
   explicit-useraddr ioctl, which requires a working KGSL fd; native init does not
   bring the GPU/KGSL subsystem to a state where open completes. Reaching the
   ioctl would itself be a separate, unsolved bring-up problem.
2. **Observation requires GPU-side follow-up.** A wrapped/oversized SVM insertion
   produces a bad IOMMU mapping in the rbtree/pagetable; turning that into a
   crash or kernel R/W needs subsequent GPU activity (command submission against
   the bad mapping) or reclaim — i.e. exploitation technique, not a crash-only
   one-shot. Same diagnostic wall as the other candidates (KASAN off, no one-shot
   signal).

## Verdict

> `kgsl-cve-2023-33107-primitive-present-source-reachable-but-runtime-open-blocked-and-exploit-dev-gated`

KGSL is the strongest of the three candidates on paper: the SVM range-wrap
primitive is present (fix marker absent, unguarded `gpuaddr + size`) and is
source-reachable via `IOCTL_KGSL_MAP_USER_MEM`. It is closed not because the bug
is absent (it is not), but because:

- the only wrap-capable path needs a KGSL fd that native init cannot open (V2287);
- confirming/using the wrap needs GPU-side follow-up = exploit development;
- the device is EOL, so the value does not justify solving the open-block and
  crossing into exploitation.

This is an honest "present but environment-gated and exploit-dev-gated" outcome,
distinct from Binder (`primitive absent`, V2307) and FastRPC
(`channel-down`, V2291).

## Phase consequence

All three triaged candidates are now resolved host-only, without ever triggering
memory corruption:

| Candidate | Primitive | Reachability | Closure reason |
| --- | --- | --- | --- |
| FastRPC CVE-2024-43047 | present (fix-marker absent) | DSP rpmsg channel down under native init (V2291) | unreachable |
| Binder CVE-2023-20938/21255 | **absent** (`is_failure`-keyed, balanced callers) (V2307) | reachable end-to-end (V2306) | not vulnerable |
| KGSL CVE-2023-33107 | present (fix-marker absent) | source-reachable via MAP_USER_MEM, but `/dev/kgsl-3d0` open-blocked under native init (V2287, V2308) | runtime-blocked + exploit-dev-gated |

The recon charter question — "is EL1 realistically attemptable via n-day from this
environment, within non-destructive scope?" — is answered **no** for all three
top candidates, each for a concrete, source-grounded reason.

## Decision

> Close the kernel-security recon phase.

No remaining candidate is both reachable from native init and confirmable
non-destructively. Any continuation would require either solving the KGSL
device-open under native init **and** crossing into GPU-side exploit development,
or chartering a different environment (full Android userspace) — neither
justified by an EOL device. Recommended: commit the open reports
(V2305/V2306/V2307/V2308) and write a phase-closing checkpoint consolidating the
three triage outcomes and the reusable reachability/tooling knowledge.
