# V1298 Execns Helper v272 Deploy

- date: 2026-05-31
- scope: deploy-only helper update
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v272_deploy_preflight_v1298.py`
- local helper: `stage3/linux_init/helpers/a90_android_execns_probe_v272`
- remote helper: `/cache/bin/a90_android_execns_probe`
- evidence: `tmp/wifi/v1298-execns-helper-v272-deploy/manifest.json`
- result: `execns-helper-v272-deploy-pass`
- pass: `true`
- sha256: `1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885`

## Purpose

V1297 built helper `v272` with the compact dense late-`per_proxy` response
sampler. V1298 deploys that helper only, without starting PM/CNSS actors,
Wi-Fi HAL, scan/connect, DHCP/routes, or external network traffic.

## Result

Deploy passed using serial fallback:

| field | value |
|---|---|
| transfer method | `serial` |
| chunk size | `1800` |
| chunks written | `1010` |
| encoded bytes | `1817918` |
| line check | `pass` |
| max cmdv1 line bytes | `3788` |
| remote sha256 | `1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885` |
| remote marker | `a90_android_execns_probe v272` |

NCM was not reachable during preflight, so the wrapper used the serial
appendfile + `uudecode` path. Post-deploy selftest remained `pass=11 warn=1
fail=0`.

## Post-Deploy Proof

Read-only checks after deploy confirmed the remote helper:

```text
1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885  /cache/bin/a90_android_execns_probe
a90_android_execns_probe v272
--pm-observer-late-per-proxy-compact-response-sampler
```

## Safety Audit

- deploy-only: `true`
- device mutation: helper write to `/cache/bin/a90_android_execns_probe`
- daemon start: `false`
- Wi-Fi HAL start: `false`
- scan/connect/link-up: `false`
- credential use: `false`
- DHCP/route: `false`
- external ping: `false`
- flash / boot image write / partition write: `false`

## Verification

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v272_deploy_preflight_v1298.py
python3 scripts/revalidation/wifi_execns_helper_v272_deploy_preflight_v1298.py --assume-yes preflight
python3 scripts/revalidation/wifi_execns_helper_v272_deploy_preflight_v1298.py \
  --assume-yes \
  --apply \
  --approval-phrase 'approve v1298 deploy execns helper v272 only; no daemon start and no Wi-Fi bring-up' \
  --transfer-method auto \
  run
python3 scripts/revalidation/a90ctl.py --json run /cache/bin/toybox sha256sum /cache/bin/a90_android_execns_probe
python3 scripts/revalidation/a90ctl.py --json run /cache/bin/a90_android_execns_probe --help
python3 scripts/revalidation/a90ctl.py --json selftest verbose
```

## Next

V1299 should run the bounded compact dense no-write response sampler live:

- helper `v272`
- `--pm-observer-late-per-proxy-response-sampler`
- `--pm-observer-late-per-proxy-dense-response-sampler`
- `--pm-observer-late-per-proxy-compact-response-sampler`
- no PMIC write
- no userspace GPIO line request/hold
- no direct eSoC ioctl
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- cleanup and postflight health checks required
