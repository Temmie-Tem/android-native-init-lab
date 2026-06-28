# Kernel Security Tier-2 Runtime Kernel REPL v2a2 — Poke Round-Trip Source Gate

- Cycle: `TIER2_REPL_V2A2`
- Date: `2026-06-29`
- Decision: `tier2-repl-v2a2-poke-roundtrip-source-gate-pass` (host/source only; later LIVE attempt
  blocked by allocator ABI mismatch)
- Scope: extend the existing host driver for an allocator-backed `poke` -> `peek` round-trip over the
  already-live-proven v1-repl image. No new boot image and no new kernel `.text`.
- Driver: `workspace/public/src/scripts/revalidation/a90_repl.py`
- Test: `tests/test_a90_repl.py` (28 host-only tests after the live-ABI guard update)
- Live image to drive later: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
  SHA256 `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: clean V2321 SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

## What This Adds

`a90_repl.py` now has a `poke-roundtrip` subcommand. It reuses the v1-repl ops already proven live:

1. `op0 slide`
2. `op3 call __kmalloc(0x1000, GFP_KERNEL)`
3. `op2 poke(ptr, sentinelA, 8)` then `op1 peek(ptr, 8)`
4. `op2 poke(ptr, sentinelB, 8)` then `op1 peek(ptr, 8)`
5. optional `op2 poke(ptr, low32, 4)` then `op1 peek(ptr, 8)`
6. `op3 call kfree(ptr)`

The public JSON redacts raw runtime pointers and the per-boot slide. If `--evidence-dir` is supplied,
the driver writes raw values only to private evidence under `workspace/private/`.

## GFP_KERNEL Correction

The v2a2 charter had a stale cross-check note saying `GFP_KERNEL` should be `0x6c0`. The actual
checked-in A90 4.14 source at
`workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel/include/linux/gfp.h` says:

- `___GFP_IO = 0x40`
- `___GFP_FS = 0x80`
- `___GFP_DIRECT_RECLAIM = 0x400000`
- `___GFP_KSWAPD_RECLAIM = 0x1000000`

Therefore `GFP_KERNEL = __GFP_RECLAIM | __GFP_IO | __GFP_FS = 0x14000c0` for this tree. The driver
derives this from the header by default instead of copying a note.

## Host Validation

- `py_compile`: PASS for `a90_repl.py` and `tests/test_a90_repl.py`.
- `tests.test_a90_repl`: 28 PASS.
- `poke-roundtrip --help`: command surface present.
- Full `python3 -m unittest discover -s tests`: attempted, but the repository-wide suite is not green in
  this checkout (`3679` tests, `217` failures, `56` errors, `3` skipped). Representative errors are
  pre-existing private audio artifact dependencies such as missing
  `workspace/private/builds/audio/*/deploy-plan.json` and missing private
  `workspace/private/runs/audio/*/libacdbloader.so`; the focused v2a2 tests pass cleanly.
- Private v2a2 System.map regenerated under
  `workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/`.
- Symbol anchors from the regenerated map:
  - `printk @ 0xffffff800813d8cc`
  - `kgsl_pwrctrl_force_no_nap_store @ 0xffffff80089273b4`
  - `__kmalloc @ 0xffffff80082724bc`
  - `kfree @ 0xffffff800827276c`
- v1-repl image SHA remains `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- V2321 rollback image SHA remains `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.

## Live Follow-Up

The later live attempt is recorded separately in
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_LIVE_ALLOCATOR_ABI_BLOCKED_2026-06-29.md`.
It flashed the unchanged v1-repl image, reached clean health, but the allocator call faulted before
any `poke`: this kernel's recovered `__kmalloc` entry dereferences `x0` as a context/cache pointer
before the first helper call, so `__kmalloc(size, GFP_KERNEL)` is not a valid scalar direct-call ABI for
the v1-repl `op3` caller. The device was rolled back to clean V2321 with final `selftest fail=0`.
Do not rerun the direct `__kmalloc` path without a newly validated allocator target or a revised
owned-buffer mechanism.

## Original Live Command Shape

After flashing the unchanged v1-repl image and regenerating/using the private v2a2 System.map, the
original command shape was:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/a90_repl.py poke-roundtrip \
  --map workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/System.map \
  --evidence-dir workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/live-evidence
```

Live validation must restore `panic_on_oops=1`, roll back to clean V2321 via
`native_init_flash.py`, and require final `selftest fail=0`.

## Safety

- No new boot image was built.
- No device command or flash was run in this source gate.
- The future live `poke` writes only to a fresh `__kmalloc` buffer that the driver owns, then calls
  `kfree`; it never targets `.text`, rodata, page tables, cred, or any other protected object.
- No forbidden partition write, raw flash path, RKP bypass, RWX, grooming, UAF, spray, or power write.
- Raw runtime pointers and per-boot slide values stay out of committed artifacts.
