# Kernel Security Tier-2 Runtime Poke Agent — brick re-diagnosis + corrected build (LIVE)

- Cycle: `TIER2_RUNTIME_POKE_AGENT`
- Date: `2026-06-28`
- Decision: `tier2-runtime-poke-agent-corrected-live-pass`
- Scope: flash-once runtime kernel write primitive on stock kernel `4.14.190`, RECON/operator-tooling
- Builder: `workspace/public/src/scripts/revalidation/build_kernel_runtime_poke_agent.py`
- Base / rollback: clean V2321 (`0.9.285 (v2321-usb-clean-identity-rodata)`, SHA256 `ca978551…`)

## Goal

Stop re-flashing the kernel for every EL1 / kernel-memory experiment. Flash **once** a
kernel that turns a benign write-only sysfs node into a runtime "poke" channel, so
thereafter arbitrary kernel-memory writes are issued at runtime over the bridge with no
reflash/reboot. This is an operator research/debug tool on an owned, bootloader-unlocked
device (we already run our own EL1 code by flashing); it grants no new privilege, it only
removes the per-experiment flash cost. Pinned to V2321.

## Mechanism

Hijack `kgsl_pwrctrl_force_no_nap_store(dev, attr, buf, count)` — a benign GPU debug-flag
sysfs **store** handler at `/sys/class/kgsl/kgsl-3d0/force_no_nap`. Store ABI is
`ssize_t store(struct device*, struct device_attribute*, const char *buf, size_t count)`
⇒ `x2 = buf` (a kernfs page, NUL-terminated, zero-padded), `x3 = count`. The replacement
leaf body reads a 32-byte command and does a single store:

    movz/movk x7, <MAGIC>           ; x7 = 0xA90C0DE5DEADBEEF
    ldr  x4,[x2] ; cmp x4,x7 ; b.ne ret_path   ; magic guard
    ldr  x4,[x2,#8]  (addr)
    ldr  x5,[x2,#16] (val)
    ldr  x6,[x2,#24] (width)
    cmp  x6,#8 ; b.ne store32
    str  x5,[x4]                    ; 64-bit store
    b    ret_path
  store32: str w5,[x4]             ; 32-bit store
  ret_path: mov x0,x3 ; ret        ; return count

Protocol: write 32 LE bytes `{u64 magic, u64 addr, u64 val, u64 width}`; magic must equal
`MAGIC` or the handler no-ops and returns count; `width==8` → 64-bit store else 32-bit.

CFP-safety: leaf body, no `bl`/`blr`, no `x30` spill, only direct branches (`b`, `b.ne` —
not JOPP-gated); `ret` returns the plain `x30` so no ROPP `eor` dance is needed. The
dispatching `blr` from the sysfs layer still lands on the **preserved** RKP/JOPP magic
`0x00be7bad` at the function's `-4` word, so JOPP is satisfied. Poking an RKP-protected
region (cred/page-tables/`.text`) still faults under RKP (expected, out of scope).

## Brick re-diagnosis (the important correction)

The **first** build of this agent bootlooped the device. The initial post-brick guess —
"native-init selftest writes `force_no_nap` during boot, so the poke code read boot-time
ASCII as a wild `{addr,val}`" — was **wrong**: `rg` proves native-init never reads or
writes `force_no_nap` anywhere.

Verified root cause (disassembly of clean V2321): the builder's `ENTRY_OFF = 0x8A7920`
was a **stale/incorrect offset**, ~1.4 KB away from the real handler. `0x8A7920` is
`gpu_busy_percentage_show` — a *read* handler (`mul ×100; udiv; snprintf(buf,4096,…)`) —
and native-init **does read** `/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage` during boot
(`a90_metrics.c:149`, `a90_monitor.c:671`). So at boot the hijack ran with `x2 = output
buffer`, executed `str x5,[x4]` to a garbage address, and `panic_on_oops=1` (boot default)
turned the oops into a bootloop (it reached "SELF running" — the selftest HUD line — then
died each cycle).

Why the "safety" asserts missed it: they only checked `eor x16,x30,x17` + RKP magic
`0x00be7bad` — which **every ROPP-instrumented function** begins with. They matched the
wrong function. **Lesson: verify a patch target by its function fingerprint / semantics
(disasm), never by the generic ROPP prologue shape.**

## Corrected build

Real `kgsl_pwrctrl_force_no_nap_store` resolved via `force_no_nap` string → its
`device_attribute` → `.store` pointer, then disassembly-confirmed as a genuine store
(stack frame + `kstrtobool(buf)` + mutex + set/clear flag + `return count`):

- entry: file-off `0x8A73C8`, vaddr `0xffffff80089273b4`; room to next RKP magic = 212 B.
- Asserts now pin the **exact fingerprint** (`sub sp,sp,#0x40` = `0xD10103FF`, then `eor` =
  `0xCA1103D0`) plus both bracketing RKP magics — not the generic ROPP shape.
- Added the **MAGIC guard** so any stray / short / ASCII write can never trigger a store.
- native-init never reads or writes `force_no_nap`, and the periodic monitor reads only
  `gpu_model / gpu_busy_percentage / cur_freq / max_freq / max_gpuclk / temp`, so nothing
  drives this handler at boot or at runtime unless we send the exact 32-byte command.

Host validation: builder run is clean; objdump of the patched body matches the design
exactly; the image diff is contained to `{boot-id @0x240, force_no_nap_store body}` with
zero bytes changed elsewhere, and both RKP magics are preserved.
Image: `boot_linux_tier2_runtime_poke_agent.img`, SHA256 `025020af…` (private, `0600`).

## Live validation (slide-free, recoverable)

Flashed via `native_init_flash.py --from-native --expect-sha256 025020af…`.

1. **Boot:** clean — `0.9.285 (v2321-…)`, `selftest pass=11 warn=1 fail=0`. The previous
   wrong-offset image bricked at boot; this one boots fine ⇒ **brick fixed.**
2. `panic_on_oops` set to `0` so a deliberate fault is survivable.
3. **Smoke A (guard reject):** wrote 32 bytes with a *wrong* magic and `addr=0` →
   `rc=0` (write succeeds, no store), device alive, `selftest fail=0`. ⇒ handler dispatches
   and the magic guard correctly rejects non-matching writes.
4. **Smoke B (store path / primitive):** wrote 32 bytes with the *correct* magic and
   `addr=0` → `[signal 11]` `rc=139`; the trailing `echo` never printed; **device survived**
   (`selftest fail=0`). ⇒ on magic match the handler dereferences the supplied address
   (`str x5,[x4]`), faulting at the controlled pointer.
5. The **A vs B delta** (identical command except the magic; A = no fault, B = fault on the
   dereference) proves: dispatch + magic-guard discrimination + the arbitrary-write store
   path all work. (`addr=0` is a user-range VA, so the EL1 fault routed to the task as
   SIGSEGV rather than emitting a kernel-oops banner; the primitive is identical for any
   address the store targets.)
6. **Rollback:** `native_init_flash.py --from-native --expect-sha256 ca978551…` →
   `0.9.285 (v2321-…)`, `panic_on_oops=1` (reset by reboot), `selftest fail=0`.

## Remaining blocker for poking real static globals

The poke takes a **runtime** virtual address, but kallsyms is `%p`-hashed even at
`kptr_restrict=0` (Samsung backported pointer hashing; `/proc/kallsyms` shows 32-bit
hashes, not `0xffffff80…`), so the KASLR slide is hidden. Poking a *named static symbol*
therefore needs the V2216 codeword/perf exact-slide method
(`workspace/public/src/native-init/helpers/a90_bpf_perf_regs_codeword_sample_ring.c`)
first. For real exploitation this is moot (use leak-derived heap addresses). The
validation above is deliberately slide-free (`addr=0`).

## Guardrails / status

- Boot-partition-only via the checked flash helper with readback verify; v2321/v2237/v48
  rollback gates present; odin4 boot-only recipe is the proven download-mode recovery path.
- No write to forbidden partitions; no PMIC/GPIO/power writes.
- The image and its raw runtime pointers are private; this report carries no runtime
  pointers or slide.
- Device left on clean V2321, `selftest fail=0`. The poke agent is a proven, resident-
  flashable tool; slide-wiring is deferred until a concrete EL1 experiment is chartered.
