# Tier-2 capability test: static kernel `.text` patch boots AND takes effect under RKP — VIABLE (2026-06-28)

**Result: a kernel `.text`-modified boot image booted cleanly under Samsung RKP with
`selftest fail=0` (Stage A), and a patched constant in a real function changed its
runtime-observable output 5→99→5 (Stage B). Static `.text` patching of the stock kernel is
VIABLE on this device.**
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

## Stage B — observable runtime effect CONFIRMED (2026-06-28)
Stage A proved boot-survival with a no-op. Stage B proves the patched `.text` actually
**executes with its new behavior** at runtime. Target: `kgsl_pwrctrl_num_pwrlevels_show`
(readable at `/sys/class/kgsl/kgsl-3d0/num_pwrlevels`, reachable under native-init since the
GPU is up). Its display value is computed by `sub w3, w8, #1` (`51000503`, vaddr
`0xffffff8008926320`). Patched that one instruction → `mov w3, #99` (`52800c63`) so the
handler always prints 99; recomputed boot id (24-byte total diff). This function carries a
ROPP epilogue (`eor x30, x16, x17 ; ret`) but the patched `sub` is a plain data instruction,
not a `ret`/indirect-branch (CFP-safe). Result, all on the same boot cycle:
- clean v2321: `num_pwrlevels` = **5**
- patched kernel: booted `fail=0`, `num_pwrlevels` = **99**
- rolled back to clean v2321: `num_pwrlevels` = **5** again
The patched code path executed with its modified constant — **RKP does not restore/revert
patched `.text` at runtime**, and a patch inside a real ROPP-protected function body works.

## What this proves / does not prove
- **Proves:** RKP permits static `.text` modification at boot (no boot-time text
  hash-verify) AND the patched code executes with new behavior at runtime (Stage B,
  num_pwrlevels 5→99→5). Tier-2 patching of **non-CFP instructions in real functions** is
  fully viable, including functions that have ROPP epilogues (as long as the patched
  instruction is not the `ret`/indirect-branch itself).
- **Does NOT yet prove:** that patching a **CFP control-flow instruction itself** (a ROPP
  `ret` or a JOPP indirect branch) survives, or that **code injection with new
  calls/branches** (e.g. logging that calls `printk`) satisfies RKP_CFP. Those remain the
  only open Tier-2 questions; the core capability (observable data/constant/behavior patches)
  is proven.

## Stage C attempt — code injection with a direct call (`bl printk`): BLOCKED on symbol resolution
Attempted 2026-06-28. **Analytical answer (favorable):** a direct `bl` is a PC-relative call,
**not** an indirect branch, so JOPP (which gates `blr`/`br` via the `0x00be7bad` magic) does
not apply; the callee handles its own ROPP return-address encryption. So a patched-in **direct**
call (exactly what KASAN-lite logging needs) should execute under RKP_CFP; only an **indirect**
`blr` would need JOPP handling. **Empirical test blocked:** a `bl printk` needs printk's exact
image address, and we could not resolve it reliably:
- The staged `v2197-stock-kallsyms` `System.map` does **not** match the v2321 kernel image —
  disassembling at its `printk` address (`0xffffff800813be60`) under either file↔vaddr mapping
  (`-0x8080000` or `-0x8080000+0x14`) shows mid-function/branch code, not a `printk` prologue,
  and its `__memmove` address lands on NOPs. Symbol addresses are shifted/mismatched.
- Runtime `/proc/kallsyms` returns **pointer-hashed** addresses even at `kptr_restrict=0`
  (kernel `%p` hashing), so the real KASLR/link addresses are not readable that way.
A safe injection test therefore needs a symbol map extracted **from the v2321 image itself**
(kallsyms-in-image parse) to pin `printk`, plus a code cave + register save/restore. Deferred:
the analytical answer covers the direct-call case that matters; the empirical confirmation is a
documented next step if KASAN-lite is actually built. No injection was flashed (a wrong `bl`
target would crash). Device left on clean v2321, `fail=0`.

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
