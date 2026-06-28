# Kernel Security Tier-2 Runtime Kernel REPL v2c - vmlinux-to-elf Third Oracle

- Date: 2026-06-29
- Unit: `v2c third-oracle cross-check`
- Decision: `a90-repl-v2c-vmlinux-to-elf-third-oracle-host-pass`
- Device action: no
- Boot image changed: no
- External tool: `vmlinux-to-elf`
- External tool source: `https://github.com/marin-m/vmlinux-to-elf`
- External tool commit: `19683fb95b29cd31362d49e6f48ab8368f96cbdf`
- Private tool path: `workspace/private/inputs/external_tools/kernel/vmlinux-to-elf`
- Private run path: `workspace/private/runs/kernel/v2c-vmlinux-to-elf-crosscheck`

## Objective

Run `vmlinux-to-elf` as an independent third oracle for the v2321 kernel map
after Gate-2 promoted the C2B padding fix and `printk` BL-xref disambiguation.
Require agreement among:

- promoted extractor map;
- C2E relocated-`__ksymtab` oracle;
- `vmlinux-to-elf` recovered kallsyms map.

## Tool Setup

The external tool was cloned and installed only under `workspace/private`.
No public code depends on it at runtime.

```sh
git clone --depth 1 https://github.com/marin-m/vmlinux-to-elf.git \
  workspace/private/inputs/external_tools/kernel/vmlinux-to-elf

uv venv workspace/private/inputs/external_tools/kernel/vmlinux-to-elf/.venv
uv pip install --python \
  workspace/private/inputs/external_tools/kernel/vmlinux-to-elf/.venv/bin/python \
  -e workspace/private/inputs/external_tools/kernel/vmlinux-to-elf
```

Resolved private tool commit:

```text
19683fb95b29cd31362d49e6f48ab8368f96cbdf 2026-06-05T07:29:18+02:00 Update Flatpak distribution to GNOME runtime 50
```

## vmlinux-to-elf Run

Command:

```sh
workspace/private/inputs/external_tools/kernel/vmlinux-to-elf/.venv/bin/kallsyms-finder \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
  --output workspace/private/runs/kernel/v2c-vmlinux-to-elf-crosscheck/vmlinux-to-elf.kallsyms
```

Observed tool evidence:

- unpacked Qualcomm-appended DTB and Android boot image;
- detected `aarch64`;
- found `kallsyms_token_table` at `0x02103100`;
- found `kallsyms_token_index` at `0x02103500`;
- found `kallsyms_markers` at `0x02101f00`;
- found `kallsyms_names` at `0x01f10700`;
- found `kallsyms_num_syms` at `0x01f10600`;
- found relocation table at `0x2699618..0x2a532b8` with count `162780`;
- applied `162753` relocations;
- found `kallsyms_offsets` at `0x01e80700`;
- emitted `147295` symbols.

Private output hash:

```text
9e6a1d6f322344e3d6fced7e6d29a254e1516cc5163bad8595388a9d0d02ec3a  workspace/private/runs/kernel/v2c-vmlinux-to-elf-crosscheck/vmlinux-to-elf.kallsyms
```

## Promoted Extractor Agreement

The promoted extractor map and the `vmlinux-to-elf` map are byte-identical:

```sh
cmp -s \
  workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  workspace/private/runs/kernel/v2c-vmlinux-to-elf-crosscheck/vmlinux-to-elf.kallsyms
```

Result:

```text
maps-identical
```

Both files have SHA256:

```text
9e6a1d6f322344e3d6fced7e6d29a254e1516cc5163bad8595388a9d0d02ec3a
```

Anchor agreement:

- `printk = 0xffffff800813adfc`
- `__kmalloc = 0xffffff800826ae34`
- `kfree = 0xffffff800826b354`
- `kallsyms_lookup_name = 0xffffff800817cfa4`
- `kgsl_pwrctrl_num_pwrlevels_show = 0xffffff80089262dc`
- `kgsl_pwrctrl_force_no_nap_store = 0xffffff80089273b4`

## C2E Relocated ksymtab Agreement

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_repl.py ksymtab-ground-truth \
    --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
    --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
    --compare-map promoted=workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
    --compare-map vmlinux-to-elf=workspace/private/runs/kernel/v2c-vmlinux-to-elf-crosscheck/vmlinux-to-elf.kallsyms
```

Observed counts:

- current v2a1 map: `0` matches / `12518` mismatches / `0` missing
- promoted extractor map: `12515` matches / `3` mismatches / `0` missing
- `vmlinux-to-elf` map: `12515` matches / `3` mismatches / `0` missing

The residual mismatch set is identical for promoted extractor and
`vmlinux-to-elf`:

- `ehci_reset`
- `iio_read_channel_ext_info`
- `iio_write_channel_ext_info`

For each residual, both independent kallsyms decoders emit the same map rows,
and the C2E relocated export row points at the exported `T` twin. This remains
fenced for operator disassembly review and is not treated as silent ground truth.

## Conclusion

The third oracle confirms the promoted extractor map exactly. The byte-identical
agreement with `vmlinux-to-elf`, plus the C2E relocated export oracle, validates
the C2B padding correction and the `printk` BL-xref disambiguation as the current
best host-side map. C1 fail-closed remains the live safety boundary, and the
three residual export/local twin conflicts remain explicitly fenced.
