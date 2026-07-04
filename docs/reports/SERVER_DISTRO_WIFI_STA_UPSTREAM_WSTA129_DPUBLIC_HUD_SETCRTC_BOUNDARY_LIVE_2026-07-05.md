# WSTA129 D-public HUD SETCRTC Boundary Live

Date: 2026-07-05 07:27 KST

## Verdict

WSTA129 live did not pass as a non-root direct-KMS HUD proof.  It produced a
cleaner and more valuable boundary result:

`a90-service-launch dpublic-hud` starts the HUD as `a90hud`, reaches DRM/KMS
display discovery, logs `display=1080x2400 connector=28 crtc=133`, and then
exits at `setcrtc: Permission denied`.

The WSTA127/WSTA128 assumption that the Debian `a90hud` process can own direct
KMS presentation is therefore not live-proven.  The next design should use a
root-owned minimal KMS presenter/broker, or keep native init as display owner
while Debian supplies HUD status/render intent.

## Scope

No boot flash, native reboot, Wi-Fi association, DHCP, public tunnel, packet
filter mutation, userdata mutation, or switch-root was performed.  This was a
no-flash SD work-image HUD live gate on resident:

`A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)`

The final device health check remained clean after runtime cleanup:

- `selftest fail=0`
- `transport.tcpctl=ready`
- `netservice: enabled tcpctl=running`

## Live Attempts

### Default SD Image

Run directory:

`workspace/private/runs/server-distro/wsta129-dpublic-hud-live-20260705T0700KST`

Result:

- decision: `wsta129-blocked-hud-probe`
- blocker: `A90WSTA129_STRACE_PRESENT=0`
- cleanup: `/proc` unmounted, final selftest fail-zero

This proved the default work image is not the right HUD syscall-profile target.

### WSTA115 Strace Image

Image:

`workspace/private/runs/server-distro/wsta115-strace-rootfs-20260705T0309KST/debian-bookworm-arm64-wsta115-strace.img`

SHA256:

`40a01268ae6f77d1548dd71f9ef30f4d31fdce437d90a6edcc7721f0e26dd159`

Run directory:

`workspace/private/runs/server-distro/wsta129-dpublic-hud-live-strace-20260705T0712KST`

Result:

- decision: `wsta129-blocked-hud-probe`
- blocker: `A90WSTA129_DRM_SYSFS_PRESENT=0`

The source runner was updated to mount and clean `/sys` inside the chroot for
the DRM sysfs discovery step.

### Sysfs-Mounted Probe

Run directory:

`workspace/private/runs/server-distro/wsta129-dpublic-hud-live-sysfs-20260705T0718KST`

Result:

- decision: `wsta129-blocked-hud-probe`
- `A90WSTA129_DRM_SYSFS_PRESENT=1`
- `A90WSTA129_DRM_NODE_PRESENT=1`
- `A90WSTA129_DRM_NODE_POLICY_APPLIED=1`
- `A90WSTA129_TRACE_PROCESS_STARTED=1`
- launcher logged `service=dpublic-hud`, `user=a90hud`, `no_new_privs=1`
- HUD logged `display=1080x2400 connector=28 crtc=133 refresh=1s`
- blocker: `setcrtc: Permission denied`

The source runner was then updated to preserve trace/profile evidence when the
HUD exits before PID sampling.

### SETCRTC Boundary Probe

Run directory:

`workspace/private/runs/server-distro/wsta129-dpublic-hud-live-setcrtc-boundary-20260705T0725KST`

Result:

- decision: `wsta129-blocked-hud-setcrtc-permission`
- `hud_probe returncode=52`
- `A90WSTA129_PUBLIC_ENABLE_ABSENT=1`
- `A90WSTA129_STRACE_PRESENT=1`
- `A90WSTA129_DRM_SYSFS_PRESENT=1`
- `A90WSTA129_DRM_NODE_PRESENT=1`
- `A90WSTA129_DRM_NODE_POLICY_APPLIED=1`
- `A90WSTA129_TRACE_PROCESS_STARTED=1`
- `A90WSTA129_HUD_EXITED_EARLY=1`
- `A90WSTA129_HUD_SETCRTC_PERMISSION_DENIED=1`
- `A90WSTA129_TRACE_FILE_NONEMPTY=1`
- `A90WSTA129_SYSCALL_PROFILE_NONEMPTY=1`
- `A90WSTA129_SYSCALL_NETWORK_ABSENT=1`
- `A90WSTA129_DRM_NODE_RESTORED=1`
- `A90WSTA129_SYS_UNMOUNTED=1`
- `A90WSTA129_PROC_UNMOUNTED=1`

Observed syscall names:

`brk close execve exit_group fstat getrandom ioctl lseek mmap mprotect munmap newfstatat openat prlimit64 read readlinkat rseq rt_sigaction set_robust_list set_tid_address write`

Private artifacts:

- raw trace: `workspace/private/runs/server-distro/wsta129-dpublic-hud-live-setcrtc-boundary-20260705T0725KST/wsta129_hud.strace`
  - size: `5171`
  - SHA256: `973ce0e50baec60c1792ec7d575c6f4f1cebbdf4100efabe7fe7790dcdd812d8`
- syscall list: `workspace/private/runs/server-distro/wsta129-dpublic-hud-live-setcrtc-boundary-20260705T0725KST/wsta129_hud.syscalls`
  - size: `177`
  - SHA256: `de722c614b33ee5c0c5caf4bbf8c3566c6623b0f37a5aac7b4ebc5ced4537630`

## Source Changes

`run_wsta129_dpublic_hud_live_gate.py` now:

- mounts `/sys` inside the chroot for DRM sysfs discovery;
- performs host-side emergency cleanup for chroot `/sys` and `/proc` mounts;
- preserves launcher log, HUD log, trace, and syscall profile when the HUD exits
  early at `setcrtc`;
- classifies that boundary as `wsta129-blocked-hud-setcrtc-permission` instead
  of collapsing it into a generic `hud-pid` failure.

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

`9 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

`431 tests OK`.

## Next

WSTA130 should revise the HUD display architecture.  Do not fold WSTA129 as a
HUD live pass into WSTA108.  The direct non-root KMS model is blocked at
`SETCRTC`; the next bounded unit should define and test one of:

- a tiny root-owned KMS broker/presenter with a narrow command/input surface; or
- a native-init owned display presenter that receives Debian HUD status/render
  intent without handing KMS master to the Debian service.
