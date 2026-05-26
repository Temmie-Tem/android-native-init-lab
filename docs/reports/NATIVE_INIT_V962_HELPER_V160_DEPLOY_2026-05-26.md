# V962 Helper v160 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy-only wrapper | `tmp/wifi/v962-execns-helper-v160-deploy/manifest.json` | `execns-helper-v160-deploy-pass` |

V962 deployed helper `a90_android_execns_probe v160` to
`/cache/bin/a90_android_execns_probe`.

## Scope

- Deploy-only helper replacement.
- No daemon, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  or external ping was executed.
- Transfer path: serial appendfile plus uudecode.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_helper_v160_deploy_v962.py
python3 scripts/revalidation/native_wifi_helper_v160_deploy_v962.py plan
python3 scripts/revalidation/native_wifi_helper_v160_deploy_v962.py \
  --approval-phrase "approve v962 deploy execns helper v160 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  --serial-chunk-size 1850 \
  run
```

Result:

- decision: `execns-helper-v160-deploy-pass`
- expected helper sha256:
  `2b4d621b111fa8e0e24a3591dd233478ac1d94ca87fa8c0eb1541db4d6d11998`
- chunks written: `886`
- postflight native health: pass
- remote helper contract: pass
- daemon start: false
- Wi-Fi bring-up: false

## Next

V963 should run the bounded `post-provider-no-wlfw` live proof with helper
`v160`, keeping `pm_proxy_helper`, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, and external ping blocked.
