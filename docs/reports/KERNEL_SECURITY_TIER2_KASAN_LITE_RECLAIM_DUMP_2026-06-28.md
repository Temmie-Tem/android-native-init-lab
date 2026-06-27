# Kernel Security Tier-2 KASAN-Lite Reclaim Dump

- Cycle: `TIER2_KASAN_LITE_RECLAIM_DUMP`
- Date: `2026-06-28`
- Decision: `tier2-kasan-lite-reclaim-dump-live-pass`
- Scope: PROCA/FIVE `task_integrity` UAF use-site raw-object dump, RECON only

## Build / execution split

The candidate image was built + statically validated host-only by the Codex rescue
subagent; its sandbox cannot reach the USB serial bridge (`a90ctl: Operation not
permitted`, no serial candidates), so the **live device half was executed by the
operator** on real hardware. Classification of the captured dumps was then done
host-only. This split is the working pattern for device-bound work: companion/sandbox
runners do build/RE/validation, the operator drives the bridge.

## Result

PASS (live). The Gate-2-verified KASAN-lite direct-`printk` hook executed under
RKP_CFP and produced the intended use-site raw-object dump with no fault.

- Flashed the candidate (`63f44378…`) via `native_init_flash.py --from-native`;
  booted `0.9.285 (v2321-...)`, `selftest pass=11 warn=1 fail=0`.
- `panic_on_oops` set to `0`; ran `a90_five_uaf_probe` (ping-pong-execve victim +
  `/proc/<vpid>/integrity/reset_file` reader) twice (`--secs 2 --max-reads 250` each),
  `RESULT reader_exited code=0` both times — **no fault** (the patched handler dumps
  raw words and returns `0`, never dereferencing `reset_file`/`d_path`).
- Captured `1500` `A90KAL` kernel-log lines (`500` reset_file reads × 3 lines).
- `panic_on_oops` restored to `1`; rolled back to clean `v2321` (boot-block readback
  `ca978551…`), final `selftest pass=11 warn=1 fail=0`. Device left clean on `v2321`.

Private capture (gitignored, raw kernel pointers — not committed):
`workspace/private/runs/security/kasan-lite-reclaim-20260628/`.

## Rollback Gate Evidence

Pinned rollback/fallback inputs were present and matched the documented hashes:

- v2321 rollback:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- v2237 deeper fallback:
  `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- v48 final fallback:
  `workspace/private/inputs/boot_images/boot_linux_v48.img`
  SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- TWRP recovery image:
  `workspace/private/inputs/firmware/twrp/recovery.img`
  SHA256 `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`

## Built Candidate

- Builder:
  `workspace/public/src/scripts/revalidation/build_kernel_tier2_kasan_lite_reclaim_dump.py`
- Base boot: clean v2321
- Candidate boot:
  `workspace/private/inputs/boot_images/boot_linux_tier2_kasan_lite_reclaim_dump.img`
- Candidate SHA256:
  `63f44378a054220c1a00ba37dbaaa5eb16027cc1b96b4051f4dde36bce5e224b`
- Candidate mode: `0600`
- Boot header id: `fc720dd47d8a33ca192d70d318dd79fba6c63be6`
- Diff contract: `191` changed bytes, limited to the boot header id and the
  `proc_integrity_reset_file` replacement body.

## Hook Details

- Real patched target, located by instruction signature:
  `proc_integrity_reset_file`
- RKP magic offset: kernel-file `0x2ab0fc`
- Entry offset: kernel-file `0x2ab100`,
  vaddr `0xffffff800832b0ec`
- Next RKP magic offset: kernel-file `0x2ab1bc`
- Patch room / payload length: `188 / 188` bytes
- Original handler evidence:
  - `task->integrity` load: `[x3, #0xb40]`
  - `reset_file` load: `[task_integrity, #0x58]`
  - original `d_path` callsite: `0xffffff800832b140 -> 0xffffff80082b0734`
- Direct `bl` target: plain `printk(fmt, ...)` wrapper at kernel-file
  `0xbd8e0`, vaddr `0xffffff800813d8cc`

The replacement body preserves `x17`, uses a ROPP-shaped prologue/epilogue, has
no `blr`, and avoids vararg stack spilling. It emits three lines per
`/proc/<pid>/integrity/reset_file` read:

```text
A90KAL%d %llx %llx %llx %llx %llx
```

The first `%llx` is the `task_integrity *`; the remaining four values are raw
64-bit words from offsets:

- `A90KAL0`: `0x00`, `0x08`, `0x10`, `0x18`
- `A90KAL1`: `0x20`, `0x28`, `0x30`, `0x38`
- `A90KAL2`: `0x40`, `0x48`, `0x50`, `0x58`

This covers `usage_count` (`0x08`), `label` (`0x18`), `reset_cause` (`0x50`),
and `reset_file` (`0x58`). It intentionally does not dereference `label` or
`reset_file`.

## Static Validation

Passed:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile
  workspace/public/src/scripts/revalidation/build_kernel_tier2_kasan_lite_reclaim_dump.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3
  tests/test_kernel_tier2_kasan_lite_reclaim_dump.py` (`2` tests)
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3
  tests/test_kernel_tier2_stage_c_direct_bl_printk.py` (`4` tests)
- `git diff --check` on the new builder/test
- Disassembly confirmed the patched body loads `[x3,#2880]`, dumps qwords
  `0x00..0x58`, calls `0xffffff800813d8cc` directly, restores the ROPP return
  path, returns `0`, and leaves the following RKP magic intact.

The pycache prefix was required because
`workspace/public/src/scripts/revalidation/__pycache__` is owned by
`nobody:nogroup` in this environment.

## A90KAL Captures

`1500` lines = `500` reset_file reads × 3 lines (`A90KAL0/1/2` = struct words at
`0x00..0x58`). Raw kernel pointers redacted below (masked `ffffffc1_xxxxxxxx`).
Two representative reads:

```text
A90KAL0 <ti>  00000000_00000000  0188_0188_00000001  0000_0000_00a800a8  0   ; uv=0 val=0 usage=1 lock label=0
A90KAL1 <ti>  0 0 0 0                                                          ; events.* empty
A90KAL2 <ti>  <ti+0x40> <ti+0x40>  4  <valid file*>                           ; list self-ref, reset_cause=NO_CERT, reset_file=valid
--- and the 6.2% PROCESSING variant ---
A90KAL0 <ti>  00000000_ffffffff  ...._00000002  ...  0                        ; user_value=INTEGRITY_PROCESSING, usage=2
```

Decoded field map (4.14 packed enums): `0x00` user_value(4)+value(4); `0x08`
usage_count(4)+value_lock(4); `0x10` list_lock; `0x18` label*; `0x20..0x38`
events.{event,task,file,function}; `0x40/0x48` events.list.next/prev;
`0x50` reset_cause; `0x58` reset_file*.

## Classification

All `500` grouped reads (parsed deterministically):

| Class | Count | % |
| --- | --- | --- |
| Live, validly re-alloc'd (NONE): `usage_count=1`, `user_value=value=0`, `label=NULL`, `events.list` self-referential, `reset_cause∈{UNSET,NO_CERT}`, `reset_file` NULL-or-valid | 469 | 93.8 |
| Live mid-verification (PROCESSING): `user_value=0xffffffff`, `value=0`, `usage_count=2` | 31 | 6.2 |
| All-zero scrubbed-freed (`usage_count=0`) | **0** | 0 |
| Foreign-reclaim (non-integrity/arbitrary data at usage_count/label/list/reset_file) | **0** | 0 |

Supporting field stats: `usage_count` was only ever `1` (×469) or `2` (×31), **never
`0`**; `label` was `NULL` in `500/500`; `events.list` was self-referential in
`491/500`; `reset_file` non-NULL `473/500`; `reset_cause` = `NO_CERT` `473`, `UNSET`
`27`; and the entire run cycled through only **4 distinct `task_integrity` slot
addresses** (two adjacent-slot pairs).

## Verdict

**Passive racing does NOT place attacker-controllable data in the freed
`task_integrity_cache` slot — controllability is empirically NEGATIVE for the passive
path.** `0/500` reads observed a scrubbed-freed or foreign-reclaimed slot; every read
caught a live, validly re-allocated object (refcount 1 or 2). The dedicated cache
(`SLAB_HWCACHE_ALIGN`, `init_once`) LIFO-recaptures the just-freed slot with the next
`execve`'s own `task_integrity_alloc` before the reader observes it — the run cycled
only 4 slots. This is a **kernel-side, deterministic** confirmation of the
dedicated-cache exploitation obstacle, and it supersedes the earlier passive-`value`
misread (commit `b26fc2d5`): the Tier-0 passive split (`0x0` 93.9% / `0xffffffff`
6.1%) is now explained exactly as live `NONE` (93.8%) vs live `INTEGRITY_PROCESSING`
(6.2%), i.e. the passive read was watching the live object's `NONE↔PROCESSING`
transition, never freed content.

Two precise consequences:
- The Tier-0 `proc_integrity_reset_file → d_path` fault is a **dangling `struct file*`
  UAF window** (reset_file is non-NULL ~94.6% of the time pointing at a real `file`;
  during free the kernel `fput()`s it then NULLs the field, so the original handler can
  catch a transiently-dangling `file` and fault in `d_path`) — it is NOT a
  `task_integrity` foreign-reclaim.
- Weaponizing would require **active heap grooming / cross-cache** to defeat the
  dedicated-cache LIFO recapture. That crosses the RECON→exploit boundary and is out of
  scope here; it would need a separate explicit charter and a justifying EL1-only wall.

## Safety

- RECON only.
- No grooming, spray, primitive construction, EL1 attempt, PMIC/GPIO/power
  write, forbidden partition write, raw flash path, or non-boot partition
  action.
- No boot image, raw log, compiled binary, or private run artifact is committed
  (raw capture with kernel pointers stays under `workspace/private/`, gitignored).
- The patched hook only reads raw struct words via a direct `bl printk`; it does not
  dereference `label`/`reset_file`, so it cannot follow the dangling pointer and did
  not fault. `panic_on_oops=0` was a safety net only; restored to `1` afterward.
- Device ended on clean `v2321` (readback `ca978551…`, `selftest fail=0`).

## Follow-up ①: grooming-pressure measurement (RECON, 2026-06-28)

Question: under allocation pressure, does the victim's freed `task_integrity` slot
escape the LIFO self-recapture (a precursor to slot controllability)? Measured with a
private pressure harness (`a90_five_uaf_groom`, `--pressure K` = K extra execve-storm
processes pinned to the victim cpu to contend the dedicated cache's per-cpu freelist),
reusing the same KASAN-lite image; harness source/binary kept private (gitignored),
not committed. Each level: clear dmesg, run `--secs 2 --max-reads 250 --pressure K`,
classify the use-site dumps. All runs `reader_exited code=0` (no fault).

| pressure K | reads | distinct slots | scrubbed-freed (usage_count=0) | live PROCESSING | foreign |
| --- | --- | --- | --- | --- | --- |
| 0 | 250 | 2 | 0 | 11 | 0 |
| 16 | 250 | 1 | 0 | 0 | 0 |
| 32 | 250 | 1 | 0 | 0 | 0 |

`usage_count` was `1` (live) on every read at K=16/32; pressure did not produce a
single scrubbed-freed or foreign-owned observation, and slot diversity did not grow.

Mechanistic confirmation (source, no extra flash): `five_bprm_check`
(security/samsung/five/.../five_main.c) swaps integrity in the order **alloc NEW →
`task_integrity_assign(task, NEW)` → `task_integrity_put(OLD)`** — i.e. the new object
is installed BEFORE the old is freed. So `task->integrity` is never dangling; a handler
that re-reads `task->integrity` (as our hook does, and as the real handler does for its
loads) always observes a valid object, which is exactly why pressure cannot surface a
freed/foreign `task_integrity` slot through this path.

### Updated verdict on the controllability question
- **`task_integrity` object/slot control = NEGATIVE**, now both empirically (0/1000+
  reads across single-thread and 32× pressure ever showed a freed/foreign slot) and
  mechanistically (assign-before-free + dedicated cache). The simplest grooming
  (allocation pressure) does not open the window.
- The genuinely exploitable surface is therefore **not** `task_integrity` but the
  **`reset_file` `struct file *`**: the CVE race is a reader holding/with a stale view
  across `task_integrity_put` → `fput(reset_file)`, a UAF on the **`file` object in the
  filp cache** (a different, general-purpose cache), reached via `d_path` in the
  original handler. Characterizing/controlling that is a separate investigation
  (filp-cache UAF), is real exploit-dev under RKP_KDP/RKP_CFP, and stays behind the
  RECON→exploit charter gate. Not pursued here.
