# Tier-0 PROCA/FIVE UAF recon protocol (CVE-2026-20971) — EXECUTED 2026-06-27, UAF CONFIRMED

## RESULT (2026-06-27, attended, init 0.11.104 / kernel 4.14.190)

**The PROCA/FIVE `task_integrity` UAF (CVE-2026-20971) is empirically triggerable under
native-init — confirmed in a ~5 s pilot.** A `panic_on_oops=0` non-fatal run (sec_debug
already off) of the `a90_five_uaf_probe` harness (aarch64 static, sha256
`4049ea75822a4f73ce532fa0b7ca3aac84f50693d40c6e1c0f32c3f0d3e1de1e`) produced
`reader_terminated_by_signal=11` and the exact kernel oops:

```
Call trace:
 d_path+0x30/0x188
 proc_integrity_reset_file+0x58/0xc0
 proc_single_show+0x58/0xb0
 seq_read+0x1bc/0x510
 __vfs_read / vfs_read / SyS_read / __sys_trace_return
Code: ... (f9400400)   # ldr x0,[x0] — deref of a freed/garbage reset_file pointer
---[ end trace 28c1400c0fcf950b ]---
```

The fault is `proc_integrity_reset_file` dereferencing `task->integrity->reset_file->f_path`
(via `d_path`) after the object was freed by a concurrent `execve` (`__five_bprm_check`) — the
CVE race exactly. **`panic_on_oops=0` held: the oops was non-fatal, only the reader task was
killed, the device stayed up** (kernel activity continued, no reboot). Cleanup: harness removed,
`panic_on_oops` restored to 1, `selftest pass=12 warn=1 fail=0`, no loop collision.

**Conclusion:** reachability is no longer just source-plausible — it is empirically proven, with
the exact fault site.

### Info-leak / reclaim observation (value-only variant, 2026-06-27)
A second non-faulting harness (`a90_five_uaf_leak`, reads only `/proc/<vpid>/integrity/value`
= `task_integrity_user_read` → `user_value` at offset 0, no pointer chase) ran 10 s:
`reads=568150`, `zero(0x0)=533327` (93.9%, the valid `INTEGRITY_NONE`), `nonzero=34823` (6.1%,
ALL `0xffffffff`), `changes=69463`, device survived (value reads do not fault; slab page stays
mapped), `selftest fail=0` after restore. **The race is won constantly (value toggles 0 ↔
0xffffffff ~69k times), but the freed-slot leak is a single FIXED sentinel `0xffffffff` (-1) —
NOT diverse heap-reclaim content.** Whether 0xffffffff is a free/reset-transition value or slab
poison/freelist-tail (not traced further), the exploitability takeaway is the same: **passive
observation shows no controllable reclaim content in the dedicated `task_integrity_cache`** —
empirical support that weaponizing this needs ACTIVE heap grooming / cross-cache, not passive
reuse. The dedicated-cache obstacle is real.

This stays RECON — no grooming/primitive/EL1 was attempted, and the exploitation obstacles
(dedicated `task_integrity_cache` + RKP_CFP + RKP_KDP) are unchanged. The Tier-0 warm-start kit
is now complete: trigger confirmed (fault site) + freed-slot passive behavior (fixed sentinel).

### CORRECTION (2026-06-28, host-only source RE — the value-leak interpretation above was WRONG)
Source review of the stock kernel tree
(`workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel` +
`tmp/wifi/v766-.../source/security/samsung/five/`) overturns two claims in the value-leak section:

1. **`0xffffffff` is NOT a sentinel/poison — it is a legitimate enum value.**
   `include/linux/task_integrity.h`: `INTEGRITY_PROCESSING = 0xffffffff` (and `INTEGRITY_NONE = 0x0`).
   The ping-pong-execve harness keeps the victim mid-`execve`, so the `0 ↔ 0xffffffff` toggle is the
   **live** object's normal `NONE ↔ PROCESSING` transition during verification — NOT freed-slot
   reclaim content. The leak harness was largely observing a healthy live object, not a freed one.

2. **The free path SCRUBS the object before `kmem_cache_free`, so passive value-read is BLIND to
   reclaim by construction.** `task_integrity_free()` (security/samsung/five/task_integrity.c) sets
   `user_value=INTEGRITY_NONE(0)`, `value=0`, `usage_count=0`, `reset_cause=CAUSE_UNSET(0)`,
   `reset_file=NULL`, `kfree(label); label=NULL` — then frees. The freed slot therefore starts
   **zeroed**; reading `value` (offset 0) after free yields 0 until/unless another allocation
   overwrites it. So `zero=93.9%` is "scrubbed-freed OR settled-live", and the read CANNOT reveal
   reclaim content even if reclaim occurs.

**Consequence:** the prior conclusion *"passive observation shows no controllable reclaim content →
the dedicated-cache obstacle is real"* was an **over-read**. Passive observation is structurally
incapable of seeing reclaim here (free-scrub + only offset 0 exposed). **Controllability is still
OPEN**, not refuted; deciding it needs ACTIVE heap grooming + a use-site full-object observation,
which crosses the RECON→exploit boundary and requires a separate explicit charter. What IS
established: the triggered `reset_file` UAF fault proves the slot DOES get incidentally reclaimed
with non-NULL data at the `reset_file` offset during the race (otherwise the `!reset_file` guard
would have taken the empty branch). The dedicated cache (`kmem_cache_create("task_integrity_cache",
…, SLAB_HWCACHE_ALIGN|SLAB_PANIC|SLAB_NOTRACK, init_once)`) remains an exploitation obstacle, but
"no controllable reclaim" is NOT a proven fact — it is untested.

---

## Original design (executed as written below)

**Status: DESIGN ONLY. Not yet executed.** This is the bounded, stock-kernel, no-recompile
recon experiment for the PROCA/FIVE `task_integrity` UAF. It is RECON, not exploitation: it
aims only to (a) prove the race is empirically triggerable under native-init and (b) observe
the freed-object reclaim/leak behaviour. It does NOT attempt EL1, control-flow hijack, the
spinlock-write primitive, heap grooming, or any kernel write. See the assessment +
warm-start kit: `KERNEL_SECURITY_DEFERRED_PROCA_FIVE_CVE_2026_20971_2026-06-27.md`.

Execute ONLY with: operator attended + present, the autonomous loop confirmed paused (no
live run), rollback `v2321` staged, and an explicit per-run go. Abort on the first hard
sign of instability beyond a single recoverable reboot.

## Why Tier 0 (vs KASAN / Tier 2)
- KASAN would catch the UAF at the moment of use but needs a recompiled kernel that must
  boot under RKP (RKP_DMAP_PROT guards the exact memory-layout change KASAN makes) — an
  unproven, RKP-fraught capability. Not Tier 0.
- Tier 2 (functional `.text` patch / one-site KASAN-lite) gives deterministic free↔use
  correlation but is `.text` code injection that must satisfy RKP_CFP (JOPP/ROPP) and may
  not even boot under RKP — defer until a minimal `.text`-patch boot test passes.
- Tier 0 needs neither: `sec_debug.enable=0` is already set (no upload-mode hard reset) and
  `panic_on_oops` is a writable runtime sysctl, so a UAF oops can be made non-fatal +
  logged on the **stock kernel**, no recompile, no RKP risk beyond a possible recoverable
  reboot.

## What Tier 0 can and cannot yield
- CAN: empirical proof the race triggers; oops fault signature (faulting addr, call stack:
  `seq_read → proc_integrity_label_read/reset_file → freed-object deref`, which field faults
  first); via the `value` read, an info-leak sample of what lands in the freed slot across
  the race (probes the dedicated-cache reclaim question).
- CANNOT: catch the UAF at the instant of use (no KASAN); deterministic detection (it is
  statistical); EL1 or any control-flow result (RKP_CFP wall); guaranteed survival — some
  corruptions (RKP_KDP/DMAP hard-fault, oops in atomic context) may still hard-reset.

## Mechanism
`fs/proc/base.c` handlers deref `task->integrity` with no refcount; on `execve`,
`__five_bprm_check` does `task_integrity_put(old)` (free) + reallocate. `execve` preserves
pid, so `/proc/<pid>/integrity/*` stays valid while the underlying integrity object is
freed/replaced — the race.

- **Trigger field:** `reset_file` (handler derefs `task->integrity->reset_file->f_path` —
  double deref, most likely to fault on freed/reused memory). `label` also faults
  (`spin_lock(&...->value_lock)` then `->label`).
- **Leak field:** `value` (`task_integrity_user_read` reads an enum — least likely to fault,
  best info-leak channel to observe reclaim content).

## Harness (aarch64 static, RECON-only; build with aarch64-linux-gnu-gcc, verify with `file`)
Two-mode single binary, ping-pong execve to keep a stable victim pid:
- **victim:** `execve(self, {mode=victim})` in a tight loop (execve preserves pid; loop by
  re-exec); deadline carried in `envp` (re-read each exec) → exit when exceeded.
- **reader:** parent pins to a different CPU (`sched_setaffinity`), tight loop
  `open("/proc/<victim_pid>/integrity/{value|reset_file}") + read()`; records read count,
  the `value` byte distribution / any anomalous change, and any `read()` error.
- **bounds (hard):** `--max-iters` (default 500k), `--max-seconds` (default 60),
  `--stop-on-first-anomaly`. No writes anywhere. No setuid. No exploit payload.

## Procedure (attended)
1. **Preflight:** bridge up; `version` + `selftest fail=0`; record resident build to restore;
   confirm loop paused (no live run); `v2321` staged.
2. **Snapshot dmesg tail** (baseline) via `/bin/busybox sh -c 'dmesg | tail -n 80'`.
3. **Set non-fatal:** `echo 0 > /proc/sys/kernel/panic_on_oops`; read back to confirm `0`.
   Confirm `sec_debug.enable=0` (already in cmdline). (If panic_on_oops refuses to stick,
   ABORT — do not run the race with panic_on_oops=1.)
4. **Stage + run harness** under tight bounds; capture stdout (read count, value samples).
5. **Capture dmesg** after the run (bounded tail, serial `cmdv1x`): look for oops with a
   bad-address deref in `proc_integrity_*`/`seq_read`; record faulting addr + stack.
6. **Restore:** `echo 1 > /proc/sys/kernel/panic_on_oops`; remove harness; `selftest`.
7. **Health gate:** if `selftest fail=0` and device stable → keep build; if unstable → roll
   back to `v2321` and confirm `selftest fail=0`.

## Outcome interpretation
- **oops with freed-deref in proc_integrity path** → UAF empirically confirmed triggerable;
  record signature into the warm-start kit.
- **anomalous/changing `value` leak, no oops** → race won but reclaim was benign/observable;
  the leaked bytes characterize dedicated-cache reuse (key exploitability datum).
- **clean (no oops, no anomaly) within bounds** → race not won at this rate; note iters/timing,
  optionally widen CPU pinning — do NOT raise bounds unboundedly.
- **reboot** → panic_on_oops didn't hold or RKP hard-faulted; device returns to the resident
  build; treat as a recoverable data point, then STOP (do not loop reboots).

## Hard stop conditions
- panic_on_oops won't set to 0 → do not run.
- More than one reboot in the session → STOP, leave it; escalation needs KASAN/Tier-2, not
  repeated blind reboots.
- Any sign of non-recoverable state (device unreachable after reboot) → STOP, rollback,
  incident note.
- This stays RECON. Crossing into grooming/primitive/EL1 needs a separate explicit charter
  AND a named EL1-only wall (per the deferral's reopen gate).
