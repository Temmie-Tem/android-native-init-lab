# V972 Execns Helper v162 Deploy

- generated: `2026-05-26`
- scope: deploy-only
- decision: `execns-helper-v162-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v972-execns-helper-v162-deploy/manifest.json`
- deployed helper: `/cache/bin/a90_android_execns_probe`
- expected sha256: `c51912bd4b723beddcd54ab2f958462dff4b291ace209bd0590bc45d108d0db7`

## Summary

V972 deployed helper `a90_android_execns_probe v162` after the V971 validation allowlist repair.

Deployment used serial `appendfile + uudecode`:

- chunk size: `1850`
- chunks written: `886/886`
- max command line bytes: `3886`
- safe line limit: `3968`
- remote sha matched `c51912bd4b723beddcd54ab2f958462dff4b291ace209bd0590bc45d108d0db7`

## Guardrails

- deploy-only
- no service-manager start
- no CNSS daemon start
- no Wi-Fi HAL start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no boot or partition write

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v162_deploy_v972.py
python3 scripts/revalidation/native_wifi_helper_v162_deploy_v972.py preflight
python3 scripts/revalidation/native_wifi_helper_v162_deploy_v972.py --apply --assume-yes --approval-phrase "approve v972 deploy execns helper v162 only; no daemon start and no Wi-Fi bring-up" run
```

Result:

```text
decision: execns-helper-v162-deploy-pass
pass: True
reason: helper v162 deployed or already current; no daemon or Wi-Fi bring-up executed
```

## Next

Rerun the bounded Android service-window live proof with helper `v162`.
