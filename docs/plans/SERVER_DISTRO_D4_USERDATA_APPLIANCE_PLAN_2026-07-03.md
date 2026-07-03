# Server-Distro D4 Userdata Appliance Plan

- Date: `2026-07-03`
- Scope: D4 design and execution plan
- Device action in this document: none
- Parent spec: `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md`
- Current prerequisite: D3B live `switch_root` proof is complete and v2321 rollback is clean

## 1. Objective

D4 converts the server-distro stack from an SD-backed proof into a persistent appliance:

```text
native-init Stage0
  -> verify and mount userdata as plain ext4
  -> use userdata as the Debian rootfs mount
  -> switch_root to Debian init
  -> expose local management over USB/NCM SSH
```

D4 does not publish anything to the public internet. `D-public` remains a separate gate.

## 2. Success Criteria

D4 is complete only when all of these are true:

- `userdata` was re-derived at runtime by `PARTNAME=userdata` and only that partition was formatted.
- The GPT table and all forbidden partitions were untouched.
- `userdata` is plain ext4 and mounted read-write.
- Debian rootfs is installed directly on the `userdata` ext4 mount, not as an SD loop proof.
- The device reaches Debian PID1 through `switch_root`.
- Internal management works over USB/NCM SSH.
- The final report contains target identity, preflight output, format transcript, rootfs install proof,
  PID1 proof, SSH proof, and rollback/recovery state.
- No credentials, rootfs images, private keys, raw logs, or boot images are committed.

## 3. Storage Shape

Use `userdata` as the root filesystem mount itself:

```text
/dev/block/by-name/userdata  (resolved and hard-verified at runtime)
  mkfs.ext4
  mount -> /mnt/a90-userdata-root
    /sbin/init
    /etc
    /usr
    /var
    /root
    /a90-stage0/
```

This keeps the later handoff simple:

```text
switch_root /mnt/a90-userdata-root /sbin/init
```

Avoid a loop image inside `userdata` for D4. D1-D3 used a loop image to stay non-destructive; D4's point
is to make the whole UFS `userdata` ext4 partition the appliance store.

## 4. Bounded Units

### D4A - Read-Only Preflight

No writes, no mounts, no format.

Collect and fail closed on:

- Current resident is v2321 and `selftest fail=0`.
- Rollback images exist and match:
  - v2321: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - v2237: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - v48: present
- TWRP/recovery is available.
- D3B pass report exists.
- SD rootfs source exists so the Debian appliance can be populated after format.
- `userdata` target identity:
  - by-name symlink target
  - `PARTNAME=userdata`
  - size near the D0-observed value, about 110 GiB
  - not currently mounted
  - not equal to any forbidden partition path
- `mkfs.ext4`, `mount`, `tar`/copy tooling, `switch_root`, and required busybox applets are available or
  explicitly staged for the D4-capable candidate.

Required output: private JSON preflight plus public metadata report. The public report must print the
exact target device, PARTNAME, size, and a clear `NO FORMAT PERFORMED` line.

### D4B - D4-Capable Native-Init Surface

Host/source build only until static gates pass.

Add explicit, token-gated PID1 surfaces:

- `userdata-appliance-preflight <token>`
  - read-only device-side target identity check.
- `userdata-appliance-format <token> <expected-partname> <expected-size-range> <expected-rdev>`
  - re-runs target identity checks immediately before `mkfs.ext4`.
  - refuses if any value drifted.
- `userdata-appliance-populate <token> <source-image-or-tree> <sha>`
  - mounts the fresh ext4 filesystem and installs the Debian rootfs.
- `switch-root-to-userdata <token> <root-sha-or-marker>`
  - verifies rootfs marker and executes `switch_root`.

All mutating D4 commands must be impossible to run accidentally:

- require a long token string;
- print target identity before action;
- check `PARTNAME=userdata`;
- deny any target whose path/name contains a forbidden partition;
- deny mounted targets before format;
- deny operation if rollback artifacts are not confirmed by the host runner;
- return bounded, parseable markers.

### D4C - Format and Populate

This is the irreversible Android `/data` disposal step.

Sequence:

1. Run D4A preflight again in the same session.
2. Flash the D4-capable candidate through `native_init_flash.py`.
3. Verify candidate boot and `selftest fail=0`.
4. Run device-side `userdata-appliance-preflight`.
5. Run `userdata-appliance-format` only if host and device preflight agree on the same target.
6. Mount the new ext4 `userdata`.
7. Populate Debian rootfs from the SD-staged clean source.
8. Install per-run/admin SSH material, host keys, and minimal service config.
9. Write an appliance marker under the rootfs, for example `/etc/a90-appliance-stage`.
10. Leave the system in native-init with userdata mounted and proof files collected, or immediately run D4D
    if the switch-root surface is ready.

If any write/readback/check fails after formatting starts, stop and report. Do not retry-loop formatting.

### D4D - Appliance Handoff Proof

Prove the appliance boot path:

1. From the D4-capable candidate, verify the userdata rootfs marker.
2. Execute `switch_root /mnt/a90-userdata-root /sbin/init`.
3. Observe over USB/NCM SSH:
   - Debian version;
   - `/proc/1/comm=init` or the selected appliance init;
   - `/proc/1/exe`;
   - root filesystem device is `userdata`;
   - SSH service is reachable;
   - `userdata=appliance-root`.
4. Keep a bounded recovery path. For first D4D, include a mandatory timed reboot back to the boot
   candidate until the handoff is proven stable.
5. Roll back boot to v2321 if the unit charter requires a clean checkpoint, or explicitly promote the
   D4-capable boot image as the new appliance resident in a separate reported decision.

## 5. Safety Rules

Absolute deny list:

- never write `efs`, `sec_efs`, modem, RPMB, keymaster, `vbmeta`, `dsp`, `keydata`, `keyrefuge`,
  bootloader, `persist`, or GPT;
- never raw-write from the host to any partition;
- never use `fastboot` or host `dd`;
- never run `mkfs` unless the target is re-derived as `PARTNAME=userdata` in the same live session;
- never proceed if v2321/v2237/v48/TWRP are not available;
- never treat D4 approval as D-public approval.

Stop conditions:

- target identity drift between host and device checks;
- `userdata` is mounted before format;
- by-name symlink does not resolve to the same block device as the `PARTNAME=userdata` scan;
- size is outside the expected range;
- any forbidden partition appears in the target chain;
- D4A or D4B fails twice on the same approach;
- candidate boot health check fails before format;
- post-format mount/readback fails.

## 6. Reports and Commits

Use one report per bounded unit:

- `SERVER_DISTRO_D4A_USERDATA_PREFLIGHT_YYYY-MM-DD.md`
- `SERVER_DISTRO_D4B_USERDATA_APPLIANCE_SURFACE_YYYY-MM-DD.md`
- `SERVER_DISTRO_D4C_USERDATA_FORMAT_POPULATE_YYYY-MM-DD.md`
- `SERVER_DISTRO_D4D_USERDATA_APPLIANCE_HANDOFF_YYYY-MM-DD.md`

Commit public code, tests, GOAL updates, and metadata reports only. Keep these private:

- rootfs images and extracted trees;
- SSH keys and host keys;
- raw transcripts;
- full private JSON evidence;
- boot images and compiled binaries.

## 7. Immediate Next Step

Implement and run D4A first. It is read-only and should answer one question:

```text
Is the exact `userdata` target, recovery envelope, and rootfs source ready for the destructive D4C step?
```

D4C must not run until D4A has a clean public report and D4B has a statically validated D4-capable
native-init surface.
