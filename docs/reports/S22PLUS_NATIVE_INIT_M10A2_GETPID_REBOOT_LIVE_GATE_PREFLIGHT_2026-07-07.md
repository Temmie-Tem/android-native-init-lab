# S22+ Native-Init M10A2 Getpid Reboot Live Gate Preflight - 2026-07-07

## Verdict

M10A2 live-gate preflight passed. No live flash was run.

Codex added the SHA-pinned `AGENTS.md` M10A2 boot-only/Odin exception and the
guarded helper
`workspace/public/src/scripts/revalidation/s22plus_m10a2_getpid_reboot_live_gate.py`.
The helper verifies the exact M10A2 candidate, rollback APs, manifest safety,
`AGENTS.md` authorization text, Android/Magisk baseline stability, and current
boot hash before any live flash.

M10A2 is the narrow split after the operator-corrected M10A1 result. M10A1
bootlooped and required manual download-mode rollback after a read-only
`newfstatat("/dev")` before `reboot("download")`. M10A2 removes pathname/VFS
access entirely and tests only `getpid()` before the same Samsung download-mode
reboot request.

## Candidate

```text
AP.tar.md5             108c0a5e2a1fd80efed5ae93ea01b4b98c4990f7d3d8b292ef35ccc0de2fdb60
boot.img               f0238a82cad63a3d8017a0892a3a85bfe79c8c503848a4ac0fa4a21a77a72c94
M10A2 /init            0839562fbef74328abb17646d957516154ae85ab954667782c809249cf8bde99
source                 5b15166dfc405a7ee1297ac1cd0da3bd844779099748cf98ee3aca8e2e665d9a
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-c-raw-syscall
```

Rollback APs verified by the helper:

```text
Magisk boot-only rollback AP  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot-only fallback AP   1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Helper Gates

Offline-check command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a2_getpid_reboot_live_gate.py --offline-check
```

Result:

```text
offline-check ok
device_action=0
agents_exception_checked=0
android_checked=0
```

Default dry-run command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a2_getpid_reboot_live_gate.py
```

Result:

```text
dry-run ok
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash matches 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
host Odin endpoint absent during dry-run snapshot
manual_download_ambiguity_policy=later Odin endpoint is not automatic proof without operator confirmation
```

Manifest safety verified:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
intended_syscall_count=2
intended_syscalls=["getpid", "reboot"]
first_runtime_side_effect=getpid-non-vfs
vfs_setup=none
vfs_mutation=false
pathname_access=false
mkdirat=false
marker_write=false
kmsg_write=false
mknodat=false
mounts=false
sleep_before_reboot=false
module_insertions=false
module_binary_injection=false
module_files_injected_into_boot_ramdisk=0
module_list_files_injected_into_boot_ramdisk=0
configfs_runtime_gadget=false
udc_binding=false
usb_role_force=false
block_device_writes=false
tar_members=["boot.img.lz4"]
```

Private run logs:

```text
workspace/private/runs/s22plus_m10a2_getpid_reboot_live_gate_20260707T123427Z/s22plus_m10a2_getpid_reboot_live_gate.txt
workspace/private/runs/s22plus_m10a2_getpid_reboot_live_gate_20260707T123432Z/s22plus_m10a2_getpid_reboot_live_gate.txt
```

## Live Contract

The next supervised live command is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a2_getpid_reboot_live_gate.py --live --ack S22PLUS-M10A2-GETPID-REBOOT-LIVE-GATE
```

Rollback-only command if the candidate does not return to download mode and the
operator manually enters download mode:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a2_getpid_reboot_live_gate.py --rollback-from-download --ack S22PLUS-M10A2-ROLLBACK-FROM-DOWNLOAD
```

Expected branch logic:

```text
original Odin endpoint disconnects, later Odin endpoint appears, operator confirms no manual entry:
  one non-VFS pre-reboot syscall is survivable.
  M10A1 points at pathname VFS access.

original Odin endpoint disconnects, later Odin endpoint appears, operator manually entered download:
  rollback succeeds, but result is ambiguous/manual and not automatic proof.

no later Odin endpoint / bootloop:
  enter download mode manually, run rollback-only command, and treat the issue as
  broader than pathname VFS access.
```

No live flash was executed in this preflight unit.
