# KERNEL SECURITY Tier-2 Runtime Kernel REPL U3 Gate-2 Source Verdict Wiring

Date: 2026-06-29

Scope: host-only correction to U3 advisory candidate filtering. No device action, no live calls, no flash, no boot-image change, no network dependency.

## Result

The source pointer verdict is now wired into candidacy.

Previous behavior only blocked non-seeded candidates when disasm taint found arg-derived memory-base flow. That missed source-declared pointer consumers when disasm under-approximated their dereference. The advisory blocker now uses:

```text
source pointer_arg_indices union disasm arg-memory-flow indices
```

For any non-seeded symbol, if that union is not covered by a vetted gate pointer contract, the row gets `unseeded-arg-memory-flow-without-gate-pointer-contract` and cannot be `candidate_safe`.

Rows now also expose source evidence directly:

- `source_signature`
- `source_annotation_flags`
- `source_evidence`

## Targeted Evidence

Allocator re-sweep:

- Command: `call-safety-sweep --family allocator --limit 80 --no-objdump`
- Rows: 28
- `candidate_safe_count=1`
- Candidate list: `ksize`
- `host_only=true`, `device_action=false`, `network_dependency=false`

Important rows:

- `ksize`: seeded gate pointer contract, source signature `size_t ksize(const void *)`, source pointer `[0]`, remains `candidate_safe=true`
- `kfree_const`: source signature `extern void kfree_const(const void *x)`, source pointer `[0]`, union `[0]`, flag `unseeded-arg-memory-flow-without-gate-pointer-contract`, `candidate_safe=false`
- `kmem_cache_shrink`: source signature `int kmem_cache_shrink(struct kmem_cache *)`, source pointer `[0]`, union `[0]`, flag `unseeded-arg-memory-flow-without-gate-pointer-contract`, `candidate_safe=false`

Read-I/O re-sweep:

- Command: `call-safety-sweep --family read-io --limit 40 --no-objdump`
- Rows: 40
- `candidate_safe_count=3`
- Candidate list: `filp_close`, `filp_open`, `kernel_read`
- `host_only=true`, `device_action=false`, `network_dependency=false`

The read-I/O candidates are seeded or contract-backed pointer-call rows, preserving the firewall distinction between advisory source evidence and the runtime call gate.

## Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl.CallSafetyClassificationTests
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel --no-objdump --family allocator --limit 80
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel --no-objdump --family read-io --limit 40
```

Results:

- `py_compile`: PASS
- `CallSafetyClassificationTests`: 12/12 PASS
- Full `tests.test_a90_repl`: 62/62 PASS
- Allocator re-sweep: PASS, only `ksize` remains candidate-safe
- Read-I/O re-sweep: PASS, seeded/contract-backed candidates remain

## Safety Notes

The runtime firewall remains unchanged. Sweep output stays advisory, does not mutate `CALL_SAFETY_SEEDS`, and does not widen `auto_call_allowed`. No device, bridge, flash helper, boot image, live call, or network path was touched.
