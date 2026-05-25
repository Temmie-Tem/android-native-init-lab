# V870 Helper v135 Deploy-only Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v870-execns-helper-v135-plan/manifest.json` | `execns-helper-v135-deploy-plan-ready` |
| preflight | `tmp/wifi/v870-execns-helper-v135-preflight/manifest.json` | `execns-helper-v135-deploy-preflight-ready` |
| deploy | `tmp/wifi/v870-execns-helper-v135-deploy/manifest.json` | `execns-helper-v135-deploy-pass` |
| post health | `tmp/wifi/v870-post-health/manifest.json` | PASS |

V870 deployed helper `v135` to `/cache/bin/a90_android_execns_probe`. It did not
start Android actors and did not bring up Wi-Fi.

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
ad1bbbf295be61ef612406091ccd469c4ef45ab44c0f753c4de034e487ddaad1  /cache/bin/a90_android_execns_probe
```

Usage output includes:

- `a90_android_execns_probe v135`
- `wifi-companion-esoc-control-preflight`

## Post-health

| Check | Result |
| --- | --- |
| selftest | `pass=11 warn=1 fail=0` |
| helper SHA | pass |
| helper marker | pass |
| helper mode token | pass |
| actor hits | `0` |
| Wi-Fi link hits | `0` |

Post-health evidence:

- `tmp/wifi/v870-post-health/version.txt`
- `tmp/wifi/v870-post-health/selftest.txt`
- `tmp/wifi/v870-post-health/helper-sha.txt`
- `tmp/wifi/v870-post-health/helper-usage.txt`
- `tmp/wifi/v870-post-health/ps.txt`
- `tmp/wifi/v870-post-health/proc-net-dev.txt`

## Guardrails

- No `mdm_helper`, no `ks`, no `pm_proxy_helper`, no service-manager trio, no
  CNSS, no Wi-Fi HAL.
- No scan/connect, credentials, DHCP/routes, or external ping.
- No live eSoC control preflight, no `REG_REQ_ENG`, no `REG_CMD_ENG`, no
  `CMD_EXE`, no `WAIT_FOR_REQ`, no `NOTIFY`, no `PWR_ON`.
- No module load/unload, boot image write, partition write, or firmware
  mutation.

## Next

V871 can be a bounded live eSoC control preflight with helper `v135`, limited to
node visibility and read-only eSoC status ioctls. Mutating eSoC state-machine
steps remain blocked until a later gate.
