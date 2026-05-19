# V375 Execns Helper v12 Deploy / Preflight Report

## Result

- decision: `execns-helper-v12-deploy-blocked`
- pass: `false`
- device_mutations: `false`
- daemon_start_executed: `false`
- wifi_bringup_executed: `false`
- evidence:
  - `tmp/wifi/v375-plan-smoke/`
  - `tmp/wifi/v375-preflight-20260520-015315/`

## Verified

- local V374 helper artifact exists.
- local helper SHA-256 matches `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`.
- local helper strings include `a90_android_execns_probe v12` and `service-manager-start-only`.
- native bridge commands responded.
- native version matched `A90 Linux init 0.9.61 (v319)`.
- native `status` and `selftest` were clean with `fail=0`.
- no service-manager family process was running.
- no Wi-Fi link surface was active.

## Blockers

1. `ncm-host-reachable`
   - host ping to `192.168.7.2` failed.
   - V375 deploy uses NCM transfer, so host NCM must be reconfigured before approved run.
2. `remote-helper-v12`
   - remote `/cache/bin/a90_android_execns_probe` is still v11.
   - remote SHA-256: `f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b`.
   - remote usage lacks `service-manager-start-only`.

## Next Command

After NCM is reachable and the operator accepts `/cache/bin` helper replacement:

```bash
python3 scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py \
  --out-dir tmp/wifi/v375-deploy-$(date +%Y%m%d-%H%M%S) \
  --approval-phrase "approve v375 deploy execns helper v12 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

This command installs/verifies the helper only. It does not start service-manager or Wi-Fi.
