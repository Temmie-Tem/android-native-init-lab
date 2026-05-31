# Native Init V1375 Execns Helper v282 Deploy Preflight

## Summary

- Cycle: `V1375`
- Type: deploy-only helper preflight
- Script: `scripts/revalidation/wifi_execns_helper_v282_deploy_preflight_v1375.py`
- Remote helper: `/cache/bin/a90_android_execns_probe`
- Helper: `a90_android_execns_probe v282`
- SHA256: `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`
- Decision: `execns-helper-v282-deploy-pass`
- Result: PASS
- Device mutation: replacing `/cache/bin/a90_android_execns_probe` only
- No daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write occurred.

## Result Matrix

| field | value |
| --- | --- |
| decision | `execns-helper-v282-deploy-pass` |
| pass | `true` |
| remote sha verified | `true` |
| helper usage marker checked | `true` |
| post selftest | `pass` |
| deploy method | `serial` |
| serial chunks | `1061` |
| serial chunk size | `1800` |
| max cmdv1 line bytes | `3786` |
| device mutations | `true` |
| daemon start executed | `false` |
| wifi bringup executed | `false` |

## Transfer Notes

- NCM was inactive, so `auto` transfer selected serial fallback.
- A first `--serial-chunk-size 3000` attempt was rejected by the wrapper before transfer because the encoded cmdv1x line exceeded the safe console line limit.
- The successful run used `--serial-chunk-size 1800`, `1061` chunks, and max cmdv1 line bytes `3786` below safe limit `3968`.

## Post-Deploy Evidence

- `tmp/wifi/v1375-execns-helper-v282-deploy/manifest.json`
- `tmp/wifi/v1375-execns-helper-v282-deploy/post-deploy-steps.json`
- `tmp/wifi/v1375-execns-helper-v282-deploy/host/serial-install-helper.txt`
- `tmp/wifi/v1375-execns-helper-v282-deploy/native/sha-helper.txt`
- `tmp/wifi/v1375-execns-helper-v282-deploy/native/helper-usage.txt`

## Next Gate

V1376 may run the bounded Android participant parity + corrected RC1 enumerate gate using helper v282. It must remain below Wi-Fi HAL/scan/connect/network and must treat transport loss as reboot/recovery evidence, not success.
