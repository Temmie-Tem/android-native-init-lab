# Native Init V926 Helper v153 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V926 helper deploy | `tmp/wifi/v926-execns-helper-v153-deploy-preflight/manifest.json` | `execns-helper-v153-deploy-pass` |

V926 deployed the V925-built helper `a90_android_execns_probe v153` to
`/cache/bin/a90_android_execns_probe` and verified the remote checksum.

## Implementation

- Added deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v153_deploy_preflight.py`
- Local artifact:
  `tmp/wifi/v925-execns-helper-v153-build/a90_android_execns_probe`
- Deploy evidence:
  `tmp/wifi/v926-execns-helper-v153-deploy-preflight/host/serial-install-helper.txt`

## Execution

Preflight:

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v153_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_v153_deploy_preflight.py preflight
```

Deploy:

```bash
python3 scripts/revalidation/wifi_execns_helper_v153_deploy_preflight.py \
  --approval-phrase "approve v926 deploy execns helper v153 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

## Transfer Notes

- Initial `--serial-chunk-size 3000` was rejected before writing any chunks:
  max cmdv1 line was `6190`, above the safe `3968` byte limit.
- The wrapper was corrected to chunk size `1800`.
- Final serial transfer wrote `860/860` chunks.
- Maximum cmdv1 line size was `3790`, below the safe `3968` byte limit.
- An NCM setup attempt enabled device-side `ncm0`, but host IP configuration
  required sudo and was not used for deploy. Post-deploy `netservice status`
  showed `enabled=no`, `ncm0=present`, and `tcpctl=stopped`.

## Verification

| Check | Value |
| --- | --- |
| local helper marker | `a90_android_execns_probe v153` |
| local helper SHA-256 | `ef9b5b779909be67a6cf9a29e14f5445505220ec6a9c651c888ff48acda1326e` |
| remote helper SHA-256 | `ef9b5b779909be67a6cf9a29e14f5445505220ec6a9c651c888ff48acda1326e` |
| deploy method | serial `appendfile` + `uudecode` |
| chunks written | `860/860` |
| bootstatus after deploy | `BOOT OK` |
| selftest after deploy | `pass=11 warn=1 fail=0` |
| service-manager/HAL started | `false` |
| Wi-Fi bring-up executed | `false` |

## Guardrails

- No service-manager start.
- No Wi-Fi HAL start.
- No CNSS live actor start.
- No scan/connect.
- No credentials.
- No DHCP/routes.
- No external ping.
- No boot image, partition, firmware, GPIO, sysfs, debugfs, or module mutation.

## Interpretation

V926 passes. The device now has helper `v153` deployed and ready for the next
bounded compact CNSS-before-eSoC precondition gate.

The first failed deploy attempt was a local safety-gate failure only:
`chunks_written=0`, so the remote helper was not modified until the successful
safe-chunk retry.

## Next

V927 should run helper `v153` in compact
`wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture` mode. It should
verify whether the namespace repairs change the CNSS/WLFW precondition result
without starting service-manager, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, or external ping.
