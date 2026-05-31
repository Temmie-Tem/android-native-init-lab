# Native Init V1285 Execns Helper v269 Deploy

- generated: 2026-05-31
- cycle: V1285
- command: deploy-only
- decision: `execns-helper-v269-deploy-pass`
- pass: true
- helper: `a90_android_execns_probe v269`
- remote path: `/cache/bin/a90_android_execns_probe`
- sha256: `dbb1f67652913ffe94b1f083a082d8f221820040b9f28e08b226eb1e0a50fc83`

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

- `tmp/wifi/v1285-execns-helper-v269-deploy/manifest.json`
- `tmp/wifi/v1285-execns-helper-v269-deploy/summary.md`
- `tmp/wifi/v1285-execns-helper-v269-deploy/host/serial-install-helper.txt`

## Safety

The deploy gate wrote only `/cache/bin/a90_android_execns_probe`. It did not
start service-manager, Wi-Fi HAL, CNSS, scan/connect, credential handling,
DHCP/routing, external ping, flash, boot image write, or partition write.

## Next

V1286 should rerun the bounded PCIe/GDSC/klogctl response sampler live with
helper v269 and classify whether the repaired kernel-log collector sees any
PCIe RC1, GDSC, MHI, ext-mdm, SDX50M, or WLFW response during the PM-service
`/dev/subsys_esoc0` window.
