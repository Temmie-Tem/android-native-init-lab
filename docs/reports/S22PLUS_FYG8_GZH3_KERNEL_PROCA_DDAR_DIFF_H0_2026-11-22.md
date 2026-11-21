# S22+ kernel PROCA / DualDAR diff, FYG8 → GZH3 (H0)

Date: 2026-11-22
Target: Samsung Galaxy S22+ `SM-S906N` stock kernels.
- FYG8: Linux `5.10.226-android12-9-30958166-abS906NKSS7FYG8`.
- GZH3: Linux `5.10.236-android12-9-31998796-abS906NKSS9GZH3`, SPL 2026-08-05.

Both kernels were built with clang 12.0.5 (r416183b).
Scope: H0 static symbol-level diff. Host-only, read-only, no device contact.
No reproduction, no proof of concept, no exploit work, and no
instruction-level reconstruction of any fix.
Serves: backlog lane 3 (kernel/driver) and the new
[Lab layer](../plans/S22PLUS_FYG8_POST_2025_08_SECURITY_BACKLOG_2026-09-16.md#lab-layer) column.

## Why this touches the lab stack

Every Samsung-kernel native-init config on disk has `CONFIG_PROCA=y` and
`CONFIG_DDAR=y`, as does `CONFIG_FIVE=y`. That covers the P363, P393, P406, P407, P408, P410 and P413
and Debian-port configs and the 2026-10-20 autoboot `exact-image.config`.
These candidates are built from FYG8 kernel source, so they carry the FYG8
(pre-fix) code of both drivers.

- **PROCA is an LSM.** Its hooks (`proca_hook_task_forked`,
  `proca_hook_file_processed`) run for any userspace, including Debian under
  native-init.
- **DualDAR paths** need DualDAR userspace to be exercised. They are probably
  idle under native-init. This is not verified.
- The mainline kernels (ML builds) do not contain either driver.

## Inputs and provenance

| | FYG8 | GZH3 |
|---|---|---|
| `boot.img` sha256 | `4150b962…40ae` | `dbb80954…6032` |
| AVB | hash descriptor in policy-pinned FYG8 `vbmeta` verified | hash descriptor in GZH3 `vbmeta` verified (same key as FYG8) |
| Kernel | raw arm64 Image, boot header v4 | same |
| Recovered symbols | 112,355 | 112,596 |

## Method

- **Symbol recovery.** `kallsyms510.py` (private, new) recovers a System.map
  from each boot image. It parses the 5.10 base-relative kallsyms tables
  (offsets, relative base, names, markers, token table, token index). Nothing
  is executed.
- **Validation.** On FYG8 the recovered map has exactly the same PROCA (46),
  `dd_` (68) and FIVE (54) text-symbol counts as the lab's own Full-LTO FYG8
  build (`p296 repro-b/System.map`). Addresses are 100 % monotonic.
- **Diff.** `kdiff.py` sizes each text symbol as the distance to the next
  symbol, then compares the two maps.
- **Baseline.** Over all 55,578 common text symbols, **1.6 %** change size
  between the two LTS levels.

## Result

| Subsystem | Text symbols (FYG8/GZH3) | Common: changed / unchanged | Added | Removed |
|---|---|---|---|---|
| PROCA | 46 / 47 | **12 / 31 (28 %)** | 4 | 3 |
| DualDAR (`dd_*`) | 68 / 69 | **1 / 67** | 1 | 0 |
| FIVE (no backlog row) | 54 / 59 | 7 / 51 | 6 | 1 |

### PROCA (CVE-2026-20971, Jan-2026, "PROCA driver UAF")

- **The change rate is 17× the kernel baseline.** The changes cluster in two
  areas.
- **Task-descriptor lifecycle:**

  | Function | FYG8 → GZH3 |
  |---|---|
  | `proca_table_add_task_descr` | 628 → 868 B |
  | `create_proca_task_descr` | 156 → 164 B |
  | `destroy_proca_task_descr` | 124 → 164 B |
  | `proca_get_task_cert` | 108 → 144 B |
  | `proca_table_init` | 72 → 104 B |
  | `proca_identity_copy` | 308 → 356 B |
  | `proca_certificate_copy` | 356 → 392 B |

- **Configuration and xattr handling:**
  - `init_proca_config` 460 → 192 B;
  - `proca_fcntl_setxattr` 728 → 976 B;
  - new `proca_setxattr_noperm`;
  - `proc_get_proca_cert` was removed.
- A new `proca_task_descr_debugfs_init` and GAF init moved into
  `proca_init_gaf`.
- Interpretation (hypothesis): a use-after-free advisory against a driver
  whose larger deltas sit in object create, add, destroy and copy paths is
  consistent. The PROCA *trustlet* row (CVE-2026-21093, Sep-2026) is outside
  this window and is TEE, not kernel. So 20971 is the only listed PROCA-kernel
  item in the window. Undisclosed SVE items cannot be excluded.

### DualDAR (CVE-2026-20968, Jan-2026, "DualDAR UAF")

- The only differences are `dd_mmap` (480 → 492 B) and a new `dd_vm_close`.
- The delta is small and confined to the device's mmap path. The other 67
  functions are unchanged.
- Interpretation (hypothesis): consistent with a lifetime fix in that path.
  The advisory names DualDAR without saying "driver". This delta shows the
  in-window DualDAR change is in the kernel.
- The Sep-2026 DualDAR rows (21101, 21102) are outside the window.

### FIVE

FIVE (Samsung's file-integrity LSM) also changed:
- a new inode integrity cache (`five_iint_*`, `five_inode_get/free`);
- `five_fcntl_close`/`five_fcntl_edit` reduced to stubs (600/576 → 16 B);
- the xattr hooks grew.

No disclosed backlog row names FIVE. Recorded only.

## State change

- **CVE-2026-20971 (PROCA driver): `PUBLISHED` → `DIFFED`.** The component is
  in the FYG8 stock kernel and in every Samsung-kernel native-init candidate.
  Lineage is continuous. A pre/post-fix delta stands well above baseline and
  sits in the lifecycle paths. It is attributed by elimination among the
  listed rows, not by vendor detail.
- **CVE-2026-20968 (DualDAR): `PUBLISHED` → `DIFFED`.** There is a
  single-path kernel delta (`dd_mmap`, new `dd_vm_close`). The Lab layer moves
  from `Samsung kernel?` to `Samsung kernel`.
- CVE-2026-21101 and CVE-2026-21102 (Sep-2026 DualDAR) need a build with SPL
  2026-09 or later. None is on FUS yet.

## Limits

- Symbol sizes are next-symbol distances, and LTO can merge or split
  functions. Counts are pointers, not proof.
- The two kernels also differ by ten LTS releases. The 1.6 % baseline bounds
  that noise but does not remove it.
- "Hook runs under native-init" comes from PROCA being an LSM in the config.
  No runtime observation was made.

## Private outputs

Analysis `s22plus-gzh3-compare.YUuibTvm` holds:
- `verify_boot.py` and `boot-verified.json`;
- `kallsyms510.py`;
- `kernel/{fyg8,gzh3}.map`;
- `kdiff.py` and `kdiff.json`;
- `kernel/boot.img` (GZH3).
