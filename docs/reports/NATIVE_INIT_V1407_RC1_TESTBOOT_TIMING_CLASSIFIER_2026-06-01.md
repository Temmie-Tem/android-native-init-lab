# Native Init V1407 RC1 Test-Boot Timing Classifier

## Summary

- Cycle: `V1407`
- Type: host-only RC1 test-boot timing classifier
- Decision: `v1407-test-boot-rc1-trigger-still-late-no-l0`
- Result: PASS for host-only classification; still BLOCKED for Wi-Fi connect readiness
- Reason: V1406 boot-time debugfs makes the corrected RC1 path reachable, but the trigger still lands in the same late timing class as V1391 and RC1 fails before L0.
- Evidence: `tmp/wifi/v1407-rc1-testboot-timing-classifier`

## Timing Comparison

| Path | esoc0→assert | release→success/fail | L0 | link fail |
|---|---:|---:|---|---|
| Android reference | 0.254929s | 0.016666s to L0 | yes | no |
| V1391 early observer | 3.604570s | 0.110837s to fail | no | yes |
| V1406 test boot | 3.597881s | 0.108666s to fail | no | yes |

## Classification

- `trigger_late_vs_android`: `True`
- `v1406_same_late_class_as_v1391`: `True`
- `v1406_trigger_delta_basis`: `esoc0_to_test11_sec`
- `v1406_extra_esoc0_to_assert_vs_android_sec`: `3.342952`
- `v1406_esoc0_to_assert_ratio_vs_android`: `14.113`
- `link_failed_no_l0`: `True`

V1406 proves debugfs availability is no longer the blocker. The remaining
difference is timing/endpoint readiness: the corrected RC1 write still occurs
seconds after `esoc0`, while Android reaches the RC1 assert window in roughly
a quarter second and reaches L0 immediately after reset release.

## Safety Scope

This cycle is host-only. It executes no device command, flash, Wi-Fi scan/connect,
credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, or blind
eSoC notify/`BOOT_DONE` spoof.

## Next

V1408 source/build-only: split corrected RC1 trigger into a tiny PID1-started parallel watcher that does no service snapshots and writes debugfs immediately after the first esoc0/powerup condition.
