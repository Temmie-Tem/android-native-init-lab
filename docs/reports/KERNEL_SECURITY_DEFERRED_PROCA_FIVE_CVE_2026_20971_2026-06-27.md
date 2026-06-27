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
2. **Only offensive utility, and only if "alive."** For us the bug could at most be a
   candidate **EL0 → EL1** (kernel code execution) primitive. Whether
   FIVE/PROCA is initialized under our custom init (LSM/bprm hooks + policy load)
   determines whether `/proc/<pid>/integrity/` even exists — likely inert. "Alive"
   gates *reachability of a tool*, not *risk*.
3. **Long, weak IF-chain even if alive.** alive → triggerable UAF (race + controlled
   realloc) → **KCFI** bypass → usable write → and **RKP/EL2** (KNOX hypervisor) still
   sits above EL1 (the same RKP per-boot-key wall that closed ROPP symbolization).
   `reachable ≠ exploitable`, confirmed ×3 in the kernel-security recon phase.
4. **Nothing on the current roadmap needs EL1.** GPU ④ zero-copy (KGSL/DRM), SoftAP
   (nl80211/cfg80211), sensors/BT/haptics (dev-node/HAL glue), and the headless-server
   distro pivot (`pivot_root` on the stock kernel) are all **EL0 userspace-driver-glue**
   problems — the method that has carried WiFi, USB, audio (ACDB), and GPU so far.

## Relationship to the closed kernel-security recon phase

The kernel-security recon phase is **CLOSED** (`NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md`).
Its three triaged n-days were FastRPC (CVE-2024-43047), Binder
(CVE-2023-20938/-21255), and KGSL (CVE-2023-33107); charter answer: *EL1 via
non-destructive n-day from this environment = no.* CVE-2026-20971 is a **new** n-day
not in that triage, but it does **not** by itself meet the phase's reopen criteria —
it is exploit-dev-gated and behind KCFI + RKP.

## Reopen gate (exact)

Reopen **only** when BOTH hold:
1. The GPU epic is closed (④ zero-copy eye-confirmed), and
2. A **named, concrete** roadmap wall appears where the stock kernel refuses an EL0
   userspace path and **only kernel code execution** would clear it (e.g. a driver
   `open()`/ioctl hard-gated under native-init, mirroring the KGSL
   "runtime-open-blocked" finding) — bring that wall's name to the reopen.

First step on reopen is **read-only**, no exploit: confirm whether FIVE/PROCA is live
under native-init by checking for `/proc/self/integrity/` (and `/proc/1/integrity/`)
existence on the resident image. If absent/inert, the candidate is dead for us and this
note can be closed. Do not attempt the UAF, KCFI bypass, or any kernel write.

## Sources

- LucidBit Labs — "When Defenses Become Attack Surface" (technical analysis):
  https://lucidbitlabs.com/blog/when-defenses-become-attack-surface/
- SecurityWeek — Eight-Year-Old Samsung KNOX Flaw:
  https://www.securityweek.com/eight-year-old-samsung-knox-flaw-exposed-millions-of-galaxy-devices-to-kernel-attacks/
- SC Media — CVE-2026-20971 patched in January 2026:
  https://www.scworld.com/brief/samsung-knox-kernel-flaw-cve-2026-20971-patched-in-january-2026
