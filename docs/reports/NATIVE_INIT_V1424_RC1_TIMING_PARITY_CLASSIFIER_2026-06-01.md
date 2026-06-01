# Native Init V1424 RC1 Timing Parity Classifier

## Summary

- Cycle: `V1424`
- Type: host-only/read-only classifier over existing Android and native evidence
- Decision: `v1424-rc1-timing-precondition-parity-but-endpoint-no-l0`
- Result: PASS
- Reason: RC1 trigger/reset/release timing is close enough to Android; native diverges after PERST release when the endpoint fails to reach L0
- Android input: `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt`
- Native input: `tmp/wifi/v1422-wifi-test-boot-rc1-window-sampler-handoff/test-v1393-dmesg.stdout.txt`

## Timing Comparison

| Signal | Android V852 | Native V1422 |
| --- | --- | --- |
| esoc0 to RC1 assert | `254.929ms` | `287.384ms` |
| assert to release | `7.196ms` | `5.756ms` |
| release to terminal state | L0 in `16.666ms` | fail in `109.086ms` |
| L0 | `True` | `False` |
| link failed | `False` | `True` |
| downstream Wi-Fi | BDF/FW-ready/`wlan0` present | downstream absent `True` |

## Classification

- esoc-to-assert gap: `32.455ms`
- timing close within 50ms: `True`
- RC1 INT mask parity: `True`
- native reset path present: `True`
- V1422 RC1-window sample count valid: `True`

The native test boot no longer looks primarily blocked by a too-early or
too-late RC1 trigger. The assert/release path is close to Android and uses
the same RC1 INT mask. The divergence is after PERST release: Android reaches
L0 quickly, while native enters poll-active/poll-compliance and fails before
L0, with no MHI/WLFW/BDF/FW-ready/`wlan0`.

## Safety Scope

This cycle was host-only. It did not run device commands, flash, reboot,
write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,
ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/BOOT_DONE,
run global PCI rescan, or bind/unbind platform devices.

## Next

V1425 should target the post-release endpoint-response gap. The safest next
implementation is a source/build-only higher-resolution read-only sampler
around RC1 release and link failure, or a narrowly planned rollbackable test
that changes only the RC1 timing/retry policy after documenting why repeated
case writes are still below Wi-Fi scan/connect.
