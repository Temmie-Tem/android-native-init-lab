# WSTA149 D-public HUD Intent Syscall Trace Live Pass

Date: 2026-07-05 11:02 KST

## Scope

WSTA149 profiles the split D-public HUD Debian-side intent producer before any
seccomp enforcement work.  The traced process is `a90-dpublic-hud-intent`
launched through `a90-service-launch dpublic-hud`; native init remains the
root-owned KMS presenter.

This unit did not build or flash a boot image, reboot native init, associate
Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, touch userdata,
switch root, open DRM, or perform KMS operations.

## Source Changes

- Added `run_wsta149_dpublic_hud_intent_syscall_trace.py`.
- Added focused tests in
  `tests/test_server_distro_wsta149_dpublic_hud_intent_syscall_trace.py`.
- The runner:
  - uses the WSTA115 strace rootfs image by default;
  - builds a fresh arm64 `a90-dpublic-hud-intent` from source;
  - stages service-hardening assets and HUD split markers in the chroot;
  - runs `strace` around only the HUD intent producer;
  - requires no network syscalls, no `ioctl`, and no DRM trace content;
  - saves raw trace, syscall list, launcher log, and intent JSON privately.

## Live Result

Run:

```text
workspace/private/runs/server-distro/wsta149-dpublic-hud-intent-syscall-trace-live-20260705T1058KST/
```

Decision:

```text
wsta149-dpublic-hud-intent-syscall-trace-live-pass
```

Resident:

```text
A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)
```

Input image:

```text
workspace/private/runs/server-distro/wsta115-strace-rootfs-20260705T0309KST/debian-bookworm-arm64-wsta115-strace.img
sha256=40a01268ae6f77d1548dd71f9ef30f4d31fdce437d90a6edcc7721f0e26dd159
```

Key proof:

- public exposure default-off.
- `strace` present.
- service launcher exec decision logged for `dpublic-hud`.
- service identity lowered to UID/GID `3904/3904`.
- `NoNewPrivs=1`.
- effective capabilities were zero.
- intent file `/run/a90-dpublic/hud-intent.json` was written with schema
  `a90-dpublic-hud-intent-v1`, sequence `14901`, and `PUBLIC_OFF`.
- raw trace saved privately.
- syscall-name profile saved privately.
- atomic write path observed via `fsync` and `renameat`.
- no network syscalls observed.
- no `ioctl` syscall and no `/dev/dri`/DRM trace content observed.
- final device health remained clean: `selftest fail=0`.

Captured syscall-name profile:

```text
brk
close
execve
exit_group
faccessat
fchmod
fsync
getpid
getrandom
mkdirat
mmap
mprotect
munmap
newfstatat
openat
prlimit64
read
renameat
rseq
set_robust_list
set_tid_address
write
```

Artifact metadata:

- raw trace: private artifact saved, size `3408`, SHA256
  `20a905a6a4db8598eac67ca91aeb3c4560eec619f5bf68285b158993b3f50983`.
- syscall list: private artifact saved, size `182`, SHA256
  `b820769322fb0d08d81352b854ebaf2bb58905bb9776cb8ec5a10d94033407f3`.
- intent JSON: private artifact saved, size `294`, SHA256
  `0010ed9aae829d62b951131df224f00ab2983ca88418730d664422afd58e9c23`.
- launcher log: private artifact saved, size `394`, SHA256
  `cf5c73436f13ed80035838d6934e8b8fae456416137a20aa9b254268d7fe03af`.

Cleanup note:

- The runner's cleanup output included a transient
  `cleanup_dropbear_absent=0`, but its postcheck reported
  `dropbear_absent=true`, `mount_absent=true`, and `loop_node_absent=true`.
- A follow-up bounded post-clean command also confirmed
  `A90WSTA149_POST_CLEAN_DROPBEAR_ABSENT=1`.
- Final explicit `selftest` after that cleanup remained `pass=12 warn=1 fail=0`.

## Interpretation

The remaining optional HUD syscall profile is now live-proven for the current
split architecture.  The Debian side is an intent producer only: it writes a
bounded JSON handoff file as `a90hud`, with no network syscalls and no DRM/KMS
path.  Native init remains the display owner.

This proof does not claim seccomp is enforced yet.  It provides the syscall
baseline for a later seccomp or containment unit.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta149_dpublic_hud_intent_syscall_trace.py \
  tests/test_server_distro_wsta149_dpublic_hud_intent_syscall_trace.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta149_dpublic_hud_intent_syscall_trace

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

Result:

- Focused WSTA149 tests: `8 tests OK`.
- Full server-distro WSTA regression: `470 tests OK`.
- WSTA149 live: `wsta149-dpublic-hud-intent-syscall-trace-live-pass`.
- Final device selftest: `fail=0`.

## Next

Fold this proof into WSTA108 operator status so the optional HUD syscall profile
is no longer listed as a remaining blocker.  After that, continue broader
containment hardening or design a concrete seccomp policy unit from this
profile.
