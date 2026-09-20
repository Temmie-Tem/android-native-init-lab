# S22+ Debian rootfs/bootstrap construction H0

Date: 2026-09-21. Target research: `SM-S906N/g0q/S906NKSS7FYG8`.
Device actions: **zero**. All boots below are ARM64 QEMU `virt` boots.
No phone staging, Samsung boot/AP package, F1 activation or remaining grant.

## Outcome

The first host construction unit is complete: a rootfs from signed,
version-locked Debian 13 arm64 packages, a matching executable virt bootstrap, a separate prospective
FYG8 storage-loader object, reproducibility checks and real ARM64 lifecycle
and rejection tests. This advances the
[research construction plan](S22PLUS_DEBIAN_BOOTSTRAP_RESEARCH_2026-09-19.md).
It does **not** establish a Debian boot or recovery capability on the phone.

| Item | Result and boundary |
| --- | --- |
| Debian closure | 129 packages; both official InRelease signatures, uncompressed Packages hashes and every installed `.deb` independently rechecked. |
| Rootfs reproducibility | Two separate locked builds are byte-identical: 201,960,960-byte tar, SHA-256 `e6d8ec4ef0f85da6668d780c7357314be923946e386ddbbcefd9bc54c0f57789`. |
| Bootstrap reproducibility | Static ARM64 init and gzip/newc initramfs rebuild byte-identically with the same filesystem UUID, manifests, BusyBox and source inputs. |
| PID 1/root transition | Actual `/proc/1/exe` is `/usr/sbin/init`; PID 1 owns the ext4 root; temporary bootstrap children are reaped and old-root userspace does not survive. |
| Basic operation | tmpfs device nodes, devpts/user PTY, public-key SSH, mdev cold rescan, logging, cron and SSH start/stop/restart pass. |
| DHCP lifecycle | Duplicate starts retain one owner; the separate stop/start job returns status zero and its completion marker; exactly one daemon remains. |
| Package/service workload | Authenticated apt update and `hello` installation/execution; cron produces its file and logger record. |
| Fresh boot/persistence | Normal SysV reboot, different boot ID, second boot counter, retained user file, installed package and SSH host key; normal shutdown and `e2fsck -fn` pass. |
| Rejection tests | Wrong UUID, missing loader, lost init execute permission, changed `/sbin` link, changed executable content and failed ext4 mount stop before handoff; all six complete disk hashes remain unchanged. |
| FYG8 storage preparation | 42 exact stock modules in dependency order, derived from explicit provider roots plus the existing eight-module UFS declaration; ARM64 object compiled, no insertion performed. |

The final lifecycle result is `vm-final-4/result.json`; the final negative
result is `negative-final-2/result.json`. Earlier partial results must not be
substituted for those terminals.

## Implementation and proof scope

Sources and reproduction instructions are in
[`workspace/public/src/debian/s22plus_v1`](../../workspace/public/src/debian/s22plus_v1/README.md).
The host build uses standard mmdebstrap in an isolated mapped-root namespace,
with signature checks enabled. The package cache is captured before essential
packages are removed. No generic Debian kernel or bootloader is installed in
the product rootfs. The systemd package and libraries are present as dependency
providers; SysVinit owns PID 1, systemd-sysv/udev are absent, and the packaged
udev init script exits without its daemon.

The virt kernel is upstream Linux 5.10.226. Its resolved config retains the
FYG8 omissions relevant to this workload: devtmpfs, FHANDLE, PID/user
namespaces, SysV IPC, POSIX message queues, cgroup PIDs, legacy uevent helper,
virtual terminals, tmpfs xattrs/ACLs and fanotify. File locking, sysctl,
Unix98 PTYs, ext4, networking and other required facilities are enabled;
virtual storage/network/RTC drivers are test substitutions. This is not the
retained Samsung kernel or a claim of complete kernel-config equivalence.

The C init is explicitly bound to the virt board and owns PID 1. It verifies
the root UUID, mounts `ro,noload`, checks the root marker and initramfs-owned
content/metadata manifests, and checks the init ELF/loader/library closure.
The metadata child chroots before inspecting types, owners, modes and exact
symlink text. The content child executes the trusted initramfs BusyBox by
descriptor after chroot. The bootstrap reaps its children, rejects surviving
userspace, remounts the verified root normally, explicitly moves `/dev`,
`/proc`, `/sys` and `/run` (including nested devpts), closes extra descriptors,
and execs BusyBox `switch_root`, which execs Debian init.

The manifest binds existing execution/configuration paths, including merged
`/usr` and SysV service links. Declared mutable files and new unlisted paths
are outside that binding. Updating an existing bound package/configuration
requires a new pair; the demonstrated additional-package install is not proof
of unrestricted updates. This H0 fixture blocks accidental mismatched root
execution before destructive handoff. Its scope ends with this qualification
pair; review is triggered by package/configuration changes, and a reviewed
target update/identity design must replace it before general-purpose use.

The reusable rootfs enables key-only `lab` SSH and disables root/password
login. Only the private virt overlay enables root-key access for lifecycle
tests, behind a host loopback forward. Host keys are generated uniquely and
persisted in the tested VM. Raw identities, keys, logs and images remain private.

`storage.c` is separate from the renderer and has no entrypoint. Its generated
table pins each module's bytes/size, verifies its descriptor, and specifies
one `finit_module` attempt with empty parameters. It is not linked into the
virt initramfs. The module vermagic contains `-gki-`; the retained Image's
uname/banner release does not. These separately observed identities are
preserved rather than normalized into an invented common string.
The selected provider roots and symbol dependencies are a construction
hypothesis, not proof of platform binding, firmware requests, UFS readiness,
USB, power or thermal behavior. No DRM renderer is used by this prototype.

SELinux is compiled into the VM kernel with the relevant FYG8 settings.
No Debian SELinux policy is installed; the observed post-handoff state is
permissive. This is not enforcing-policy qualification. Likewise, mdev tests
cover initial/cold rescan and service ownership, not injected hotplug events
or FYG8 firmware handling.

## Retained corrections and independent review

Initial host setup needed `arch-test` and a root user mapping that could read
the private build paths. An initially future SOURCE_DATE_EPOCH was corrected
before the final paired builds. Generic allnoconfig initially omitted block/
virtio support, file locking, sysctl, RTC and BASE_FULL; the resolved config
was corrected against the retained FYG8 evidence before final tests.

Independent review found a non-idempotent DHCP start. The service now uses
one pidfile-owned foreground udhcpc under start-stop-daemon. Metadata binding
was expanded to cover symlinks and permissions. The first fresh-boot check
then correctly exposed Debian changing `/etc/mtab`; the symlink enumeration
was fixed to honor its already-declared mutable status.

Review also caught a test-harness false positive: a missing asynchronous DHCP
completion file was followed by another successful shell command. The original
`vm-final-2/result.json` is preserved with a separate superseding audit note;
its combined lifecycle claim is invalid. The corrected harness checks job
status, marker and daemon count independently. It then exposed direct execution
of a temporary test script on Debian's noexec `/run`. Invoking its shell
explicitly fixed that harness error. A fresh disk produced the final
`vm-final-4` result with actual `job_status=0` and `NETWORK_CYCLE_PASS` evidence.
The six negative cases use the unchanged final runtime bytes.

The independent review covers this H0 source/evidence scope. It is not
source-bound activation of a Samsung runner or a grant for any device effect.

## Prospective staging and post-handoff recovery

This is a concrete next design unit, **not an active device policy**.
The [existing native ext4 exception](../operations/S22PLUS_NATIVE_EXT4_V1.md)
explicitly excludes Debian rootfs staging. P399/P400, their format attempt and
finite grant remain consumed. The filesystem, witness and Android32 layout
must be preserved.

1. **Exact staging owner:** design a fixed, attended native-rootfs staging
   successor with a fresh target/boot binding, full existing GPT comparison,
   both native/userdata sysfs extents, filesystem UUID/features/clean state and
   preserved witness. Reuse the existing validated resolver and metadata
   reader where appropriate. Existing format/recovery grants confer no write
   authority. Common/target review and the new finite scope are prerequisites.
2. **Payload and write set:** bind the 201,960,960-byte archive, its complete
   inventory, authorized account key and unique per-install SSH host-key
   bundle. A proposed first staging path transfers the exact archive through
   reviewed ordinary Android staging, then runs one fixed privileged installer
   on the exact existing native filesystem. Reject archive escapes, unexpected
   nodes, conflicting existing roots and witness replacement before extraction.
   The initial installation owns only the declared Debian paths; no formatter,
   GPT writer, Android userdata writer or generic root shell is part of it.
   Record one intent before extraction, bounded output, readback, fsync/syncfs
   and normal unmount. Interrupted or uncertain writes do not replay; preserve
   partial data for read-only diagnosis. Boot restoration does not undo them.
3. **Target bootstrap adapter:** join the required stock/custom hardware
   providers, existing native partition/GPT/witness checks and the tested
   handoff logic. Qualify actual module probe readiness and needed firmware;
   then build a fresh Samsung boot candidate. The current virt initramfs and
   compile-only storage object are not that candidate. Do not reuse consumed
   P399/P400 as installation authority.
4. **One post-handoff access owner:** Debian takes the selected USB NCM gadget,
   addressing, SSH and health ownership after the native observer terminates.
   Pin the per-install SSH public host key before handoff, so first device
   observation is not accepted merely through trust-on-first-use. Qualify
   controller/PHY/custom-PDIC providers, configfs ownership, device permissions,
   addressing/DNS/time and required power/thermal behavior. The virt network
   proves none of these hardware-specific transitions.
5. **Observation and return:** extend the owner to identify one Debian boot's
   actual PID 1, root/build, absence of native userspace, authenticated SSH,
   selected service and persistent state. A responsive Debian normal shutdown
   followed by the fixed Download reboot needs separate implementation and
   target qualification. Do not send an old resident CONTROL command after
   its owner has been replaced or interpret planned USB departure as health.
6. **Failure cases:** pre-exec failure leaves the bootstrap parked; failed
   switch_root/init, missing SSH and kernel/UFS/USB stalls have different last
   available controls. No automatic recovery has been proved. The first live
   unit must bind attendance, exact retained physical Download/original-A
   recovery and rooted Android/GPT/capacity final health. Physical Download
   must terminate the experimental kernel before that one bound A transfer.
   Filesystem integrity remains a separate result; do not reformat or repair it
   merely to close Android recovery.

## Private evidence

All evidence is under
`workspace/private/outputs/s22plus-debian-bootstrap-h0-20260921-1/`:
`rootfs-c/`, `rootfs-d/`, `bootstrap-repeat/`, `kernel-build/`,
`storage-final-2/`, `vm-final-4/`, `negative-final-2/`, build logs, the earlier
failed/partial runs, and their audit notes. Exact source/tool/artifact
identities and the final independent-review disposition are retained in the
private construction summary. No raw evidence or compiled artifact is tracked.
