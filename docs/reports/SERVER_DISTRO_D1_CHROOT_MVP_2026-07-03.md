# Server Distro Endgame - D1 Chroot MVP

- Date: 2026-07-03 KST / 2026-07-02 UTC
- Unit: D1 chroot MVP.
- Design: `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md`
- Decision: `server-distro-d1-chroot-mvp-pass`
- Device action: non-destructive SD-only runtime work. No flash, no format, no `userdata`
  mount/write.
- End state: resident stayed `v2321-usb-clean-identity-rodata`; final standalone
  `selftest pass=11 warn=1 fail=0`; no `distro-root` mount or `/dev/loop*` node remained.

## Scope

D1 proved that the host-staged Debian ext4 image can run as a real userspace on the stock
Samsung 4.14 kernel through a loop-mounted SD image and `chroot`.

Raw command output is private only:

`workspace/private/runs/server-distro/d1-chroot-mvp-20260702T204408Z/`

The committed report contains only the redacted proof and health classification needed to
charter D2.

## Implementation

Added a reusable host-side D1 runner:

`workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py`

The runner:

1. Refuses to proceed unless the resident device reports v2321 and baseline selftest `fail=0`.
2. Checks the local Debian image SHA-256:
   `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`.
3. Stages the image to
   `/mnt/sdext/a90/runtime/debian-bookworm-arm64-20260701-024412.img` when the remote SHA is
   missing or mismatched.
4. Creates `/dev/loop0` from the runtime loop major (`7`), mounts the ext4 image at
   `/mnt/sdext/a90/runtime/distro-root`, and enters the chroot.
5. Runs known Debian binaries inside the chroot and records `A90D1_CHROOT_BEGIN` /
   `A90D1_CHROOT_DONE`.
6. Cleans up the mount, detaches the loop device, removes the runtime loop node, and verifies no
   mount or loop node remains.
7. Re-checks final v2321 and selftest `fail=0`.

The runner also fixed a host-side reporting bug found live: relative `--run-dir` values are now
normalized under the repository root before the redacted summary is written.

## Live Result

Private summary:

- `decision`: `server-distro-d1-chroot-mvp-pass`
- `remote_image`:
  `/mnt/sdext/a90/runtime/debian-bookworm-arm64-20260701-024412.img`
- `remote_sha256`:
  `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`
- `image_staged_this_run`: `true`
- `debian_version`: `12.14`
- `loop_major`: `7`
- `loop_node_created`: `true`
- `chroot_debian_binary_executed`: `true`
- `stage_marker_present`: `true`
- `cleanup_mount_absent`: `true`
- `cleanup_loop_node_absent`: `true`
- `final_v2321`: `true`
- `final_selftest_fail0`: `true`
- `userdata_touched`: `false`
- `flash_performed`: `false`

Relevant proof markers:

```text
A90D1_BEGIN
A90D1 loop_major=7
A90D1 loop_node_created=1
A90D1 mounted=1
A90D1_CHROOT_BEGIN
debian_version=12.14
stage_marker=present
A90D1_CHROOT_DONE
A90D1 cleanup_mount_absent=1
A90D1 cleanup_loop_node_absent=1
A90D1_DONE
```

The first `umount` observed `Device or resource busy`; the runner's bounded cleanup fallback used
lazy unmount and then verified the mount was absent. A separate post-run check also found no
`distro-root` mount and no `/dev/loop*` node.

## Safety Result

- No boot image was built or flashed.
- No rollback flash was needed because resident v2321 was maintained throughout.
- No forbidden partition was touched.
- `userdata=/dev/block/sda33` stayed untouched; D4 remains the only possible future
  `userdata` reformat gate.
- Persistent change from D1 is limited to the inert Debian image stored on SD.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py tests/test_server_distro_d1_chroot_mvp.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_d1_chroot_mvp`
  - `Ran 3 tests ... OK`

Device validation:

- Baseline `version/status/selftest` passed before D1.
- The staged image SHA matched the expected host image SHA.
- Debian 12.14 chroot executed known binaries on the live device.
- Cleanup verified mount and loop node absence.
- Final runner health and standalone post-run `selftest` both reported `fail=0`.

## D2 Readiness

D2 is unblocked as the next non-destructive rung: run `dropbear` inside the same SD-backed
chroot and prove SSH login over the native-init USB/NCM network path. D2 remains SD-only and
must not touch `userdata`.
