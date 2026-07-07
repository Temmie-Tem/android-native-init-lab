# S22+ Native-Init M10A4 Inline Probe Reboot Live Gate Preflight - 2026-07-07

## Verdict

M10A4 live-gate preflight passed. No live flash was run.

Codex added the SHA-pinned `AGENTS.md` M10A4 boot-only/Odin exception and the
guarded helper
`workspace/public/src/scripts/revalidation/s22plus_m10a4_inline_probe_reboot_live_gate.py`.
The helper verifies the exact M10A4 candidate, rollback APs, manifest safety,
`AGENTS.md` authorization text, Android/Magisk baseline stability, and current
boot hash before any live flash.

M10A4 is the narrow split after the operator-corrected M10A3 result. M10A3
bootlooped and required manual download-mode rollback after a separate
no-syscall probe helper call/return before `reboot("download")`. M10A4 removes
that separate helper boundary, keeps a small inline stack probe in `_start`,
then branches once to the reboot helper.

## Candidate

```text
AP.tar.md5             a4d7c9d05536d22c3f56bd1891a7fbc0c8fa6d3500cf8b1036e11bd0c9569c26
boot.img               38986a19454d7fd49e8860d025ad4241e2c130b5fc28956bed892c26842fb3a9
M10A4 /init            d70c794979bc16f12917871f5e6e7b2231569f72682a5f6ebcd87f901a11837b
source                 2d168c28dbdef67bedc7d9d39250c7e61c928daf89a2b973616534453a835a84
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a4_inline_probe_reboot_live_gate.py --offline-check
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a4_inline_probe_reboot_live_gate.py
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
pre_reboot_work=inline-stack-probe-no-syscall
pre_reboot_helper_call=false
first_runtime_side_effect=none-before-reboot
first_externally_observable_action=inline-probe-then-reboot-download
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
branch_targets=["0x40010c"]
reboot_func_start=0x40010c
```

Private run logs:

```text
workspace/private/runs/s22plus_m10a4_inline_probe_reboot_live_gate_20260707T131035Z/s22plus_m10a4_inline_probe_reboot_live_gate.txt
workspace/private/runs/s22plus_m10a4_inline_probe_reboot_live_gate_20260707T131041Z/s22plus_m10a4_inline_probe_reboot_live_gate.txt
```

## Live Contract

The next supervised live command is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a4_inline_probe_reboot_live_gate.py --live --ack S22PLUS-M10A4-INLINE-PROBE-REBOOT-LIVE-GATE
```

Rollback-only command if the candidate does not return to download mode and the
operator manually enters download mode:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m10a4_inline_probe_reboot_live_gate.py --rollback-from-download --ack S22PLUS-M10A4-ROLLBACK-FROM-DOWNLOAD
```

Expected branch logic:

```text
original Odin endpoint disconnects, later Odin endpoint appears, operator confirms no manual entry:
  inline stack work is survivable.
  M10A3 points at the separate helper call/return boundary.

original Odin endpoint disconnects, later Odin endpoint appears, operator manually entered download:
  rollback succeeds, but result is ambiguous/manual and not automatic proof.

no later Odin endpoint / bootloop:
  enter download mode manually, run rollback-only command.
  any pre-reboot stack work or instruction delay before the reboot helper is suspect.
```

No live flash was executed in this preflight unit.
