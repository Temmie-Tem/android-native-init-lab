# Native Init V1445 Wi-Fi Test Boot Case-Aligned Micro Endpoint Source Build

## Summary

- Cycle: `V1445`
- Type: source/build-only Wi-Fi test boot artifact
- Decision: `v1445-wifi-test-boot-case-aligned-micro-endpoint-source-build-pass`
- Result: PASS
- Reason: built a rollbackable test boot that starts micro endpoint sampling only after the corrected RC1 `case=11` write has returned
- Manifest: `tmp/wifi/v1445-wifi-test-boot-case-aligned-micro-endpoint-sampler/manifest.json`

## Artifact

- Boot image: `tmp/wifi/v1445-wifi-test-boot-case-aligned-micro-endpoint-sampler/boot_linux_v1445_wifi_test.img`
- Native init: `0.9.82 (v1445-wifitest)`
- Init SHA256: `9d8939df668270cfac9f8ae1b1ea06e895ee3a0a40c061b7e6933129e7811148`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- Ramdisk SHA256: `809b1ebde856f9658bb3a1341737ace400bb4a5d60121b549094eb7b3c7765f1`
- Boot SHA256: `90335a2fc0ffdc701d1f5f92cab4ec3cfc7742eef8a56e00f9a90039bb86cd3a`

## Instrumentation Contract

- Adds `read-only-v1445-case-aligned-micro-endpoint`.
- Keeps the RC1 endpoint sampler and micro sampler gates enabled.
- Forks a writer child for corrected `rc_sel=2` and `case=11`.
- Waits for the writer to return, records `rc1_micro_writer_summary`, then starts parent sampling at `0ms`, `1ms`, `2ms`, `5ms`, `10ms`, `20ms`, `50ms`, `100ms`, and `150ms` after confirmed case completion.
- Emits labels `case_aligned_micro_after_case_%dms` and keeps the same narrow active-window fields as V1441: selected interrupts, exact endpoint GPIOs, and pcie1 link-state files.
- Keeps a single slower `post_case_aligned_micro_200ms` context sample after the active window.
- Preserves the existing `250ms` delay before corrected RC1 entry and does not add retries.

## Validation

- Static aarch64 init and helper build completed.
- Ramdisk and boot image repack completed from `stage3/boot_linux_v724.img`.
- Marker verification passed for `A90v1445`, `read-only-v1445-case-aligned-micro-endpoint`, `rc1_case_aligned_micro_endpoint_sampler_requested`, `case_aligned_micro_after_case_%dms`, and `post_case_aligned_micro_200ms`.
- Manifest records `rc1_case_aligned_micro_endpoint_sampler=true`, `rc1_micro_endpoint_sampler=true`, `rc1_endpoint_sampler=true`, `rc1_immediate_endpoint_sampler=false`, `rc1_focused_endpoint_sampler=false`, and `rc1_retry_count=0`.
- No live command, flash, reboot, partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, or external ping occurred.

## Next

V1446 should perform local-only artifact sanity over the exact V1445 manifest,
boot image, marker contract, v724 header/kernel parity, static binaries,
private modes, and forbidden credential-like byte absence before any live
handoff.
