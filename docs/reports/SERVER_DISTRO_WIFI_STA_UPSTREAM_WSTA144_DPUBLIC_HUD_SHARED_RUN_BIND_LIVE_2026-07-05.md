# WSTA144 D-public HUD Shared Run Bind Live Pass

Date: 2026-07-05 10:14 KST

## Verdict

WSTA144 fixes the WSTA143 split-`/run/a90-dpublic` blocker.  V3401 makes the
native HUD presenter runtime directory an explicit tmpfs mount and bind-mounts
that same directory into the userdata Debian root before `switch_root`.

Live result: PASS.  The durable native presenter survived the Debian handoff,
remained the only DRM fd owner, Debian `a90hud` had no DRM fd, and a fresh
Debian-written intent sequence was consumed by the preserved native presenter.

## Build

- Candidate: `A90 Linux init 0.11.157 (v3401-dpublic-hud-shared-run-bind)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3401_dpublic_hud_shared_run_bind.img`
- Boot SHA256:
  `d9496d565af554f4fb30a9064c1998356b27396163b7cc67fd693db8a3a8e418`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3401_DPUBLIC_HUD_SHARED_RUN_BIND_SOURCE_BUILD_2026-07-05.md`

Static validation:

- V3401 builder/test `py_compile`: pass.
- Focused V3400+V3401 builder tests: `10 tests OK`.
- Full server-distro WSTA regression: `458 tests OK`.
- AArch64 native-init/helper compile and required-string audit: pass.

## Flash Gate

The checked helper flashed the exact V3401 artifact:

- local Android boot magic: ok
- local SHA256: `d9496d565af554f4fb30a9064c1998356b27396163b7cc67fd693db8a3a8e418`
- recovery ADB came up
- remote pushed image SHA256 matched
- boot partition prefix readback SHA256 matched
- post-boot cmdv1 `version/status` verify passed
- native health after flash: `selftest pass=12 warn=1 fail=0`

Rollback preconditions were confirmed before flash:

- v2321 rollback image SHA matched
- v2237 fallback image SHA matched
- v48 fallback image present with recorded SHA
- TWRP recovery artifacts present

## Live Proof

Private run directory:

`workspace/private/runs/server-distro/wsta144-dpublic-hud-shared-run-bind-live-20260705T1007KST/`

Native pre-handoff proof:

- `dpublic-hud-presenter-service start` emitted
  `A90WSTA144 shared_run_dir=shared-run-dir-bind-before-switch-root`.
- Service mounted shared runtime:
  `A90WSTA144 shared_run_dir=mounted path=/run/a90-dpublic fstype=tmpfs mode=1770 owner=root:a90hud`.
- Presenter PID: `625`.
- `status.drm_fd=1`, `status.debian_direct_kms=0`.
- `/proc/mounts` showed `a90-dpublic-hud /run/a90-dpublic tmpfs ... mode=1770,gid=3904`.
- Pre-handoff intent `sequence=14400` reached
  `last_sequence=14400`, `present_rc=0`.

Handoff proof:

- `switch-root-to-userdata SERVER-DISTRO-D4-USERDATA-APPLIANCE userdata=appliance-root`
  reached `exec_switch_root_now`.
- Handoff cleanup killed stale native DRM owner PIDs `546`, `548`, and `550`.
- Handoff cleanup preserved presenter PID `625`.
- Shared bind succeeded:
  `A90WSTA144 shared_run_bind=ok ... same_dev=1 same_ino=1`.
- The presenter consumed the Debian firstboot intent immediately after handoff.

Debian-side proof:

- Debian came up as PID1 `/usr/sbin/init`.
- Root filesystem was userdata ext4.
- Debian `/run/a90-dpublic`: `root:a90hud 1770`.
- Presenter status before fresh write showed
  `pid=625`, `last_sequence=1`, `present_rc=0`.
- Path comparison showed the Debian path and presenter-root path share the same
  tmpfs:
  - `/run/a90-dpublic`: `stat_dev=18`, `stat_ino=28011`, `fs_type=tmpfs`
  - `/proc/625/root/run/a90-dpublic`: same `stat_dev=18`, same `stat_ino=28011`,
    same `fs_type=tmpfs`
- DRM scan before and after fresh write showed only PID `625` holding
  `/dev/dri/card0`.
- `a90hud` launch proof:
  - UID/GID/groups: `3904`
  - `CapEff=0000000000000000`
  - fds were pipes only, no DRM target
- Debian `a90hud` wrote fresh intent `sequence=14401`.
- Presenter status after fresh write:
  - `pid=625`
  - `last_sequence=14401`
  - `present_rc=0`

## Final Health

The device was rebooted from Debian back to the V3401 native image.

- `version: 0.11.157 build=v3401-dpublic-hud-shared-run-bind`
- `selftest: pass=12 warn=1 fail=0`
- `status` completed with serial/NCM/tcpctl ready.

No rollback was needed.  The device is intentionally left on the live-passed
V3401 resident image.

## Safety

No Wi-Fi association, DHCP, public tunnel, public smoke request, packet-filter
mutation, userdata format/populate, forbidden partition write, PMIC/regulator/
GDSC/GPIO/backlight write, or panel reinitialization ran in WSTA144.  Userdata
was only used as the already-populated D4 root for the bounded handoff proof.

## Next

The durable split HUD handoff is now live-proven.  The next server-distro unit
can fold this result into the operator status/endgame model, then continue with
the remaining D-public service integration or containment hardening work.
