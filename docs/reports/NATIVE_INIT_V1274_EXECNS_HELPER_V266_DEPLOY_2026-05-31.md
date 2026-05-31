# V1274 Execns Helper v266 Deploy

## Result

- decision: `execns-helper-v266-deploy-pass`
- evidence: `tmp/wifi/v1274-execns-helper-v266-deploy/manifest.json`
- helper: `a90_android_execns_probe v266`
- helper SHA256: `3bf4105d685f023ccdeb75ae28d7d104ca005fc9f70870dc6f402a9ea4038ed4`
- transfer: serial fallback, `1010` chunks, safe line check passed
- post-deploy direct SHA verification: passed
- post-deploy selftest: `fail=0`
- scope: deploy-only; no daemon start, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, flash, boot image write, or partition write

## Verification

V1274 installed only `/cache/bin/a90_android_execns_probe` and verified:

- local helper SHA and marker
- native version/selftest
- remote helper SHA
- helper usage includes `a90_android_execns_probe v266`
- post-deploy selftest remains `fail=0`

NCM was unavailable, so the wrapper used serial fallback with chunk size `1800`.

## Next

V1275 should run the bounded AP2MDM block sampler with helper v266.  It should
reuse the same late `per_proxy` / PM-service `/dev/subsys_esoc0` response window
and parse the new `*_debugfs_block_*` and `*_pinconf_block_*` fields.
