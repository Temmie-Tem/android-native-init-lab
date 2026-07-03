# Server-Distro D3B Switchroot Attempt 7 - Console ENODEV

- Date: `2026-07-03`
- Unit: `D3B live checked switch_root handoff`
- Candidate: `A90 Linux init 0.11.132 (v3371-server-distro-switchroot-devprep)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3371_server_distro_switchroot_devprep.img`
- Candidate SHA256: `29cc5eda5df385f70b6bb5e10adf8a3f7969152dc7a80b881c1f5f52c57727ff`
- D3 keyed image: pre-staged on SD before candidate flash
- Final device state: rolled back to `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Result

V3371 passed the `/dev` non-mountpoint blocker. The live transcript reached the final handoff marker:

```text
A90D3B devpts=mounted path=/mnt/sdext/a90/runtime/distro-root/dev/pts
A90D3B dev_mountpoint=0 dev_nodes=prepared root=/mnt/sdext/a90/runtime/distro-root/dev
A90D3B exec_switch_root_now busybox=/bin/busybox root=/mnt/sdext/a90/runtime/distro-root init=/sbin/init
switch_root: can't open '/dev/console': No such device
```

The runner did not observe `A90D3_MARKER`; the final SSH attempt ended with port 2222 connection
refused. The D3A mandatory auto-reboot returned to the V3371 candidate, then the runner rollback-flashed
v2321. The post-rollback health check reported v2321 and `selftest fail=0`. The `timeline.json` used
the standardized `events:[{name,timestamp_utc}]` schema and included all eight required phases.

## Root Cause

The V3371 switch argv used BusyBox `switch_root -c /dev/console ...`. The A90 native boot command line
uses `console=null`, so the character node `5:1` exists but is not a usable console endpoint in this
environment. BusyBox stops before `exec /sbin/init` when the `-c` console reopen fails with `ENODEV`.

## Follow-up

V3372 removes the `-c /dev/console` option and relies on inherited PID1 stdio for the bounded handoff.
The D3 proof path is NCM SSH, not serial console, so serial console reopening is not required for the
success criterion.
