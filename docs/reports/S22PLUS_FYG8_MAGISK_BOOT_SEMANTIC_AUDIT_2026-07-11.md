# S22+ FYG8 Magisk Boot Semantic Audit

Date: 2026-07-11 KST
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Scope: host-only, read-only input analysis; no device contact, repack, AP build, or flash

## Verdict

`PASS_EXACT_MAGISK_SEMANTICS_IDENTIFIED`

The known-booting Magisk boot is not the stock boot with only a ramdisk
replacement. Magisk v30.7 made exactly two kernel changes:

- DEFEX instruction patch: 3 changed bytes at kernel offset `0x4cd4fc`;
- PROCA string patch: 6 changed bytes at kernel offset `0x1e6aa28`.

No other kernel byte differs. The RKP and legacy-SAR binary patterns did not
match, so those Magisk hexpatch operations were no-ops. The embedded IKCONFIG is
unchanged and still has `CONFIG_RKP=y`, along with KDP, UH, DEFEX, FIVE, and
PROCA enabled. The precise baseline is therefore: **DEFEX binary gate patched,
PROCA name patched, RKP configuration and code preserved from stock**.

This resolves an R3 ambiguity: a rebuilt kernel cannot simultaneously be
unpatched and reproduce the current Magisk-root baseline. The selected first
boot proof must be called `magisk-equivalent-kernel`, not an unchanged or
byte-identical stock kernel.

## Pinned Inputs

| Input | SHA256 |
|---|---|
| FYG8 stock `boot.img` | `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae` |
| Known-booting Magisk `boot.img` | `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e` |
| Magisk v30.7 APK | `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5` |
| Pinned AOSP `lz4` | `91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8` |
| Pinned AOSP `avbtool` | `063d7c7a19744ceeb72553c95962ac98fff977fc27f5f95e6063c2f15f8d3e88` |

Magisk source reference is official tag `v30.7`, commit
`e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac`. The release and source are pinned
to the [official Magisk repository](https://github.com/topjohnwu/Magisk/tree/e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac).

## Boot Container

Both images are 96 MiB Android boot v4 containers with the same kernel payload
length, Android 12.0.0 metadata, 2025-08 patch level, empty command line, and
4096-byte boot-signature field. That field is byte-identical and all zero. The
header changes only as required by the ramdisk size.

| Field | Stock | Magisk |
|---|---:|---:|
| Kernel bytes | 41,490,944 | 41,490,944 |
| Compressed ramdisk bytes | 1,978,967 | 1,428,430 |
| Decompressed cpio bytes | 3,143,424 | 1,492,480 |
| AVB original image size | 43,483,664 | 42,930,192 |
| AVB vbmeta offset | 43,487,232 | 42,934,272 |
| AVB vbmeta bytes | 2,112 | 2,112 |

The AVB vbmeta blob is exactly identical in both images, SHA256
`2128d4fa64fdbed386f8cf628e1df89b1161a60a59aec985bb28a5770873561d`.
Pinned `avbtool verify_image` fully verifies stock. For Magisk, the vbmeta
signature still verifies but the boot payload digest does not match the copied
stock descriptor. This is an expected property of the known-booting unlocked
baseline, not a newly valid signature. Any R3 policy must state that the
candidate retains a stale descriptor and relies on the already-unlocked boot
path.

## Kernel Delta

| Patch | Stock | Magisk | Result |
|---|---|---|---|
| DEFEX | `821b8012` | `e2ff8f12` | 3 byte changes; final `12` unchanged |
| PROCA | `proca_config\0` | `proca_magisk\0` | 6 byte changes |
| RKP | upstream pattern count 0 | replacement count 0 | no-op |
| Legacy SAR | `skip_initramfs` count 0 | `want_initramfs` count 0 | no-op |

These operations match the exact sequence in official Magisk v30.7
[`boot_patch.sh`](https://github.com/topjohnwu/Magisk/blob/e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac/scripts/boot_patch.sh#L223-L252).
The stock and Magisk kernels have these hashes:

- stock: `027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d`;
- Magisk: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`.

Their embedded IKCONFIG payload is byte-identical, SHA256
`99352a4f8db49814330c9d2c28038fafbbd1dadbe1fef3082c6d7e2614c2dbf1`.

## Ramdisk Delta

The cpio audit classifies every entry, including mode, owner, timestamp, size,
and content:

- all 11 common stock entries other than `init` are exactly preserved;
- `init` is the only replaced common entry;
- no stock entry is removed;
- exactly nine Magisk-owned entries are added under `.backup` and `overlay.d`.

The stock init is preserved losslessly as `.backup/init.xz`:

- stock `init` SHA256:
  `5bc266151967c4da67e0253b4f0917150b1ccb799e199858fb436f322f10a428`;
- decompressed `.backup/init.xz` SHA256: same;
- Magisk `/init` SHA256:
  `383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468`.

The ramdisk `magiskinit`, `magisk`, `init-ld`, and stub APK each match the
corresponding arm64 payload in the pinned v30.7 APK byte-for-byte. The embedded
configuration is:

```text
KEEPVERITY=true
KEEPFORCEENCRYPT=true
RECOVERYMODE=false
VENDORBOOT=false
PREINITDEVICE=sda32
SHA1=e5d9f312f1709561e8ee81dec0d30809047e0658
```

The SHA1 equals the complete pinned stock boot image. `sda32` is confirmed as
the configured pre-init device string only; its S22+ partition meaning remains
unresolved. A90 storage mappings are not evidence for this target.

## Expected Boot Flow

This section is source-grounded expected behavior, not a new live trace.

1. The kernel executes the ramdisk `/init`, which is the exact v30.7
   `magiskinit` binary.
2. PID 1 mounts temporary proc/sysfs only if needed, reads boot configuration,
   and selects first-stage, second-stage, recovery, legacy-SAR, or rootfs mode.
3. The stock init contains `selinux_setup`, `first_stage_ramdisk`, and
   `second_stage_resources`, so S22+ is structurally a two-stage-init target.
   Exact runtime branch selection remains unobserved in this host-only unit.
4. In first stage, Magisk copies its init, backup, and overlay into a temporary
   `/data` tmpfs, decompresses/restores the original init, and eventually execs
   it. See official [`init.rs`](https://github.com/topjohnwu/Magisk/blob/e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac/native/src/init/init.rs#L33-L45).
5. In second stage, it prepares `/debug_ramdisk` when `/sbin` is absent,
   materializes the compressed Magisk payloads, injects root overlays and rc
   fragments, patches SELinux setup, and then execs original Android init. See
   [`rootdir.cpp`](https://github.com/topjohnwu/Magisk/blob/e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac/native/src/init/rootdir.cpp#L262-L335)
   and [`mount.rs`](https://github.com/topjohnwu/Magisk/blob/e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac/native/src/init/mount.rs#L95-L107).
6. `PREINITDEVICE` is located through sysfs block metadata and mounted read-only
   during early setup; this does not establish what `sda32` names on this S22+.

## R3 Carrier Contract

Use these labels precisely:

- `byte-identical-stock-kernel`: exact shipped stock kernel hash. A rebuild is
  not expected to satisfy this.
- `static-stock-equivalent-kernel`: the unpatched R2-GO rebuild whose config,
  KMI CRCs, vermagic, required-symbol closure, layout, and every residual delta
  are explained.
- `magisk-equivalent-kernel`: the static-stock-equivalent kernel plus exactly
  the v30.7 DEFEX and PROCA binary patches, with RKP and legacy-SAR patch steps
  remaining no-ops.

Selected first live proof: `magisk-equivalent-kernel`. It preserves the known
booting security posture and keeps Magisk `uid=0` as a legitimate PASS signal.
It is not an unchanged or strict stock kernel.

Required order:

1. R1 completes an unmodified Full-LTO build.
2. R2 grants static stock-equivalence to the unpatched rebuild.
3. A future host-only candidate builder applies pinned Magisk v30.7 semantics.
4. A future candidate audit compares the unpatched rebuild against its patched
   candidate and requires only DEFEX+PROCA changes. Multiple patch-pattern
   matches or any other delta stop before packaging.
5. Only then may a boot-only AP and fresh SHA-pinned one-shot `AGENTS.md` policy
   be prepared. This report grants no live authorization.
6. Live PASS requires Android, hardware identity, required modules, USB,
   display, storage, Magisk root, and mandatory rollback to the pinned current
   Magisk boot even on success.

A strict unpatched live proof remains a separate optional experiment. If used,
Magisk root must be removed from its PASS requirements; boot and hardware health
are the proof target.

## Reproduction

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_magisk_boot_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 -m unittest tests.test_s22plus_fyg8_magisk_boot_audit -v
```

Private machine-readable result:
`workspace/private/outputs/s22plus_fyg8_magisk_boot_analysis_r0/audit.json`.
