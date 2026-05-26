# V969 Execns Helper v161 Deploy

- generated: `2026-05-26`
- scope: deploy-only
- decision: `execns-helper-v161-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v969-execns-helper-v161-deploy/manifest.json`
- deployed helper: `/cache/bin/a90_android_execns_probe`
- expected sha256: `1d936d9117e68b97c1449d9ed357560ec7ae1901eeb179da474f1dacbc837643`

## Summary

V969 deployed and verified helper `a90_android_execns_probe v161` on the device.

The first approved V969 run used serial `appendfile + uudecode` and wrote the helper to `/cache/bin/a90_android_execns_probe`. The serial transcript records:

- `append` chunks: `886`
- target sha256 matched `1d936d9117e68b97c1449d9ed357560ec7ae1901eeb179da474f1dacbc837643`
- helper usage printed `a90_android_execns_probe v161`

The follow-up V969 run observed the same remote sha and contract, so it skipped install and returned pass.

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
python3 -m py_compile scripts/revalidation/native_wifi_helper_v161_deploy_v969.py
python3 scripts/revalidation/native_wifi_helper_v161_deploy_v969.py preflight
python3 scripts/revalidation/native_wifi_helper_v161_deploy_v969.py --apply --assume-yes --approval-phrase "approve v969 deploy execns helper v161 only; no daemon start and no Wi-Fi bring-up" run
```

Final result:

```text
decision: execns-helper-v161-deploy-pass
pass: True
reason: helper v161 deployed or already current; no daemon or Wi-Fi bring-up executed
```

Extra device confirmation:

```text
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
1d936d9117e68b97c1449d9ed357560ec7ae1901eeb179da474f1dacbc837643  /cache/bin/a90_android_execns_probe
```

## Notes

An attempted serial chunk size of `3000` was rejected before writes because it exceeded the native console safe line limit. The successful deploy used the default safe chunk size and completed all `886` chunks.

## Next

Run V970 as a separate bounded live gate:

```text
wifi-companion-android-wifi-service-window-start-only
```

It should use helper `v161`, strict timeout, cleanup, no `qcwlanstate`, no eSoC open/ioctl, no scan/connect, no DHCP, no credentials, and no external ping.
