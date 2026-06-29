# Kernel Security Tier-2 Runtime Kernel REPL U4 - Perf + Runbook Close

- Date: `2026-06-29`
- Scope: host-only U4 polish for the runtime kernel REPL tooling
- Device action: none
- Flash / boot image change: none
- Network dependency: none

## Changes

`workspace/public/src/scripts/revalidation/a90_repl.py` now keeps the U3 verdict logic but removes
the repeated broad scans that made family sweeps slow:

- `lookup_source_signature()` first checks symbol-specific or family-specific source hints and
  returns immediately when an authoritative declaration is found.
- Source file text is cached per process.
- Non-C identifiers such as dotted local clone symbols are rejected before invoking `rg`.
- Direct BL xref counting is indexed once per raw kernel image, then reused for each symbol.

The runbook was added at
`docs/operations/NATIVE_INIT_RUNTIME_KERNEL_REPL_RUNBOOK.md`.

## Correctness-Pinned Verdicts

Allocator sweep:

- Command: `call-safety-sweep --family allocator --limit 80 --no-objdump`
- Elapsed: `6.10s`
- Swept symbols: `28`
- `candidate_safe_ranked`: `['ksize']`
- `kmem_cache_init`: dropped by `source-__init-annotation`
- `kfree_const`: dropped by `unseeded-arg-memory-flow-without-gate-pointer-contract`
- `kmem_cache_shrink`: dropped by `unseeded-arg-memory-flow-without-gate-pointer-contract`
- `kfree_skb_partial`: dropped by `unseeded-arg-memory-flow-without-gate-pointer-contract`

Read-I/O sweep:

- Command: `call-safety-sweep --family read-io --limit 40 --no-objdump`
- Elapsed: `4.76s`
- Swept symbols: `40`
- `candidate_safe_ranked`: `['filp_close', 'filp_open', 'kernel_read']`

Representative source lookup:

- `ksize`: `candidate_scan_strategy=hint`, `candidate_file_count=1`, selected
  `include/linux/slab.h`, signature `size_t ksize(const void *)`

## Regression Coverage

Added tests pinning:

- `lookup_source_signature('ksize')` still returns `found=True`, `has_pointer_arg=True`, and uses
  the hint-fast path.
- Allocator family candidates stay exactly `['ksize']`.
- Read-I/O family candidates stay exactly `['filp_close', 'filp_open', 'kernel_read']`.
- The U3 drop reasons for `kmem_cache_init`, `kfree_skb_partial`, `kfree_const`, and
  `kmem_cache_shrink` remain enforced.

## Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --no-objdump \
  --family allocator \
  --limit 80

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --no-objdump \
  --family read-io \
  --limit 40

git diff --check
```

Results:

- `py_compile`: PASS
- `CallSafetyClassificationTests`: `13/13` PASS
- Full `tests.test_a90_repl`: `63/63` PASS
- Allocator sweep: PASS, verdict unchanged
- Read-I/O sweep: PASS, verdict unchanged
- `git diff --check`: PASS

## Safety Notes

This unit did not contact the device, did not flash, did not mutate a boot image, and did not run
any live REPL op. The advisory/firewall model is unchanged: sweep candidates do not mutate
`CALL_SAFETY_SEEDS` and do not become runtime-callable without a separate one-target live-call gate.
