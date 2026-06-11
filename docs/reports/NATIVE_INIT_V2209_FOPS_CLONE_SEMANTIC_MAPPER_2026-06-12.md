# Native Init V2209 Fops Clone Semantic Mapper

## Decision

- Decision: `v2209-fops-clone-semantic-map-built`
- Reason: Source fops initializer fields, slot-accurate stock RELA entries, rebuilt label checks, and V2206 live values all agree.
- Runtime RELA slide: `0x80000`
- Semantic rows: `12`
- Stock slot RELA present: `true`
- Rebuilt labels match source: `true`
- V2206 live values match predicted runtime: `true`

## Interpretation

- V2209 converts V2208's clone/landing addends into semantic fops targets by using the source initializer field, not nearest System.map symbol names.
- The stock RELA slot is matched by `clone_base + struct file_operations.<field offset>`, so shared targets such as `null_lseek` and `write_null` no longer collapse onto the first addend-only row.
- The rebuilt ELF validates the source semantics: the same fops field slots point at the expected labeled functions before stock RKP_CFP/JOPP clone/landing transformation.
- Nearest stock symbols around the clone addends remain misleading and must not be used as semantic names for these targets.

## Runtime Semantic Map

| Runtime pointer | Semantic target | Uses |
| --- | --- | --- |
| `0xffffff80087a3534` | `null_lseek` | null_fops.llseek, zero_fops.llseek |
| `0xffffff80087a354c` | `read_null` | null_fops.read |
| `0xffffff80087a355c` | `write_null` | null_fops.write, zero_fops.write |
| `0xffffff80087a356c` | `read_iter_null` | null_fops.read_iter |
| `0xffffff80087a357c` | `write_iter_null` | null_fops.write_iter, zero_fops.write_iter |
| `0xffffff80087a35b4` | `splice_write_null` | null_fops.splice_write |
| `0xffffff80087a35ec` | `read_iter_zero` | zero_fops.read_iter |
| `0xffffff80087a367c` | `mmap_zero` | zero_fops.mmap |
| `0xffffff80087a36bc` | `get_unmapped_area_zero` | zero_fops.get_unmapped_area |

## Slot-Accurate Rows

| Field | Offset | Semantic | Clone slot | Stock addend | Runtime | Delta from stock label | Nearest stock symbol | Rebuilt OK | Live OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `null_fops.llseek` | `0x8` | `null_lseek` | `0xffffff8009b7bbb8` | `0xffffff8008723534` | `0xffffff80087a3534` | `-0x1014` | `vtty_write_room`0xc | true | true |
| `null_fops.read` | `0x10` | `read_null` | `0xffffff8009b7bbc0` | `0xffffff800872354c` | `0xffffff80087a354c` | `-0x1024` | `vtty_write_room`0x24 | true | true |
| `null_fops.write` | `0x18` | `write_null` | `0xffffff8009b7bbc8` | `0xffffff800872355c` | `0xffffff80087a355c` | `-0x1044` | `vtty_write_room`0x34 | true | true |
| `null_fops.read_iter` | `0x20` | `read_iter_null` | `0xffffff8009b7bbd0` | `0xffffff800872356c` | `0xffffff80087a356c` | `-0x107c` | `vtty_write_room`0x44 | true | true |
| `null_fops.write_iter` | `0x28` | `write_iter_null` | `0xffffff8009b7bbd8` | `0xffffff800872357c` | `0xffffff80087a357c` | `-0x11e4` | `vtty_write_room`0x54 | true | true |
| `null_fops.splice_write` | `0xb0` | `splice_write_null` | `0xffffff8009b7bc60` | `0xffffff80087235b4` | `0xffffff80087a35b4` | `-0x130c` | `vtty_write_room`0x8c | true | true |
| `zero_fops.llseek` | `0x8` | `null_lseek` | `0xffffff8009b7bca8` | `0xffffff8008723534` | `0xffffff80087a3534` | `-0x1014` | `vtty_write_room`0xc | true | true |
| `zero_fops.write` | `0x18` | `write_null` | `0xffffff8009b7bcb8` | `0xffffff800872355c` | `0xffffff80087a355c` | `-0x1044` | `vtty_write_room`0x34 | true | true |
| `zero_fops.read_iter` | `0x20` | `read_iter_zero` | `0xffffff8009b7bcc0` | `0xffffff80087235ec` | `0xffffff80087a35ec` | `-0x1524` | `vtty_write_room`0xc4 | true | true |
| `zero_fops.write_iter` | `0x28` | `write_iter_null` | `0xffffff8009b7bcc8` | `0xffffff800872357c` | `0xffffff80087a357c` | `-0x11e4` | `vtty_write_room`0x54 | true | true |
| `zero_fops.mmap` | `0x58` | `mmap_zero` | `0xffffff8009b7bcf8` | `0xffffff800872367c` | `0xffffff80087a367c` | `-0x159c` | `vtty_write_room`0x154 | true | true |
| `zero_fops.get_unmapped_area` | `0x98` | `get_unmapped_area_zero` | `0xffffff8009b7bd38` | `0xffffff80087236bc` | `0xffffff80087a36bc` | `-0x15ec` | `vtty_chars_in_buffer`0x2c | true | true |

## Clone Bases

- `null_fops` clone base: `0xffffff8009b7bbb0`
- `zero_fops` clone base: `0xffffff8009b7bca0`

## Next

- Use this semantic map as the naming layer for V2206 fops pointers instead of direct nearest-symbol lookup.
- Generalize the same method to other RELA-backed callback tables: source initializer slot → stock RELA addend → runtime pointer via `0x80000` → semantic name.
- For stack/timer symbolization, keep raw IP/frame decoding separate; this fops map solves clone semantic naming for RELA-populated callback tables, not ROPP stack decoding.

## Safety

- host_only: `true`
- live_device_access: `false`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`

## Evidence

- Private result: `workspace/private/runs/kernel/v2209-fops-clone-semantic-mapper/result.json`
- V2208 result: `workspace/private/runs/kernel/v2208-rela-fops-discriminator/result.json`
- Stock raw: `workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw`
- Source `mem.c`: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/mem.c`
- Source `fs.h`: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/include/linux/fs.h`
- Rebuilt ELF: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/vmlinux`
