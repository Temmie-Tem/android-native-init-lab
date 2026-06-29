# Native-Init Runtime Kernel REPL Runbook

Date: 2026-06-29

Scope: Tier-2 runtime kernel REPL host tooling for the already-built v1-repl image. This document
is operational guidance only; it does not authorize device work by itself.

## Canonical Inputs

- Driver: `workspace/public/src/scripts/revalidation/a90_repl.py`
- Kallsyms extractor: `workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py`
- Verified map: `workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map`
- v1-repl image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- v2321 rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Source oracle root: `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel`
- Private evidence dir pattern: `workspace/private/runs/kernel/<unit>/`

Use `PYTHONPYCACHEPREFIX=/tmp/a90_pycache` for local validation because repo-local pycache
ownership can be hostile.

## Verified Map Regeneration

Regenerate the corrected v2321 map from the boot image:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py \
  --kernel workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
  --out-map /tmp/a90_v2321_verified.System.map \
  --out-json /tmp/a90_v2321_verified.json
```

The promoted extractor must preserve the C2B padding fix and printk xref disambiguation:

- `padding_before_relative_base=380` accounts for the 95 zero dwords before the base-relative
  address table.
- `printk` is the max-direct-BL variadic wrapper, not the low-xref twin.

Four anchor link addresses:

| Symbol | Expected link address |
| --- | --- |
| `printk` | `0xffffff800813adfc` |
| `__kmalloc` | `0xffffff800826ae34` |
| `kfree` | `0xffffff800826b354` |
| `kgsl_pwrctrl_force_no_nap_store` | `0xffffff80089273b4` |

Ground truth uses three oracles together:

1. C2B corrected kallsyms decode, including base-relative padding.
2. C2E relocated `__ksymtab` export rows for exported symbols.
3. Static semantic/disassembly anchors, including JOPP entry checks, direct-BL xrefs, and the
   KGSL sysfs anchor.

If those disagree, treat the map as untrusted and fail closed.

## Host-Only Commands

Resolve a symbol from the map without touching the device:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py resolve \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  printk
```

Run the C1/call-safety classifier without live I/O:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  printk __kmalloc kfree ksize kallsyms_lookup_name commit_creds
```

Run advisory family sweeps:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --no-objdump \
  --family allocator \
  --limit 80
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --no-objdump \
  --family read-io \
  --limit 40
```

Run the relocated `__ksymtab` oracle:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py ksymtab-ground-truth \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Expected advisory family verdicts:

- Allocator: `candidate_safe_ranked == ['ksize']`.
- Read I/O: `candidate_safe_ranked == ['filp_close', 'filp_open', 'kernel_read']`.
- `kmem_cache_init` remains dropped by `source-__init-annotation`.
- `kfree_skb_partial`, `kfree_const`, and `kmem_cache_shrink` remain dropped by missing vetted
  gate pointer contracts.

## Live Commands

The following commands touch the live v1-repl device state and require the normal bridge/health
preflight plus rollback gate. They are not part of host-only sweeps.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py selftest \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --evidence-dir workspace/private/runs/kernel/<unit>/
```

Read-only runtime observations:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py peek \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  printk
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py read \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --len 64 \
  printk
```

Owned-buffer write proof only:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py poke \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  0xa90f00d1cafe0001
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py poke-roundtrip \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --evidence-dir workspace/private/runs/kernel/<unit>/
```

One-target live call gate:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  printk @repl_format
```

Before any live `call` unit:

- Confirm the device is already on the intended v1-repl image or flash only via
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Confirm `v2321`, `v2237`, and `v48` rollback images and recovery/TWRP availability.
- Set `panic_on_oops=0` only inside the bounded validation.
- Call one vetted target, check one result, and stop. Never mass-call candidates from a sweep.
- Roll back to v2321 when the unit requires a clean end state.

## Safety Model

- C1 identity resolution is fail-closed. A map label is not enough for a live call.
- Call-safety tiers are `SAFE-SCALAR`, `SAFE-WITH-VALID-PTR`, `CONTEXT-SENSITIVE`,
  `BEHAVIOR-CHANGING`, and `DENY`.
- `call-safety-sweep` is advisory. `candidate_safe_ranked` never mutates `CALL_SAFETY_SEEDS`
  and never opens the runtime `call` gate.
- `SAFE-WITH-VALID-PTR` requires verified pointer tokens such as `@repl_format` or
  `@owned_kmalloc_ptr`; arbitrary scalar addresses are refused.
- `DENY` cannot be overridden. Non-DENY override requires the exact explicit token and remains
  an operator-gated exception.
- Raw runtime pointers, the per-boot slide, raw logs, boot images, and private evidence stay under
  `workspace/private/` and out of commits.
