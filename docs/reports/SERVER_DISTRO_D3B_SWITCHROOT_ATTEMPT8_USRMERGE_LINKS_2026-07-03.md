# Server-Distro D3B Switchroot Attempt 8 - Usrmerge Links Broken

- Date: `2026-07-03`
- Unit: `D3B live checked switch_root handoff`
- Candidate: `A90 Linux init 0.11.133 (v3372-server-distro-switchroot-stdio)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3372_server_distro_switchroot_stdio.img`
- Candidate SHA256: `09db071ae6bebe538d0f9c6c62f6e86b28a4b1a2a6954f1910f8d189675cc653`
- D3 keyed image: pre-staged on SD before candidate flash
- Final device state: rolled back to `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Result

V3372 passed the loop, `/dev`, and console blockers. The handoff reached BusyBox `switch_root` with
the inherited-stdio marker:

```text
A90D3B exec_switch_root_now busybox=/bin/busybox root=/mnt/sdext/a90/runtime/distro-root init=/sbin/init console=reuse-stdio
switch_root: can't execute '/sbin/init': No such file or directory
```

The runner did not observe the D3 SSH marker. The V3372 candidate returned, then the runner rollback-
flashed v2321. Post-rollback health check reported v2321 and `selftest fail=0`; `timeline.json` included
the standardized eight phase events.

## Root Cause

Host inspection showed `/sbin/init` exists and is executable, but its ELF interpreter is
`/lib/ld-linux-aarch64.so.1`. In the D3A image, `/lib/ld-linux-aarch64.so.1` and
`/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1` were missing from the `/lib` path, while the base Debian
rootfs contains the loader under `/usr/lib`.

The base rootfs is usrmerge-style (`/bin -> usr/bin`, `/sbin -> usr/sbin`, `/lib -> usr/lib`). After
`dpkg-deb -x` of the sysv packages, the D3A rootfs had real directories at `/bin`, `/sbin`, and `/lib`
instead of symlinks. Package files such as `/sbin/init` and `/lib/init/*` landed in those real
directories, breaking the dynamic loader path.

## Follow-up

The D3A rootfs builder now restores usrmerge links after package extraction: it merges any extracted
`/bin`, `/sbin`, and `/lib` contents into `/usr/bin`, `/usr/sbin`, and `/usr/lib`, then recreates the
top-level symlinks. The next live attempt should reuse V3372 native-init and only refresh the D3 keyed
image staged on SD.
