# S22+ switch_root primary-source research

## Finding and scope

The initramfs-to-Linux-root handoff is established practice on Android-derived
platforms. The selected S22+ bootstrap follows the main BusyBox pattern, but
P405 has no recovered proof that it reached or crossed that boundary. P406's
clean, matching root observation does not locate P405's earlier stop. The next
useful distinction is preparation complete, replacement PID 1 entered, and
distribution init entered, observed independently of Debian NCM/SSH.

This is H0 research only: public-source retrieval, retained host artifact
inspection and documentation. No device command, image construction, policy
activation or new grant occurred. P406 remains closed with healthy Android.

Exa searches covered three angles: implementation requirements, mobile Linux
handoffs, and early-boot observation. Eight queries requested 43 results; only
relevant primary sources and a developer's own porting account informed the
conclusions below. Several postmarketOS wiki results returned an access
challenge and were not treated as readable evidence. Search/fetch material and
local identities are private under
`workspace/private/outputs/s22plus-switch-root-web-h0-20260926-1/`.

## Applicable implementation semantics

Use the [Linux 5.10 initramfs documentation](https://www.kernel.org/doc/html/v5.10/filesystems/ramfs-rootfs-initramfs.html)
for this kernel generation. Initial rootfs is ramfs/tmpfs; this document
describes freeing its contents, moving the mounted replacement root over it,
changing process root and executing the next init. The initramfs `/init` is
PID 1 and must arrange the handoff itself. A chroot-child success is not this
transition. Newer kernel documentation is not automatically applicable to
the retained FYG8 kernel.

The retained ARM64 BusyBox binary identifies itself as 1.37.0,
Debian `1:1.37.0-6+b9`, and `file` confirms static linkage. The matching
[Debian source-version implementation](https://sources.debian.org/src/busybox/1%3A1.37.0-6/util-linux/switch_root.c/)
checks PID 1, a different filesystem for the new root, a regular old `/init`
and ramfs/tmpfs as the old root. It removes old-root contents, performs the
mount move/chroot and executes the selected init. It does not implement the
four pseudo-filesystem moves for its caller. Internal failures terminate the
applet rather than returning to the replaced bootstrap program.

The [util-linux implementation](https://github.com/util-linux/util-linux/blob/master/sys-utils/switch_root.c)
does include handling for `/dev`, `/proc`, `/sys` and `/run`. Its options and
mount behavior must not be attributed to the BusyBox binary merely because
both commands are named switch_root. No change of implementation is justified
by the present evidence.

## Closely related cases

| Primary source | Observation | Relevance and limit |
| --- | --- | --- |
| [Halium distribution architecture](https://github.com/Halium/docs/blob/master/Distribution.rst) | Its boot image mounts a Linux root image and uses an exec-based switch_root to start host systemd; Android services run later in LXC. | Direct architectural precedent for a Linux host init on an Android-derived platform. Its systemd/LXC and storage layout differ from this SysVinit/native_data design. |
| [Halium Early Init](https://docs.halium.org/en/latest/porting/debug-build/early-init.html) | Provides initramfs debugging before the main system, including a pre-switch state exposed through USB descriptors and a diagnostic log. | Separate early-boot evidence from main-system SSH. Descriptor signaling still requires functioning USB enumeration and cannot prove stages before it works. |
| [Developer account: stock kernel on postmarketOS, 2021-03-01](https://mainlining.dev/2021/03/01/running-stock-kernel-on-postmarketos/) | The phone exposed a USB network device but no usable debug service. Moving observation points through init located a stall in partition-mounting code. | Similar missing-debug-endpoint symptom can precede root handoff. The article's deliberate PID 1 exit/panic method is not an adopted S22+ procedure; its successful demonstration was initramfs bring-up, not proof of our full Debian boot. |
| [postmarketOS initramfs refactor, 2024](https://gitlab.com/postmarketOS/pmaports/-/commit/cb8414a20d5cd6fef842482d427e6412bd3a6f6a) | Separates early setup/debug facilities from later root preparation and final init transition. | Useful staged-observation precedent. Historical source diff, not a current package qualification or a drop-in runner. |
| [Samsung milletwifi USB issue, 2024](https://gitlab.com/postmarketOS/pmaports/-/issues/2564) | Retained initramfs debug output reports a gadget/UDC failure while other initramfs work is visible. | Missing USB networking is not by itself evidence of switch_root failure. Different Samsung target and kernel. |
| [Droidian debugging guide](https://docs.droidian.org/porting-guide/debugging-tips/) | Lists distinct pre-boot partition, command-line, console and later USB/service failures. | A useful distinction between failure stages; its recovery writes and service workarounds are not applied here. |

[Droidian's kernel guide](https://docs.droidian.org/porting-guide/kernel-compilation/)
also explicitly expects kernel adaptation and lists devtmpfs, virtual console
and USB configuration requirements. Its systemd/udev assumptions differ from
the selected S22+ userspace. This is evidence that successful phone Linux ports
have explicit kernel/userspace contracts, not evidence that the unmodified
FYG8 kernel needs any particular change.

The exact-target search did not establish a public SM-S906N/g0q/FYG8 handoff
success. The [S22+ upstream submission returned by that search](https://lkml.iu.edu/hypermail/linux/kernel/2505.0/03179.html)
is explicitly SM-S906B/g0s with Exynos 2200. It is not this target, and its
device-tree or CPU workarounds cannot be transferred to g0q.

## Comparison with the actual local consumer

The current [handoff.c](../../workspace/public/src/debian/s22plus_v1/handoff.c)
already has relevant pieces:

- PID 1 entry check and private mount propagation.
- Static initramfs BusyBox, separate mounted native root, and child-based
  metadata/content and dynamic-loader preflight.
- Explicit `/dev`, `/proc`, `/sys`, `/run` moves before final exec.
- A no-remaining-userspace-child check before handoff.
- A pre-handoff record, with stdout/stderr directed to the RAM bootstrap log.

These are source facts, not a claim that P405 executed them. The retained
ARM64 VM used substituted board discovery and cannot prove Samsung module/UFS
initialization or the on-device transition.

One observation gap is concrete. `handoff.c:281` replaces itself with BusyBox.
The following `stop("switch-root-exec")` only catches failure to execute
BusyBox. Once that exec succeeds, failures inside switch_root, including the
later init exec, cannot reach the old handler. Thus a pre-handoff record would
still not prove post-switch PID 1. The retained FYG8 `kernel/exit.c` also has
the global-init last-thread exit panic path. These are static failure-path
findings; no evidence establishes that P404 or P405 took them.

The current bootstrap log is under `/run` and follows the moved tmpfs. Its
continued existence in RAM is not host-observable evidence if the only reader
depends on Debian networking. Adding more log lines alone would retain the
same diagnostic dependency.

## Consequence for the next bounded design

1. Choose and qualify a bounded evidence path before the next candidate.
   Early native transport is a possible input because P406 proved its own
   runtime, but adding it must not silently replace the initialization path
   under investigation. USB descriptor state avoids IP/SSH dependencies only
   after gadget enumeration is established.
2. Separate records for module/UFS readiness, protected root/preflight
   completion and readiness for root transition. Include actual mount identity,
   old-root type, PID/namespace, executable/loader identity and errno where
   meaningful. This is an observation design, not permission to relax a guard.
3. In a separately qualified minimal handoff candidate, have a fixed replacement
   program establish entry as the same host PID 1 on the expected new root
   before testing full SysVinit startup. Define its evidence and recovery path
   first; merely keeping a second supervisor alive would change the objective.
4. Only after distinguishing that boundary, attribute subsequent failures to
   init/service startup or USB/networking using their own evidence.

The research supports staged handoff observation. It does not identify a
confirmed switch_root defect, justify replaying consumed images, or establish
Debian host PID 1/SSH on this device.
