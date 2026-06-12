# Native Init V2255 Wi-Fi Detail Surface Live

## Summary

- Cycle: `V2255`
- Track: T2 WLAN native-init surface/cleanup.
- Type: rollbackable live validation of V2254 Wi-Fi detail status surface.
- Decision: `v2255-wifi-detail-surface-live-pass`
- Result: `PASS`
- Reason: V2254 exposed read-only route/DNS status fields and screenapp wifi-status presented; rollback selftest fail=0 passed
- Execute mode: `True`
- Evidence: `workspace/private/runs/wifi/v2255-wifi-detail-surface-live-20260612-135207`

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img`
- Test SHA256: `c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9`
- Test version: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- Rollback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Rollback version: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`
- Known-good fallback image present: `True`

## Live Evidence

- Preflight baseline verified: `True` selftest fail=0: `True`
- V2254 flash OK: `True`
- V2254 health: version=`True` status=`True` selftest_fail0=`True`
- V2254 version match source: `status_fallback`
- `wifi status` OK: `True` all V2254 fields present: `True`
- `screenapp wifi-status` OK: `True` presented=`1`
- Rollback OK: `True` via `from-native`
- Rollback health: version=`True` status=`True` selftest_fail0=`True`

## Status Field Classification

- `default_route_present`: present=`True` value=`0`
- `gateway_label`: present=`True` value=`none`
- `gateway_rc`: present=`True` value=`-2`
- `resolv_conf.present`: present=`True` value=`0`
- `resolv_conf.nameserver_count`: present=`True` value=`0`

- secret_values_logged: `0`
- gateway_masked: `1`
- forbidden scan/connect/DHCP/ping markers: `{'connect': False, 'dhcp': False, 'ping': False, 'scan': False}`

## Interpretation

- V2254's read-only `wifi status` surface exposes route/default-DNS detail without needing scan/connect/DHCP/ping.
- The on-device `NETWORK > WIFI STATUS` path is reachable through `screenapp wifi-status` and presented successfully.
- Public report values remain metadata-only; private stdout artifacts retain the raw command output under `workspace/private/**`.
- Next T2 unit can either promote V2254 after an explicit baseline decision, or continue with remaining test-script cleanup if promotion is deferred.

## Safety Scope

- Flash path is limited to boot partition via `native_init_flash.py`.
- Rollback target is V2237, with post-rollback `version`/`status`/`selftest fail=0` verification.
- Live observations are limited to `wifi status` and `screenapp wifi-status`.
- This run does not use Wi-Fi scan/connect, credentials, DHCP/routes, external ping, `probe_write_user`, tracefs control writes, eSoC/PCIe/GDSC/PMIC/GPIO paths, platform bind/unbind, or `sda29` writes.
