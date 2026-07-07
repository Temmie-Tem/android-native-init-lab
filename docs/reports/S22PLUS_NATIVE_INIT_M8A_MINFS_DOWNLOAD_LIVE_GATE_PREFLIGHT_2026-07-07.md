# S22+ Native-Init M8A Minimal-FS Download Live Gate Preflight - 2026-07-07

## Verdict

M8A live gate preflight passed. No live flash was run.

Codex added the SHA-pinned `AGENTS.md` M8A boot-only/Odin exceptions and the
guarded helper
`workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py`.
The helper now verifies the exact M8A candidate, rollback APs, manifest safety,
`AGENTS.md` authorization text, Android/Magisk baseline stability, and current
boot hash before any live flash.

## Candidate

```text
AP.tar.md5             c97d29e38fe3293ad145a7743b61ae5fddae8f1b028e619dcd56e2f640de3c19
boot.img               8a816fb3bf8e644de4bbe0409f6cf94fd06a33d16e672569c130535ce139ad44
M8A /init              aac2a03a2b20e72c3d69cfa3c4d3e5c045c817c293c347ac2aaf81f1bfb029b1
source                 830f95cc0f4237f10f2e132ead873a69f543134a503816fa2281205d41362538
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
marker                 S22_NATIVE_INIT_M8A_MINFS_DOWNLOAD
```

Rollback APs verified by the helper:

```text
Magisk boot-only rollback AP  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot-only fallback AP   1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Helper Gates

Offline-check command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py --offline-check
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py
```

Result:

```text
dry-run ok
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash matches 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
host Odin endpoint absent during dry-run snapshot
```

Manifest safety verified:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
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
workspace/private/runs/s22plus_m8a_minfs_download_live_gate_20260707T110313Z/s22plus_m8a_minfs_download_live_gate.txt
workspace/private/runs/s22plus_m8a_minfs_download_live_gate_20260707T110319Z/s22plus_m8a_minfs_download_live_gate.txt
```

## Live Contract

The next supervised live command is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py --live --ack S22PLUS-M8A-MINFS-DOWNLOAD-LIVE-GATE
```

Expected branch logic:

```text
original Odin endpoint disconnects, later Odin endpoint appears:
  M8A direct PID1 survived minimal fs setup and reached reboot("download").
  Roll back immediately through the helper and continue to M8B module split.

no later Odin endpoint / bootloop:
  Enter download mode manually, then run:
  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py --rollback-from-download --ack S22PLUS-M8A-ROLLBACK-FROM-DOWNLOAD
  Treat the failure as below the module layer.
```

No live flash was executed in this preflight unit.
