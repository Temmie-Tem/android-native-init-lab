# S22+ Native-Init M3.1 Live Result - 2026-07-07

## Scope

Ran one attended boot-only Odin live gate for the M3.1 marker-only native-init
candidate, then rolled back to the pinned Magisk boot-only AP. This run did not
touch vbmeta, recovery, userdata, EFS, modem, bootloader, or any non-boot
partition.

Private run directory:

```text
workspace/private/runs/s22plus_m31_marker_live_gate_20260706T183728Z/
```

Live command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py \
  --live \
  --ack S22PLUS-M31-MARKER-LIVE-GATE
```

## Pinned Artifacts

Candidate:

```text
workspace/private/outputs/s22plus_native_init/marker_m31_v0_1/odin4/AP.tar.md5
AP.tar.md5 SHA256: 999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb
boot.img SHA256:   f3dea68c02be295141265820f4acdd425a12460e05957edf75c83a62c4a617c5
marker init SHA256: 4ad9c013ef101528a9f6181723c8448972ea2939d78fc93107313f3b9be2e8f6
```

Rollback:

```text
workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5
AP.tar.md5 SHA256: d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
```

Fallback rollback stayed staged but was not needed:

```text
workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/AP.tar.md5
AP.tar.md5 SHA256: 1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Timeline

All timestamps are UTC from the private helper log.

| Time | Event |
| --- | --- |
| 18:37:28 | Android/Magisk preflight passed: `SM-S906N` / `g0q` / `S906NKSS7FYG8`, orange verified boot, boot completed, Magisk root. |
| 18:37:39 | Candidate download target appeared. |
| 18:37:39-18:37:41 | Odin boot-only candidate flash succeeded; transfer contained only `boot.img.lz4`. |
| 18:37:41 | Candidate observation window began; ADB absent. |
| 18:37:41-18:38:10 | No ADB device and no Odin/download target observed. |
| 18:38:12 | Odin/download target reappeared at candidate sample 16. |
| 18:38:17 | Rollback phase saw download target and started Magisk boot-only rollback. |
| 18:38:17-18:38:18 | Odin boot-only Magisk rollback succeeded; transfer contained only `boot.img.lz4`. |
| 18:38:48 | Android ADB returned; boot-completed was not yet set. |
| 18:38:52 | Android boot-completed reached `1`; Magisk root verified. |

## Result

Safety result: pass.

- Candidate boot-only flash completed.
- Device returned to download mode without physical button recovery during the
  helper window.
- Pinned Magisk boot-only rollback completed.
- Android returned with boot completed, orange verified boot, and Magisk root.
- A later manual host check again showed `boot_completed=1`, `boot_recovery=0`,
  bootreason `reboot,download`, and Magisk root.

Native-init proof result: fail.

- ADB never appeared during the candidate window.
- `/sys/fs/pstore` was empty after rollback.
- `S22_NATIVE_INIT_MARKER_ONLY_M31` was not found.
- The download-mode return happened around 31 seconds after candidate
  observation began, not as a clean 10-second proof of the programmed M3.1
  marker path.

## Interpretation

M3.1 is a recovery-success/native-proof-fail result. It proves the current
boot-only Odin rollback envelope can recover this class of failed native-init
candidate, but it does not prove the direct `/init` marker code executed.

The operator observed a bootloop/download recovery situation. The host evidence
matches that operationally: the candidate never exposed ADB, then the device
returned to download mode and was rolled back. Because no pstore marker survived,
the run cannot distinguish an early bootloader/kernel fallback from a marker path
whose pmsg/pstore evidence was not retained.

## Next Boundary

Stop live S22+ native-init flashes here. The next unit should be host-only
postmortem before another candidate:

- audit whether Samsung boot image v3 first-stage init replacement needs any
  extra ramdisk/header metadata beyond the current repack;
- compare stock/Magisk/native boot ramdisks for required init staging files,
  sepolicy expectations, and early Samsung recovery/download triggers;
- decide whether the next observable channel must be bootconfig/cmdline,
  initramfs file side effect, recovery-visible marker, or a minimal Android-init
  chainload rather than direct static `/init`.

