# Native Init V1312 Execns Helper v275 Deploy

## Summary

- Cycle: `V1312`
- Type: deploy-only helper update
- Decision: `execns-helper-v275-deploy-pass`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1312-execns-helper-v275-deploy/manifest.json`
  - `tmp/wifi/v1312-execns-helper-v275-deploy/summary.md`
  - `tmp/wifi/v1312-execns-helper-v275-deploy/native/sha-helper.txt`
  - `tmp/wifi/v1312-execns-helper-v275-deploy/host/serial-install-helper.txt`
- Script: `scripts/revalidation/wifi_execns_helper_v275_deploy_preflight_v1312.py`
- Helper: `a90_android_execns_probe v275`
- Remote path: `/cache/bin/a90_android_execns_probe`
- SHA256: `66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677`

V1312 deployed the V1311-built helper `v275` to the native device cache path. NCM was not active during preflight, so the wrapper used serial fallback.

## Checks

| check | result |
| --- | --- |
| native version | `A90 Linux init 0.9.68 (v724)` |
| native health | `status/selftest rc=0`, `fail=0` |
| local helper marker | `a90_android_execns_probe v275` |
| remote helper sha | `66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677` |
| service-manager processes | clean |
| Wi-Fi link surface | clean |
| V373 post-deploy preflight | pass; approval still required for daemon-start smoke |

`helper-usage` exits with rc `2`, which is expected for usage output. The output still confirms the `v275` marker and the `--pm-observer-late-per-proxy-lower-sequence-summary-sampler` option.

## Validation

```bash
python3 scripts/revalidation/wifi_execns_helper_v275_deploy_preflight_v1312.py \
  --transfer-method auto \
  --serial-chunk-size 1800 \
  --apply \
  --assume-yes \
  --approval-phrase 'approve v1312 deploy execns helper v275 only; no daemon start and no Wi-Fi bring-up' \
  run
```

The deploy completed with `rc=0` and `device_mutations=True` limited to the approved `/cache/bin/a90_android_execns_probe` helper update.

## Next

V1313 should run the bounded lower-sequence summary sampler live using helper `v275`. It should verify:

- `response_sampler.end=1`;
- `response_summary.sample_count>=81`;
- no helper stdout truncation;
- `/dev/subsys_esoc0` / `mdm_subsys_powerup` is seen;
- PCIe GDSC/MHI/`ks`/`wlan0` progression or confirmed absence is summarized.

## Safety

- No daemon-start smoke was executed in V1312.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
- No PMIC write, userspace GPIO request/hold, or direct eSoC ioctl occurred.
