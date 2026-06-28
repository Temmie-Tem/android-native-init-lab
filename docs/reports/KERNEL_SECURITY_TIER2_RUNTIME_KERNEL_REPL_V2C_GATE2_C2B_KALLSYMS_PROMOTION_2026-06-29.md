# Kernel Security Tier-2 Runtime Kernel REPL v2c Gate-2 - C2B Kallsyms Promotion

- Date: 2026-06-29
- Unit: `v2c Gate-2`
- Decision: `a90-repl-v2c-gate2-c2b-kallsyms-promotion-host-pass`
- Device action: no
- Boot image changed: no
- Public code:
  - `workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py`
  - `workspace/public/src/scripts/revalidation/build_kernel_tier2_stage_c_direct_bl_printk.py`
  - `workspace/public/src/scripts/revalidation/a90_repl.py`
- Private regenerated map:
  - `workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map`
  - `workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/stock-kallsyms.json`

## Objective

Apply the OPERATOR GATE-2 correction: promote the C2B kallsyms offset-padding
fix, fix the `printk` twin locator by direct-BL xref count, regenerate the
private map, and re-run the C2E relocated-`__ksymtab` drift oracle.

## Changes

- Re-applied `padding_before_relative_base` handling in
  `a90_stock_kallsyms_extract.py`.
- Re-applied the KGSL local-run early-return guard so already-correct
  base-relative KGSL local symbols are not overwritten.
- Changed `locate_printk_variadic_wrapper` to select the variadic-body
  candidate with the highest direct `bl` xref count.
- Updated Stage-C users of the locator to tolerate the selected real `printk`
  target not having the old optional VA-helper/emit-core fields.
- Updated C1 verified resolution so `printk` is allowed to use the export/xref
  ground truth instead of falling back to a callable lower-xref map twin.

## Regenerated Map Evidence

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py \
    --kernel workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
    --out-map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
    --out-json workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/stock-kallsyms.json
```

Observed:

- `padding_before_relative_base`: `380`
- `printk`: `0xffffff800813adfc`
- `__kmalloc`: `0xffffff800826ae34`
- `kfree`: `0xffffff800826b354`
- `kallsyms_lookup_name`: `0xffffff800817cfa4`
- `kgsl_pwrctrl_num_pwrlevels_show`: `0xffffff80089262dc`
- `kgsl_pwrctrl_force_no_nap_store`: `0xffffff80089273b4`
- decode sources: `147294` base-relative, `1` printk xref override

## C2E Drift Recheck

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_repl.py ksymtab-ground-truth \
    --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
    --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
    --compare-map promoted=workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map
```

Observed:

- current v2a1 map: `0` matches / `12518` mismatches / `0` missing
- promoted map: `12515` matches / `3` mismatches / `0` missing
- four anchors pass:
  - `printk=0xffffff800813adfc`
  - `kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4`
  - `__kmalloc=0xffffff800826ae34`
  - `kfree=0xffffff800826b354`
- residual promoted-map mismatches:
  - `ehci_reset`
  - `iio_read_channel_ext_info`
  - `iio_write_channel_ext_info`

The residual list is fenced for operator disassembly review. C1 fail-closed
resolution remains the live safety boundary.

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py \
  workspace/public/src/scripts/revalidation/build_kernel_tier2_stage_c_direct_bl_printk.py \
  workspace/public/src/scripts/revalidation/build_kernel_tier2_repl_v1_repl.py \
  workspace/public/src/scripts/revalidation/build_kernel_tier2_kasan_lite_reclaim_dump.py \
  tests/test_a90_repl.py \
  tests/test_a90_stock_kallsyms_extract.py \
  tests/test_kernel_tier2_stage_c_direct_bl_printk.py \
  tests/test_kernel_tier2_repl_v1_repl.py \
  tests/test_kernel_tier2_kasan_lite_reclaim_dump.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest \
  tests.test_a90_repl \
  tests.test_a90_stock_kallsyms_extract \
  tests.test_kernel_tier2_stage_c_direct_bl_printk \
  tests.test_kernel_tier2_repl_v1_repl \
  tests.test_kernel_tier2_kasan_lite_reclaim_dump
```

Results:

- `py_compile`: pass
- focused unittest set: `71/71` pass
- device action: none

## Conclusion

Gate-2 is host-passed. C2B is promoted in source, the `printk` twin false
positive is fixed by BL-xref disambiguation, and the regenerated private map
nearly saturates the C2E relocated export oracle. The promoted map is still
subject to the operator's independent disassembly review before being treated
as broad ground truth.
