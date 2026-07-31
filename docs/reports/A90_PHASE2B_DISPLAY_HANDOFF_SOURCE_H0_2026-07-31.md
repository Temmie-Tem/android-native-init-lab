# A90 Phase 2B Display Handoff Source Implementation

- Date: 2026-07-31 KST
- Tier: H0
- Decision: `A90_PHASE2B_DISPLAY_HANDOFF_SOURCE_H0_PASS`
- Device action: none
- Candidate identity: none
- Host schema: `phase2-display-v1`

## Result

The Phase 2A VT-less display handoff contract now has a current-source host
implementation on both sides of `switch_root`.

Native PID 1 now has an explicit D3-only KMS release path. Debian has a
statically linked direct-DRM presenter, a bounded sysvinit launcher, and a
reproducible 2 GiB rootfs profile. Both the native five-artifact build and the
Debian rootfs build reproduced byte-identical A/B output.

This is source and host-artifact qualification only. The output is not a
candidate, creates no live authority, and does not prove that Debian acquired
the physical panel on a device.

## Native release implementation

`a90_kms.c` now opens the primary DRM node with `O_CLOEXEC` and independently
sets `FD_CLOEXEC`. Its handoff release API records and performs:

1. scaled-plane disable;
2. primary CRTC disable;
3. scaled and primary mapping removal;
4. framebuffer removal;
5. dumb-buffer destruction;
6. DRM master drop;
7. descriptor close; and
8. complete in-process KMS state reset.

An error in any required step is retained while later cleanup still runs.
Release failure prevents D3 handoff.

`a90_server_distro.c` applies this only to D3 strict cleanup. The D4
preserve-D-public wrapper still passes a null release proof and retains its
existing semantics.

After stopping all modeled display services and native child owners, D3:

- releases PID 1 KMS state;
- scans every `/proc/<pid>/fd`, including PID 1;
- requires PID 1 and every other process to hold zero DRM descriptors;
- requires the native KMS state to report uninitialized; and
- creates an absent-only, root-owned release marker in the verified work root
  before any core mount is moved.

The marker contains:

```text
schema=a90-native-display-release-v1
native_pid1_drm_fd_count=0
other_drm_fd_count=0
native_kms_initialized=0
display_services_restart_blocked=1
release_complete=1
```

The synchronous handoff corridor has no post-release action that restarts a
native presenter.

## Debian display implementation

The new `phase2_display_v1` rootfs overlay contains:

- `/usr/local/sbin/a90-debian-display-v1`;
- `/usr/local/sbin/a90-debian-display-launcher-v1`;
- a dedicated numeric `a90display` identity, UID/GID 3904; and
- one sysvinit `once` entry for the launcher.

The presenter:

1. requires the exact native release marker;
2. proves zero DRM descriptors and no `/init` process before opening DRM;
3. reads `card0` major/minor from sysfs and creates or validates only the exact
   matching character device;
4. opens one `O_CLOEXEC | O_NOFOLLOW` primary descriptor and requires exact
   `DRM_IOCTL_SET_MASTER` success;
5. creates and maps one dumb framebuffer;
6. while still root, proves that the presenter is the only DRM-fd owner and
   that PID 1 is `/usr/sbin/init`;
7. drops supplementary groups, GID and UID to 3904, sets
   `no_new_privs=1`, and proves `CapEff=0000000000000000`;
8. only then performs `DRM_IOCTL_MODE_SETCRTC`; and
9. writes the acquisition marker as the non-root display identity.

The marker binds the validated DRM major/minor, connector, CRTC, mode,
ownership counts, Debian PID 1, presenter identity, zero capabilities,
no-new-privileges state, and successful modeset.

Signal cleanup disables the CRTC, unmaps memory, removes the framebuffer,
destroys the dumb buffer, drops master, and closes the descriptor.

The launcher makes at most three attempts and writes one failure marker. It
does not use VT, NCM, Dropbear, sockets, reboot, sync, or sysrq. The inherited
V3405 firstboot remains in the rootfs to provide the separately proven
no-sync bounded return path, but display startup and retry do not depend on
network success.

## Reproducible host profiles

The native profile is a one-level `phase2-display-v1` child of
`v3404-effective`. It overrides the current native closure and build identity,
keeps `candidate_authority=false`, and does not create V3406.

The Debian manifest pins:

- the clean V3405 diagnostic base image and summary;
- presenter, launcher, inittab, stage marker, draw source/header, KMS header;
- the rootfs builder itself; and
- exact cross-tool versions.

The builder accepts only a new path below `workspace/private/outputs`, changes
no source or base input, normalizes ext4 inode and superblock time state, and
runs read-only `e2fsck`.

The first rootfs A/B trial exposed five nondeterministic ext4 superblock bytes:
the write time plus checksum. The builder fixed the cause by setting the
debugfs current time before the final batch. No output byte was ignored or
post-hoc patched.

## Historical baseline behavior

The V3404 flat manifest deliberately pins the old canonical native closure.
Once Phase 2 changed native source, that historical profile correctly became
non-buildable rather than silently accepting drift.

The Phase 1 resolver test was adjusted accordingly:

- raw V3404 and no-op effective-data/hash equality remains tested;
- resolver, path, authority, cycle, depth, type, and lineage tests remain
  unchanged; and
- historical V3404 input validation must now reject the changed native
  closure.

The current Phase 2 child supplies and validates the new closure hash.

## Validation

Focused host tests:

```text
Phase 2 display tests       9/9 PASS
flat-builder regression   14/14 PASS
```

Additional checks passed:

- Python `py_compile` for both touched test modules and the rootfs builder;
- shell syntax check for the launcher;
- AArch64 `-Wall -Wextra -Werror` compilation of the presenter;
- AArch64 `-Wall -Wextra -Werror` object compilation of both touched native C
  translation units;
- static/stripped AArch64 format and no dynamic interpreter for the presenter
  and native executables;
- no canonical source-path string in native init;
- rootfs manifest audit and native flat-manifest audit;
- offline ext4 inittab, owner/mode, label, clean-state, and absent runtime
  release-marker inspection; and
- `git diff --check`.

The final native A/B receipt reports:

```text
boot     3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb
ramdisk  7a34eec3bfd66abfca5d6d4043d514d87eb4eb3c458d281562025045ea45be66
init     67db45ee45144c1cd7bfde9cfd2ac6401292bad57fcf36f6c8543e31b59b83bd
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   5b262978867bf98239e5d7e1b112f29b0217b59f057fc48c5b6e91d90eb5eaad
```

All five are A/B byte-identical. The accepted historical V3404 boot remained
unchanged.

The final Debian A/B receipt reports:

```text
presenter  8c41524749c6a59a8896e02d96a613efdffafcd01d165872f2317b22606a805b
ext4       cf2cf17d5c706123f85b21d4f2479fc348329cdc09e48fe6406874328e3977c8
```

Both are A/B byte-identical. Each ext4 side is exactly 2 GiB and passes
read-only `e2fsck`; the pinned V3405 base and every pinned source remained
unchanged.

## Independent review

Independent review initially found two evidence-order/closure gaps:

1. `CapEff=0` was first checked after `SETCRTC`; and
2. the acquisition marker omitted the sysfs-matched DRM major/minor.

Both were fixed before the final A/B run. Capability zero is now proved inside
the privilege-drop boundary before presentation, and the verified device
number is carried into the ready marker.

The final-code independent review returned `GO` with no remaining Critical,
High, or Medium finding.

## Evidence boundary and next unit

Phase 2B proves deterministic host construction and statically enforces the
handoff contract. It does not prove:

- that native release ioctls all succeed on the A90 kernel;
- that the Debian process acquires DRM master on the device;
- that the panel displays the Debian frame; or
- that the acquisition marker and bounded return are observed in one live run.

The next bounded unit is Phase 2C H0: build a candidate-qualification and
observation packet around these exact host profiles, re-audit the A90 checked
boot-only flash and fresh-work-image staging path, and define fail-closed
display plus return evidence. Phase 2C itself creates no live authority.
