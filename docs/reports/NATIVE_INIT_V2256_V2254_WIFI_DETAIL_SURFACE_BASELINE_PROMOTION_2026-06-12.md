# Native Init V2256 V2254 Wi-Fi Detail Surface Baseline Promotion

Date: `2026-06-12`

## Summary

V2256 promotes the V2254 Wi-Fi detail surface build as the current native-init
rollback/test baseline.

- Decision: `v2256-v2254-wifi-detail-surface-baseline-promotion-pass`
- Promoted baseline: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img`
- Boot SHA256: `c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9`
- Builder: `workspace/public/src/scripts/revalidation/build_native_init_boot_v2254_wifi_detail_surface.py`
- Source root: `workspace/public/src/native-init/`
- Helper marker: `a90_android_execns_probe helper-v427`
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`
- Previous verified rollback artifact: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- Known-good fallback: `workspace/private/inputs/boot_images/boot_linux_v48.img`

## Evidence

- V2254 source/build report:
  `docs/reports/NATIVE_INIT_V2254_WIFI_DETAIL_SURFACE_SOURCE_BUILD_2026-06-12.md`
- V2255 live validation report:
  `docs/reports/NATIVE_INIT_V2255_WIFI_DETAIL_SURFACE_LIVE_2026-06-12.md`
- V2255 private evidence root:
  `workspace/private/runs/wifi/v2255-wifi-detail-surface-live-20260612-135207`

V2255 rollbackably flashed V2254, validated `version`/`status`/`selftest`,
queried `wifi status`, presented `screenapp wifi-status`, and rolled back to
V2237 with `selftest fail=0`.

## Promotion Scope

V2254 keeps the V2237 Wi-Fi lifecycle route and adds a read-only detail surface:

- `default_route_present`
- redacted `gateway_label`
- `gateway_rc`
- `resolv_conf.present`
- `resolv_conf.nameserver_count`
- `NETWORK > WIFI STATUS` route/default-DNS rendering

The V2255 live validation intentionally did not perform scan, connect, DHCP,
ping, route mutation, or credential handling.

## Accepted Notes

- The immediate V2255 `version` command stdout missed the banner once, but
  `native_init_flash.py` and the `status` health output both verified
  `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`.
- V2237 remains the previous verified rollback artifact for conservative
  regression comparisons.
- Long idle/hold data-path stability remains separate follow-up evidence, not
  a blocker for this baseline promotion.

## Decision

Use `v2254-wifi-detail-surface` as the current native-init rollback/test
baseline for future bounded Wi-Fi lifecycle and command-surface work unless a
test explicitly targets an older rollback artifact.
