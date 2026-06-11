# Native Init V2206 Fops Member Text Anchor

## Decision

- Decision: `v2206-fops-member-pointer-stub-layer-observed`
- Pass: `true`
- Object/fops slide: `0x8179c`
- Member/text slide: `0x7ee1c`
- Member exact: `false`
- Reason: fewer than four known fops member function pointers agreed

## Interpretation

- Capture succeeded when `selftest fail=0` is true; `member_exact=false` is a classifier result, not a transport/runtime failure.
- The fops object pointers still agree on the V2204 object/rodata slide.
- The fops member function pointers are readable, but they do not point to known real function entries under one uniform text slide.
- Treat the member values as a CFP/JOPP stub layer until the stub-to-real-target decode is implemented.

## Method

- Opens `/dev/null` and `/dev/zero` read-only in the helper process.
- Reads `current->files->fdt->fd[]->file->f_op` and selected fops members with `bpf_probe_read` only.
- Compares member runtime pointers against known `drivers/char/mem.c` functions in the bit-exact stock `System.map`.

## Member Function Pointers

| Field | Runtime | Candidate slides |
| --- | --- | --- |
| `fd0_llseek` | `0xffffff80087a3534` | `null_lseek` 0x7efec |
| `fd0_read` | `0xffffff80087a354c` | `read_null` 0x7efdc |
| `fd0_write` | `0xffffff80087a355c` | `write_null` 0x7efbc |
| `fd0_read_iter` | `0xffffff80087a356c` | `read_iter_null` 0x7ef84 |
| `fd0_write_iter` | `0xffffff80087a357c` | `write_iter_null` 0x7ee1c |
| `fd0_splice_write` | `0xffffff80087a35b4` | `splice_write_null` 0x7ecf4 |
| `fd1_llseek` | `0xffffff80087a3534` | `null_lseek` 0x7efec |
| `fd1_write` | `0xffffff80087a355c` | `write_null` 0x7efbc |
| `fd1_read_iter` | `0xffffff80087a35ec` | `read_iter_zero` 0x7eadc |
| `fd1_write_iter` | `0xffffff80087a357c` | `write_iter_null` 0x7ee1c |
| `fd1_mmap` | `0xffffff80087a367c` | `mmap_zero` 0x7ea64 |
| `fd1_get_unmapped_area` | `0xffffff80087a36bc` | `get_unmapped_area_zero` 0x7ea14 |

## Ranked Member Slides

- `0x7ee1c` count=2 sources=`fd0_write_iter:write_iter_null, fd1_write_iter:write_iter_null`
- `0x7efbc` count=2 sources=`fd0_write:write_null, fd1_write:write_null`
- `0x7efec` count=2 sources=`fd0_llseek:null_lseek, fd1_llseek:null_lseek`
- `0x7ea14` count=1 sources=`fd1_get_unmapped_area:get_unmapped_area_zero`
- `0x7ea64` count=1 sources=`fd1_mmap:mmap_zero`
- `0x7eadc` count=1 sources=`fd1_read_iter:read_iter_zero`
- `0x7ecf4` count=1 sources=`fd0_splice_write:splice_write_null`
- `0x7ef84` count=1 sources=`fd0_read_iter:read_iter_null`
- `0x7efdc` count=1 sources=`fd0_read:read_null`

## Safety

- read_only_bpf: `true`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`

## Evidence

- Private run: `workspace/private/runs/kernel/v2206-fops-member-anchor-20260612-015121`
- System.map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- Helper SHA-256: `2fe4353e2d8e3a1fd8f23ecd15f66c03b259455bb669b74d0422048950b2ce09`
- Selftest fail=0: `true`
