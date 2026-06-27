# Deferred exploration candidate — Samsung PROCA/FIVE kernel UAF (CVE-2026-20971)

**Status: DEFERRED / backlog. Not chartered. Do not start work on this.**
Park it until the GPU epic closes (④ zero-copy Z0→Z3) AND a concrete EL0-blocked
wall appears that only kernel (EL1) code execution can clear. This file is an
operator note recording why the candidate exists and the exact gate to reopen it.

Date: 2026-06-27 (operator host-side, web-research only; no device action).

## What it is

- **CVE-2026-20971** — use-after-free (race condition) in Samsung's **PROCA**
  (Process Authenticator) ↔ **FIVE** (Samsung kernel integrity subsystem)
  interaction. CVSS **7.8 (high)**. Discovered by LucidBit Labs; ~8 years latent.
  Fixed in Samsung's **January 2026** Security Maintenance Release.
- Affected: Galaxy **S9 → S25**, **A-series**, Exynos + Qualcomm, Android
  13/14/15/16 before the Jan-2026 patch. Tested by the finder on S21/S22/S24/**A54**.
  The A90 5G (`SM-A908N`, kernel 4.14.190) is in the same device/kernel family and
  predates the patch, so the source-level bug is plausibly present in our stock kernel.

## Mechanism (for later reachability work)

- Vulnerable object: **`task_integrity`** struct (fields `user_value`, `value`,
  `usage_count`, `value_lock`, `label`, `reset_cause`, `reset_file`).
- procfs handlers fetch the pointer via `#define TASK_INTEGRITY(task) ((task)->integrity)`
  **without taking a refcount**: `proc_integrity_value_read()`,
  `proc_integrity_label_read()`, `proc_integrity_reset_file()`.
- Race: parent reads `/proc/<child_pid>/integrity/*` → handler grabs the pointer and
  is scheduled out → child `execve()` → `__five_bprm_check()` frees the old object via
  `task_integrity_put(old_tint)` → parent resumes on freed memory.
- Trigger vector: `/proc/<pid>/integrity/` reads; no special permission in the
  original (Android-app) threat model.
- Primitives reported: DWORD info-leak from freed memory; **arbitrary-call BLOCKED by
  KCFI**; small write via stale `spin_lock()/spin_unlock()` at offset `0xc`. (Weak —
  turning the spinlock small-write into reliable kernel code execution is a heavy
  exploit-dev lift.)

## Why it is NOT a problem (and not a task) for this project

1. **Wrong direction for our threat model.** The CVE is *unprivileged Android app →
   kernel* privesc. Native-init runs as **PID1/root (EL0)** and controls all of
   userspace — there is **no untrusted attacker** in our boot, so there is **no
   defensive security problem** whether FIVE is alive or not.
2. **Only offensive utility — and "alive" is now CONFIRMED (see host-RE section below).**
   For us the bug could at most be a candidate **EL0 → EL1** (kernel code execution)
   primitive. The earlier guess that FIVE/PROCA is "likely inert" under native-init was
   **wrong**: it is compiled in, `CONFIG_FIVE=y`, inits at boot, and the vulnerable
   `/proc/<pid>/integrity/{value,label,reset_file}` nodes are live for every process.
   "Alive" gates *reachability of a tool*, not *risk* — and the tool is reachable.
3. **Still an IF-chain, but lighter than on the devices LucidBit tested.** reachable
   (confirmed) → triggerable UAF (race + controlled realloc) → usable primitive → and
   **RKP/EL2** (KNOX hypervisor) still sits above EL1 (the RKP per-boot-key wall that
   closed ROPP symbolization). **Key delta: our kernel is 4.14 with NO kernel CFI**
   (1 cfi symbol in `System.map`), so the **arbitrary-call primitive that KCFI blocked
   on the S21/S24/A54 (5.x) that LucidBit tested is likely NOT blocked here.** That
   removes the single mitigation LucidBit called out, making this the strongest EL0→EL1
   lead the project has found (vs the 3 closed-phase n-days: FastRPC unreachable, Binder
   not-vulnerable, KGSL runtime-open-blocked). It is still real exploit-dev, and
   `reachable ≠ exploitable` remains the discipline.
4. **Nothing on the current roadmap needs EL1.** GPU ④ zero-copy (KGSL/DRM), SoftAP
   (nl80211/cfg80211), sensors/BT/haptics (dev-node/HAL glue), and the headless-server
   distro pivot (`pivot_root` on the stock kernel) are all **EL0 userspace-driver-glue**
   problems — the method that has carried WiFi, USB, audio (ACDB), and GPU so far.

## Host-RE + live read-only confirmation (2026-06-27, idle-window investigation)

Done host-only from the stock `System.map`/`kernel.raw` plus a single **read-only**
native-init probe (no exploit, no write, no flash) while the autonomous loop was paused:

- **Compiled in + active.** `System.map` carries the full FIVE subsystem
  (`__five_bprm_check`, `five_fork`, `five_file_*`, `five_hook_*`, `init_five`,
  `__initcall_init_five7`) and PROCA (`proca_module_init7`, `proca_hook_task_forked`,
  `g_proca_table`, `__initcall_proca_init_gaf1`). The exact CVE handlers are registered:
  `proc_integrity_value_read`, `proc_integrity_label_read`, `proc_integrity_reset_file`,
  `proc_integrity_inode_operations`.
- **Nodes are LIVE under native-init.** On init `0.11.104` (kernel `4.14.190`), a
  read-only probe showed `/proc/self/integrity/` and `/proc/1/integrity/` both contain
  `value`, `label`, `reset_cause`, `reset_file`, and **411** `/proc/<pid>/integrity`
  directories exist — i.e. `task_integrity` is allocated per task for every process.
  Kernel config confirms `CONFIG_FIVE=y`, `CONFIG_INTEGRITY=y` (legacy Samsung FIVE,
  not GKI). **Reachability = YES.**
- **No kernel CFI.** `System.map` has 1 cfi symbol → the 4.14 kernel is not built with
  kernel CFI, so the arbitrary-call mitigation LucidBit hit on newer Galaxies is absent.
- **RKP/EL2 present** (119 hyp/rkp/knox symbols; prior project work already proved RKP is
  active) → still a wall for EL1 cred/page-table persistence, not for EL1 code-exec itself.

Net: this moved from "probably dead for us" to **"reachable, mitigation-light EL0→EL1
candidate"** — but it stays DEFERRED. We are already EL0 root, there is no named roadmap
wall that needs EL1, and turning the UAF into reliable code exec is still exploit-dev under
RKP. The read-only reopen step is now DONE (positive); what remains gated is the decision
to spend exploit-dev effort, which needs a concrete EL1-only wall to justify it.

## Relationship to the closed kernel-security recon phase

The kernel-security recon phase is **CLOSED** (`NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md`).
Its three triaged n-days were FastRPC (CVE-2024-43047), Binder
(CVE-2023-20938/-21255), and KGSL (CVE-2023-33107); charter answer: *EL1 via
non-destructive n-day from this environment = no.* CVE-2026-20971 is a **new** n-day
not in that triage, but it does **not** by itself meet the phase's reopen criteria —
it is exploit-dev-gated and behind KCFI + RKP.

## Reopen gate (exact)

The read-only reachability step is **DONE (positive, 2026-06-27)** — see the host-RE
section. What remains gated: reopen for **exploit-dev** only when a **named, concrete**
roadmap wall appears where the stock kernel refuses an EL0 userspace path and **only
kernel code execution** would clear it (e.g. a driver `open()`/ioctl hard-gated under
native-init, mirroring the KGSL "runtime-open-blocked" finding). Bring that wall's name
to the reopen; do not start exploit-dev speculatively just because the bug is reachable.
Until then: do not attempt the UAF race, the arbitrary-call/spinlock-write primitive, or
any kernel write. The value recorded here is that the lead is **live and the strongest
EL0→EL1 option on file**, ready if a wall ever demands it.

## Experiment design + static exploitability assessment — PREPARED warm-start kit (2026-06-27, NOT executed)

Recorded so that if a future EL1-only wall ever justifies this, the work resumes warm
instead of cold (project lesson: a pre-staged tool/reference is the unblock). Everything
below is host-only source analysis + the read-only live characterization already done; the
live UAF trigger was NOT run and must not be on this device (see the device blocker).

**Confirmed vulnerable code (our source).** `fs/proc/base.c`: the `integrity` DIR is added
to `tgid_base_stuff[]` unconditionally under `#ifdef CONFIG_FIVE` (so live for every pid),
and the handlers dereference `task->integrity` with **no refcount** on the integrity object:
- `proc_integrity_value_read` → `task_integrity_user_read(task->integrity)`
- `proc_integrity_label_read` → `spin_lock(&task->integrity->value_lock); l = task->integrity->label`
- `proc_integrity_reset_file` → `task->integrity->reset_file->f_path`

**Object (`struct task_integrity`, `include/linux/task_integrity.h`):**
`user_value`(0), `value`(4), `atomic_t usage_count`(8 — the refcount the handlers fail to
take), `spinlock_t value_lock`(0xc — LucidBit's spinlock-write offset), `spinlock_t list_lock`,
`struct integrity_label *label`, `struct processing_event_list events`,
`enum reset_cause`, `struct file *reset_file`. Allocated from a **dedicated slab cache**
`kmem_cache_create("task_integrity_cache", ...)`.

**Live characterization (read-only, init 0.11.104).** Our unsigned native-init processes
carry `value=0`, `label=NULL` (handler prints `-1`), `reset_cause=no-cert`,
`reset_file=<live struct file*>`. So `reset_file` is a dereferenceable kernel pointer and
`value_lock` is a live spinlock in the freed-object window; `label` is NULL for us.

**Static exploitability verdict.** The UAF is reachable and the primitive surface is real
(refcount UAF; spinlock write at 0xc; `label`/`reset_file` pointer derefs → leak/arb-read),
and the 4.14 kernel has **no kernel CFI**, so the arbitrary-call mitigation LucidBit hit on
5.x Galaxies is absent here. BUT two hard obstacles remain: (1) **dedicated
`task_integrity_cache`** blocks the easy spray — reclaiming the freed slot with
attacker-controlled bytes needs same-type reclaim (kernel-initialized content, hard to
weaponize) or a **cross-cache attack** (advanced, unreliable); (2) **RKP/EL2** still guards
cred/page-tables above EL1. Verdict: *plausible for the bug class, but a hard exploit-dev
project with a real chance of failing — not a "keep poking and it falls out."*

**Device blocker (why ③ live-trigger is not on this device).** `CONFIG_KASAN` not set +
`CONFIG_PANIC_ON_OOPS=y` → no instrumented UAF detection and any bad deref oops → immediate
panic/reboot. The race would be "loop execve until garbage-leak or panic," blind, on the
single device running the autonomous loop. No safe observation path here.

**What a real attempt would need (the prepared tool list).** A sacrificial secondary device
(or emulator) with a **KASAN-built kernel** for observation; a heap-grooming strategy for the
dedicated cache (same-type reclaim vs cross-cache page-reclaim); a race harness (parent
`open`+`read` of `/proc/<child>/integrity/value` via seq_file vs child repeated `execve`,
pinned to opposing CPUs); a target plan for converting the spinlock-write/pointer-deref into
PC control given no-CFI; and an RKP-aware post-EL1 plan (avoid cred/PT writes — we are
already root, so the goal is EL1 code exec, not cred escalation). Reopen still gated on a
named EL1-only wall (see Reopen gate).

## Sources

- LucidBit Labs — "When Defenses Become Attack Surface" (technical analysis):
  https://lucidbitlabs.com/blog/when-defenses-become-attack-surface/
- SecurityWeek — Eight-Year-Old Samsung KNOX Flaw:
  https://www.securityweek.com/eight-year-old-samsung-knox-flaw-exposed-millions-of-galaxy-devices-to-kernel-attacks/
- SC Media — CVE-2026-20971 patched in January 2026:
  https://www.scworld.com/brief/samsung-knox-kernel-flaw-cve-2026-20971-patched-in-january-2026
