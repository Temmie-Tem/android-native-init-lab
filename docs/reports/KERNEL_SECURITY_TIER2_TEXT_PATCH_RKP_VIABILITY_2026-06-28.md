# Tier-2 capability test: static kernel `.text` patch boots under RKP — VIABLE (2026-06-28)

**Result: a kernel `.text`-modified boot image booted cleanly under Samsung RKP with
`selftest fail=0`. Static `.text` patching of the stock kernel is VIABLE on this device.**
This unlocks the Tier-2 class (one-site KASAN-lite instrumentation, functional kernel
behavior patches) that was previously unproven. Attended, rolled back to clean v2321.

## Why this was tested
The project had only ever done Tier-1 patches (length-preserving rodata/data byte edits,
e.g. USB `SAMSUNG`→`A90-LNX`), never a `.text` (executable code) change. Whether a static
`.text` patch boots under RKP gates a large class of future capability (KASAN-lite at a bug
site, kernel behavior modification). Host analysis first showed **RKP does not hash-verify
`.text` at boot** — it uses `uh_call(UH_APP_RKP, RKP_RKP_ROBUFFER_ALLOC, …)` to allocate
page tables from RO buffers and enforces text/rodata RO at runtime, with no text
hash/measure/verify code found. Prediction: a static `.text` patch should boot like a
rodata patch does. The only added risk is RKP_CFP (ROPP return-address encryption / JOPP
indirect-branch magic), so the test target avoided control-flow instructions.

## Method (minimal, provably-safe target)
- Base: clean `v2321` (`ca978551…`).
- Kernel format: Samsung `UNCOMPRESSED_IMG` header (16B magic + 4B size) + raw arm64
  `Image` (magic `ARMd` at file 0x4c), uncompressed → raw byte patch is valid.
- Target: file offset `0x1928a3c` in the kernel = vaddr `0xffffff80099a8a3c`, which
  `System.map` places in the **alignment padding between `memcpy` and `__memmove`**
  (`__memmove` starts at `…a8a40`). The last padding word — `NOP` (`1f2003d5`) — is
  **never executed** (control reaches it only by fall-through past `memcpy`'s `ret`, which
  cannot happen). Patched `NOP` → `mov x0,x0` (`e00300aa`): harmless even if executed,
  touches no `ret`/indirect-branch (RKP_CFP-safe).
- Boot image built by **direct patch of the v2321 image** (4 kernel bytes) + recomputed
  Android boot header v1 `id` (SHA1 over kernel/ramdisk per `mkbootimg`). Diff vs clean
  v2321 = exactly **24 bytes** (4 kernel + 20 SHA1 id). Test image `1d98b046…`.

## Result
Flashed via the checked `native_init_flash.py --from-native` path (native-init → TWRP →
flash + readback verify → system). The patched-kernel image **booted**:
`A90 Linux init 0.9.285 (v2321-...)`, kernel `4.14.190`, **`selftest pass=11 warn=1
fail=0`**. RKP did not reject the modified `.text`. Rolled back to clean v2321
(readback `ca978551…` ok, `selftest fail=0`). No autonomous-loop collision.

## What this proves / does not prove
- **Proves:** RKP permits static `.text` modification at boot (no boot-time text
  hash-verify); a `.text`-patched stock kernel boots and runs healthy. Tier-2 is viable.
- **Does NOT yet prove:** that patching a **CFP-protected control-flow site** (a ROPP
  `ret` or a JOPP indirect branch) survives at runtime, or that **code injection with new
  calls/branches** (e.g. logging that calls `printk`) satisfies RKP_CFP. Those are the next
  questions (Stage B observable-effect patch, then a CFP-site patch). The boot-survival gate
  — the 90% question — is open.

## Implication for the PROCA/FIVE work
The Tier-2 path that was listed as "unproven .text-patch under RKP" in the UAF warm-start
kit is now **proven for benign non-CFP `.text` patches**. A one-site KASAN-lite (poison the
freed `task_integrity`, or log free↔use at the proc handler) becomes a realistic option for
deterministic UAF instrumentation **without** a full KASAN kernel — subject to keeping the
inserted logic CFP-safe. Still gated behind a named EL1-only wall for actual exploit-dev;
this only expands the available tooling.

## Safety
Attended; loop paused; boot-partition-only via the checked helper with readback verify;
rolled back to clean v2321 (`fail=0`). Throwaway test image not committed (no boot images
in git). No forbidden partitions touched.
