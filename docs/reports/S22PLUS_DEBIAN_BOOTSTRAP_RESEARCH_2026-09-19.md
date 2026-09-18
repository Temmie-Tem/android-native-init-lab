# S22+ Debian rootfs and bootstrap research

Date: 2026-09-19. Target: `SM-S906N/g0q/S906NKSS7FYG8`.
Scope: H0 official-document, package-source and retained-artifact research.
Device actions: **zero**. No rootfs build, staging, kernel change or activation.

## Research conclusion

Use **Debian 13 trixie arm64, SysVinit and BusyBox mdev** as the first H0
construction candidate with the retained FYG8 kernel. This is a source-supported
choice to implement and test, not a qualified Debian boot configuration.
Debian's release page identifies trixie as stable and includes arm64;
`sysvinit-core` remains an available Debian package. Pin the codename and the
actual package set when constructing the rootfs, rather than following a moving
`stable` alias. [Debian release](https://www.debian.org/releases/trixie/),
[SysVinit package](https://packages.debian.org/trixie/sysvinit-core).

The retained kernel lacks both `CONFIG_DEVTMPFS` and `CONFIG_FHANDLE`, which
upstream systemd 257 lists among its requirements. Switching only PID 1 to
SysVinit does not fix the default device-manager path: Debian's actual
SysVinit 3.14-4 `debian/src/initscripts/etc/init.d/udev` explicitly refuses to
start udev without devtmpfs. Thus neither systemd/udev nor SysVinit/udev is a
ready configuration for these kernel bytes. This establishes unmet documented
requirements and a package-script rejection, not a performed systemd boot test.
[systemd 257 requirements](https://raw.githubusercontent.com/systemd/systemd/v257/README),
[Debian SysVinit packaging source](https://deb.debian.org/debian/pool/main/s/sysvinit/sysvinit_3.14-4.debian.tar.xz).

The alternative is a separately qualified FYG8 kernel enabling the missing
features and then a systemd/udev rootfs. That may become preferable for broader
desktop or service compatibility. It changes the kernel/module qualification
unit; it is not necessary to select it before testing the smaller headless
candidate. No kernel option was changed in this research.

## Exact local evidence

The embedded configuration was freshly extracted from P399's retained
`build-1/inputs/fixed-Image`, and its identity matches `build-1/result.json`:

| Input | Identity |
| --- | --- |
| Kernel version string | `5.10.226-android12-9-30958166-abS906NKSS7FYG8` |
| Image size | 41,490,944 bytes |
| Image SHA-256 | `d510a3f83a6d48392649df325223e9847f85e2ee35989f32db0fb6abff371a3d` |
| Extracted config SHA-256 | `39fa29708f124e3fa7deee49caf433cbbfd182dbb1ff13890f525de8854f15a7` |

This is retained candidate provenance, not an observation of the device's
current boot. The [ext4 live report](S22PLUS_NATIVE_EXT4_FIRST_RUN_2026-09-17.md)
separately establishes the filesystem/witness and recovered Android return.
Neither consumed P399 nor P400 is a new bootstrap candidate.

| Capability in the actual Image | Value | Consequence for the first Debian candidate |
| --- | --- | --- |
| ARM64, 4 KiB pages, ELF, initramfs | enabled | Select arm64 binaries and the existing initramfs boot route. |
| ext4, JBD2, ext4 ACL/security, tmpfs | enabled | Existing native ext4 is the root candidate; no reformat is needed. |
| procfs, sysfs, Unix sockets, epoll, inotify, signalfd, timerfd | enabled | Basic userspace facilities exist; package workloads still need testing. |
| devtmpfs, file-handle API | disabled | Default systemd/udev requirements are unmet. |
| namespaces, network namespace, UTS namespace | enabled | Do not infer that every namespace type exists. |
| PID namespace, user namespace | disabled | Do not design around containers; host PID 1 replacement remains possible. |
| cgroups, memory controller | enabled | Their presence is distinct from an actual mounted/configured hierarchy. |
| cgroup PID controller | disabled | PID-limit features are unavailable; upstream permits systemd with all controllers disabled, so this alone is not its blocker. |
| SysV IPC, POSIX message queues | disabled | Record workload limitations; the SysVinit name does not imply a SysV IPC requirement. |
| Unix98 PTYs, TTY | enabled | Prepare devpts and ptmx for SSH sessions. |
| virtual terminals | disabled | Do not retain default `tty1` through `tty6` getty entries. |
| tmpfs xattrs, tmpfs ACLs | disabled | Service isolation, permissions and labeling assumptions need explicit checks. |
| seccomp and seccomp filters | enabled | Relevant to OpenSSH; successful sandbox operation is still unproved. |
| SELinux | enabled; boot-parameter disable support absent | Declare and test the actual native policy state; do not assume `selinux=0` disables it. |
| legacy uevent helper | disabled | The old `/proc/sys/kernel/hotplug` mdev recipe is not the selected path. |
| configfs, USB gadget, ACM, NCM, ECM, RNDIS | enabled | USB network functions are compiled in; an actual usable network remains unproved. |
| IPv4, IPv6, packet sockets | enabled | Networking foundations exist, separate from link/address/routing/DNS proof. |

SysVinit 3.14's inspected `src/init.c` uses child reaping and its init-control
FIFO. That supports investigating it with `SYSVIPC=n`; it does not establish
compatibility of every service installed beside it.
[Upstream source release](https://deb.debian.org/debian/pool/main/s/sysvinit/sysvinit_3.14.orig.tar.gz).

## Device manager and package construction

Debian BusyBox 1.37.0-6 packaging enables `MDEV`, `FEATURE_MDEV_DAEMON` and
`SWITCH_ROOT`. The downloaded arm64 `busybox-static` package's SHA-256 matched
its official download page; its `mdev --help` under QEMU-user with canonical
`argv[0]=busybox` returned zero and advertised netlink daemon/foreground modes.
The upstream source binds its netlink socket before its initial sysfs scan.
This makes mdev a concrete existing implementation to evaluate, with no need
to invent a device-manager daemon. It is not a drop-in implementation of udev
rules, libudev databases or desktop seat management.
[Debian binary](https://packages.debian.org/trixie/arm64/busybox-static/download),
[Debian build configuration archive](https://deb.debian.org/debian/pool/main/b/busybox/busybox_1.37.0-6.debian.tar.xz),
[BusyBox 1.37 source](https://busybox.net/downloads/busybox-1.37.0.tar.bz2).

Design mdev as a Debian-owned service over a device-capable tmpfs `/dev`.
The bootstrap supplies only the nodes it needs to mount root and observe boot.
After handoff, Debian starts the one device manager, handles its lifecycle,
permissions and logs, and cold-scans the already registered devices. Confirm
which events must be handled before handoff; start no competing long-lived
old-root manager. Keep module/firmware rules specific to the required hardware;
do not adopt unrestricted modalias loading merely because it appears in an
example. Device-node creation, add/remove events, firmware requests, and
restart reconciliation remain integration work.

The inspected arm64 `libc6` 2.41-12+deb13u4 binary has GNU ABI note
`Linux 3.7.0`. Its package hash matched the official page. Debian's generic
build rule says minimum 3.2, so the actual architecture-specific binary was
checked rather than treating that generic value as the arm64 result. The
5.10 kernel version is above the binary's declared minimum; this is not proof
of complete libc or package compatibility.
[Debian arm64 libc package](https://packages.debian.org/trixie/arm64/libc6/download),
[Debian libc build rules](https://deb.debian.org/debian/pool/main/g/glibc/glibc_2.41-12+deb13u4.debian.tar.xz).

Construct a merged-/usr, minimal arm64 Debian root with a standard bootstrap
tool. `debootstrap --foreign` separates unpacking from the foreign second
stage; `minbase` includes required packages and apt. Preserve archive signature
verification, Release/Packages identities, versions and package hashes.
Complete configuration in an isolated host-side build environment, then remove
build-only service-start suppression and emulator artifacts from the product.
Package-page hashes used in this research are not a substitute for that signed
repository chain. [Debian arm64 bootstrap guide](https://www.debian.org/releases/trixie/arm64/apds03.en.html),
[debootstrap manual](https://manpages.debian.org/trixie/debootstrap/debootstrap.8.en.html).

The initial requested package set should include `sysvinit-core`, `sysv-rc`,
`initscripts`, `busybox-static`, `e2fsprogs`, `util-linux`, `kmod`, `procps`,
`iproute2`, `ifupdown`, `openssh-server`, CA certificates and a selected logger.
Resolve the complete dependency closure before freezing it. Do not request a
generic Debian kernel or bootloader installation for this target. Review
recommendations explicitly: OpenSSH recommends a logind implementation but
does not hard-depend on systemd as PID 1. Preserve working PAM/account behavior
instead of treating an arbitrary set of excluded packages as a valid rootfs.
[OpenSSH package](https://packages.debian.org/trixie/openssh-server),
[ifupdown package](https://packages.debian.org/trixie/ifupdown).

OpenSSH's current Debian packaging includes a SysV start/stop/restart script.
For the additional ordinary-service workload, select Debian `cron`, whose
arm64 package includes `/etc/init.d/cron`. Prove its installation, service
lifecycle and one controlled job in the integrated run; do not equate package
presence with operation. Choose the logger and any companion SysV script at
build time, checking the actual package files.
[OpenSSH init script](https://sources.debian.org/src/openssh/1:10.0p1-7%2Bdeb13u4/debian/openssh-server.ssh.init/),
[cron file list](https://packages.debian.org/trixie/arm64/cron/filelist).

## Bootstrap and ownership transition

Use the Linux **5.10** initramfs model. Its documentation and the retained FYG8
source explain why initial rootfs cannot be handled like an ordinary
`pivot_root` mount. The current unversioned documentation has different
nullfs/pivot-root language and must not be applied to this older kernel.
The prospective path is a pinned `switch_root` implementation executed by
PID 1 after preparing the mounted Debian root.
[Linux 5.10 initramfs](https://www.kernel.org/doc/html/v5.10/filesystems/ramfs-rootfs-initramfs.html).

An important implementation distinction: util-linux `switch_root` documents
moving `/proc`, `/dev`, `/sys` and `/run`; the inspected BusyBox implementation
does not do those moves for the caller. Select BusyBox for the first static
bootstrap candidate and explicitly design those mount moves, including nested
devpts/configfs mounts and private propagation. Verify the actual mount topology
before destructive old-root cleanup, and verify the init ELF, interpreter,
libraries and rootfs identity before replacing PID 1.
[util-linux semantics](https://manpages.debian.org/trixie/util-linux/switch_root.8.en.html),
[Linux 5.10 mount propagation](https://www.kernel.org/doc/html/v5.10/filesystems/sharedsubtree.html).

The bootstrap must stop and reap its temporary children, release unnecessary
descriptors, preserve only declared console/log handles and mounts, and then
exec the root-transition tool, which execs Debian init. Debian does not become
a child of a surviving native supervisor. Once the old root has been cleaned
or init successfully replaced, a bootstrap fallback cannot be assumed.

There is a concrete local coupling to remove: P399's retained renderer calls
`p351_prepare_driver()` and then `ufs1_prepare()` inside `--supervised-drm`,
before opening DRM and dropping privilege. Storage preparation is currently
embedded in a display process. A headless Debian bootstrap must extract the
needed storage/provider initialization with its dependencies, rather than
retain the renderer simply to make UFS appear. The existing eight-module UFS
order is an input; it is not the whole platform dependency closure.
[Reviewed UFS profile](../operations/S22PLUS_NATIVE_UFS_V1.md).

| Existing component | Proposed lifetime/owner | Remaining work |
| --- | --- | --- |
| Exact platform, clock, regulator, interconnect and UFS initialization | Bootstrap; loaded kernel drivers persist | Derive the necessary provider closure from actual imports/ordering; preserve module ABI and firmware identity. |
| Partition identity, native root mount and initial device nodes | Bootstrap | Bind the existing ext4 and mount scope; move needed mounts into Debian. |
| USB controller/PHY initialization and boot observation | Bootstrap until a declared handoff | Separate kernel hardware state from native console-process ownership. |
| USB gadget, addresses, routing, DNS, SSH | Debian services | One gadget owner; validate NCM first, including intentional re-enumeration and host link setup. |
| mdev, process reaping, package/service management and logs | Debian init and services | Define ordering, permissions, account setup and start/stop behavior. |
| Required thermal/power monitoring or other hardware helpers | Debian service if a userspace lifetime is actually required | Identify the exact need and test its lifecycle; telemetry alone is not thermal protection. |
| Native resident supervisor, command cage, HUD and DRM renderer | End before Debian handoff; display work deferred | Prove that no old-root service process survives. |
| Formatter and consumed ext4 witness operation | No role in normal Debian boot | Preserve the existing filesystem and witness. |

Firmware requested after handoff must still be available through the selected
kernel's search/loading mechanism in the new root. A module remaining loaded
does not establish that a later reprobe or resume needs no firmware.
[Linux 5.10 firmware API](https://www.kernel.org/doc/html/v5.10/driver-api/firmware/request_firmware.html).

## Access, failure and proof

USB NCM is the first network candidate because its function and underlying
network facilities are present. This is a static capability observation, not
network qualification. Debian must own configfs gadget policy and link setup;
define the handoff from the boot observer so two processes do not compete for
the same gadget. Host routing can provide package-network access, but normal
Debian boot must not need an interactive native shell or a host control daemon.
[Linux 5.10 gadget configuration](https://docs.kernel.org/5.10/usb/gadget_configfs.html).

Prepare a named account, private deployment of its authorized public key and
unique host keys, an actual PTY-capable `/dev`, and persistent logs. Validate
the effective SSH configuration and authenticated command/session behavior.
DNS, usable routing, time/certificate behavior and apt operation are separate
checks. [Debian SSH configuration](https://manpages.debian.org/trixie/openssh-server/sshd_config.5.en.html).

Host-only checks should first cover the resolved package set, loader and init
paths, device-manager scripts, mount ordering, old-root cleanup and service
configuration. An ARM64 system VM can test a representative full PID 1/root
transition with a comparable kernel configuration; its virtual devices are
not the FYG8 UFS/USB hardware. QEMU-user executes translated userspace on the
host kernel, so its successful mdev help probe is only applet availability.
[QEMU user emulation](https://www.qemu.org/docs/master/user/main.html).

The subsequent integrated device run must identify, in one boot, Debian's
actual `/proc/1/exe`, root mount and rootfs build, initial PID namespace,
absence of old native userspace owners, authenticated SSH, package operation
and the selected service workload. Then test clean shutdown/fresh Debian boot
and retained configuration/data. Exec-intent, a child shell, or an open port
cannot substitute for these observations.

Before that run, qualify post-handoff recovery against the fresh bootstrap:
pre-exec preparation failure, init/loader failure during transition, Debian
without SSH, and kernel/storage/USB nonresponse have different last available
controls. The existing physical Download/original-A route is a design input,
not proof that Debian will automatically return. Debian reboot-to-Download
semantics also need explicit implementation and qualification. Android boot
restoration does not undo rootfs writes or prove ext4 integrity after failure.
The old finite grant is closed; staging and handoff need their separately
reviewed scope under the existing contracts.

## Next bounded implementation unit

Build the first **host-only matched rootfs/bootstrap candidate** using the
above package/init/device-manager choice. Its completion criterion is:

1. a recorded signed package closure and generated rootfs manifest, with the
   exact init, dynamic loader, services, account setup and writable paths;
2. a minimal bootstrap dependency list and concrete mount/exec/child-cleanup
   implementation, with UFS no longer dependent on a running DRM renderer;
3. representative ARM64 host validation of root transition and selected
   userspace behavior, with device-only gaps still explicit; and
4. a concrete prospective staging and post-handoff recovery design, preserving
   the existing ext4/witness and Android32 layout.

Rootfs construction, package closure resolution, Debian PID 1, target mdev
events, target SSH, persistent Debian boot and post-handoff recovery remain
**unproved**. No new live gate or capability is activated by this report.

## Retained research evidence

Private evidence is in
`workspace/private/outputs/s22plus-debian-bootstrap-research-20260919-1/`:
`kernel-evidence.json`, `kernel.config`, source/archive indexes and selected
source members, `local-source-index.json`, `binary-inspection.json`, the
canonical-argv0 mdev help result and `research-summary.json`.

The research also preserves two host-inspection corrections: matching BusyBox
by basename initially selected both its executable and a config file; an exact
member fixed that selection. Running its renamed executable without canonical
argv0 selected a nonexistent applet; using `argv[0]=busybox` returned the
expected help. Neither attempted a device action or a root transition.

Source downloads and binaries stay private. Only this claim-bounded report
and the current goal update belong to the public change. Existing consumed
results, policy/review bindings and unrelated work remain unchanged.
