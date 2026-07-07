# S22+ Native-Init M10A3 Probe Reboot Live Gate Preflight - 2026-07-07

## Verdict

M10A3 live-gate preflight passed. No live flash was run.

Codex added the SHA-pinned `AGENTS.md` M10A3 boot-only/Odin exception and the
guarded helper
`workspace/public/src/scripts/revalidation/s22plus_m10a3_probe_reboot_live_gate.py`.
The helper verifies the exact M10A3 candidate, rollback APs, manifest safety,
`AGENTS.md` authorization text, Android/Magisk baseline stability, and current
boot hash before any live flash.

M10A3 is the narrow split after the operator-corrected M10A2 result. M10A2
bootlooped and required manual download-mode rollback after a non-VFS
`getpid()` syscall before `reboot("download")`. M10A3 keeps the extra
pre-reboot helper call and stack-probe shape, but removes the pre-reboot
syscall.

## Candidate

```text
AP.tar.md5             7415538ac9cbfdf4af27f294927c3c81d2656412a7f779fce515138ec28e7e3b
boot.img               eb2d1cfc278e63cdfe009379f05139e5299b49859a2b247d4e6996be5f24959c
M10A3 /init            4c7908026430658250a0999fad2d47c7e5d99c212dc8daa3ba8fbafb0f4a8371
source                 9b5e3669a7a790a369bf8ed4beb662cb5262189e5d8f22011c731fc827955856
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a3_probe_reboot_live_gate.py --offline-check
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a3_probe_reboot_live_gate.py
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
pre_reboot_helper=stack-probe-no-syscall
first_runtime_side_effect=none-before-reboot
intended_syscalls=["reboot"]
intended_syscall_count=1
vfs_setup=none
vfs_mutation=false
pathname_access=false
getpid=false
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
workspace/private/runs/s22plus_m10a3_probe_reboot_live_gate_20260707T125331Z/s22plus_m10a3_probe_reboot_live_gate.txt
workspace/private/runs/s22plus_m10a3_probe_reboot_live_gate_20260707T125344Z/s22plus_m10a3_probe_reboot_live_gate.txt
```

## Live Contract

The next supervised live command is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a3_probe_reboot_live_gate.py --live --ack S22PLUS-M10A3-PROBE-REBOOT-LIVE-GATE
```

Rollback-only command if the candidate does not return to download mode and the
operator manually enters download mode:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a3_probe_reboot_live_gate.py --rollback-from-download --ack S22PLUS-M10A3-ROLLBACK-FROM-DOWNLOAD
```

Expected branch logic:

```text
original Odin endpoint disconnects, later Odin endpoint appears, operator confirms no manual entry:
  the extra helper/stack shape is survivable.
  M10A2 points at the prior getpid syscall.

original Odin endpoint disconnects, later Odin endpoint appears, operator manually entered download:
  rollback succeeds, but result is ambiguous/manual and not automatic proof.

no later Odin endpoint / bootloop:
  enter download mode manually, run rollback-only command.
  the extra helper/timing/stack shape is enough to lose self-download.
```

No live flash was executed in this preflight unit.
