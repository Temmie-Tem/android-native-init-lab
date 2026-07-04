# WSTA129 D-public HUD Live Gate Source

Date: 2026-07-05 06:56 KST

## Verdict

WSTA129 source gate is prepared and host-validated.  No live device HUD/DRM/KMS
operation was run in this unit.

The new runner is fail-closed by default and requires all explicit live gates:

- `--execute-hud-live`
- `--allow-hud-live`
- `--ack-drm-control`
- `--ack-private-trace-artifact`
- `--ack-runtime-cleanup`

## Scope

Added `workspace/public/src/scripts/server-distro/run_wsta129_dpublic_hud_live_gate.py`.

The runner reuses the existing WSTA110/WSTA114 live pattern:

- prepare the SD work image and mount the Debian chroot;
- start temporary key-only Dropbear;
- stage service users, service launcher, and service policy;
- stage `/usr/local/bin/a90-dpublic-hud`;
- launch through `a90-service-launch dpublic-hud`;
- trace the HUD runtime with `strace`;
- save private raw/syscall artifacts under the run directory;
- clean HUD processes, trace sidecars, DRM node mode/owner, chroot/dropbear/loop state.

HUD-specific checks are encoded for the future live run:

- process UID/GID must be `3904/3904` (`a90hud`);
- `NoNewPrivs=1`;
- `CapEff=0000000000000000`;
- no `socket:` fd on the HUD process;
- no `socket`, `bind`, `listen`, `accept`, or `connect` in the syscall profile;
- `/dev/dri/card0` policy applied and restored;
- DRM fd observed;
- core syscalls `execve`, `openat`, `ioctl`, `mmap`, and `munmap` observed;
- runtime cleanup and final native selftest pass required.

## Inert Smoke

Command:

```sh
python3 workspace/public/src/scripts/server-distro/run_wsta129_dpublic_hud_live_gate.py \
  --run-id wsta129-dpublic-hud-live-gate-source-20260705T0656KST \
  --run-dir workspace/private/runs/server-distro/wsta129-dpublic-hud-live-gate-source-20260705T0656KST
```

Result:

- decision: `wsta129-blocked-hud-live-required`
- `device_action=false`
- `boot_flash=false`
- `native_reboot=false`
- `wifi_connect=false`
- `dhcp=false`
- `public_tunnel=false`
- `public_smoke=false`
- `packet_filter_mutation=false`
- `drm_open=false`
- `kms_setcrtc=false`
- `switch_root=false`

Private inert result:

`workspace/private/runs/server-distro/wsta129-dpublic-hud-live-gate-source-20260705T0656KST/wsta129_result.json`

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta129_dpublic_hud_live_gate.py \
  tests/test_server_distro_wsta129_dpublic_hud_live_gate.py
```

Pass.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta129_dpublic_hud_live_gate.py'
```

`8 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

`430 tests OK`.

## Next

Run the explicit WSTA129 live gate only when the operator wants the actual DRM/KMS
proof on the SD work image:

```sh
python3 workspace/public/src/scripts/server-distro/run_wsta129_dpublic_hud_live_gate.py \
  --execute-hud-live \
  --allow-hud-live \
  --ack-drm-control \
  --ack-private-trace-artifact \
  --ack-runtime-cleanup
```

This remains no-flash and SD work-image scoped, but it will temporarily take DRM
master/KMS control for the HUD proof.
