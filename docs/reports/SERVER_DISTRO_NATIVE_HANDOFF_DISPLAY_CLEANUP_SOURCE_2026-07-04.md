# Server-Distro Native Handoff Display Cleanup Source Gate

- Date: 2026-07-04 KST
- Unit: native-init server-distro display-owner cleanup before `switch_root`.
- Scope: source/static validation only.
- Device action: none.  No flash, no rollback, no reboot, no public-tunnel interruption.

## Verdict

Native-side handoff cleanup is implemented and statically validated.

The D-public live HUD pass proved the final architecture should be a real PID1 handoff, not a
long-lived `chroot`: native-init prepares the appliance and then `switch_root` execs Debian
`/sbin/init`.  The remaining rough edge was display ownership.  In the live D-public session, Debian
firstboot had to recover DRM ownership because a non-PID1 native `/init` child still held
`/dev/dri/card0` after the handoff.

This unit moves that cleanup to native-init.  Debian firstboot can remain a fallback, but native-init now
does the primary cleanup before handing PID1 to Debian.

## Change

`workspace/public/src/native-init/a90_server_distro.c` now includes `a90_service.h` and adds a shared
handoff cleanup path:

- Stop the tracked auto-HUD service with `a90_service_stop(A90_SERVICE_HUD, 3000)`.
- Scan `/proc` for non-self processes whose executable is `/init`.
- For each matching native `/init`, inspect `/proc/<pid>/fd/*`.
- If any fd target looks like DRM/KMS ownership (`/dri/`, `card0`, or `drm`), terminate the process.
- Escalate from `SIGTERM` to `SIGKILL` if it does not exit within the bounded wait.
- Fail closed with `stop=handoff-display-owner` if a DRM-owning native child cannot be stopped.

The cleanup runs in both PID1 handoff paths:

- D3 SD-backed rootfs: after root/init validation, before moving `/proc`, `/sys`, and `/dev`.
- D4 userdata appliance: after marker/init validation, before moving `/proc`, `/sys`, and `/dev`.

That placement keeps normal validation failures recoverable in native-init and prevents avoidable
old-userspace DRM fd state from crossing into the Debian PID1 world.

## Validation

Static/source validation:

```text
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Iworkspace/public/src/native-init \
  -c workspace/public/src/native-init/a90_server_distro.c \
  -o /tmp/a90_server_distro_handoff.o
file /tmp/a90_server_distro_handoff.o
```

Result:

```text
/tmp/a90_server_distro_handoff.o: ELF 64-bit LSB relocatable, ARM aarch64, version 1 (SYSV), not stripped
```

Regression tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_native_handoff_cleanup \
  tests.test_build_native_init_boot_v3381_server_distro_journaled_formatter \
  tests.test_dpublic_smoke_helpers
```

Result:

```text
Ran 12 tests in 0.006s
OK
```

## Safety Boundary

- No boot image was built or flashed in this unit.
- No block device, partition, PMIC, GPIO, regulator, or display panel init path was touched.
- The live Debian appliance/HUD/quick Tunnel from the previous unit was not interrupted.
- Public URL and private run artifacts remain private-only.

## Next Gate

The next live validation, if requested, should be a new native candidate build/run identity, then a
checked-helper flash or hot-reload route only after the current public tunnel inspection is done.  The live
check should confirm that `switch-root-to-userdata` prints the `handoff_display` markers and that Debian
firstboot no longer needs to kill a native `/init` DRM holder.
