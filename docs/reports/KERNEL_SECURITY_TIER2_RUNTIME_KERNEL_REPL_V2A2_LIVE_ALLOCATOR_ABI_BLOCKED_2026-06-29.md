# Kernel Security Tier-2 Runtime Kernel REPL v2a2 - Live Allocator ABI Blocked

- Cycle: `TIER2_REPL_V2A2`
- Date: `2026-06-29`
- Decision: `tier2-repl-v2a2-live-allocator-abi-blocked`
- Scope: live attempt of the source-gated `poke-roundtrip` driver over the unchanged v1-repl image.
- Candidate image: `boot_linux_tier2_repl_v1_repl.img`,
  SHA256 `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: clean V2321,
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Public report policy: raw per-boot slide and runtime pointers redacted.

## Live Result

The v1-repl image was flashed through `native_init_flash.py` after rollback preconditions were
confirmed. Post-flash `version`/`status`/`selftest` were clean (`selftest fail=0`).

The first `poke-roundtrip` run timed out while setting `panic_on_oops=0`; the device stayed reachable
and the setting had landed. A retry reached the allocator call and failed before any `poke` happened:
the REPL did not capture an `A90R` return for `op3 call __kmalloc(...)`. A bounded dmesg read showed an
Oops at fault address `0x1048` with `lr` in the v1-repl `force_no_nap_store` caller.

## Root Cause

The live fault matches the static instruction stream for the recovered `__kmalloc` entry in the
v1-repl boot image:

- `__kmalloc @ 0xffffff80082724bc` is JOPP-shaped (`entry-4 == 0x00be7bad`).
- Its prologue saves `x0` then executes `ldr x23, [x0, #72]` before the first helper call.
- The v2a2 source-gate driver called it as `__kmalloc(size=0x1000, flags=GFP_KERNEL)`.
- Therefore the first dereference is `0x1000 + 0x48 == 0x1048`, exactly the observed fault address.

So the named map proof from v2a1 proved address resolution, not the callable allocator ABI. This
kernel's recovered `__kmalloc` symbol is not safe to call through the generic v1-repl `op3` scalar
calling convention as `(size, flags)`.

## Cleanup / Recovery

No owned-buffer `poke` executed. `panic_on_oops` was restored to `1`. The device was rolled back through
the checked helper to clean V2321; helper readback SHA matched `ca978551...`, `version/status` passed,
and final `selftest verbose` reported `pass=11 warn=1 fail=0`. A later direct check showed
`panic_on_oops=1`.

## Code Guard Added

`a90_repl.py` now rejects this unsafe path before live execution: for scalar allocator candidates it
scans the static image entry and fails host-side if the candidate dereferences `x0` before the first
`BL`. The current v1-repl `__kmalloc` is rejected by that guard.

## Next Bounded Action

Do not rerun direct `call __kmalloc(size, GFP_KERNEL)`. The next unit should be host-only unless a new
boot artifact is explicitly designed: find a callable owned-buffer strategy by static ABI validation
first, or replace the v2a2 plan with a small bounded helper that creates/returns a scratch buffer under
the same flash gates.
