# V1294 Execns Helper v271 Deploy

- date: 2026-05-31
- scope: deploy-only helper update
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v271_deploy_preflight_v1294.py`
- local helper: `stage3/linux_init/helpers/a90_android_execns_probe_v271`
- remote helper: `/cache/bin/a90_android_execns_probe`
- evidence: `tmp/wifi/v1294-execns-helper-v271-deploy/manifest.json`
- result: `execns-helper-v271-deploy-pass`
- pass: `true`
- sha256: `335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24`

## Purpose

V1293 built helper `v271` with the dense late-`per_proxy` response sampler.
V1294 deploys that helper only, without starting PM/CNSS actors, Wi-Fi HAL,
scan/connect, DHCP/routes, or external network traffic.

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
| remote sha256 | `335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24` |
| remote marker | `a90_android_execns_probe v271` |

NCM was not reachable during preflight, so the wrapper used the safe serial
appendfile + `uudecode` path.

## Post-Deploy Proof

Read-only checks after deploy confirmed the remote helper:

```text
335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24  /cache/bin/a90_android_execns_probe
a90_android_execns_probe v271
--pm-observer-late-per-proxy-dense-response-sampler
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
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v271_deploy_preflight_v1294.py
python3 scripts/revalidation/wifi_execns_helper_v271_deploy_preflight_v1294.py --assume-yes preflight
python3 scripts/revalidation/wifi_execns_helper_v271_deploy_preflight_v1294.py \
  --assume-yes \
  --apply \
  --approval-phrase 'approve v1294 deploy execns helper v271 only; no daemon start and no Wi-Fi bring-up' \
  --transfer-method auto \
  run
python3 scripts/revalidation/a90ctl.py --json run /cache/bin/toybox sha256sum /cache/bin/a90_android_execns_probe
python3 scripts/revalidation/a90ctl.py --json run /cache/bin/a90_android_execns_probe --help
```

## Next

V1295 should run the bounded dense no-write response sampler live:

- helper `v271`
- `--pm-observer-late-per-proxy-response-sampler`
- `--pm-observer-late-per-proxy-dense-response-sampler`
- no PMIC write
- no userspace GPIO line request/hold
- no direct eSoC ioctl
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- cleanup and postflight health checks required
