# V992 Execns Helper v168 Deploy

- generated: `2026-05-26`
- scope: deploy-only helper replacement
- decision: `execns-helper-v168-deploy-pass`
- evidence: `tmp/wifi/v992-execns-helper-v168-deploy/manifest.json`
- local artifact: `tmp/wifi/v991-execns-helper-v168-build/a90_android_execns_probe`
- expected sha256: `4407766d01d816e03bc81bde6ea994112cb59fb66bf9444900929db862889fa0`

## Summary

V992 deployed helper `v168` to `/cache/bin/a90_android_execns_probe` and verified
remote checksum/version parity. No daemon start or Wi-Fi bring-up was executed
during the deploy unit.

An attempted `--serial-chunk-size 3000` run failed closed before mutation because
the encoded command line exceeded the native console safe limit. The successful
run used the default safe serial chunk size.

## Guardrails

- deploy-only mutation to `/cache/bin/a90_android_execns_probe`
- no service-manager/HAL live proof in deploy unit
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v168_deploy_v992.py
python3 scripts/revalidation/native_wifi_helper_v168_deploy_v992.py --serial-chunk-size 3000 preflight
python3 scripts/revalidation/native_wifi_helper_v168_deploy_v992.py \
  --approval-phrase "approve v992 deploy execns helper v168 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
```

Result:

```text
decision: execns-helper-v168-deploy-pass
pass: True
wifi_bringup_executed: False
```

## Next

Run the bounded Android service-window proof once with helper `v168`.
