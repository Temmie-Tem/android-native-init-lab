# Native Init V866 Helper v134 Deploy Report

## Result

V866 completed as deploy-only.

| Unit | Evidence | Decision |
|---|---|---|
| plan | `tmp/wifi/v866-execns-helper-v134-plan/manifest.json` | `execns-helper-v134-deploy-plan-ready` |
| preflight | `tmp/wifi/v866-execns-helper-v134-preflight/manifest.json` | `execns-helper-v134-deploy-preflight-ready` |
| deploy retry r3 | `tmp/wifi/v866-execns-helper-v134-deploy-r3/manifest.json` | `execns-helper-v134-deploy-pass` |
| post health | `tmp/wifi/v866-post-health/` | selftest/checksum/actor-clean pass |

## Deploy Details

- target: `/cache/bin/a90_android_execns_probe`
- method: serial appendfile + uudecode
- safe chunk size: `1850`
- chunks written: `788`
- encoded bytes: `1456699`
- remote sha256:
  `92792fb954de42825d328c047498c5291be803185d9897d22dd734fd9bd77582`
- helper marker: `a90_android_execns_probe v134`
- new mode present:
  `wifi-companion-peripheral-manager-init-contract-start-only`

Two earlier retries failed before writing chunks because the requested serial
chunk size exceeded the native console line limit:

| Run | Chunk | Result |
|---|---:|---|
| `tmp/wifi/v866-execns-helper-v134-deploy/` | `3000` | blocked by line check, chunks written `0` |
| `tmp/wifi/v866-execns-helper-v134-deploy-r2/` | `1900` | blocked by line check, chunks written `0` |
| `tmp/wifi/v866-execns-helper-v134-deploy-r3/` | `1850` | pass |

## Post-deploy Health

Post-deploy read-only checks:

- selftest: `pass=11 warn=1 fail=0`
- actor process count for service-manager/PM/mdm/CNSS/Wi-Fi actors: `0`
- Wi-Fi link count: `0`
- daemon start executed by deploy wrapper: `False`
- Wi-Fi bring-up executed by deploy wrapper: `False`

## Guardrails Held

- No `pm-service`, `pm-proxy`, `pm_proxy_helper`, `mdm_helper`, `ks`, CNSS,
  Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up, credentials,
  DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem write, module load/unload,
  boot image write, or partition write.
- Mutation was limited to `/cache/bin/a90_android_execns_probe` plus temporary
  `/cache/a90-runtime/bin` staging files cleaned by the deploy flow.

## Next

Proceed to V867 bounded PeripheralManager init-contract start-only proof using
helper `v134`. V867 may start only `pm_proxy_helper`, `per_mgr`, and
`per_proxy` under Android node parity. `mdm_helper`, `ks`, Wi-Fi HAL,
scan/connect, DHCP/routes, credentials, and external ping remain blocked.
