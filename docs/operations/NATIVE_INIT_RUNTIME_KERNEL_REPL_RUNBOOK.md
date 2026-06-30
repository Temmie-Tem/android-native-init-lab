# Native-Init Runtime Kernel REPL Runbook

Date: 2026-06-30

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

Owned-input proof for a vetted target:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  hex_to_bin
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  __sw_hweight8
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  __sw_hweight16
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  __sw_hweight32
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  hex2bin
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  bin2hex
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  parse_option_str
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strsep
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memzero_explicit
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  simple_strtoull
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtoull
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtoll
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtouint
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtou16
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtou8
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtos8
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtobool
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtoint
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrtos16
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  ksize
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  filp_open
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kernel_read
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strlen
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strnchr
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  skip_spaces
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strim
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strreplace
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strnlen
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strscpy
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strlcpy
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strcpy
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strlcat
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strncat
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strcat
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strncpy
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strchr
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strchrnul
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strstr
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strnstr
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  match_string
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  __sysfs_match_string
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  match_token
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  match_int
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  match_octal
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  match_strdup
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  sysfs_streq
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrdup
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kstrndup
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kmemdup
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  kmemdup_nul
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strpbrk
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strspn
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strcspn
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strcmp
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strcasecmp
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strncasecmp
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strncmp
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memcmp
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memchr
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memchr_inv
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memcpy
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memmove
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  strrchr
```

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/<unit>/ \
  memset
```

`call-proof` is not a mass-call mechanism. It owns the input object internally, performs the static
C1/source/call-safety checks, calls only the selected target, checks the return contract, frees the
owned allocations, and redacts the runtime slide/allocation pointers from public output. The
`hex_to_bin` is the scalar-only proof case: it calls the verified helper with fixed ASCII character
inputs, requires the expected decoded nibble for `0`, `9`, `a`/`A`, `f`/`F`, requires invalid `g` to
return 32-bit `-1`, and has no owned pointer setup or cleanup. The `__sw_hweight32` proof is also
scalar-only: it calls the verified helper with fixed 32-bit words, requires the expected population
count for zero, all-ones, alternating, single-high-bit, and mixed marker cases, and has no owned
pointer setup or cleanup. The `__sw_hweight16` and `__sw_hweight8` proofs are the same scalar-only
pattern for fixed 16-bit and 8-bit low-word inputs, requiring the expected population count for zero,
all-ones, alternating, single-high-bit, and mixed marker cases. The `hex2bin` proof allocates owned
destination and source buffers, writes a fixed even-length ASCII hex source, calls
`hex2bin(dst, src, count)`, requires return `0`, verifies the destination bytes match the decoded
source bytes, verifies the destination canary and source buffer stay unchanged, frees both buffers,
and redacts the owned pointers and observed raw bytes from public output. The `bin2hex` proof
allocates owned destination and source buffers, writes fixed binary source bytes, calls
`bin2hex(dst, src, count)`, requires the returned pointer to equal the destination plus `count*2`,
verifies lower-case ASCII hex output, verifies the destination canary and source buffer stay
unchanged, frees both buffers, and redacts the owned pointers and observed raw bytes from public
output. The `parse_option_str` proof allocates owned NUL-terminated comma-separated option and option
string buffers, requires an exact comma-delimited token hit to return `1`, requires a prefix-only token
and a missing token to return `0`, verifies both strings and canaries stay unchanged, frees both
buffers, and redacts the owned pointers and observed raw bytes from public output. The
`strsep` proof allocates an owned `char **` cursor slot, an owned mutable NUL-terminated string, and
an owned delimiter string, calls `strsep(&cursor, ",")` over `A90STRSEP-HEAD,Q-TAIL`, requires the
return to be the original string pointer at public offset `0`, requires the delimiter at offset `14`
to be replaced with NUL, requires the cursor slot to advance to offset `15`, verifies delimiter
immutability plus slot/string/delimiter canary preservation, frees all three buffers, and redacts
runtime/allocation pointer values and observed raw bytes. The
`simple_strtoull` proof allocates an owned NUL-terminated numeric string and an owned `char **` output
slot, calls `simple_strtoull("1234abcdZ", &endp, 16)`, requires return `0x1234abcd`, requires `endp`
to equal the owned input pointer plus offset `8`, verifies input immutability and end-slot canary
preservation, frees both buffers, and redacts runtime/allocation pointer values and observed raw bytes.
The `kstrtoull` proof allocates an owned NUL-terminated numeric string and an owned
`unsigned long long *` result slot, calls `kstrtoull("1234567890abcdef", 16, &res)`, requires return
`0`, requires `res` to equal `0x1234567890abcdef`, verifies input immutability and 8-byte
result-slot canary preservation, frees both buffers, and redacts runtime/allocation pointer values
and observed raw bytes. The `kstrtoll` proof allocates an owned NUL-terminated signed numeric string
and an owned `long long *` result slot, calls `kstrtoll("-1234567890abcdef", 16, &res)`, requires
return `0`, requires `res` to equal signed `-1311768467294899695` with raw `0xedcba9876f543211`,
verifies input immutability and 8-byte result-slot canary preservation, frees both buffers, and
redacts runtime/allocation pointer values and observed raw bytes. The `kstrtouint` proof allocates
an owned NUL-terminated numeric string and
an owned `unsigned int *` result slot, calls `kstrtouint("123456789", 10, &res)`, requires return
`0`, requires `res` to equal `123456789`, verifies input immutability and result-slot canary
preservation, frees both buffers, and redacts runtime/allocation pointer values and observed raw
bytes. The `kstrtou16` proof allocates an
owned NUL-terminated numeric string and an owned `u16 *` result slot, calls
`kstrtou16("54321", 10, &res)`, requires return `0`, requires `res` to equal unsigned `54321` with
raw `0xd431`, verifies input immutability and 2-byte result-slot canary preservation, frees both
buffers, and redacts runtime/allocation pointer values and observed raw bytes. The `kstrtou8` proof
allocates an owned NUL-terminated numeric string and an owned `u8 *` result slot, calls
`kstrtou8("213", 10, &res)`, requires return `0`, requires `res` to equal unsigned `213` with raw
`0xd5`, verifies input immutability and 1-byte result-slot canary preservation, frees both
buffers, and redacts runtime/allocation pointer values and observed raw bytes. The `kstrtos8` proof
allocates an owned NUL-terminated signed numeric string and an owned `s8 *` result slot, calls
`kstrtos8("-85", 10, &res)`, requires return `0`, requires `res` to equal signed `-85` with raw
`0xab`, verifies input immutability and 1-byte result-slot canary preservation, frees both
buffers, and redacts runtime/allocation pointer values and observed raw bytes. The `kstrtobool` proof
allocates an owned NUL-terminated bool string and an owned `bool *` result slot, calls
`kstrtobool("Y", &res)`, requires return `0`, requires `res` to equal `true` with raw `0x01`,
verifies input immutability and 1-byte result-slot canary preservation, frees both buffers, and
redacts runtime/allocation pointer values and observed raw bytes. The `kstrtoint` proof
allocates an owned NUL-terminated signed numeric string and an owned `int *` result slot, calls
`kstrtoint("-12345", 10, &res)`, requires return `0`, requires `res` to equal signed `-12345` with
raw `0xffffcfc7`, verifies input immutability and result-slot canary preservation, frees both
buffers, and redacts runtime/allocation pointer values and observed raw bytes. The `kstrtos16` proof
allocates an owned NUL-terminated signed numeric string and an owned `s16 *` result slot, calls
`kstrtos16("-1234", 10, &res)`, requires return `0`, requires `res` to equal signed `-1234` with raw
`0xfb2e`, verifies input immutability and 2-byte result-slot canary preservation, frees both buffers,
and redacts runtime/allocation pointer values and observed raw bytes.
The `kernel_read` proof opens `/init`, reads 16 bytes into an owned buffer with an owned `loff_t *`
position, requires ELF magic plus position advancement, closes the file, and frees all owned buffers.
The `strlen` proof writes an owned NUL-terminated string buffer, requires exact length return, and
frees the owned buffer. The `strnchr` proof allocates one owned NUL-terminated string buffer, searches
for a scalar byte with a bounded count, requires the returned pointer at the expected offset, reruns
with a count ending immediately before that byte and requires `0`, verifies string and canary
immutability, frees the buffer, and redacts the owned pointer and observed raw bytes from public output.
The `skip_spaces` proof writes an owned NUL-terminated string buffer with
leading ASCII spaces, requires the returned pointer to match the expected first non-space offset,
rewrites the same owned buffer with no leading spaces, requires the original pointer to be returned,
verifies string and canary immutability after both calls, and redacts the owned pointer and observed
raw bytes from public output. The `strim` proof writes an owned mutable NUL-terminated string buffer
with leading and trailing ASCII spaces, requires the returned pointer to match the expected first
non-space offset, verifies the first trailing space was replaced with NUL and the canary was preserved,
then rewrites the buffer with a clean no-space string, requires the original pointer to be returned,
and redacts the owned pointer and observed raw bytes from public output. The `strreplace` proof writes
an owned mutable NUL-terminated string buffer, replaces a scalar old byte with a scalar new byte,
requires the returned pointer to match the owned NUL terminator offset, verifies the bounded byte
replacement and canary preservation, then checks a missing-byte no-op case. The `strnlen` proof uses the same owned-string pattern with a scalar `maxlen`
and requires exact bounded length return. The `strscpy` proof allocates owned destination and source
buffers, bounds the size inside the destination, requires exact copied length, verifies the destination
prefix and post-size canary, and frees both buffers. The `strlcpy` proof uses the same owned-buffer
shape, but requires exact source length return because `strlcpy` returns `strlen(src)`. The `strcpy`
proof allocates owned destination and source buffers, requires the returned pointer to match the owned
destination pointer, verifies the destination matches the source including the NUL byte, verifies the
post-NUL tail and canary stay unchanged, verifies source immutability, and frees both buffers. The
`strncat` proof allocates an owned mutable destination string plus an owned source string, passes a
scalar bounded count, requires the returned pointer to match the owned destination pointer, verifies
the destination contains the original prefix plus only the count-bounded source prefix followed by NUL,
verifies post-NUL tail/canary preservation, verifies source immutability, and frees both buffers. The
`strlcat` proof allocates an owned mutable destination string plus an owned source string, passes a
scalar bounded size greater than the destination length, requires return `strlen(dst)+strlen(src)`,
verifies the destination contains the original prefix plus only the size-bounded source prefix followed
by NUL, verifies post-NUL tail/canary preservation, verifies source immutability, and frees both
buffers. The
`strcat` proof allocates an owned mutable destination string plus an owned source string, requires the
returned pointer to match the owned destination pointer, verifies the destination contains the original
prefix plus source including the NUL byte, verifies post-NUL tail/canary preservation, verifies source
immutability, and frees both buffers. The `strncpy` proof also uses owned destination and source
buffers, but requires the returned pointer to match the owned destination pointer, verifies NUL padding
up to the bounded count, verifies the post-count canary, and redacts the runtime pointer value from
public output. The `strchr` proof
allocates one owned NUL-terminated string buffer, searches for a byte that appears multiple times, requires the returned
pointer to match the expected first-occurrence offset, checks a missing byte returns `0`, verifies the
string and canary stay unchanged, and redacts the owned pointer and observed raw bytes from public
output. The `strchrnul` proof uses the same owned-string shape, but checks a missing byte returns the
owned string NUL-terminator pointer instead of `0`, verifies the string and canary stay unchanged, and
redacts the owned pointer and observed raw bytes from public output. The `strstr` proof allocates owned
haystack and needle strings, requires the present needle to return the expected haystack offset, rewrites
the needle buffer to a missing string and requires `0`, verifies both strings and canaries stay unchanged,
frees both buffers, and redacts the owned pointers and observed raw bytes from public output. The
`strnstr` proof uses the same owned haystack/needle shape plus a scalar bounded length inside the
haystack, requires the present needle to return the expected haystack offset when the length covers it,
requires `0` when the bounded length excludes one needle byte, rewrites the needle buffer to a missing
string and requires `0`, verifies both strings and canaries stay unchanged, frees both buffers, and
redacts the owned pointers and observed raw bytes from public output. The `match_string` proof builds
one owned layout containing a bounded `const char *` array and owned NUL-terminated string entries,
requires the search string to return the expected array index, rewrites the search string to a missing
value and requires 32-bit `-EINVAL`, verifies zero-count also returns 32-bit `-EINVAL`, verifies the
pointer table, strings, search string, and canaries stay unchanged, frees the layout, and redacts the
owned pointer and observed raw bytes from public output. The `__sysfs_match_string` proof builds the
same owned array/search layout shape but uses a search string with one trailing newline, requires the
sysfs newline-tolerant hit to return index `1`, rewrites the search string to a missing value and
requires 32-bit `-EINVAL`, verifies zero-count also returns 32-bit `-EINVAL`, verifies the table,
items, search string, and canaries stay unchanged, frees the layout, and redacts runtime pointers and
observed raw bytes from public output. The `match_token` proof builds one owned
layout containing a mutable option string, one 16-byte-entry `match_token` table with an exact
no-`%` pattern plus NULL-pattern terminator, and an owned `substring_t args[MAX_OPT_ARGS]` region,
calls `match_token`, requires the exact-pattern token `0x4a90`, verifies the table, args, input
string, pattern string, and canaries stay unchanged, frees the layout, and redacts runtime pointers
and observed raw bytes from public output. The `%d/%s/%u/%o/%x` parser extraction paths are out of
scope for this proof. The `match_int` proof builds one owned layout
containing a `substring_t {from,to}` slot pointing at bounded decimal text `12345` and an owned
4-byte `int` result slot, calls `match_int`, requires return `0`, requires the result slot to contain
signed `12345` with raw `0x00003039`, verifies the substring slot, input text, and result-slot canary
stay unchanged, frees the layout, and redacts runtime pointers and observed raw bytes from public
output. The `match_octal` proof uses the same owned `substring_t` plus owned `int *` result-slot
layout shape, but points the substring at bounded octal text `755`, calls `match_octal`, requires
return `0`, requires the result slot to contain signed `493` with raw `0x000001ed`, verifies the
substring slot, input text, and result-slot canary stay unchanged, frees the layout, and redacts
runtime pointers and observed raw bytes from public output. The `match_strdup` proof builds one owned
layout containing a `substring_t {from,to}` slot pointing at bounded text `A90MATCH-STRDUP-Q-END`,
calls `match_strdup`, requires a sane distinct returned kmalloc string pointer, verifies the duplicate
bytes equal the substring plus generated NUL, verifies the substring slot and input bytes stay
unchanged, frees both the returned duplicate and proof layout, and redacts runtime pointers and
observed raw bytes from public output. The `sysfs_streq` proof allocates two owned
NUL-terminated string buffers, requires a left-trailing-newline sysfs match and an exact match to
return `1`, rewrites the right string to a mismatch and requires `0`, verifies both strings and
canaries stay unchanged, frees both buffers, and redacts the owned pointers and observed raw bytes
from public output. The `kstrdup` proof allocates one owned source string, calls
`kstrdup(source, GFP_KERNEL)`, requires a distinct owned kernel duplicate pointer, verifies the
duplicate bytes match the source including NUL, verifies the source string and canary stay unchanged,
frees both the duplicate and source allocations, and redacts the owned pointers and observed raw bytes
from public output. The `kstrndup` proof allocates one owned source string, calls
`kstrndup(source, bounded_len, GFP_KERNEL)` with a bound that truncates before the source NUL, requires
a distinct owned kernel duplicate pointer, verifies the duplicate bytes match the bounded source prefix
plus NUL, verifies the full source string and canary stay unchanged, frees both the duplicate and
source allocations, and redacts the owned pointers and observed raw bytes from public output. The
`kmemdup` proof allocates one owned initialized source buffer, calls
`kmemdup(source, bounded_len, GFP_KERNEL)`, requires a distinct owned kernel duplicate pointer,
verifies the duplicate bytes match the bounded source bytes including embedded NUL and non-ASCII byte,
verifies the source buffer and canary stay unchanged, frees both the duplicate and source allocations,
and redacts the owned pointers and observed raw bytes from public output. The `kmemdup_nul` proof
allocates one owned initialized source buffer, calls `kmemdup_nul(source, bounded_len, GFP_KERNEL)`,
requires a distinct owned kernel duplicate pointer, verifies the duplicate bytes match the bounded
source bytes plus generated trailing NUL, verifies the source byte after `len` is not copied, verifies
the source buffer and canary stay unchanged, frees both the duplicate and source allocations, and
redacts the owned pointers and observed raw bytes from public output. The `strpbrk` proof allocates owned haystack and accept-set strings, requires the
present accept set to return the expected haystack offset, rewrites the accept buffer to a missing set
and requires `0`, verifies both strings and canaries stay unchanged, frees both buffers, and redacts
the owned pointers and observed raw bytes from public output. The `strspn` proof allocates owned haystack and accept-set
strings, requires a prefix-only accept set to return the initial accepted span length as a scalar size,
rewrites the accept buffer to a full haystack-covering set and requires the haystack length, verifies
both strings and canaries stay unchanged, frees both buffers, and redacts the owned pointers and
observed raw bytes from public output. The `strcspn` proof allocates owned haystack and reject-set
strings, requires the present reject set to return the first reject byte offset as a scalar size, rewrites
the reject buffer to a missing set and requires the haystack length, verifies both strings and canaries
stay unchanged, frees both buffers, and redacts the owned pointers and observed raw bytes from public
output. The `strcmp`
proof allocates two owned
NUL-terminated string buffers, compares equal strings for return `0`, changes one right-string byte so
the first difference should return a positive sign, verifies both strings and canaries stay unchanged
after both calls, and redacts the owned pointers and observed raw bytes from public output. The
`strcasecmp` proof uses the same two-owned-string shape, but the first call compares case-only
differences for return `0`; the second call rewrites one right-string byte so the first casefolded
difference should return a positive sign, then verifies both strings and canaries stay unchanged. The
`strncasecmp` proof adds a scalar bounded count inside both owned strings: the first call compares
casefold-equal prefixes and proves a post-count difference is ignored, the second call rewrites one
right-string byte inside count so the first casefolded difference should return a positive sign, then
verifies both strings and canaries stay unchanged. The
`strncmp` proof allocates two owned NUL-terminated string buffers, sets a bounded count that stops
immediately before a deliberate post-count byte difference, requires return `0`, then introduces a
count-internal right-string byte difference that should return a positive sign, verifies both strings
and canaries stay unchanged after both calls, and redacts the owned pointers and observed raw bytes
from public output. The
`memcmp` proof allocates two owned
initialized buffers, compares equal bytes for return `0`, changes one right-buffer byte so the first
difference should return a positive sign, verifies both buffers stay unchanged after both calls, and
redacts the owned pointers and observed raw bytes from public output. The `memchr` proof allocates one
owned initialized buffer, searches for a byte inside the bounded size, requires the returned pointer to
match the expected first-occurrence offset, searches for a byte present only in the post-size canary and
requires `0`, verifies the buffer and canary stay unchanged, and redacts the owned pointer and observed
raw bytes from public output. The `memchr_inv` proof allocates one owned initialized buffer, searches
for the first byte that differs from a scalar fill byte inside a bounded size, requires the returned
pointer to match the expected non-fill offset, rewrites the bounded range so every byte equals the fill
byte, requires `0` even though the post-size canary contains non-fill bytes, verifies buffer and canary
immutability, and redacts the owned pointer and observed raw bytes from public output. The `memcpy` proof allocates distinct owned destination and source buffers,
requires non-overlapping allocation ranges and a bounded size inside both buffers, copies a fixed source
byte sequence into an initialized destination, requires the returned pointer to match the destination,
verifies the destination prefix, destination post-size canary, and source immutability, then frees both
buffers and redacts the owned pointers and observed raw bytes from public output. The `memmove` proof
allocates one owned buffer, sets `src=base`, `dst=base+5`, and a bounded size inside the allocation,
requires the ranges to overlap, requires the returned pointer to match the destination, verifies the
final buffer against overlap-safe snapshot-copy semantics, verifies the post-move canary, frees the
owned buffer, and redacts the owned pointer and observed raw bytes from public output. The `strrchr` proof allocates one
owned NUL-terminated string buffer, searches for a byte that appears multiple times, requires the
returned pointer to match the expected last-occurrence offset, checks a missing byte returns `0`, verifies
the string and canary stay unchanged, and redacts the owned pointer and observed raw bytes from public
output. The `memset` proof allocates one owned destination buffer, writes an initialized prefix plus a
post-size canary, calls `memset(dst, 0x5a, 32)`, requires the returned pointer to match the destination,
verifies the first 32 bytes changed to the fill byte, verifies the canary is preserved, and redacts the
owned pointer and observed raw bytes from public output. The `memzero_explicit` proof allocates one
owned initialized destination buffer, writes an initialized body plus a post-count canary, calls
`memzero_explicit(dst, 24)`, ignores the observed return value because the source API is `void`,
verifies the first 24 bytes became zero, verifies bytes after the count and the canary are preserved,
frees the owned buffer, and redacts the owned pointer and observed raw bytes from public output.

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
