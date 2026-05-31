# Native Init V1278 Execns Helper v267 Deploy

- generated: 2026-05-31
- cycle: V1278
- command: deploy-only
- decision: `execns-helper-v267-deploy-pass`
- pass: true
- helper: `a90_android_execns_probe v267`
- remote path: `/cache/bin/a90_android_execns_probe`
- sha256: `eccd9ca475927c2a37551304fedcc6740d19aeb048ebd137f966a18c269f0337`

## Scope

V1278 deployed the V1277-built helper v267 to the live native init runtime so
the next bounded live gate can capture TLMM GPIO135/GPIO142 debugfs range blocks
during the PM-service `/dev/subsys_esoc0` response window.

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

- `tmp/wifi/v1278-execns-helper-v267-deploy/manifest.json`
- `tmp/wifi/v1278-execns-helper-v267-deploy/summary.md`
- `tmp/wifi/v1278-execns-helper-v267-deploy/host/serial-install-helper.txt`

## Safety

The deploy gate wrote only `/cache/bin/a90_android_execns_probe`. It did not
start service-manager, Wi-Fi HAL, CNSS, scan/connect, credential handling,
DHCP/routing, external ping, flash, boot image write, or partition write.

## Next

V1279 should run the bounded TLMM range sampler live with helper v267 and collect
whether TLMM GPIO135/GPIO142 range blocks are visible while GPIO142 IRQ, PCIe
RC1, MHI pipe, and `wlan0` remain read-only observations.
