# Native Init V3383 Server-Distro Handoff Cleanup Live Gate

- Cycle: `V3383`
- Decision: `v3383-server-distro-handoff-cleanup-live`
- Init: `A90 Linux init 0.11.139 (v3383-server-distro-handoff-cleanup)`
- Boot image SHA256: `c2cb74e014c7a3e2121ef50d818e6225d7ab8d042eba75166c77e133f3fd012c`
- Result: `PASS`

## Scope

Live-prove the native-side display-owner cleanup before D4 userdata
`switch_root`: stop the tracked native HUD, terminate native processes holding the
DRM device, then hand off to the Debian userdata appliance so Debian can own the
panel directly.

This unit did not start or publish a public tunnel. No public URL, tunnel token,
device serial, or device IP is recorded here.

## Preconditions

- Rollback images were present and SHA-checked before the flash gate:
  - `v2321` clean USB identity rollback.
  - `v2237` deeper Wi-Fi-proven fallback.
  - `v48` final fallback.
- TWRP/recovery path was available.
- Candidate source-build gate was already committed in
  `docs/reports/NATIVE_INIT_V3383_SERVER_DISTRO_HANDOFF_CLEANUP_SOURCE_BUILD_2026-07-04.md`.

## Checked Flash

`native_init_flash.py --from-native` flashed the exact V3383 boot image through the
checked helper path. The helper verified:

- local marker: `0.11.139`
- pushed image SHA256 matched the candidate SHA256
- boot partition readback prefix SHA256 matched the candidate SHA256
- post-boot native cmdv1 verification succeeded

Native health after flash:

```text
A90 Linux init 0.11.139 (v3383-server-distro-handoff-cleanup)
selftest: pass=12 warn=1 fail=0
autohud: running
netservice/tcpctl: running
```

## Handoff Proof

Command:

```text
switch-root-to-userdata SERVER-DISTRO-D4-USERDATA-APPLIANCE userdata=appliance-root
```

Expectedly, `a90ctl.py` reported `A90P1 END marker not found` because the command is
a `CMD_NO_DONE` exec-style handoff. The transcript reached the handoff point:

```text
A90D4 marker=ok value=userdata=appliance-root
A90D4 appliance_init=ok path=/mnt/a90-userdata-root/sbin/init mode=755
A90D4 handoff_display service=autohud stop_rc=0
A90D4 handoff_display drm_owner_pid=544 action=term
A90D4 handoff_display drm_owner_pid=546 action=term
A90D4 handoff_display drm_owner_pid=548 action=term
A90D4 handoff_display=done killed=3 rc=0
A90D4 mount_move=/proc->/mnt/a90-userdata-root/proc ok=1
A90D4 mount_move=/sys->/mnt/a90-userdata-root/sys ok=1
A90D4 devpts=mounted path=/mnt/a90-userdata-root/dev/pts
A90D4 dev_mountpoint=0 dev_nodes=prepared root=/mnt/a90-userdata-root/dev
A90D4 exec_switch_root_now busybox=/bin/busybox root=/mnt/a90-userdata-root init=/sbin/init marker=userdata=appliance-root
```

This proves the new native cleanup path ran before `switch_root`, stopped the
tracked HUD cleanly, and removed three DRM owners before Debian took over.

## Debian Proof

SSH over the local USB network became reachable immediately after handoff. Debian
state:

```text
proc1_comm=init
proc1_exe=/usr/sbin/init
debian_version=12.14
root_mount=/dev/block/a90-userdata ext4 /
marker=A90DPUBLIC_MARKER
```

Runtime service proof:

```text
dropbear: running under Debian PID1
a90-dpublic-hud: running under Debian PID1
cloudflared: not running in the current process table
```

Smoke and HUD proof:

```text
HTTP/1.1 200 OK
A90_DPUBLIC_SMOKE_OK
service=loopback-http
public_exposure=outbound-tunnel-only

a90-dpublic-hud display=1080x2400 connector=28 crtc=133 refresh=2s
```

No native `/init` process remained in the Debian process table after handoff.
Stale cloudflared log/pid files from earlier public runs are still present under
the runtime state directory, but no active `cloudflared` process was observed and
those stale files are not used as live evidence.

## Safety

- Boot image was flashed only through `native_init_flash.py`.
- No forbidden partitions were touched.
- No raw host `dd`, fastboot, PMIC/regulator/GDSC/GPIO/backlight, or panel
  re-init was used.
- Public tunnel exposure was not started in this unit.
- The device was left in the live Debian userdata appliance for operator
  inspection.

## Conclusion

V3383 closes the native-display handoff gap: the native init now releases the panel
before `switch_root`, Debian comes up as PID1 on the userdata appliance, loopback
smoke works, and the Debian HUD owns the display without needing to recover from a
leftover native DRM holder.
