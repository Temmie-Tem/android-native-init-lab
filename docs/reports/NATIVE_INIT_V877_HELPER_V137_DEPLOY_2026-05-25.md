# V877 Helper v137 Deploy-only Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v877-execns-helper-v137-plan/manifest.json` | `execns-helper-v137-deploy-plan-ready` |
| preflight | `tmp/wifi/v877-execns-helper-v137-preflight/manifest.json` | `execns-helper-v137-deploy-preflight-ready` |
| deploy | `tmp/wifi/v877-execns-helper-v137-deploy-preflight/manifest.json` | `execns-helper-v137-deploy-pass` |

V877 deployed helper `v137` to `/cache/bin/a90_android_execns_probe`. It did
not start Android actors, did not execute live eSoC ioctls, and did not bring up
Wi-Fi.

## Deploy Details

| Item | Value |
| --- | --- |
| method | serial appendfile + uudecode |
| chunk size | `1850` |
| chunks written | `788` |
| encoded bytes | `1456699` |
| max cmdv1 line bytes | `3890` |
| safe line limit | `3968` |
| uses cmdv1x | `true` |

Remote helper:

```text
e47eb52b0b2b2fb601fdbc4ecebdf72e2fda9519eac37e776d62c11d2d469aa3  /cache/bin/a90_android_execns_probe
```

Usage output includes:

- `a90_android_execns_probe v137`
- `wifi-companion-esoc-engine-register-preflight`
- `--allow-esoc-engine-register-preflight`

Post-deploy health:

- `selftest` stayed `fail=0`.
- service-manager process hits: `0`
- Wi-Fi netdev hits: `0`

## Guardrails

- No `REG_CMD_ENG`, `REG_REQ_ENG`, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`,
  `NOTIFY`, or `/dev/subsys_esoc0` open.
- No actor start, no `mdm_helper`, no `ks`, no `pm_proxy_helper`, no CNSS, no
  service-manager trio, and no Wi-Fi HAL.
- No scan/connect, credentials, DHCP/routes, or external ping.

## Next

Run V878 bounded live `REG_CMD_ENG`/`REG_REQ_ENG` registration preflight only.
