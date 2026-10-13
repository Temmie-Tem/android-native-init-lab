# Debian-owned early boot, ARM64 H0 prototype

This prototype runs Debian initramfs-tools' shell `/init` as initial PID 1,
then Debian's packaged `run-init` executes installed SysVinit. The existing
native PID1/console runtime is not in this boot path. The original `h0.py`/`vm.py` path uses fresh private regular-file disks for
QEMU `virt`. The `fyg8.py` port below builds a prospective target initramfs.
Neither path contains a device transport, Samsung boot package or activation
command.

The retained virtual Linux 5.10.226 kernel has DEVTMPFS and FHANDLE disabled.
Its storage/network drivers are built-in virtio substitutes, not FYG8 UFS/USB.
The existing Debian root fixture and read-only metadata/content consumers are
reused. A small C child verifier includes those consumers; linker garbage
collection removes the old C PID1 entrypoint and unused boot machinery.

## Construction and test

Run from the repository root with **new** output directories:

```sh
python3 workspace/public/src/debian/s22plus_initramfs_h0/h0.py fetch \
  --output workspace/private/outputs/debian-early-example/packages
python3 workspace/public/src/debian/s22plus_initramfs_h0/h0.py build \
  --packages workspace/private/outputs/debian-early-example/packages \
  --output workspace/private/outputs/debian-early-example/build
python3 workspace/public/src/debian/s22plus_initramfs_h0/vm.py \
  --build workspace/private/outputs/debian-early-example/build \
  --output workspace/private/outputs/debian-early-example/vm
```

`fetch` verifies Debian trixie's InRelease and ARM64 package index before
extracting six build packages. The reference run used initramfs-tools 0.148.4.
`build` independently rechecks that chain, verifies the retained root archive
and virtual kernel/configuration, compiles the ARM64 child verifier, and uses
Debian `mkinitramfs` twice inside a mapped-root user/mount/PID namespace.
No package is installed in the host system. The existing isolated builder
requires working ARM64 binfmt/QEMU-user, the GNU ARM64 compiler, the Debian
archive keyring and the prior private bootstrap fixtures/tools.

The builder intentionally extracts the needed tools into a private Debian
tree without installing udev. Its device setup is explicitly adapted; this
is not an unmodified default Debian initramfs or a supported on-device package
update path. The fixed historical inputs fail closed if their bytes differ.
Missing inputs are not permission to rebuild a phone root or reuse old grants.

`build.json` records source snapshots, exact package-manifest identity,
generated binding and root-manifest inputs, helper/image identities and A/B
equality. `vm.py` preserves raw serial/SSH logs and a structured result even
when a check fails. Its positive path proves early and installed PID1 in the
same boot, actual root/dev mounts, public-key SSH, ordinary shutdown and clean
ext4. Wrong UUID and modified init cases must stop before writable admission
and leave the entire copied disk byte-identical to its pre-boot state.

## Small runtime adaptation

| File | Responsibility |
| --- | --- |
| `h0-dev` | Replaces the single devtmpfs mount line in Debian `/init`; admits only the virt board, creates tmpfs device nodes and cold-scans with mdev. |
| `h0-boot` | Debian's `BOOT=` extension for the fixed VM root; partition RO, identity/clean-state checks, read-only fsck, protected mount/manifests, then normal RW root mount. |
| `h0-bottom` | Moves `/dev` into the new root before Debian's existing final mount moves and `run-init`. |
| `h0-hook` | Build hook that includes the checker and exact root manifests. |
| `root-check.c` | Child-only virt identity/clean-state check and reused root metadata/content consumers; cannot run as PID1. |

There is no early mdev daemon to transfer or stop: the virtual storage is
already registered and a cold scan suffices in this experiment. Installed
Debian starts its own mdev service. This does not establish the correct event
or firmware lifecycle for the phone.

The first successful result and independent review are recorded in the
[H0 report](../../../../../docs/reports/S22PLUS_DEBIAN_OWNED_EARLY_BOOT_H0_2026-10-07.md).
The next target question is the complete cold platform/UFS preparation and
its early evidence path. Physical root admission, recovery, USB and service
qualification remain separate. Kernel modification was unnecessary for this
VM result; later kernel work should address a demonstrated target need or a
measured optimization, with its own validation.

## FYG8 preparation port

`fyg8.py inventory` rederives 73 retained platform modules plus eight UFS
modules, checks symbol CRC closure against the fixed Image and preceding
modules, and preserves private inspection evidence. `fyg8.py build` emits the
Debian-owned initramfs containing a child preparation helper. The production
hook always stops after GPT/protected-superblock observation; it has no root
mount, repair, installed-init execution, USB gadget or recovery operation.

```sh
python3 workspace/public/src/debian/s22plus_initramfs_h0/fyg8.py inventory \
  --output workspace/private/outputs/fyg8-early-example/inputs
python3 workspace/public/src/debian/s22plus_initramfs_h0/fyg8.py build \
  --inputs workspace/private/outputs/fyg8-early-example/inputs \
  --packages workspace/private/outputs/debian-early-example/packages \
  --output workspace/private/outputs/fyg8-early-example/build
python3 workspace/public/src/debian/s22plus_initramfs_h0/fyg8_vm.py \
  --inputs workspace/private/outputs/fyg8-early-example/inputs \
  --build workspace/private/outputs/fyg8-early-example/build \
  --output workspace/private/outputs/fyg8-early-example/vm
```

The VM derivative substitutes board checks, module insertion/presence and UFS
sysfs discovery. All module file checks, real block ioctls, exact GPT and
superblock reads and RAM evidence writes still execute on ARM64. VM-only
terminal export and poweroff are absent from the target hook. Sparse extent
fingerprints include every allocated byte and hole position of the writable
regular-file disk; they are not a whole-file SHA-256.

`METADATA_CLEAN` is not full root admission. RAM records are lost on reset and
are not authenticated device evidence. Module presence is not firmware or
driver readiness. The [FYG8 H0 report](../../../../../docs/reports/S22PLUS_DEBIAN_FYG8_PREPARATION_H0_2026-10-07.md)
records exact scope, provenance, tests, firmware limits and the remaining
physical work. These commands never activate a phone candidate.

## Integrated initial boot and installed services

`integrated.py build` constructs the separate `debian-integrated-v1` candidate.
Debian `/init` runs the fixed platform and parent-measurement children, then
execs the temporary PID1 transition entry. Stock logger readiness uses the
observed `8.samsung,kernel_log_buf` binding. A fixed intermediate SPMI provider
barrier precedes client insertion, and raw ACM is published before the eight
UFS modules. Complete protected current-root admission precedes the sole
native_data RW mount and installed SysVinit.

`integrated_vm.py --build … --output …` runs actual Debian startup, root checks,
child settlement, 120-second services, same-boot pinned SSH and controlled
shutdown on private regular-file disks. It substitutes Samsung module, board,
provider, UFS discovery, USB and network hardware. Rejected module, parent,
descriptor, authentication and root cases must preserve the disk exactly.
`integrated_package.py --build … --vm … --output …` packages the unchanged
retained kernel with that qualified initramfs and checks actual boot/AP joins.

The distinct first wire request is an effectful compound start with a durable
host intent. It is never an early read-only retry. Fixed continuations and SSH
shutdown remain bound to the existing V3 journal and original physical-return
owner. Checked bounded local service records can survive classified reporting
loss after START, but do not prove USB receipt or SSH. Neither H0 output nor a
passing VM opens a phone grant. See the
[integrated policy](../../../../../docs/operations/S22PLUS_DEBIAN_INTEGRATED_V1.md)
and [P425 report](../../../../../docs/reports/S22PLUS_DEBIAN_INTEGRATED_P425_H0_2026-10-13.md).
