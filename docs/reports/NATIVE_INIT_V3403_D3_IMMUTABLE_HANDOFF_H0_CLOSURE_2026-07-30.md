# Native Init V3403 D3 Immutable Handoff H0 Closure

Date: 2026-07-30 KST

Status:
`V3403_HOST_CLOSURE_PASS_NO_LIVE_AUTHORITY`

## Scope

This report closes the host-only successor work selected after the V3402
Debian handoff stopped at display-owner cleanup and consumed the prior rootfs
identity. No device command, SD staging, flash, mount on the target,
`switch_root`, network exposure, or userdata action was performed.

## Exact private artifacts

- V3403 boot:
  `workspace/private/inputs/boot_images/boot_linux_v3403_d3_immutable_handoff.img`;
- boot size: `66379776`;
- boot SHA256:
  `2b2b458b4f021825e0567c239ef86996d482a7b55baccc4e4a8cd9e670a2e2b9`;
- fresh D3 rootfs:
  `workspace/private/builds/server-distro/a90-v3403-d3-immutable-source-20260730.img`;
- rootfs size: `2147483648`;
- rootfs SHA256:
  `16c504a8b1860fcc56272140b48d27a015bab1748b6c6be10fdb958bcdd7d749`;
- exact V2321 rollback:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`;
- rollback size: `60882944`;
- rollback SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.

Each artifact was reopened from its stable regular-file path and rehashed
after the build and validation work. The previous changed V3402 rootfs is not
an input to this closure.

## Handoff correction

V3403 moves strict display-owner cleanup before loop attachment and any
read-write mount. It stops both native presenters, terminates every other
native-init DRM owner, rescans, and requires zero remaining owners.

The manifest-bound source image is never attached to a loop or mounted
read-write. V3403 rehashes it after display cleanup, creates one absent-only
work copy, verifies both hashes, and attaches only the copy. Every
pre-`switch_root` failure restores moved mounts, unmounts the work root,
detaches the loop, removes only the work copy owned by that invocation, and
rehashes the original source. A preexisting work path is a hard failure.

The host fault model injected every declared pre-switch failure. It also
proved that multiple display owners can be drained and that a retained busy
owner fails before copy, loop attachment, or mount.

## Fresh Debian input

The new Debian Bookworm arm64 base completed debootstrap configuration under
an unprivileged host path. The first single-ID user-namespace extraction
stopped on an unmapped package group and remains quarantined; it was not
adopted. The adopted tree completed its second stage through private PRoot
with PRoot seccomp acceleration disabled after a direct arm64 execution smoke
test.

The package trust chain was independently closed:

1. an archive-keyring package fetched over authenticated HTTPS matched the
   preserved debootstrap archive byte-for-byte;
2. that keyring verified the Bookworm `InRelease` signatures;
3. the signed `Packages` digest and size matched the local index;
4. all `135` base archives matched the signed index by package, version,
   architecture, size, and SHA256;
5. the installed dpkg set matched those `135` archives exactly; and
6. all `5` added sysvinit archives matched the same signed index.

The base dpkg audit was empty. The final ext4 image passed read-only
`e2fsck`, reported a clean `A90D3ROOT` filesystem, and contained root-owned
mode-correct `/sbin/init`, `/etc/inittab`, the bounded firstboot helper,
Dropbear, and the network utility. SysV init executed under QEMU and reported
version `3.06`.

The root password is locked. No `authorized_keys`, SSH host key, Dropbear host
key, credential, or private network configuration is present. The firstboot
contract retains its mandatory bounded auto-reboot.

## Static closure

- Python compilation passed for the new model, builder, and touched tests.
- The focused V3372/V3383/V3400/V3401/V3402/V3403, D3 rootfs, and handoff
  cleanup suite passed `41/41`.
- The production C source cross-compiled to an AArch64 relocatable ELF.
- One inherited D4 ignored-`chown` return warning remains outside the changed
  D3 path; the V3403 compile introduced no new diagnostic.
- The source-built boot manifest and rootfs summary reopened with their exact
  artifact hashes.

## Disposition

V3403 and the fresh rootfs are host-qualified inputs only. This closure does
not create a prepared F1 manifest, select a live target, stage the rootfs to
SD, grant approval, or authorize a transfer.

Any later device unit must use a new run ID and bind the exact A90 target,
V3403 boot hash, fresh rootfs hash, exact V2321 rollback hash, checked runner
version, bounded observation, and final-health requirements. It then needs
the required connected preflight and one fresh exact approval. V3402 and its
consumed manifest remain non-replayable.
