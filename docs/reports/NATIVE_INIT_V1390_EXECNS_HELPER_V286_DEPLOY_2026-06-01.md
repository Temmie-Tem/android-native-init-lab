# Native Init V1390 Execns Helper v286 Deploy Preflight

## Summary

- Cycle: `V1390`
- Type: deploy/preflight-only helper update
- Script: `scripts/revalidation/wifi_execns_helper_v286_deploy_preflight_v1390.py`
- Remote helper: `/cache/bin/a90_android_execns_probe`
- Helper: `a90_android_execns_probe v286`
- SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- Decision: `execns-helper-v286-deploy-pass`
- Result: PASS
- Device mutation: replacing `/cache/bin/a90_android_execns_probe` only
- No daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write occurred.

## Result Matrix

| field | value |
| --- | --- |
| decision | `execns-helper-v286-deploy-pass` |
| pass | `true` |
| remote sha verified | `true` |
| helper usage marker checked | `true` |
| helper early-observer flag checked | `true` |
| post selftest | `pass` |
| deploy method | `serial` |
| serial chunks | `1061` |
| serial chunk size | `1800` |
| max cmdv1 line bytes | `3788` |
| device mutations | `true` |
| daemon start executed | `false` |
| wifi bringup executed | `false` |
| V373 post-deploy preflight | `service-manager-start-only-smoke-approval-required` |

## Transfer Notes

- NCM was not reachable during preflight, so `auto` transfer selected serial fallback.
- V1390 used the proven safe `--serial-chunk-size 1800` path.
- The serial transfer wrote `1061` chunks, used cmdv1x appendfile + uudecode, and kept max encoded line size `3788` below the safe limit `3968`.

## Post-Deploy Native Steps

| step | result | rc | status | file |
| --- | --- | --- | --- | --- |
| version | PASS | 0 | ok | `native/version.txt` |
| status | PASS | 0 | ok | `native/status.txt` |
| selftest | PASS | 0 | ok | `native/selftest.txt` |
| netservice-status | PASS | 0 | ok | `native/netservice-status.txt` |
| stat-helper | PASS | 0 | ok | `native/stat-helper.txt` |
| sha-helper | PASS | 0 | ok | `native/sha-helper.txt` |
| helper-usage | FAIL | 2 | error | `native/helper-usage.txt` |
| ps | PASS | 0 | ok | `native/ps.txt` |
| proc-net-dev | PASS | 0 | ok | `native/proc-net-dev.txt` |

Note: `helper-usage` exits non-zero when invoked without a full mode, but it printed the v286 marker and early-observer corrected RC1 flag required for deploy verification.

## Evidence

- `tmp/wifi/v1390-execns-helper-v286-deploy/manifest.json`
- `tmp/wifi/v1390-execns-helper-v286-deploy/post-deploy-steps.json`
- `tmp/wifi/v1390-execns-helper-v286-deploy/host/serial-install-helper.txt`
- `tmp/wifi/v1390-execns-helper-v286-deploy/native/sha-helper.txt`
- `tmp/wifi/v1390-execns-helper-v286-deploy/native/helper-usage.txt`
- `tmp/wifi/v1390-execns-helper-v286-deploy/v373-preflight/manifest.json`

## Next Gate

V1391 may run the bounded Android participant parity + early-observer corrected RC1 live gate using helper v286. It must remain below Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, flash, boot image write, and partition write.
