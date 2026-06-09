# Native Init V2185 Network Ping Baseline Promotion

## Summary

- Promoted baseline: `A90 Linux init 0.9.257 (v2185-network-ping-test)`.
- Promotion decision: `v2185-network-ping-baseline-promotion-pass`.
- Result: PASS.
- Rollback image for the next work cycle:
  `workspace/private/inputs/boot_images/boot_linux_v2185_network_ping_test.img`.
- Boot SHA256:
  `3ab13707c4ad93cb0b23c26174407be9a0ca30460fce879131ba6bea0df253b7`.
- Device state: V2185 remains flashed after live validation and is the current
  baseline/rollback point.

## Evidence

- Source/build report:
  `docs/reports/NATIVE_INIT_V2185_NETWORK_PING_TEST_SOURCE_BUILD_2026-06-10.md`.
- Live validation report:
  `docs/reports/NATIVE_INIT_V2185_NETWORK_PING_TEST_LIVE_VALIDATION_2026-06-10.md`.
- Private live evidence:
  `workspace/private/runs/wifi/v2185-network-ping-live-20260610-075819`.

Validated live gates:

- boot partition readback SHA matched the local V2185 image;
- `version` and `status` verified the expected init build;
- `wifi connect` reached `wifi-connect-carrier-up`;
- `wifi dhcp` reached `wifi-dhcp-pass`;
- `wifi ping all` reached `wifi-ping-pass`;
- gateway and fixed external IP ping both returned `3/3` packets with `0%`
  loss;
- `screenmenu` accepted the updated network menu;
- final `selftest fail=0`.

## Baseline Meaning

Future test cycles should use V2185 as the normal rollback target unless a run
explicitly needs an older fallback image. Older V2178 profile/autoconnect and
V2169 transport-contract images remain conservative recovery options, but they
are no longer the default rollback point.

## Residual Non-Blockers

- Physical button selection of `NETWORK > PING TEST` was not captured; CLI ping
  and `screenmenu` smoke were sufficient for this baseline promotion.
- Longer repeated external-ping soak was not run; large Wi-Fi data-path evidence
  remains covered by the V2184 phone transfer validation.
- Public reports intentionally omit private gateway, private IP, SSID, BSSID,
  MAC-derived peer details, and credentials.
