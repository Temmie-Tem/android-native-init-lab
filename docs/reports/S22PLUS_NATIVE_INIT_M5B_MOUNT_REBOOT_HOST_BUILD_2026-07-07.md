# S22+ Native-Init M5B Mount/Reboot Host Build - 2026-07-07

## Scope

Host-only build of the M5B front-split candidate after M5 v0.4 USB-ACM produced
no transport. No live flash was run, no device partition was written, and no
reboot was requested.

M5B intentionally does not touch the full USB chain. It tests only the
freestanding C/raw-syscall harness plus early virtual filesystem mounts before
requesting `reboot(..., "download")`.

## Inputs

```text
source   workspace/public/src/native-init/s22plus_init_mount_reboot_m5b.c
builder  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m5b_mount_reboot.py
base     workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img
```

The builder starts from the known-booting Magisk boot image, proves a no-change
`magiskboot unpack/repack` is byte-identical, replaces only ramdisk `/init`,
and emits a boot-only Odin AP containing exactly `boot.img.lz4`.

## Native Init Behavior

The built `/init` is a freestanding AArch64 static `EXEC` binary with no
program interpreter. It uses direct syscalls only:

```text
mkdir /dev /proc /sys /config
mount /dev as devtmpfs, falling back to tmpfs
create /dev/kmsg /dev/console /dev/null /dev/zero
emit S22_NATIVE_INIT_MOUNT_REBOOT_M5B marker
mount /proc
mount /sys
mount /config
emit mounts_done
sleep 100 ms
reboot(..., "download")
park forever if reboot syscall returns
```

It does not insert modules, create a USB gadget, mount persistent partitions,
write block devices, touch watchdog, start Android/Magisk, or use glibc startup.

## Built Artifact

```text
output      workspace/private/outputs/s22plus_native_init/inplace_m5b_mount_reboot_v0_1
AP.tar.md5  workspace/private/outputs/s22plus_native_init/inplace_m5b_mount_reboot_v0_1/odin4/AP.tar.md5
member      boot.img.lz4
```

Hashes:

```text
AP.tar.md5                  872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59
AP.tar                      dcbd7898b4bdb69c4ccbf38cfb3a0cc41c50f0c551a14175dbc84dc9e7b077ea
boot.img                    21a61c84d273390a3681d029977ff6150991036568aa455a0a4879ff24590239
boot.img.lz4                542ba1a33a07a252cc675e233d41ccfe7c91d654a330cc6ba7882c963dcc3571
base Magisk boot            2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
M5B /init                   accfc6f5e04d7d302ee17c6e4ce93ee14240ebdbb70274424934805e542b9bac
source                      d41eea0711bef2d5b1f1615afd201bd442ecdb94db511f8fe1fb3e5a0dee337a
ramdisk after               e7319ab7991889d3c1791863fecbc0170e5f2f2347f72aab42493adfed1fd08e
```

Sizes:

```text
AP.tar.md5                  100669481
boot.img                    100663296
boot.img.lz4                100663699
M5B /init                   2336
ramdisk before              1492480
ramdisk after               1294856
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m5b_mount_reboot.py
aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin \
  -fno-stack-protector -Os -Wall -Wextra -Werror -Wl,-e,_start \
  -o /tmp/s22plus_m5b_mount_reboot_test \
  workspace/public/src/native-init/s22plus_init_mount_reboot_m5b.c
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m5b_mount_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m5b_mount_reboot_v0_1/odin4/AP.tar.md5
git diff --check
```

All passed. The builder also verified byte-identical no-change repack, base and
patched boot size, replaced `/init` hash, unchanged kernel hash, single tar
member, required strings, no dynamic-loader strings, no USB-module/gadget
strings, and Odin invalid-device parse gate.

## Future Live Interpretation

```text
self-download       freestanding C + VFS mounts reached reboot request
retained marker     candidate reached kmsg marker before reboot request
no transport        failure is before/during freestanding C/VFS mount/reboot beacon
```

A live gate still needs a fresh SHA-pinned `AGENTS.md` exception and guarded
helper. This host-build unit does not authorize flashing.
