# S22+ Native-Init M5B Mount/Reboot Live Gate Preflight - 2026-07-07

## Scope

Host-side preflight for the M5B mount/reboot live gate. No live flash was run,
no device partition was written, and no reboot was requested in this unit.

M5B is the first split after M5 v0.4 USB-ACM failed to expose any host
transport. It tests freestanding C plus virtual filesystem mounts before the
USB module/configfs chain.

## Helper

```text
workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py
```

Live ack token:

```text
S22PLUS-M5B-MOUNT-REBOOT-LIVE-GATE
```

Rollback-only ack token:

```text
S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD
```

Dry-run private log:

```text
workspace/private/runs/s22plus_m5b_mount_reboot_live_gate_20260706T215413Z/s22plus_m5b_mount_reboot_live_gate.txt
```

## Pinned Candidate

```text
AP.tar.md5                  872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59
boot.img                    21a61c84d273390a3681d029977ff6150991036568aa455a0a4879ff24590239
base Magisk boot            2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
M5B /init                   accfc6f5e04d7d302ee17c6e4ce93ee14240ebdbb70274424934805e542b9bac
```

The candidate AP contains exactly:

```text
boot.img.lz4
```

Manifest safety requires:

```text
runtime=freestanding-raw-syscall
glibc_static_startup=false
first_candidate_action=mount-virtual-filesystems-then-reboot-download
module_insertions=false
usb_gadget_setup=false
block_device_writes=false
persistent_partition_mount=false
```

## Rollback Payloads

```text
Magisk boot-only AP          d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot-only fallback AP  1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

Both rollback APs are verified as single-member `boot.img.lz4` packages.

## Dry-Run Result

The dry-run passed:

```text
agents_exception_missing=[]
m5b_candidate_sha256=872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59
m5b_candidate_members=['boot.img.lz4']
android_stability_result=ok samples=4
current_boot_hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Current Android preflight passed:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
bootanim=stopped
Magisk root available
```

## Live Flow Prepared

The helper is attended:

1. Verify `AGENTS.md` exception, candidate hashes, manifest safety, rollback
   AP hashes, Android identity/root, Android stability, and current boot hash.
2. Reboot the rooted Android baseline to download mode.
3. Flash only the exact M5B boot-only AP through Odin.
4. Wait for the original Odin device to disconnect.
5. Observe for candidate self-entry to Odin/download mode.
6. If self-download appears, immediately roll back to the pinned Magisk
   boot-only AP and verify Android/root returned.
7. If self-download does not appear, stop and require manual download-mode entry
   plus `--rollback-from-download`.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py
git diff --check
```

All passed.

## Next

The next live command, if supervised, is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py --live --ack S22PLUS-M5B-MOUNT-REBOOT-LIVE-GATE
```

If the phone is already in download mode and only rollback is needed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py --rollback-from-download --ack S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD
```

Do not run this unattended.
