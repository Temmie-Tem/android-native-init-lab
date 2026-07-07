# S22+ Native-Init M5B Mount/Reboot Live Incident - 2026-07-07

## Verdict

M5B did not prove the freestanding mount/reboot beacon path.

The SHA-pinned boot-only candidate AP flashed successfully, and the original
Odin download endpoint disconnected after the transfer, but the candidate did
not reappear as Odin/download, ADB, or any Samsung USB endpoint during the
bounded observation window. Host rollback could not run during the live helper
window because the phone had not yet been manually returned to download mode.

Current status: **rollback clean**. The operator later entered download mode,
Codex ran the checked rollback helper, Android returned, Magisk root was
available, and the expected boot hash was verified again.

## Candidate

```text
AP.tar.md5             872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59
boot.img               21a61c84d273390a3681d029977ff6150991036568aa455a0a4879ff24590239
M5B /init              accfc6f5e04d7d302ee17c6e4ce93ee14240ebdbb70274424934805e542b9bac
base boot              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-raw-syscall
glibc_static_startup   false
```

The AP contained exactly one Odin member:

```text
boot.img.lz4
```

## Live Timeline

Private run log:

```text
workspace/private/runs/s22plus_m5b_mount_reboot_live_gate_20260706T215559Z/s22plus_m5b_mount_reboot_live_gate.txt
```

Key events:

```text
21:55:59Z  live helper start
21:56:11Z  Odin/download device appeared for candidate flash
21:56:11Z  M5B candidate AP flash started
21:56:22Z  candidate Odin flash rc=0
21:56:23Z  original Odin endpoint disconnected
21:56:28Z  M5B self-download observation started
21:57:23Z  M5B self-download observation ended, m5b_self_download_seen=0
```

Observed during the M5B window:

```text
ADB transports       none
Odin transports      none
Samsung USB endpoint none observed by host snapshots
```

The helper exited with rc `4` and printed the designed recovery instruction:

```text
M5B self-download did not appear. Enter download mode manually and run --rollback-from-download.
```

## Post-Helper State

After helper exit, host checks still showed no transport:

```text
adb devices -l       no devices
odin4 -l             no devices
lsusb Samsung/04e8   no devices
```

Codex then ran two bounded Odin polling loops for manual recovery, first for
180 iterations and then for 240 iterations at 2 seconds per iteration. Both
ended with:

```text
odin-not-detected-after-wait
```

The operator later reported a boot loop. Codex rechecked host transport at
`2026-07-06T22:46:30Z` / `2026-07-07T07:46:30+0900`:

```text
adb devices -l       no devices
odin4 -l             no devices
lsusb Samsung/04e8   no devices
```

The operator later entered Samsung download mode. At
`2026-07-07T04:35:12Z`, the host saw exactly one Odin endpoint:

```text
/dev/bus/usb/002/094
```

Codex then ran the checked rollback helper:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD
```

Result:

```text
M5B rollback-from-download completed rc=0
log=workspace/private/runs/s22plus_m5b_mount_reboot_live_gate_20260707T043512Z/s22plus_m5b_mount_reboot_live_gate.txt
```

Post-rollback Android verification:

```text
adb device             SM-S906N/g0q
sys.boot_completed     1
init.svc.bootanim      stopped
verifiedbootstate      orange
Magisk root            uid=0(root) context=u:r:magisk:s0
boot hash              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained evidence was absent:

```text
post_rollback_pstore_files=[]
post_rollback_pstore_marker_found=0
post_rollback_last_kmsg_marker_found=0
post_rollback_retained_marker_found=0
```

## Interpretation

This result is a live NO-GO for M5B. It does not prove whether `/init` reached
the kmsg marker, the VFS mount sequence, or the `reboot(..., "download")`
syscall. It proves only that the candidate did not return through any
host-visible transport and therefore cannot be treated as a successful
freestanding mount/reboot proof.

This does not override the later host-side M5 root-cause steer that redirects
the design toward M6 full-substrate module replay. The operational recovery
precondition is now satisfied; any M6 live use still requires a fresh
SHA-pinned `AGENTS.md` M6 exception and the guarded M6 helper.

## Required Recovery

Manual operator action was completed:

1. Force the phone into Samsung download mode.
2. Confirm the screen is in the final `Downloading...` state, not only the
   warning/continue screen.
3. Once `/usr/bin/odin4 -l` shows exactly one device, run the checked rollback
   helper:

   ```text
   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
     workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py \
     --rollback-from-download \
     --ack S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD
   ```

4. After Android returns, verify:

   ```text
   sys.boot_completed=1
   init.svc.bootanim=stopped
   Magisk root available
   boot hash = 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
   ```

5. Collect retained pstore/last_kmsg through the rollback helper and record
   whether `S22_NATIVE_INIT_MOUNT_REBOOT_M5B` appears.

## Stop Rule

The M5B no-transport incident is recovered. Do not repeat M5B. The next
candidate remains M6, but M6 is not live-authorized until a fresh SHA-pinned
`AGENTS.md` boot-only exception is added for its exact hashes.
