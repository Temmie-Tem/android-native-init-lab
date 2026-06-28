# Kernel Security Tier-2 Runtime Kernel REPL U2 - Call-Safety Classifier

- Date: 2026-06-29
- Unit: `REPL U2`
- Decision: `a90-repl-u2-call-safety-classifier-host-pass`
- Device action: no
- Boot image changed: no
- Public code:
  - `workspace/public/src/scripts/revalidation/a90_repl.py`
  - `tests/test_a90_repl.py`

## Objective

Add a host-only, disassembly-backed call-safety inventory for the runtime
kernel REPL. Address identity was already settled by v2c/C2E; this unit adds a
separate safety gate so a known address is not automatically treated as a safe
live call target.

## Implementation

- Added `call-safety-classify` to `a90_repl.py`.
- Classification runs C1 identity resolution first, then records static signals:
  early argument-register dereferences, BL targets, context-sensitive lock/IRQ/
  sleep calls, leaf/non-leaf shape, direct-BL xrefs, printk variadic prologue
  matching, and an optional `aarch64-linux-gnu-objdump` excerpt.
- Added DENY-by-default seed inventory:
  - `SAFE-SCALAR`: `__kmalloc`, `kfree`
  - `SAFE-WITH-VALID-PTR`: `printk`, `ksize`, `kmem_cache_alloc`,
    `kmem_cache_free`, `kernel_read`, `filp_open`, `filp_close`
  - `BEHAVIOR-CHANGING`: `commit_creds`, `prepare_kernel_cred`,
    `set_memory_x`, `call_usermodehelper_exec`
  - `DENY`: `kallsyms_lookup_name`
- Extended C1 identity resolution for the classifier so required pointer-arg
  dereferences are not misread as identity failure for `SAFE-WITH-VALID-PTR`
  seeds. Scalar-call resolution remains fail-closed by default.
- Wired the `call` path through `require_call_safety_for_call()` before any
  serial transport action. `SAFE-WITH-VALID-PTR` calls require `@...` pointer
  tokens for the declared pointer args. `DENY` cannot be overridden.
- Added exact-token override for non-DENY unvetted calls:
  `A90_REPL_U2_ALLOW_UNVETTED_STATIC_ONLY`.

## Static Smoke

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
    --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
    --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
    --no-objdump \
    printk __kmalloc kfree kallsyms_lookup_name commit_creds prepare_kernel_cred \
    set_memory_x call_usermodehelper_exec kernel_read filp_open filp_close \
    kmem_cache_alloc kmem_cache_free ksize
```

Observed tier counts:

- `SAFE-SCALAR`: `2`
- `SAFE-WITH-VALID-PTR`: `7`
- `BEHAVIOR-CHANGING`: `4`
- `DENY`: `1`

Anchor results:

- `printk` -> `SAFE-WITH-VALID-PTR`, `0xffffff800813adfc` (not the
  `0xffffff800813d8cc` twin), direct-BL xrefs `44694`
- `__kmalloc` -> `SAFE-SCALAR`, `0xffffff800826ae34`
- `kfree` -> `SAFE-SCALAR`, `0xffffff800826b354`
- `kallsyms_lookup_name` -> `DENY`
- `commit_creds` / `prepare_kernel_cred` / `set_memory_x` /
  `call_usermodehelper_exec` -> `BEHAVIOR-CHANGING`

Objdump smoke for `printk` also passed:

```text
objdump_available=True
objdump_lines=40
```

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=tests \
  python3 -m unittest tests.test_a90_repl

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=tests \
  python3 -m unittest \
    tests.test_a90_stock_kallsyms_extract \
    tests.test_kernel_tier2_stage_c_direct_bl_printk \
    tests.test_kernel_tier2_repl_v1_repl \
    tests.test_kernel_tier2_kasan_lite_reclaim_dump
```

Results:

- `py_compile`: pass
- `tests.test_a90_repl`: `57/57` pass
- focused companion suite: `24/24` pass

## Boundary

This unit is host-only. It performs no live call-proof, no device action, and no
boot-image change. New SAFE classifications are static inventory only; live
proof of any new target remains a separate future gate.
