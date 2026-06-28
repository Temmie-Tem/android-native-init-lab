# Kernel Security Tier-2 Runtime Kernel REPL v2a2R - Allocator ABI Audit

- Cycle: `TIER2_REPL_V2A2R`
- Date: `2026-06-29`
- Decision: `a90-repl-v2a2r-allocator-abi-audit-no-live-ready-scalar`
- Scope: host-only static ABI audit for replacing the invalid direct `__kmalloc(size,gfp)` v2a2 plan.
- Driver: `workspace/public/src/scripts/revalidation/a90_repl.py allocator-audit`
- Inputs: v1-repl boot image plus regenerated private v2a2 System.map.
- Private JSON evidence:
  `workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/allocator-abi-audit-v2a2r.json`

## Result

The audit classified 13 plausible owned-buffer allocator/free pairs from the v1-repl image. None are
live-ready for the generic v1-repl `op3 call(target,x0..x7)` scalar calling convention.

| Symbol | Free pair | Result | Primary blocker |
| --- | --- | --- | --- |
| `__kmalloc` | `kfree` | rejected | pre-call `x0` deref at `+0x38`, imm `0x48` |
| `__get_free_pages` | `free_pages` | rejected | pre-call `x0` deref at `+0x2c`, imm `0x48` |
| `get_zeroed_page` | `free_pages` | rejected | pre-call `x0` deref at `+0x30`, imm `0x78` |
| `alloc_pages_exact` | `free_pages_exact` | rejected | pre-call `x0` deref at `+0x20`, imm `0x20` |
| `__alloc_pages_nodemask` | `__free_pages` | rejected | pre-call `x0` deref; also returns `struct page`, not a writable VA |
| `kmalloc_order` | `kfree` | rejected | recovered path is not accepted as pointer-return scalar allocator |
| `kmalloc_order_trace` | `kfree` | rejected | trace/bookkeeping-shaped path, not live-ready |
| `vmalloc` | `vfree` | rejected | leaf/global-return thunk in this image, not `vmalloc(size)` |
| `__vmalloc` | `vfree` | rejected | pre-call `x0` deref at `+0x20` |
| `kvmalloc_node` | `kvfree` | rejected | pre-call `x0` deref at `+0x0c`, imm `0xa0` |
| `kmem_cache_alloc` | `kmem_cache_free` | rejected | `x0` is a cache pointer, not a size |
| `kmem_cache_alloc_trace` | `kmem_cache_free` | rejected | `x0` is a cache pointer, not a size |
| `mempool_kmalloc` | `mempool_kfree` | rejected | mempool helper ABI needs pool data |

## Interpretation

The direct allocator substitution path is saturated for the current v1-repl image. The original v2a2
requirements still stand at the semantic level (prove an owned-buffer `poke` -> `peek` -> cleanup
round-trip), but the existing exported allocator names do not provide a safe scalar ABI target for
`op3`.

## Code Changes

`a90_repl.py` now exposes `allocator-audit`, a host-only command that:

- checks JOPP entry shape,
- scans each candidate for `x0` dereference before the first helper call,
- marks known pointer-argument or non-pointer-return wrappers as not live-ready,
- emits redacted JSON with no runtime pointers or per-boot slide.

The focused unit tests now pin the audit result: 13 candidates, zero live-ready scalar allocator targets.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl -v`
  - Result: 29 tests PASS.
- Host-only command:
  `a90_repl.py allocator-audit --map workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
  - Result: `live_ready_candidates=[]`, decision `a90-repl-v2a2r-allocator-abi-audit-no-live-ready-scalar`.

## Next

Move v2a2 forward with a revised owned-buffer mechanism. The lowest-risk next unit is a new small
helper image that adds an explicit scratch-buffer op or call target with a known ABI, then Gate-2 it and
run the original store-landed `poke` round-trip against that owned scratch. Do not rerun direct allocator
calls from the current v1-repl image.
