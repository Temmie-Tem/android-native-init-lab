# V375 Execns Helper v12 Deploy / Preflight Report

## Result

- decision: `execns-helper-v12-deploy-pass`
- pass: `true`
- device_mutations: `true`
- daemon_start_executed: `false`
- wifi_bringup_executed: `false`
- evidence:
  - `tmp/wifi/v375-plan-smoke/`
  - `tmp/wifi/v375-preflight-20260520-015315/`
  - `tmp/wifi/v375-approved-run-blocked-20260520-015737/`
  - `tmp/wifi/v375-deploy-20260520-015851/`
  - `tmp/wifi/v375-deploy-serial-20260520-020309/`
  - `tmp/wifi/v375-deploy-serial2-20260520-020415/`
  - `tmp/wifi/v375-postdeploy-preflight-20260520-021126/`
  - `tmp/wifi/v375-v373-postdeploy-preflight-20260520-021126/`

## Verified

- local V374 helper artifact exists.
- local helper SHA-256 matches `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`.
- local helper strings include `a90_android_execns_probe v12` and `service-manager-start-only`.
- native bridge commands responded.
- native version matched `A90 Linux init 0.9.61 (v319)`.
- native `status` and `selftest` were clean with `fail=0`.
- no service-manager family process was running.
- no Wi-Fi link surface was active.
- NCM-only deploy was blocked safely when host `192.168.7.1/24` was absent.
- serial fallback deployed the helper through `appendfile` + `toybox uudecode -o`.
- remote `/cache/bin/a90_android_execns_probe` SHA-256 now matches `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`.
- remote helper usage now shows `a90_android_execns_probe v12`, `--allow-service-manager-start-only`, and `service-manager-start-only`.
- V373 post-deploy preflight now reaches `service-manager-start-only-smoke-approval-required` with `helper-service-manager-mode` PASS.
- V375 post-deploy preflight reaches `execns-helper-v12-deploy-preflight-ready`.
- native `status` and `selftest` remained clean after deploy.

## Earlier Blockers

1. `ncm-host-reachable`
   - host ping to `192.168.7.2` failed.
   - The approved executor fell back to serial transfer instead of bypassing the gate unsafely.
2. `remote-helper-v12`
   - remote `/cache/bin/a90_android_execns_probe` is still v11.
   - remote SHA-256: `f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b`.
   - remote usage lacks `service-manager-start-only`.
   - Resolved by approved serial fallback deployment.

## Deploy Evidence

- approved phrase:
  - `approve v375 deploy execns helper v12 only; no daemon start and no Wi-Fi bring-up`
- transfer method:
  - `auto`, falling back to serial because host NCM ping was unavailable.
- install transcript:
  - `tmp/wifi/v375-deploy-serial2-20260520-020415/host/serial-install-helper.txt`
- post-deploy V373 preflight:
  - `tmp/wifi/v375-deploy-serial2-20260520-020415/v373-preflight/summary.md`
- repeated post-deploy V375 preflight:
  - `tmp/wifi/v375-postdeploy-preflight-20260520-021126/summary.md`
- repeated V373 preflight:
  - `tmp/wifi/v375-v373-postdeploy-preflight-20260520-021126/summary.md`

## Next Step

- V373 service-manager start-only live run is now unblocked at the helper-mode layer.
- It still requires a separate exact approval phrase:
  - `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
- Wi-Fi HAL start, scan/connect/link-up, credential, DHCP, routing remain blocked.
