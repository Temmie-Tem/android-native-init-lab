# S22+ Native-Init M26 HS Prefix-Download Live Result (2026-07-08)

## Verdict

M26 live was partially successful and safely recovered.

- `P00`: HIT. Candidate disconnected from original Odin endpoint and later
  returned as Odin/Download. This proves the M26 direct PID1 runtime can reach
  the checkpoint and request `reboot(download)` under the M25 DTBO high-speed
  cap.
- `P24`: NO-HIT. Candidate did not return as Odin/Download within the bounded
  observation window and required operator manual Download-mode recovery.
- Final baseline: CLEAN. Android booted, Magisk root was present, and boot,
  dtbo, and vendor_boot hashes matched the expected baseline.

## Timeline

Main live run:

- Run directory:
  `workspace/private/runs/s22plus_m26_hs_prefix_download_live_gate_20260708T125954Z`
- DTBO high-speed cap flash: started `13:00:17Z`, done `13:00:18Z`.
- Patched DTBO Android boot ready: `13:00:51Z`.
- `P00` flash: started `13:01:03Z`, done `13:01:04Z`.
- `P00` self-download observed: `13:01:39Z`.
- `P00` Magisk boot rollback: started `13:01:39Z`, done `13:01:40Z`.
- `P00` rollback Android boot ready: `13:03:10Z`.
- `P24` flash: started `13:03:22Z`, done `13:03:24Z`.
- `P24` observation ended with no self-download: `13:04:11Z`.

Manual rollback run:

- Run directory:
  `workspace/private/runs/s22plus_m26_hs_prefix_download_live_gate_20260708T130754Z`
- Manual Download endpoint detected: `/dev/bus/usb/002/024`.
- Magisk boot rollback: started `13:07:54Z`, done `13:07:56Z`.
- Android boot ready after boot rollback: `13:08:41Z`.
- Stock DTBO rollback: started `13:08:53Z`, done `13:08:54Z`.
- Android returned after stock DTBO rollback.

## Final Baseline

Manual final verification used `toybox sha256sum` because plain `sha256sum`
returned permission errors against block devices on this Android baseline.

```text
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
boot_completed=1
bootanim=stopped
vbstate=orange
Magisk root present
```

## Interpretation

`P00` removes module loading from the equation and proves the raw runtime,
ramdisk packaging, DTBO high-speed cap, and reboot-download path are viable.

`P24` fails before the checkpoint. The fault is therefore in the first 24
entries of the inherited M25 HS-only module closure, not in the later USB
function/configfs path and not in the basic `reboot(download)` syscall path.

Next unit should be host-only M27 with a narrower prefix matrix between `P00`
and `P24`, for example `P08/P12/P16/P20/P22/P23/P24`, then one fresh
SHA-pinned live exception for that smaller discriminator. Do not repeat M26
unchanged and do not jump to `P25+` until the `P00..P24` boundary is narrowed.

## Tooling Fix

The rollback helper exited with a false-negative final DTBO verification:
stock DTBO was restored, but the helper's shared partition hash command tried
plain `sha256sum` first and did not capture a usable block-device hash. Manual
`toybox sha256sum` immediately verified the expected stock DTBO hash. The shared
`read_partition_hash()` helper now prefers `toybox sha256sum` and falls back to
plain `sha256sum`.
