# Server-Distro D3B Switchroot Attempt 6 - Dev Is Not A Mountpoint

- Date: `2026-07-03`
- Unit: `D3B live checked switch_root handoff`
- Candidate: `A90 Linux init 0.11.131 (v3370-server-distro-switchroot-loopfix)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3370_server_distro_switchroot_loopfix.img`
- Candidate SHA256: `df30ac45b5dbb7c8ba05f663c394e5ad31d49aab046a5128e3e663e89d33a6f2`
- D3 keyed image: pre-staged on SD before candidate flash
- Final device state: rolled back to `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Result

V3370 passed the prior loop-major blocker. The live command verified the pre-staged SD image SHA,
created `/dev/loop0`, attached the image, mounted the D3 rootfs, verified `/sbin/init`, and moved
`/proc` and `/sys` into the new root. It stopped before `switch_root` on the `/dev` move:

```text
A90D3B loop_node_created=1 major=7 node=/dev/loop0
A90D3B loop=attached node=/dev/loop0 image=/mnt/sdext/a90/runtime/debian-bookworm-arm64-d3-sysvinit-keyed.img
A90D3B rootfs=mounted root=/mnt/sdext/a90/runtime/distro-root loop=/dev/loop0
A90D3B distro_init=ok path=/mnt/sdext/a90/runtime/distro-root/sbin/init mode=755
A90D3B mount_move=/proc->/mnt/sdext/a90/runtime/distro-root/proc ok=1
A90D3B mount_move=/sys->/mnt/sdext/a90/runtime/distro-root/sys ok=1
A90D3B mount_move=fail rc=-22
```

No `exec_switch_root_now` marker was emitted, so no Debian PID1 handoff occurred. The runner performed
the rollback flash after the error; live health check after the run showed v2321 and `selftest fail=0`.

## Root Cause

Host-side probe after rollback confirmed `/dev` is not a mountpoint on the native root:

```text
/dev is not a mountpoint
mountpoint_rc=1
```

`/proc/filesystems` exposes `proc`, `sysfs`, and `devpts`, but not `devtmpfs`. Therefore `/dev` is a
plain rootfs directory containing device nodes, and `mount("/dev", newroot/dev, NULL, MS_MOVE, NULL)`
correctly fails with `EINVAL`.

## Follow-up

V3371 changes the handoff to move `/proc` and `/sys`, but for `/dev` it first checks whether `/dev` is
a mountpoint. If it is not, V3371 creates the required device nodes inside the D3 rootfs (`console`,
`tty`, `ptmx`, `null`, `zero`, `random`, `urandom`, and optional `ttyGS0`) and mounts `devpts` when
available. V3371 also unmounts the D3 rootfs before loop detach on pre-handoff failures.
