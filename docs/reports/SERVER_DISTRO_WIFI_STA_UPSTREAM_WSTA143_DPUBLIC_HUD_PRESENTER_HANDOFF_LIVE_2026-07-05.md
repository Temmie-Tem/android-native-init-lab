# WSTA143 D-public HUD Presenter Handoff Live Blocker

Date: 2026-07-05 09:58 KST

## Verdict

WSTA143 ran the Debian handoff survival proof on resident V3400 without building
or flashing a new image.  The durable native presenter survived `switch_root`,
and handoff cleanup preserved the intended PID while removing the other native
DRM holders.  After Debian PID1 came up, that same PID was the only remaining
`/dev/dri/card0` fd owner, and a Debian `a90hud` launched intent producer had
UID/GID 3904, `CapEff=0`, and no DRM fd.

The full integration proof is still blocked: the preserved native presenter and
Debian do not see the same `/run/a90-dpublic` directory after `switch_root`.
Debian writes a fresh intent successfully, but the presenter does not consume it
because the presenter's `/run/a90-dpublic` remains on the old ramfs root while
Debian `/run/a90-dpublic` is on the userdata ext4 root.

Result: `wsta143-handoff-survival-drm-pass-intent-path-blocked`.

## Scope And Safety

- Boot flash: none.
- Native image: resident V3400
  `A90 Linux init 0.11.156 (v3400-dpublic-hud-presenter-service-dedupe)`.
- Userdata format/populate: none.
- Public tunnel/public URL: not started, not observed, not logged.
- Wi-Fi association/DHCP: none.
- Packet-filter mutation: none.
- Forbidden partitions/PMIC/GDSC/GPIO/backlight/panel reinit: none.
- Final state: rebooted back to V3400 native-init with `selftest fail=0`.

Private run directory:

`workspace/private/runs/server-distro/wsta143-dpublic-hud-presenter-handoff-live-20260705T0949KST/`

## Evidence

Pre-handoff native health:

- `version: 0.11.156 build=v3400-dpublic-hud-presenter-service-dedupe`
- `selftest: pass=12 warn=1 fail=0`
- `transport.serial=ready`, `transport.ncm=ready`, `transport.tcpctl=ready`

Presenter start:

- `A90WSTA140 start.pid=694`
- `A90WSTA140 start.process_model=forked-native-child-survives-switch-root`
- `A90WSTA140 status.pid=694`
- `A90WSTA140 status.drm_fd=1`
- `A90WSTA140 status.debian_direct_kms=0`
- pre-handoff fresh intent reached `last_sequence=14300`, `present_rc=0`

Handoff cleanup:

- `switch-root-to-userdata SERVER-DISTRO-D4-USERDATA-APPLIANCE userdata=appliance-root`
  reached `exec_switch_root_now`.
- cleanup terminated stale native DRM holders:
  - `drm_owner_pid=545 action=term`
  - `drm_owner_pid=549 action=term`
- cleanup preserved the durable presenter:
  - `drm_owner_pid=694 action=preserve-dpublic-hud-presenter`
- `handoff_display=done killed=2 rc=0`

Debian-side proof after handoff:

- `/proc/1/comm=init`
- `/proc/1/exe=/usr/sbin/init`
- Debian version `12.14`
- root filesystem: userdata ext4
- `/run/a90-dpublic` in Debian: `root:a90hud 1770`
- PID 694 alive:
  - `presenter_comm=init`
  - `presenter_exe=/init (deleted)`
  - `PRESENTERFD fd=3 target=/dev/dri/card0 (deleted)`
- DRM fd scan after handoff:
  - only PID 694 held a DRM fd
- `a90hud` launch proof:
  - `launched_uid=3904`
  - `launched_gid=3904`
  - `launched_groups=3904`
  - `launched_cap_eff=0000000000000000`
  - launched fds were pipes only, no DRM target
- Debian `a90hud` wrote fresh intent:
  - `A90WSTA132_INTENT_WRITTEN=1`
  - `A90WSTA132_INTENT_SEQUENCE=14301`
  - intent file owner: `a90hud:a90hud`, mode `0640`

Blocking evidence:

- Debian-visible `/run/a90-dpublic/hud-presenter.status` was absent after
  handoff.
- The presenter did not update to `last_sequence=14301`.
- Path comparison proved two different backing filesystems:
  - Debian `/run` and `/run/a90-dpublic`: userdata ext4.
  - `/proc/694/root/run` and `/proc/694/root/run/a90-dpublic`: old rootfs
    ramfs.
- Probe files written through each path appeared only on that side:
  - Debian `/run/a90-dpublic/debian-probe.txt`
  - presenter-root `/proc/694/root/run/a90-dpublic/rootns-probe.txt`

## Root Cause

The WSTA140 service model correctly keeps the native presenter process alive
through the Debian handoff, but it assumed `/run/a90-dpublic` would remain a
shared path across `switch_root`.  It does not.  The native child pins the old
ramfs root, while Debian PID1 and services use the userdata ext4 root.  The
same absolute path resolves to different directories for the two sides.

The next fix should make `/run/a90-dpublic` an explicit shared mount before the
handoff.  The clean shape is:

1. create or mount a small shared runtime directory for `/run/a90-dpublic`;
2. start the durable native presenter against that shared mount;
3. before `exec_switch_root_now`, bind that same mount into
   `/mnt/a90-userdata-root/run/a90-dpublic`;
4. after Debian boots, verify the presenter and Debian see the same device/inode
   and the Debian `a90hud` sequence is consumed.

This should keep Debian as intent writer only and preserve native/root as the
sole DRM/KMS owner.

## Final Health

The device was rebooted from Debian back to the resident V3400 native image.
Final health was clean:

- `version: 0.11.156 build=v3400-dpublic-hud-presenter-service-dedupe`
- `selftest: pass=12 warn=1 fail=0`
- `status` completed with serial/NCM/tcpctl ready.

## Next

WSTA144 should implement the shared `/run/a90-dpublic` handoff mount contract in
native-init source and live-gate it on a new V3401 candidate:

- pre-handoff status shows presenter PID and DRM fd;
- handoff cleanup preserves the presenter and kills other native DRM holders;
- Debian and presenter-root `/run/a90-dpublic` resolve to the same backing
  directory;
- Debian `a90hud` writes a fresh sequence that the preserved native presenter
  consumes;
- final cleanup/reboot returns to clean native health.
