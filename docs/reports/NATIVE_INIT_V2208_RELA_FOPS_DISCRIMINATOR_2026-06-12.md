# Native Init V2208 RELA Fops Discriminator

## Decision

- Decision: `v2208-stock-rela-clone-slide-resolves-v2206-members`
- Reason: A single stock-RELA-derived 0x80000 runtime slide explains every targeted V2206 /dev/null and /dev/zero fops object/member pointer.
- Corrected RELA runtime slide: `0x80000`
- Matched targets: `14/14`
- Stock RELA run: `0xffffff800a714724` → `0xffffff800aace214` (`162763` entries)

## Interpretation

- V2208 resolves the V2206/V2207 ambiguity: the live `/dev/null` and `/dev/zero` fops object/member values match stock RELA addends under one slide, `0x80000`.
- The previous `0x8179c` object slide was a symbol-label alias against `null_fops`/`zero_fops`; the stock RELA addends use clone/landing object addresses `0x179c` after those labels.
- The V2206 member slide spread was caused by comparing live runtime values to original labeled function symbols instead of the stock RELA addends that actually populate the image.
- This does not yet assign semantic function names to every clone/landing addend. It does explain the exact runtime addresses and separates relocation from semantic clone mapping.

## RELA Discovery

- `synthetic_base`: `0xffffff800807b10c`
- `start_offset`: `0x2699618`
- Record size: `24`
- Alignment note: run starts at a 4-byte-aligned offset; 8-byte-only scanners miss it

## Object Rows

| Field | Runtime | RELA addend | RELA row | Reloc slot | Expected label | Delta |
| --- | --- | --- | --- | --- | --- | --- |
| `fd0_fop` | `0xffffff8009bfbbb0` | `0xffffff8009b7bbb0` | `0xffffff800a7621fc` | `0xffffff8009b7ba40` | `null_fops` | `0x179c` |
| `fd1_fop` | `0xffffff8009bfbca0` | `0xffffff8009b7bca0` | `0xffffff800a76222c` | `0xffffff8009b7ba80` | `zero_fops` | `0x179c` |

## Member Rows

| Field | Runtime | RELA addend | RELA row | Expected label | Delta | Nearest stock symbol |
| --- | --- | --- | --- | --- | --- | --- |
| `fd0_llseek` | `0xffffff80087a3534` | `0xffffff8008723534` | `0xffffff800a762334` | `null_lseek` | `-0x1014` | `vtty_write_room`0xc |
| `fd0_read` | `0xffffff80087a354c` | `0xffffff800872354c` | `0xffffff800a76234c` | `read_null` | `-0x1024` | `vtty_write_room`0x24 |
| `fd0_write` | `0xffffff80087a355c` | `0xffffff800872355c` | `0xffffff800a762364` | `write_null` | `-0x1044` | `vtty_write_room`0x34 |
| `fd0_read_iter` | `0xffffff80087a356c` | `0xffffff800872356c` | `0xffffff800a76237c` | `read_iter_null` | `-0x107c` | `vtty_write_room`0x44 |
| `fd0_write_iter` | `0xffffff80087a357c` | `0xffffff800872357c` | `0xffffff800a762394` | `write_iter_null` | `-0x11e4` | `vtty_write_room`0x54 |
| `fd0_splice_write` | `0xffffff80087a35b4` | `0xffffff80087235b4` | `0xffffff800a7623ac` | `splice_write_null` | `-0x130c` | `vtty_write_room`0x8c |
| `fd1_llseek` | `0xffffff80087a3534` | `0xffffff8008723534` | `0xffffff800a762334` | `null_lseek` | `-0x1014` | `vtty_write_room`0xc |
| `fd1_write` | `0xffffff80087a355c` | `0xffffff800872355c` | `0xffffff800a762364` | `write_null` | `-0x1044` | `vtty_write_room`0x34 |
| `fd1_read_iter` | `0xffffff80087a35ec` | `0xffffff80087235ec` | `0xffffff800a7623f4` | `read_iter_zero` | `-0x1524` | `vtty_write_room`0xc4 |
| `fd1_write_iter` | `0xffffff80087a357c` | `0xffffff800872357c` | `0xffffff800a762394` | `write_iter_null` | `-0x11e4` | `vtty_write_room`0x54 |
| `fd1_mmap` | `0xffffff80087a367c` | `0xffffff800872367c` | `0xffffff800a762424` | `mmap_zero` | `-0x159c` | `vtty_write_room`0x154 |
| `fd1_get_unmapped_area` | `0xffffff80087a36bc` | `0xffffff80087236bc` | `0xffffff800a76243c` | `get_unmapped_area_zero` | `-0x15ec` | `vtty_chars_in_buffer`0x2c |

## Rebuilt ELF Contrast

- Available: `true`
- Rebuilt RELA entries: `162770`
- Member slots matching expected labels: `12/12`
- Meaning: the local rebuilt ELF keeps the source-level fops members tied to labeled functions, while the stock live image uses clone/landing addends. Rebuilt labels must not be treated as bit-exact stock labels.

## Next

- Treat `0x80000` as the proven runtime relocation slide for this stock RELA/object layer.
- Do not promote original System.map function names onto clone/landing addends until a clone-to-original semantic map is built.
- Next useful unit: derive that semantic clone map from stock RELA initializer order plus RKP_CFP/JOPP-generated landing metadata, then re-apply it to stack/timer/fops symbolization.

## Safety

- host_only: `true`
- live_device_access: `false`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`

## Evidence

- Private result: `workspace/private/runs/kernel/v2208-rela-fops-discriminator/result.json`
- Stock System.map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- Stock raw: `workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw`
- V2206 summary: `workspace/private/runs/kernel/v2206-fops-member-anchor-20260612-015121/summary.json`
- Rebuilt ELF: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/vmlinux`
