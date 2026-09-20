# S22+ Debian construction and first-boot preparation

Debian 13 arm64, SysVinit and BusyBox mdev. This directory builds a private
rootfs and an ARM64 **virt-only** initramfs, and separately compiles prospective
FYG8 storage initialization. The separate `device/` producer now constructs
an exact FYG8 boot/AP candidate with an embedded installer. All construction
and VM commands remain H0; the separate reviewed device owner is required
for any connected preparation or effect.

The rootfs uses a named `lab` account with a supplied public key, disables
password/root SSH login, and creates missing SSH host keys on first boot.
`mdev` owns a tmpfs `/dev`; Debian owns logging, cron, networking and SSH.
The systemd package is present through package dependencies; SysVinit owns
PID 1, and neither systemd-sysv nor udev is installed. The packaged initscripts
udev entry exits when its daemon is absent.

## Construction

Run from the repository root as the ordinary host user. Prerequisites include
`mmdebstrap`, `uidmap`, `arch-test`, the Debian archive keyring, registered
ARM64 qemu-user/binfmt, the GNU ARM64 cross compiler, e2fsprogs, and QEMU's
ARM64 system emulator. Unprivileged user/mount/PID namespaces must work.
All output directories below are fresh private directories.

```sh
python3 workspace/public/src/debian/s22plus_v1/h0.py rootfs \
  --output workspace/private/outputs/debian-example/rootfs \
  --authorized-key /absolute/private/path/to/key.pub
python3 workspace/public/src/debian/s22plus_v1/verify_packages.py \
  workspace/private/outputs/debian-example/rootfs
python3 workspace/public/src/debian/s22plus_v1/h0.py vm-image \
  --output workspace/private/outputs/debian-example/vm \
  --archive workspace/private/outputs/debian-example/rootfs/rootfs.tar
python3 workspace/public/src/debian/s22plus_v1/h0.py storage \
  --output workspace/private/outputs/debian-example/storage
```

`rootfs --lock /path/to/packages.tsv` pins every selected package version.
The essential/extras archives and signed indexes are retained before cleanup.
`verify_packages.py` verifies both InRelease signatures, their uncompressed
Packages hashes, and all installed package identities against the retained
`.deb` files. A new online build needs those versions to remain available.
Two builds of the final 2026-09-21 selection produced identical tar archives.
Private SSH keys and raw evidence must never be committed.

Build upstream Linux **5.10.226** for `ARCH=arm64` with
`CROSS_COMPILE=aarch64-linux-gnu-`, `KCONFIG_ALLCONFIG` pointing to
`qemu-5.10.config`, and `make allnoconfig` followed by `make -j8 Image` in a
private out-of-tree build directory. Verify the resolved `.config`, not just
the requested fragment. This VM kernel mirrors the selected FYG8 omissions
and required userspace facilities; its virtual hardware drivers differ.
It is not a replacement for the retained Samsung Image.

## Integration checks

`vm_test.py` accepts `--folder`, `--kernel`, `--qemu-root` and `--key`.
The QEMU root contains `usr/bin/qemu-system-aarch64` and its supplemental
libraries under `usr/lib/x86_64-linux-gnu`. The host forward binds only the
loopback address. The VM overlay enables key-only root SSH for the harness;
that override is absent from the reusable rootfs archive.

Before the lifecycle test, preserve `root.ext4` as `pristine.ext4` using a
sparse regular-file copy. The test performs real PID 1/root checks, a user PTY,
mdev cold-scan recreation, logger/cron/SSH lifecycle, DHCP duplicate start and
stop/reconnect, a signed apt install of `hello`, one cron job, normal reboot,
persistence, normal shutdown and a read-only host filesystem check.

`negative_test.py` accepts `--base` (the VM directory), a fresh `--output`,
and the same kernel/QEMU/key arguments. It checks wrong UUID, missing loader,
lost init execute permission, changed `/sbin` link, changed executable bytes,
and failed ext4 mount. Each case must stop before handoff and leave its entire
private disk image byte-identical to the pre-boot fixture.

## Deliberate limits

The initramfs owns a fixed content/metadata manifest for existing executable
and configuration paths. This prevents an unexpected root, loader or service
configuration from entering the destructive root transition. The declared
mutable paths (including Debian's `/etc/mtab`) and new unlisted files are
outside that binding. Existing bound package/configuration changes require a
new pair. This is an H0 qualification fixture, not a permanent update policy
for a general-purpose Debian installation. Review it when the selected package
set or post-handoff update design changes; retire this fixture constraint when
the target's reviewed update/identity mechanism replaces it.

`storage.c` is a compile-only function with a fixed module table derived from
the exact retained vendor archive and prospective provider roots. It has no
entrypoint and is not linked into the virt initramfs. It does not prove UFS
probe/bind readiness, firmware availability, target device events, USB access,
thermal behavior or recovery. The separate device adapter below binds the
existing GPT/partition/filesystem/witness and implements hardware preparation,
installation, post-handoff observation and Android return under its own review.

See the [construction report](../../../../../docs/reports/S22PLUS_DEBIAN_BOOTSTRAP_H0_2026-09-21.md)
for exact outcomes, retained failures, provenance and the prospective device plan.

## Exact device candidate

`device/prepare.py --output <fresh-private-directory>` consumes the retained
rootfs and P399 hardware/kernel inputs. It generates unique private SSH/USB
identities and an embedded compressed archive, compiles static ARM64 PID 1
twice, and repacks the retained boot-v4 envelope twice. Source snapshots,
archive content/metadata manifests and all actual bytes stay private.
It performs no device command, staging, mount, formatting or activation.

`device/vm_install_test.py build|qualify|negative` exercises the actual installer
on a sparse regular-file disk with the sealed 4096-byte geometry and complete
GPT. It substitutes virtual board discovery/module loading and Ethernet for
FYG8 hardware. The tests perform installation, restricted SSH qualification,
ordinary reboot/persistence and shutdown, plus six fail-closed cases. They
never mount a host block device and do not establish Samsung hardware behavior.

`s22plus_debian_artifact_v1.py` joins the actual AP, boot, kernel, modules,
archive, manifests, keys and source snapshots to those retained raw VM results.
Its qualification is H0 only. The explicit owner
`s22plus_debian_first_boot_v1.py` uses `prepare`, `approve`, `execute` and
`recover`; it refuses normal work without the source-bound independent review.
Only the operator's actual returned finite attended statement may be passed
to `approve`. Never reuse a VM key, invent that statement, replay a consumed
installation or replace recovery with another candidate transfer.

See the [first-device H0 report](../../../../../docs/reports/S22PLUS_DEBIAN_FIRST_BOOT_H0_2026-09-21.md)
and [exact policy](../../../../../docs/operations/S22PLUS_DEBIAN_FIRST_BOOT_V1.md).
