# Native Init V1327 Execns Helper v276 Deploy

## Summary

- Cycle: `V1327`
- Type: deploy-only helper update
- Decision: `execns-helper-v276-deploy-pass`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1327-execns-helper-v276-deploy/manifest.json`
  - `tmp/wifi/v1327-execns-helper-v276-deploy/summary.md`
- Script: `scripts/revalidation/wifi_execns_helper_v276_deploy_preflight_v1327.py`
- Remote helper: `/cache/bin/a90_android_execns_probe`
- Helper marker: `a90_android_execns_probe v276`
- Helper SHA256: `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f`

V1327 deployed the V1326 helper to `/cache/bin/a90_android_execns_probe`.
NCM was not active, so the deploy used serial fallback. Post-deploy manual
verification confirmed the remote SHA256 and the helper usage output includes
`a90_android_execns_probe v276` plus
`--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`.

## Checks

- Local helper exists and matches the expected V1326 SHA256.
- Native version remains `A90 Linux init 0.9.68 (v724)`.
- Native selftest remains `pass=11 warn=1 fail=0`.
- Service-manager process surface remained clean.
- Wi-Fi link surface remained clean.
- Remote helper SHA256 after deploy:
  `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f`.
- Remote helper usage contains the new timing sampler flag.

## Decision

V1327 closes the deploy-only gate for helper `v276`. The next useful unit is
V1328: a bounded live run of the `mdm2ap_timing` sampler to classify whether
the late `per_proxy` / `pm-service` path produces GPIO142, MDM errfatal, PCIe
RC1, MHI/ks, WLFW, or `wlan0` transitions.

## Safety

Deploy-only. No daemon start, service-manager start, Wi-Fi HAL start,
scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO
request/hold, direct eSoC ioctl, flash, boot image write, or partition write
occurred. The only device mutation was updating `/cache/bin/a90_android_execns_probe`.
