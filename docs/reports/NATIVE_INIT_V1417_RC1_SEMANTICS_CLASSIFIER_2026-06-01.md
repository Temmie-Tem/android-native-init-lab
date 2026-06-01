# Native Init V1417 RC1 Semantics Classifier

## Summary

- Cycle: `V1417`
- Type: host-only RC1 semantics classifier
- Decision: `v1417-delayed-rc1-timing-aligned-filtered-dmesg-recapture-needed`
- Result: PASS for classification; still BLOCKED for Wi-Fi connect readiness
- Reason: V1416 aligns corrected RC1 timing with Android within 50ms and still fails before L0, but the V1416 dmesg grep pattern omitted endpoint reset/release markers; their absence is therefore not proven.
- Evidence: `tmp/wifi/v1417-rc1-semantics-classifier`

## Timing Comparison

| Path | esoc0→trigger | reset/release markers | L0 | link fail |
|---|---:|---|---|---|
| Android reference | 0.254929s | assert+release present | yes | no |
| V1413 immediate kmsg watcher | 0.032082s | not required for this classifier | no | yes |
| V1416 delayed kmsg watcher | 0.275121s | unproven-filtered | no | yes |

## Classification

- `v1416_trigger_error_vs_android_sec`: `0.020192`
- `v1416_timing_aligned_with_android_50ms`: `True`
- `v1416_dmesg_filter_includes_reset_markers`: `False`
- `v1416_reset_markers_absent_in_filtered_evidence`: `True`
- `v1416_reset_marker_absence_proven`: `False`
- `v1416_link_failed_no_l0`: `True`
- `v1416_test11_to_phy_ready_sec`: `0.005814`
- `v1416_test11_to_link_failed_sec`: `0.11479`

V1416 removes the major timing objection from V1413: the corrected RC1
action now lands close to the Android reference window. The remaining
difference that remains proven is link behavior: V1416 reaches
PHY/LTSSM but stalls in poll-compliance. Reset/release marker absence
is not proven because the V1416 dmesg capture was filtered without those
patterns.

## Safety Scope

This cycle is host-only. It executes no device command, flash, Wi-Fi
scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC write, or blind eSoC notify/`BOOT_DONE` spoof.

## Next

V1418 should rerun the same V1414 test image with an expanded dmesg pattern that includes endpoint reset/release and PCIE20_PARF_INT markers before changing timing or trigger design.
