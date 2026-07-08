# S22+ M25 HS-Only USB2 ACM Live Result (2026-07-08)

## Summary

M25 was live-executed and consumed its one-shot authorization. It did not expose
the expected ACM control channel. The candidate returned to Odin/Download during
bounded observation, Magisk boot rollback was flashed, stock DTBO was restored,
and the device ended back on the clean Android/Magisk baseline.

Final result:

```text
M25 ACM: no-hit
rollback: complete
final Android: boot_completed=1, bootanim=stopped, verifiedbootstate=orange
final Magisk root: uid=0(root)
```

## Runs

Dry-run:

```text
workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T122344Z/
```

Live run:

```text
workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T122411Z/
```

Stock-DTBO restore run:

```text
workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T122816Z/
```

## Live Sequence

The helper flashed the pinned M25 DTBO high-speed cap:

```text
m25_dtbo_candidate_odin_rc=0
```

Android/Magisk returned after the DTBO flash, and the helper verified the
patched DTBO hash:

```text
8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17
```

The helper then flashed the pinned M25 boot AP. Bounded observation found no
M25 ACM endpoint:

```text
m25_observe_*_acm_devices=[]
```

At observation sample 30, Odin/Download appeared:

```text
m25_odin_returned=1 device=/dev/bus/usb/002/016
```

The helper flashed the pinned Magisk boot rollback AP:

```text
magisk_boot_rollback_odin_rc=0
```

The operator reported bootloop/manual Download coordination while the helper was
waiting for post-rollback Android. Codex interrupted that wait after the Magisk
boot rollback had already completed, then observed Android ADB return and used
the checked helper's `--restore-dtbo-from-android` mode to restore stock DTBO.

## Stock-DTBO Restore

The restore helper confirmed DTBO was still the patched M25 DTBO before
rollback:

```text
pre_stock_dtbo_restore_dtbo_hash_rc=0
8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17  /dev/block/by-name/dtbo
```

It rebooted to Download mode and flashed the pinned stock-DTBO rollback AP:

```text
stock_dtbo_rollback_odin_rc=0
```

After Android returned, it verified stock DTBO:

```text
stock_restore_dtbo_hash_rc=0
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c  /dev/block/by-name/dtbo
```

The stock-DTBO restore timeline is canonical and complete:

```text
live_session_start
dtbo_rollback_flash_start
dtbo_rollback_flash_done
dtbo_rollback_boot_ready
live_session_end
```

The first live-run timeline is canonical but intentionally incomplete because
the helper was interrupted after Magisk boot rollback while waiting for Android:

```text
live_session_start
dtbo_candidate_flash_start
dtbo_candidate_flash_done
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
```

## Final Baseline

Final live checks:

```text
boot_completed=1
bootanim=stopped
verifiedbootstate=orange
su uid=0(root)
```

Final partition hashes:

```text
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

## Interpretation

M25 avoided the QMP/USB3 module by using the HS-only DTBO cap and 40-module
USB2 closure, but it still did not produce the target ACM endpoint. The useful
new fact is that the candidate reached a bounded Download/Odin recovery surface
after boot candidate flash, allowing Magisk boot rollback.

The M25 one-shot AGENTS exception is consumed and must not be reused. The next
bounded unit should be a host-only postmortem and next-candidate design from the
M25 no-ACM result before requesting any new live exception.
