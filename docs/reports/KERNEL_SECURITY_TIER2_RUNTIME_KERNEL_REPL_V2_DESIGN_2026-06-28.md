# Kernel Security Tier-2 Runtime Kernel REPL — v2 design (DRAFT, for review)

- Cycle: `TIER2_REPL_V2`
- Date: `2026-06-28`
- Decision: `tier2-repl-v2-design-reviewed` (no build, no device action; Codex + operator design review folded in below)
- Scope: extend the live-proven v1-repl flash-once kernel REPL to named-symbol resolution,
  a store-landed `poke`→`peek` round-trip, and arbitrary-length `peek` output
- Base / rollback: clean V2321 (`ca978551…`)

## Where v1-repl left us (proven)

The flash-once REPL stub in `force_no_nap_store` (image `b846ae9f…`, commit f44b34c8) is
live-proven for four ops, output via plain `printk` (one result word per op):

- `op0 slide` → leaks the per-boot KASLR slide via `adr` self-PC.
- `op1 peek(addr, len≤8)` → one qword at `addr`.
- `op2 poke(addr, val, width)` → store executes (NULL-fault proven; identical `str` to the poke agent).
- `op3 call(target, x0..x7)` → `blr` a real JOPP entry, return value captured.

Gaps v2 should close:
1. **Named symbols.** Everything currently needs raw runtime addresses. We have `slide`, so any
   symbol's runtime address = `(in-image link vaddr) + slide` — but resolving the link vaddr needs the
   in-image kallsyms map, and `a90_stock_kallsyms_extract.py` currently fails ("kallsyms marker table
   not found"). Without it, `call kallsyms_lookup_name(...)` and named `peek`/`poke` are blocked.
2. **Store-landed `poke` round-trip.** v1 only proved the `op2` store *executes* (faults on a bad
   addr). A real `poke(X)=v` then `peek(X)==v` proof needs a *known writable* address `X`.
3. **Bulk `peek`.** `op1` returns one qword per call via `printk`. Dumping a struct/region is slow
   (one store-write + one dmesg read per qword) and noisy.

## The central constraint discovered during design

The natural fix for bulk output is to hijack the paired `force_no_nap_show` handler (108 B / 27 instr)
to write result bytes into its `buf` (a PAGE_SIZE kernfs page) and return a length, so `cat
/sys/.../force_no_nap` reads binary results. **But `show` receives no userspace input.** So the
store→show handoff (what to read, or the already-read bytes) must live in a **fixed writable kernel
location** that both the patched `store` and the patched `show` reach via PC-relative `adrp`
(slide-transparent). A `kmalloc`'d buffer cannot serve as the *handoff anchor* because `show` cannot be
told its address at call time.

So bulk-peek-via-show-buf has a hard prerequisite: **one safe, fixed, writable scratch anchor**
(as little as 8 bytes — enough to hold a `kmalloc`'d pointer). Finding a provably-unused writable
global needs the kallsyms map (symbol + size), which is currently broken. This dependency reorders the
plan.

## Proposed v2 plan (re-prioritized: host-tooling first, new image later)

### v2a — kallsyms-resolve + named-symbol REPL driver (host-only, NO reflash, highest ROI)
1. **Fix `a90_stock_kallsyms_extract.py`** ("marker table not found"). Likely cause to investigate:
   `CONFIG_KALLSYMS_BASE_RELATIVE` (address table stored as 32-bit offsets + `kallsyms_relative_base`)
   and/or a markers-table stride/format mismatch vs the extractor's assumptions for this 4.14 build.
   Validate by spot-checking known symbols (`force_no_nap_store` link `0xffffff80089273b4`,
   `kgsl_pwrctrl_num_pwrlevels_show`, plain `printk` `0xffffff800813d8cc`).
2. **Build a host-side `a90_repl.py` driver** that, given the live per-boot `slide` (from `op0`),
   resolves a symbol name → link vaddr (from the fixed extractor) → runtime addr, and drives the
   **existing v1-repl image** over the bridge for: named `peek`, named `call` (incl.
   `call kallsyms_lookup_name("X")` and cross-checking its return == `link(X)+slide`), and a
   **store-landed `poke`→`peek` round-trip** on a benign, restore-after writable global (e.g. a
   debug/counter symbol with a known safe value), restoring it afterward.
   - This validates the full REPL semantics with **no new boot image** — the v1-repl image already on
     the shelf is sufficient. Pure host tooling + bridge driving.

### v2b — show-buf bulk peek (needs a new image + the fixed scratch anchor)
Only after v2a proves named resolution and we can safely identify a scratch:
1. **Pick the scratch anchor.** Options, to be decided in v2a once kallsyms works:
   - (preferred) a small (8-byte) safe writable global to cache a `kmalloc`'d bulk buffer pointer:
     first `op3 call __kmalloc(0x1000, GFP_KERNEL)`, `op2 poke` the pointer into the anchor, then `show`
     reads the anchor → the bulk buffer.
   - (alt) a provably-unused ≥4 KB writable `.bss` region used directly as the bulk buffer.
2. **Patch `force_no_nap_show`** to: load the anchor via `adrp`, and copy `len` bytes from the
   scratch/buffer into `buf`, return `len`. (Loop fits in 27 instr.)
3. **Extend `store`**: a new `op4 peek_bulk(addr, len)` that copies `addr..addr+len` into the scratch
   buffer (or stashes `addr/len` for `show` to read directly). Reuses v1 budget discipline (D6 split).
4. Live-validate: bulk `peek` of a known kernel region via `cat`, bytes == image/known; round-trip;
   rollback V2321 `fail=0`.

### Fallback if a safe fixed scratch cannot be justified
Bulk peek degrades to a **host-side printk loop** over `op1` (N calls, parse N dmesg lines) — already
possible with v1-repl, no new image. v2b becomes optional polish, not a blocker.

## Open questions for review

1. Is the **re-prioritization** right — fix kallsyms + host driver (v2a) before any new image (v2b)?
   v2a unblocks named symbols + the store-landed round-trip with zero reflash; v2b only improves bulk
   output ergonomics and carries the unsolved fixed-scratch risk.
2. Is the **fixed-scratch-anchor** analysis correct, or is there a slide-free handoff that avoids a
   baked-in writable global entirely (e.g. encoding state where both `store` and `show` can recompute
   it)? Is the 8-byte-anchor-for-a-kmalloc-pointer the minimal safe surface?
3. For the **store-landed poke round-trip** in v2a, what is the safest *benign, restorable* writable
   global to use as the target (read original, poke test value, peek, restore), so we never leave the
   kernel mutated? Candidates and their risk.
4. Any **RKP / context** subtlety in calling `__kmalloc(GFP_KERNEL)` from the sysfs-write process
   context, or in the `show` handler doing a bulk `copy_to`-style loop into the kernfs page?
5. Should `op2 poke` keep its current "store executes" status, or is a real landed round-trip required
   before we consider the `poke` op fully proven?

## Design review outcome (2026-06-28, Codex critique + operator synthesis)

Codex (`task-mqxvvjd4-twxeiq`, read-only, cross-checked against the SM-A908N kernel source) and the
operator both reviewed the draft above. Verdict: the re-prioritization is directionally right, with
these accepted corrections — the FINAL v2 plan supersedes the draft plan above where they differ.

**Accepted changes**
1. **Language fix:** v2a is *"no new boot image,"* not *"host-only / no reflash."* The device is
   currently on clean V2321, so live v2a still **flashes the existing v1-repl candidate** (`b846ae9f…`)
   through the normal gates. Only the *building* of a new image is avoided.
2. **Primary `poke` round-trip target = a fresh `__kmalloc` allocation, not a global.** Do
   `op3 call __kmalloc(0x1000, GFP_KERNEL)` → `op2 poke` into it → `op1 peek` it back → `op3 call kfree`.
   This corrupts no scheduler/security/device state, and the same buffer doubles as the **kernel-resident
   string buffer** for `call kallsyms_lookup_name(buf_ptr)` (poke the symbol name bytes into it first).
   Poking an existing global is **fallback only**, and only a debug-only 32-bit knob (e.g.
   `trace_printk_enabled`) with read-original→poke→peek→**auto-restore**; NEVER `panic_on_oops`/
   `panic_on_warn`/sysrq/scheduler/RKP/SELinux/cred/KGSL-power fields.
3. **`GFP_KERNEL` exact value must be derived for THIS build** from `include/linux/gfp.h`
   (`__GFP_RECLAIM | __GFP_IO | __GFP_FS`), not guessed.
4. **The fixed-scratch claim was overstated** (but the practical conclusion holds): `show(dev,attr,buf)`
   and `store(dev,attr,buf,count)` *both* receive `dev` and `attr`, so a slide-free handoff via a field
   in the KGSL `dev` object or via `attr` is theoretically possible — but both are **unsafe** (unproven
   field path; `attr` holds sysfs metadata/function pointers). `kernfs_open_file->priv` exists but the
   device show/store don't receive `of` (would need patching sysfs core = too broad). per-cpu/per-task
   is fragile across `echo`/`cat`/migration. So persistent state is genuinely required, and the **default
   bulk-peek path is the host-side printk loop over `op1`** (no new image, no new mutable state); the
   8-byte-anchor-caching-a-`kmalloc`-pointer is preferred only IF v2b is later justified.
5. **v1 store has zero slack** (exactly 212 B). "Add `op4`" is **not a small patch** — it forces a
   `store` body replacement / `store`↔`show` split / trampoline into a confirmed-unused cave.

**Final v2 plan (supersedes the draft plan)**
- **v2a0 — validate the symbol map (host-only).** Codex found existing artifacts
  `workspace/private/tmp/tier2c/kallsyms_v2321/stock-kallsyms.json` and
  `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`; **try these first** and spot-check
  against known link addrs (`force_no_nap_store 0xffffff80089273b4`, plain `printk 0xffffff800813d8cc`).
  Only if they don't validate do we fix `a90_stock_kallsyms_extract.py` ("marker table not found",
  likely `CONFIG_KALLSYMS_BASE_RELATIVE`/markers-stride).
- **v2a1 — host REPL driver over the existing v1-repl image.** `a90_repl.py`: get live `slide` (`op0`),
  resolve name→link→runtime, drive named `peek`/`call` over the bridge (flash v1-repl, validate,
  rollback V2321). Cross-check `call kallsyms_lookup_name(name_in_kmalloc)` == `link(name)+slide`.
- **v2a2 — landed `poke` proof via kmalloc.** `__kmalloc → poke → peek(==val) → kfree`; closes the
  one v1 gap (store-landed) with zero state mutation.
- **v2b — show-buf bulk peek (BLOCKED).** Only after a concrete scratch anchor + cleanup protocol are
  proven; otherwise the printk loop is the shipping bulk path. New image; `show` becomes non-leaf →
  full ROPP discipline; bulk copy needs length-bound (< PAGE_SIZE), null/magic checks, stale-state
  handling, and a bad-source-address policy (prefer `probe_kernel_read`-style, else explicit
  panic_on_oops handling).

**Red-flag build-blockers (binding):** no fixed-scratch proof → no v2b build; broken/unvalidated
kallsyms → no named driver; any plan that mutates an existing global without automatic restore; any
`show` path calling helpers without ROPP; any bulk-copy without length bounds + null/magic + bad-address
policy. A `kmalloc`-backed round-trip that forgets `kfree` leaks kernel memory until reboot — always pair
alloc/free.

## Guardrails (unchanged)

Exploit-free RECON: no RKP bypass, no protected-memory write, no RWX, no `ret`/`blr`/CFP-site patch,
preserve `x17`, magic-guard every hijacked handler. Boot-partition-only via `native_init_flash.py` with
pinned + readback SHA; rollback V2321. Gate-2 disasm before any flash. Keep raw runtime pointers and the
per-boot slide out of committed artifacts. Operator/loop split: Codex host-builds + self-Gate-2s, the
operator re-Gate-2s and runs the live half (the codex sandbox has no bridge access).
