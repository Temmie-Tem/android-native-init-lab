# Native Init V1282 Execns Helper v268 Deploy

- generated: 2026-05-31
- cycle: V1282
- command: deploy-only
- decision: `execns-helper-v268-deploy-pass`
- pass: true
- helper: `a90_android_execns_probe v268`
- remote path: `/cache/bin/a90_android_execns_probe`
- sha256: `e86db44aad14e54572d88d77c1ea2019ea28b1f91c01f7a9af9e6eabc690a3ba`

## Result

| field | value |
| --- | --- |
| deploy method | serial fallback |
| chunks written | `1010` |
| line check | pass |
| remote SHA verification | pass |
| post-deploy selftest | `pass=11 warn=1 fail=0` |
| service-manager start | not executed |
| Wi-Fi bring-up | not executed |

Evidence:

- `tmp/wifi/v1282-execns-helper-v268-deploy/manifest.json`
- `tmp/wifi/v1282-execns-helper-v268-deploy/summary.md`
- `tmp/wifi/v1282-execns-helper-v268-deploy/host/serial-install-helper.txt`

## Safety

The deploy gate wrote only `/cache/bin/a90_android_execns_probe`. It did not
start service-manager, Wi-Fi HAL, CNSS, scan/connect, credential handling,
DHCP/routing, external ping, flash, boot image write, or partition write.

## Next

V1283 should run the bounded PCIe/GDSC/kmsg response sampler live with helper
v268 and classify whether PCIe RC1, GDSC, MHI, ext-mdm, or WLFW markers advance
during the PM-service `/dev/subsys_esoc0` window.
