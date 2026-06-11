# Native Init V2207 JOPP Stub Mapper

## Decision

- Decision: `v2207-member-targets-runtime-patched-not-direct-symbol-slide`
- Reason: V2206 member values are readable, but neither the exact object slide nor any single member slide maps them to the expected fops entries.
- Object/fops slide: `0x8179c`
- Object slide expected member hits: `0`
- Single member text slide exact: `false`

## Interpretation

- V2204/V2206 still prove the object/rodata layer: `/dev/null` and `/dev/zero` f_op objects agree on `0x8179c`.
- V2207 blocks promoting that object slide to fops member text targets: object-slide mapping sends member pointers into unrelated `msm_geni_serial_*` code, not `drivers/char/mem.c` fops entries.
- The expected fops entries in the bit-exact map do contain JOPP magic immediately before entry and ROPP prologue patterns, so the stock map/source side is internally coherent.
- The live fops member values require runtime patch/RKP_CFP/JOPP metadata interpretation; direct `runtime - single_slide = expected_symbol` is not valid yet.

## RKP_CFP Source Basis

- `CONFIG_RKP_CFP_JOPP`: `1`
- `CONFIG_RKP_CFP_ROPP`: `1`
- `CONFIG_RKP_CFP_ROPP_SYSREGKEY`: `1`
- `CONFIG_RKP_CFP_JOPP_MAGIC`: `0x00be7bad`
- Source has BLR→springboard rewrite: `true`
- Source has function-entry magic write: `true`
- Source has ROPP LR save/restore rewrite: `true`

## Object Layer

- Exact object slide: `0x8179c` from `fd0_fop:null_fops, fd1_fop:zero_fops`
- Raw stock image table slots for `null_fops/zero_fops` are zero at the checked member offsets, so live member values are runtime-populated/patched state rather than plain raw-image table data.

## Member Slide Spread

| Slide | Expected-entry hits | Sources |
| --- | --- | --- |
| 0x7efec | 2 | fd0_llseek:null_lseek, fd1_llseek:null_lseek |
| 0x7efbc | 2 | fd0_write:write_null, fd1_write:write_null |
| 0x7ee1c | 2 | fd0_write_iter:write_iter_null, fd1_write_iter:write_iter_null |
| 0x7efdc | 1 | fd0_read:read_null |
| 0x7ef84 | 1 | fd0_read_iter:read_iter_null |
| 0x7ecf4 | 1 | fd0_splice_write:splice_write_null |
| 0x7eadc | 1 | fd1_read_iter:read_iter_zero |
| 0x7ea64 | 1 | fd1_mmap:mmap_zero |
| 0x7ea14 | 1 | fd1_get_unmapped_area:get_unmapped_area_zero |

## Member Mapping Details

| Field | Runtime | Expected | Expected slide | Delta from object | Object-slide maps to | Insn |
| --- | --- | --- | --- | --- | --- | --- |
| `fd0_llseek` | `0xffffff80087a3534` | null_lseek | `0x7efec` | `0x27b0` | `msm_geni_serial_loopback_show`+1088 | other |
| `fd0_read` | `0xffffff80087a354c` | read_null | `0x7efdc` | `0x27c0` | `msm_geni_serial_loopback_show`+1112 | other |
| `fd0_write` | `0xffffff80087a355c` | write_null | `0x7efbc` | `0x27e0` | `msm_geni_serial_loopback_show`+1128 | other |
| `fd0_read_iter` | `0xffffff80087a356c` | read_iter_null | `0x7ef84` | `0x2818` | `msm_geni_serial_loopback_show`+1144 | other |
| `fd0_write_iter` | `0xffffff80087a357c` | write_iter_null | `0x7ee1c` | `0x2980` | `msm_geni_serial_loopback_show`+1160 | other |
| `fd0_splice_write` | `0xffffff80087a35b4` | splice_write_null | `0x7ecf4` | `0x2aa8` | `msm_geni_serial_loopback_show`+1216 | bl |
| `fd1_llseek` | `0xffffff80087a3534` | null_lseek | `0x7efec` | `0x27b0` | `msm_geni_serial_loopback_show`+1088 | other |
| `fd1_write` | `0xffffff80087a355c` | write_null | `0x7efbc` | `0x27e0` | `msm_geni_serial_loopback_show`+1128 | other |
| `fd1_read_iter` | `0xffffff80087a35ec` | read_iter_zero | `0x7eadc` | `0x2cc0` | `msm_geni_serial_xfer_mode_show`+40 | other |
| `fd1_write_iter` | `0xffffff80087a357c` | write_iter_null | `0x7ee1c` | `0x2980` | `msm_geni_serial_loopback_show`+1160 | other |
| `fd1_mmap` | `0xffffff80087a367c` | mmap_zero | `0x7ea64` | `0x2d38` | `msm_geni_serial_xfer_mode_store`+24 | other |
| `fd1_get_unmapped_area` | `0xffffff80087a36bc` | get_unmapped_area_zero | `0x7ea14` | `0x2d88` | `msm_geni_serial_xfer_mode_store`+88 | other |

## Expected Entry Profiles

| Symbol | Static entry | JOPP magic -4 | ROPP prologue | ROPP offsets |
| --- | --- | --- | --- | --- |
| `get_unmapped_area_zero` | `0xffffff8008724ca8` | true | true | 0,40 |
| `mmap_zero` | `0xffffff8008724c18` | true | true | 0 |
| `null_lseek` | `0xffffff8008724548` | true | true | 0,40 |
| `read_iter_null` | `0xffffff80087245e8` | true | true | 0 |
| `read_iter_zero` | `0xffffff8008724b10` | true | true | 0 |
| `read_null` | `0xffffff8008724570` | true | true | 0,48 |
| `splice_write_null` | `0xffffff80087248c0` | true | true | 0 |
| `write_iter_null` | `0xffffff8008724760` | true | true | 0 |
| `write_null` | `0xffffff80087245a0` | true | true | 0 |

## Next

- Do not label V2206 member pointers as exact text symbolization yet.
- Next useful unit is a runtime patch/metadata discriminator: either locate the RKP_CFP/JOPP function-pointer rewrite table used to populate fops members, or add a read-only live probe around the fops object update path to capture pre/post member values.
- Keep V2204 object slide available for object/rodata anchors only; keep text-stack/timer/fops-member symbolization behind the JOPP/ROPP decode gate.

## Safety

- host_only: `true`
- live_device_access: `false`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`

## Evidence

- Private result: `workspace/private/runs/kernel/v2207-jopp-stub-mapper/result.json`
- System.map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- Kernel raw: `workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw`
- V2206 summary: `workspace/private/runs/kernel/v2206-fops-member-anchor-20260612-015121/summary.json`
