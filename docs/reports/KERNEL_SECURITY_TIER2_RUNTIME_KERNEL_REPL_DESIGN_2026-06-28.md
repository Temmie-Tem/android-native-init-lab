# Kernel Security Tier-2 Runtime Kernel REPL — design (peek / poke / call / slide)

- Cycle: `TIER2_RUNTIME_KERNEL_REPL`
- Date: `2026-06-28`
- Decision: `tier2-runtime-kernel-repl-design-only` (no build, no device action)
- Scope: design a flash-once runtime kernel observe/execute toolkit on stock `4.14.190`,
  exploit-free (no RKP bypass), building on the proven Tier-2 `.text` patching capability
- Base / rollback: clean V2321 (`0.9.285 (v2321-…)`, SHA256 `ca978551…`)

## Goal

Turn the already-proven flash-once **poke** agent into a general flash-once **kernel REPL**:
after a single flash, drive runtime kernel **observation and execution** over the bridge with
no further reflash/reboot. Four operations:

- `slide` — leak the per-boot KASLR slide (bootstraps everything else)
- `peek(addr, len)` — read kernel memory
- `poke(addr, val, width)` — write kernel memory (already live-proven)
- `call(addr, x0..x7)` — invoke any real kernel function, return its result

This is operator research/debug tooling on an owned, bootloader-unlocked device (we already
run our own EL1 code by flashing). It grants no new privilege; it removes the per-experiment
flash cost and gives a structured observe/execute surface.

## What is already proven (reused, not re-derived)

- Tier-2 static `.text` patch boots under RKP; Stage C proved a **new direct `bl printk`**
  executes under RKP_CFP (`docs/reports/KERNEL_SECURITY_TIER2_STAGE_C_DIRECT_BL_PRINTK_LIVE…`).
- The **poke** primitive (hijacked `force_no_nap_store`, magic-guarded) is live-proven
  (`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_POKE_AGENT_2026-06-28.md`).
- Reusable host helpers in `build_kernel_tier2_stage_c_direct_bl_printk.py`: `encode_bl`,
  `encode_adr_x0`, `kernel_vaddr`, `locate_printk_variadic_wrapper`, plus the verified plain
  `printk` location and JOPP/ROPP constants (`JOPP_MAGIC=0x00BE7BAD`, ROPP eor `0xCA1103D0`),
  cross-checked against the V2207/V2211 JOPP/ROPP analyzers.

## Key design decisions (with rationale + measurements)

### D1 — Hijack target: the `force_no_nap` show+store pair
Both handlers of the benign GPU debug flag `/sys/class/kgsl/kgsl-3d0/force_no_nap` (never read
or written at boot/runtime by native-init; the periodic monitor reads only
`gpu_model/gpu_busy_percentage/cur_freq/max_freq/max_gpuclk/temp`). Measured room to the next
RKP magic:

| handler | entry (link vaddr) | room |
| --- | --- | --- |
| `force_no_nap_store` | `0xffffff80089273b4` | 212 B (53 instr) |
| `force_no_nap_show`  | `0xffffff8008927344` | 108 B (27 instr) |

`store` runs in **process context** (sysfs write syscall) → sleepable → safe to `call` most
kernel functions. `show` can write to its `buf` (a PAGE_SIZE kernfs page) and return a length,
so it is a clean userspace-readable **output** channel (`cat`).

Fallback if budget is tight (see D6): there are larger benign-looking caves nearby (rooms up
to 1796/1636/628 B) the entry can `b`-trampoline into — but only after confirming the cave
function is unused at boot/runtime.

### D2 — KASLR slide via `adr` self-PC leak (supersedes V2216)
The poke channel takes a **runtime** virtual address, but `/proc/kallsyms` is `%p`-hashed even
at `kptr_restrict=0` (Samsung backported pointer hashing), so the slide is hidden. The project's
existing slide method (V2216) is heavy (a staged perf helper + codeword scoring) and computes
`slide = runtime_addr − static_addr` by sampling kernel PC the hard way.

Our injected stub lives in `.text`, so a single `adr x0, .` yields the **runtime** address of
that instruction; we know its **link-time** address (`force_no_nap_store` entry + offset), so
`slide = runtime_PC − link_addr` in one instruction. The `slide` op reports that value; the host
subtracts the known link address. No perf helper, no codeword scoring, no V2216.

Once the slide is known, any symbol = `link_addr + slide`. Alternatively, with `call` working,
`kallsyms_lookup_name("name")` (still present and callable on 4.14 — it is only *unexported* in
kernels > 5.7, and we call by address regardless) resolves any symbol's runtime address.

### D3 — Output channel: printk (v1) vs show-buf (v2)
| channel | pro | con |
| --- | --- | --- |
| `printk` → dmesg | proven (Stage C); no scratch; store-only | bounded arg width; noisy; clumsy for bulk peek |
| `show`-buf (`cat`) | clean binary out; supports bulk peek | needs a store→show handoff scratch |

Phase plan: **v1 uses printk** for the small-result ops (slide = 1 value, call-return = 1–2
values, small peek = a few words) — fastest bring-up, no scratch. **v2 adds show-buf** for bulk
peek.

### D4 — Scratch via `kmalloc` bootstrap (no static-scratch hunt)
For v2 show-buf, `store` and `show` are separate calls and need a shared buffer. Rather than hunt
for a provably-unused writable global, bootstrap one at runtime: after `slide`, issue
`call kmalloc(0x1000, GFP_KERNEL)` and have the host remember the returned pointer; use it as the
peek/result scratch. `adr`/`adrp` referencing a fixed global is PC-relative (slide-transparent),
so a static scratch is *possible* but the kmalloc route avoids needing one and avoids clobber risk.

### D5 — `call` CFP / context requirements
- `call`’s `blr x_target` clobbers `x30` → **non-leaf** → must spill `x30` → must use the
  ROPP `eor` frame (`eor x16,x30,x17` … `eor x30,x16,x17`, `x17` preserved) proven in Stage C.
- `blr` is **JOPP-gated**: the target must be a real function entry (word at entry−4 ==
  `0x00be7bad`). All compiled kernel functions satisfy this; mid-function targets fault. This is
  the intended constraint (call function entries, which is what we want).
- Context: process-context, sleepable. The real limits are **not RKP** but kernel-programming
  invariants — do not call IRQ/atomic-only functions or functions assuming a held lock from here;
  pass valid pointer args.

### D6 — Room budget (the one real constraint)
`store` = 53 instr, `show` = 27 instr. A full 4-op interpreter with printk output and a ROPP
frame is **borderline-to-over** 53 instr in `store`. Mitigations, in order of preference:
1. **Split** work across the pair — keep `poke/call/slide` in `store`; do `peek`’s read loop in
   `show` (store only stashes `addr/len`). Balances the two budgets.
2. **Phase** — v1 ships a tiny `store` that proves only `slide` (frame + guard + `adr` + one
   `bl printk` ≈ 17 instr, fits easily); the largest unverified assumption (the `adr` slide leak)
   is broken first, cheaply.
3. **Trampoline** — `store` does magic-guard + a direct `b` into a confirmed-unused larger cave
   (rooms up to ~1796 B) holding the full interpreter. Only after verifying the cave is dead code.

## Safety / RKP boundary (web-confirmed)

Samsung RKP enforces **memory protection only** — page tables RO in the normal world (writable
only via the secure-world monitor), kernel code never writable, kernel data never executable. It
does **not** do behavioral monitoring of *what* legitimate code does. Therefore an exploit-free
REPL (RO `.text` code that reads memory, writes **non-protected** data, and calls **real**
function entries) is not something RKP detects or blocks. The only RKP walls are: writing
RKP-protected memory (`.text`/rodata/page-tables/cred) and creating RWX — none of which this
toolkit attempts. `peek` of RKP-write-protected regions still **reads** fine. Blind spots are
EL2 (RKP’s own memory) and EL3 (TrustZone), and unmapped physical memory (map first via `call`).

## Phased build plan (next steps, each its own unit)

1. **v1-slide** — ✅ **DONE / LIVE-PROVEN** (`build_kernel_tier2_repl_v1_slide.py`, image
   `boot_linux_tier2_repl_v1_slide.img` SHA256 `658a7d10…`). Minimal `store` stub: ROPP frame +
   magic-guard + `adr x1,.` self-PC + `bl printk`. Gate-2 disasm matched the design; flashed,
   booted clean (`selftest fail=0`); a magic-matched write to `force_no_nap` printed
   `A90SLIDE <runtime_pc>` to dmesg, and `slide = runtime_pc − (entry_vaddr + 40)` came out a
   single page-granular value, internally consistent (the `adr` at entry+0x28 reported
   entry_runtime+0x28). The `adr` self-PC slide leak is proven — the heavy V2216 perf/codeword
   method is not needed. Rolled back to clean V2321, `selftest fail=0`. (The raw per-boot slide
   is a runtime KASLR value and is deliberately kept out of this report.)
2. **v1-repl** — add `poke` (have it), small `peek`, and `call` (ROPP frame) with printk output,
   within the budget (split per D6 if needed). Validate `call` on a benign function
   (e.g. `call kallsyms_lookup_name("…")` and confirm = `link_addr + slide`).
3. **v2-bulk** — add `show`-buf output + kmalloc scratch for arbitrary-length `peek`.

## Open items / risks

- Room budget (D6) is the only hard constraint; phasing + split + trampoline cover it.
- `adr` self-PC slide leak is unproven *in our stub* (the principle is standard ARM; v1-slide
  proves it). It is the first thing to validate.
- `call` from sysfs-write context can crash if given context-inappropriate targets/args — this
  is a usage discipline, not a build blocker.

## Guardrails

- Exploit-free: no RKP bypass, no protected-memory write, no RWX, no CFP/JOPP/ROPP-site patch.
- Boot-partition-only via the checked flash helper with readback verify; V2321/V2237/V48 rollback
  gates; odin4 boot-only download-mode recovery proven.
- No forbidden-partition writes; no PMIC/GPIO/power writes.
- Reports carry no runtime pointers or slide; the slide and any leaked addresses stay out of
  committed artifacts.
- Device stays on clean V2321 until a build unit is explicitly run.
