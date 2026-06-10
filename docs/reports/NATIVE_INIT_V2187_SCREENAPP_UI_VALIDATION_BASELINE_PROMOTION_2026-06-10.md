# Native Init V2187 Screenapp UI Validation Baseline Promotion

## Summary

- Promoted baseline: `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`.
- Run/build identity: `V2187`.
- Decision: `v2187-screenapp-ui-validation-baseline-promotion-pass`.
- Result: PASS.
- Rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`.
- Rollback boot SHA256:
  `0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca`.
- Previous baseline: `A90 Linux init 0.9.258 (v2186-wifi-ui-polish)`.

## Promotion Basis

- Source build passed:
  `docs/reports/NATIVE_INIT_V2187_SCREENAPP_UI_VALIDATION_SOURCE_BUILD_2026-06-10.md`.
- Live validation passed:
  `docs/reports/NATIVE_INIT_V2187_SCREENAPP_UI_VALIDATION_LIVE_2026-06-10.md`.
- Final promotion flash passed after the V2186 rollback proof:
  - local, pushed, and boot-partition readback SHA matched
    `0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca`;
  - booted `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`;
  - post-boot `status` reported selftest `fail=0`;
  - `transport.contract=1`, `tcpctl=ready`, and SD-backed runtime remained
    present.
- Passing private evidence directory:
  `tmp/wifi/runs/v2187-screenapp-ui-validation-p1-screenapp-clean-20260610-103339`.

## Promoted Contract

- Future rollback should target V2187 unless a test explicitly requires an older
  fallback.
- V2187 preserves the V2169+ boot/bridge/transport contract and the V2186 Wi-Fi
  status/ping behavior.
- V2187 promotes `screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping]`
  as the baseline dev-display validation command.
- Public artifacts must continue to omit raw SSID, BSSID, PSK, private IP,
  gateway, and peer MAC details.

## Residual Work

- Physical button/OCR validation of `NETWORK > WIFI STATUS` and
  `NETWORK > PING TEST` remains optional polish.
- Longer N-run or multi-hour Wi-Fi/data-path soak remains optional hardening, not
  a blocker for this promotion.

## Safety Scope

- `screenapp wifi-status` and `screenapp wifi-profiles` are read-only.
- `screenapp wifi-ping` is explicit and bounded; it does not connect, run DHCP,
  or read credentials.
- No PMIC/GPIO/GDSC/regulator writes, eSoC notify/BOOT_DONE, PCI rescan,
  platform bind/unbind, or `/dev/subsys_esoc0` path is included.
