# Kernel Security Tier-2 Runtime Kernel REPL v2a2R' - Allocator Export Recovery

- Date: 2026-06-29
- Decision: `a90-repl-v2a2rp-allocator-export-recovery-pass`
- Scope: host-only recovery of ground-truth allocator addresses for the existing v1-repl image.
- Device action: none.
- Private evidence: `workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/export-recovery-v2a2rp/a90_repl_evidence.json`

## Correction

The v2a2 live blocker was not an allocator ABI problem. The recovered System.map still mislabels the
mm/slab region. The previously used map entries for `__kmalloc`, `kfree`, and related slab symbols point
to functions with zero direct `bl` xrefs and mismatched first-block semantics.

The `x0` dereference guard remains useful: it correctly rejects the mislabeled `__kmalloc` entry. It is
not evidence that real allocator entries are unsafe to call.

## Recovery Method

`a90_repl.py allocator-export-recovery` now recovers allocator addresses from the static boot image by:

1. Finding exact exported symbol strings such as `__kmalloc\0` and `kfree\0`.
2. Finding aligned qword references to those strings.
3. Selecting nearby JOPP text entries referenced from the same export record neighborhood.
4. Verifying no pre-first-`BL` `x0` dereference.
5. Counting direct `bl` xrefs as a semantic identity check.

The map's `__ksymtab_*` labels are also drifted for this region: the raw image qword at the mapped
`__ksymtab___kmalloc` and `__ksymtab_kfree` addresses is `0x0`, so those labels cannot be used as
ground truth.

## Result

Recovered link addresses:

- `__kmalloc`: `0xffffff800826ae34`
- `kfree`: `0xffffff800826b354`
- `kmalloc_order`: `0xffffff8008238444`
- `kmalloc_order_trace`: `0xffffff8008238484`

Validation signals:

- `__kmalloc`: JOPP entry, no pre-first-`BL` `x0` dereference, direct `bl` xrefs = `1765`.
- `kfree`: JOPP entry, no pre-first-`BL` `x0` dereference, direct `bl` xrefs = `10596`.
- Both required symbols mismatch the current System.map labels, as expected.

## Code Changes

- Added `allocator-export-recovery` host-only subcommand.
- Added `poke-roundtrip --use-recovered-allocator-exports` so the existing v1-repl image can run v2a2
  with recovered allocator addresses after operator disasm cross-check.
- Kept the existing direct-map `poke-roundtrip` guard; without the recovered-export flag it still rejects
  the mislabeled map `__kmalloc` before live.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_a90_repl -v

PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_repl.py allocator-export-recovery \
    --map workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/System.map \
    --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
    --evidence-dir workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/export-recovery-v2a2rp
```

Results:

- `py_compile`: PASS
- `tests.test_a90_repl`: `31/31 PASS`
- `allocator-export-recovery`: PASS, recovered required allocator addresses above.

## Next

Operator should independently disassemble/cross-check `0xffffff800826ae34` and `0xffffff800826b354`.
Only after that check, rerun the existing-image live v2a2 proof with:

```sh
python3 workspace/public/src/scripts/revalidation/a90_repl.py poke-roundtrip \
  --map workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --use-recovered-allocator-exports \
  --evidence-dir workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/live-evidence
```

The live rerun still requires the normal flash gates, health check, `panic_on_oops` restore, rollback to
v2321, and final `selftest fail=0`.
