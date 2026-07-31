# A90 Phase 2A DRM/KMS and VT-less Session Handoff Contract

- Date: 2026-07-31 KST
- Tier: H0
- Decision: `A90_PHASE2A_DRM_VTLESS_HANDOFF_CONTRACT_PASS`
- Device action: none
- Candidate identity: none

## Result

The carried A90 kernel, current native-init display path, current V3405
diagnostic Debian root, and retained Debian HUD implementation were inventoried.
The resulting steady-state display model is:

```text
native PID 1 owns direct DRM/KMS during bridge-up
-> stop every native presenter
-> explicitly tear down native PID 1 KMS state
-> require zero native DRM file descriptors
-> switch_root
-> Debian sysvinit launches one VT-less direct-DRM presenter
-> that presenter exclusively owns the primary DRM master and panel
```

This kernel has no Linux VT subsystem, DRM fbdev emulation, or DRM lease
support. A VT switch, framebuffer-console handoff, logind seat, or DRM lease
cannot be part of the contract. The supported model is one supervised Debian
process with no controlling VT and one primary DRM master.

Phase 2A changes no display source, rootfs, boot image, manifest, or live state.
It closes the inventory and design question only.

## Evidence Boundary

V3405 already proves:

- native display-owner cleanup completed before `switch_root`;
- Debian sysvinit became PID 1;
- Debian Dropbear was observed; and
- the no-sync return supervisor returned the device to healthy native-init.

The V3405 diagnostic Debian image deliberately started no DRM/KMS presenter.
Its black screen is expected and is not a panel or handoff failure.

Older D-public evidence separately proves that Debian userspace can drive this
panel:

```text
a90-dpublic-hud display=1080x2400 connector=28 crtc=133 refresh=2s
```

That earlier run reached Debian PID 1 and a successful
`DRM_IOCTL_MODE_SETCRTC`. It is capability evidence, not authority for a new
candidate and not proof that the current V3405 diagnostic image contains the
same service.

Relevant reports:

- `docs/reports/A90_V3405_DEBIAN_PID1_F1_CLOSED_2026-07-31.md`
- `docs/reports/NATIVE_INIT_V3383_SERVER_DISTRO_HANDOFF_CLEANUP_LIVE_2026-07-04.md`
- `docs/reports/SERVER_DISTRO_DPUBLIC_BOOT_VISUAL_HUD_2026-07-04.md`
- `docs/reports/NATIVE_INIT_V2864_VIDEO_VID2A_DRM_INVENTORY_LIVE_2026-06-19.md`

## Carried Kernel Inventory

The kernel extracted from the accepted V3404 boot, the V3403 base, and the
Phase 1 flat-builder output is byte-identical:

```text
d97eb6c7291477000299fae1c4272105e95fe77df09631ae13099303510b5263
```

The exact embedded configuration contains:

```text
# CONFIG_DEVTMPFS is not set
CONFIG_TTY=y
# CONFIG_VT is not set
CONFIG_UNIX98_PTYS=y
# CONFIG_LEGACY_PTYS is not set
CONFIG_DRM=y
CONFIG_DRM_KMS_HELPER=y
# CONFIG_DRM_FBDEV_EMULATION is not set
CONFIG_DRM_MSM=y
CONFIG_DRM_MSM_DSI_STAGING=y
CONFIG_DRM_SDE_WB=y
CONFIG_DRM_SDE_RSC=y
# CONFIG_DRM_MSM_LEASE is not set
CONFIG_DRM_PANEL=y
CONFIG_FB=y
# CONFIG_FB_MSM is not set
# CONFIG_FB_SIMPLE is not set
```

The boot command line includes `console=null` and a virtual-framebuffer video
argument, but the actual panel path proven by the native and Debian helpers is
MSM DRM/KMS `card0`. No `/dev/fb0` or VT contract follows from the command-line
virtual framebuffer.

Consequences:

1. `/dev/tty0`, `openvt`, `chvt`, `VT_ACTIVATE`, `VT_WAITACTIVE`, and
   `KDSETMODE` are not available handoff mechanisms.
2. There is no fbcon or DRM fbdev-emulation owner to release.
3. There is no kernel DRM lease facility. Native-init and Debian must not
   overlap; ownership is sequential and exclusive.
4. There is no automatic devtmpfs population. Debian inherits the moved
   `/dev`, or a bounded launcher materializes `card0` from
   `/sys/class/drm/card0/dev`.
5. Pseudoterminals remain available for remote administration, but they do not
   own the display.

## Current Native Ownership

The native boot path calls `boot_auto_frame()` in PID 1. That function calls
`a90_kms_begin_frame()`, draws the boot splash, and presents it. PID 1 then
calls `start_auto_hud()`, which forks without first releasing KMS state. The
child therefore inherits PID 1's DRM descriptor and mappings and continues
rendering through the inherited process image.

The relevant sources are:

- `workspace/public/src/native-init/v319/40_menu_apps.inc.c`
- `workspace/public/src/native-init/v724/90_main.inc.c`
- `workspace/public/src/native-init/a90_hud.c`
- `workspace/public/src/native-init/a90_kms.c`
- `workspace/public/src/native-init/a90_kms.h`

`a90_kms.c` currently:

- opens `card0` with `O_RDWR`, not `O_RDWR | O_CLOEXEC`;
- applies `F_DUPFD_CLOEXEC` only in the exceptional case where the returned
  descriptor is `0`, `1`, or `2`;
- tolerates `DRM_IOCTL_SET_MASTER` returning `EBUSY` or `EINVAL`;
- stores the open descriptor, two dumb buffers, framebuffers, and mappings in
  process-global KMS state; and
- exposes no primary-KMS teardown or release API.

The D3 strict cleanup in `a90_server_distro.c` correctly stops autohud and the
modeled D-public presenter and then terminates remaining child `/init`
processes with DRM descriptors. It does not inspect PID 1:

```text
pid <= 1 -> excluded from native-init owner classification
```

Therefore:

```text
required_nonpreserved_owner_count=0
```

means that no classified child owner remains. It does not prove that native
PID 1 has closed its DRM descriptor, destroyed its dumb buffers, dropped
master, or armed close-on-exec.

V3405's successful Debian PID 1 transition and the older Debian HUD success
show that a later exec/init path can end the inherited ownership in practice.
Phase 2 must not depend on an undocumented BusyBox or sysvinit descriptor-close
side effect. Native-init must establish the release postcondition before
`execve`.

The D4 cleanup mode preserves a native D-public presenter. That mode is
incompatible with the final Debian-owned display architecture. Future display
handoff work must use D3 strict semantics and must not reintroduce a preserved
native presenter.

## Current Debian Root Inventory

The exact clean V3405 diagnostic ext4 image has label `A90D3V3405`, mount count
zero, and this inittab:

```text
id:2:initdefault:
si::sysinit:/etc/a90-d3-firstboot
ca:12345:ctrlaltdel:/sbin/reboot -f
```

Its firstboot starts the return supervisor, USB-NCM configuration, marker, and
Dropbear. It has no display launch step. The image does not contain:

- `/usr/local/bin/a90-dpublic-hud`;
- `/usr/local/bin/a90-dpublic-hud-presenter`;
- `libdrm.so.2`;
- `openvt` or `chvt`; or
- `/dev/dri/card0` in the stored root.

The missing stored device node is not itself a defect because `/dev` is moved
from native-init during D3 handoff. The absence of a presenter and service is
the direct explanation for the V3405 black screen.

The tracked `workspace/public/src/scripts/server-distro/a90_dpublic_hud.c`
remains a useful direct-DRM implementation:

- it can materialize `card0` from sysfs;
- opens the node with `O_CLOEXEC`;
- creates a dumb framebuffer;
- performs `MODE_ADDFB2`, mapping, and `MODE_SETCRTC`; and
- tears down the framebuffer, dumb buffer, mapping, and descriptor on its
  normal exit path.

It cannot be copied unchanged into the new contract:

- `DRM_IOCTL_SET_MASTER` failure is ignored;
- its status content is coupled to an older public-service profile;
- it is not present in or bound by the current diagnostic rootfs;
- it is not launched by the current sysvinit profile; and
- legacy rootfs builders reference private prebuilt defaults rather than a
  fresh current-source build closure.

The older WSTA127 service model already specifies the desirable daemon posture:
a dedicated non-root identity, no network listener, no-new-privs, zero
effective capabilities, and explicit DRM-master proof. Those properties may
be reused as design input, but their old artifacts and live authority may not.

## Binding Handoff Contract

### 1. Native acquisition

During early bridge-up, native PID 1 may own primary DRM and start the native
HUD. Every native open of the primary DRM node must use `O_CLOEXEC` or
immediately set `FD_CLOEXEC`. A successful renderer must distinguish confirmed
master acquisition from an `EBUSY` or `EINVAL` observation.

### 2. Native quiesce

Before any rootfs copy, loop mount, core-mount move, or `switch_root` exec:

1. stop autohud and every modeled native presenter;
2. prevent any display service from restarting;
3. stop or reject every non-PID1 native process holding a DRM descriptor; and
4. invoke an explicit PID1 KMS teardown.

The PID1 teardown must, in dependency order:

1. disable any active overlay/scaled plane owned by native-init;
2. unmap every KMS mapping;
3. remove every framebuffer ID;
4. destroy every dumb-buffer handle;
5. attempt `DRM_IOCTL_DROP_MASTER` when the descriptor is the tracked master;
6. close the DRM descriptor; and
7. reset all in-process KMS state to an uninitialized value.

Closing the descriptor is the authoritative release operation. A
`DROP_MASTER` diagnostic may report that master was already absent, but no
open PID1 DRM descriptor may remain.

### 3. Native release proof

The final pre-exec scan must cover:

- PID 1's `/proc/1/fd`;
- every other live process, not only processes whose executable is `/init`;
- every descriptor targeting `/dev/dri/*`, `card0`, or the DRM device; and
- the tracked KMS state.

The handoff fails closed unless all of these are true:

```text
native_pid1_drm_fd_count=0
other_drm_fd_count=0
native_kms_initialized=0
display_services_restart_blocked=1
```

The scan must not open the DRM node to test ownership, because doing so would
create a new owner after the release boundary.

### 4. Mount and node transfer

D3 moves `/proc`, `/sys`, and `/dev` into the Debian root. The Debian display
launcher accepts an existing primary node only when its major/minor matches
`/sys/class/drm/card0/dev`. When absent, a bounded privileged setup step may
materialize exactly that character device and assign the dedicated display
group and mode. No raw panel, DSI, backlight, regulator, GPIO, or power-domain
write is permitted.

### 5. Debian session

The Debian display is a sysvinit-supervised, VT-less service:

- no controlling terminal;
- no `openvt`, `chvt`, logind, seat daemon, X server, or Wayland compositor
  dependency for the first direct-KMS proof;
- one fixed non-root user and display group;
- `no_new_privs=1`, zero effective capabilities after setup, and no network
  socket;
- one `O_RDWR | O_CLOEXEC` primary-node descriptor;
- exact `DRM_IOCTL_SET_MASTER` success required;
- connected connector, encoder, CRTC, and mode inventory required;
- dumb-buffer creation, `ADDFB2`, mapping, and `SETCRTC` success required; and
- bounded signal handling and complete cleanup on stop.

The launcher, not the network/Dropbear firstboot sequence, owns restart policy.
For the first proof it must use bounded attempts and a durable failure marker,
not an unlimited rapid respawn loop.

### 6. Debian acquisition proof

The runtime marker must record at least:

```text
schema=a90-debian-display-v1
pid1_exe=/usr/sbin/init
presenter_pid=<pid>
presenter_uid=<dedicated uid>
presenter_cap_eff=0000000000000000
drm_node=/dev/dri/card0
drm_node_major_minor=<sysfs-matched value>
drm_master=1
connector_id=<id>
crtc_id=<id>
mode=<width>x<height>@<refresh>
setcrtc_rc=0
native_pid1_drm_fd_count=0
other_native_drm_fd_count=0
```

The proof also requires a process/fd inventory showing exactly one intended
Debian presenter owner and no `/init` process. A marker alone is insufficient.

### 7. Stop and failure behavior

- Native release failure stops before `switch_root`.
- Debian master, mode selection, dumb-buffer, mapping, or `SETCRTC` failure
  leaves Debian alive and remotely diagnosable; it must not reboot-loop.
- Display failure must not disable the bounded return/recovery path.
- No fallback may restart a native presenter after Debian becomes PID 1.
- No display path may depend on public networking or a tunnel.

## Phase 2B Entry Conditions

Phase 2B may implement this contract host-side only. Its minimum source closure
is:

1. an explicit native PID1 KMS teardown and `CLOEXEC` discipline;
2. an all-process final DRM-fd audit that includes PID 1;
3. a current-source Debian presenter that fails on missing DRM master and
   cleans up every partial initialization path;
4. a minimal sysvinit launcher/profile independent of NCM and Dropbear;
5. a private, reproducible rootfs build receipt with no legacy private-prebuilt
   fallback;
6. focused fault tests and AArch64 cross-compilation; and
7. independent safety review of the changed display-handoff hazard closure.

Use a host schema such as `phase2-display-v1` until source, package, and static
closure pass. Do not assign V3406 candidate identity merely to start
implementation.

Phase 2B creates no live authority. A later boot-only device proof would need a
new immutable identity, exact rollback, Process v2 preflight, and fresh A90 F1
approval.

## Validation

Phase 2A used read-only host inspection:

- unpack and SHA256 comparison of the accepted and flat-builder kernels;
- `extract-ikconfig` on the carried kernel;
- source inspection of the native boot, KMS, service, and D3/D4 handoff paths;
- read-only `dumpe2fs` and `debugfs` inspection of the clean V3405 diagnostic
  image; and
- comparison with retained Debian HUD source and prior live reports.

No source compiler was required because this unit changes documentation only.
No device command, network-to-device action, staging, reboot, or flash
occurred. The separately connected S22+ was not addressed.
