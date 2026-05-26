# V1054 Helper v180 Deploy Plan

## Goal

Deploy the V1053 `a90_android_execns_probe v180` helper to
`/cache/bin/a90_android_execns_probe` and verify it without Android daemon start
or Wi-Fi bring-up.

## Inputs

- V1053 source/build report:
  `docs/reports/NATIVE_INIT_V1053_MODEM_PRE_HOLDER_PLAIN_OPEN_FALLBACK_2026-05-26.md`
- Local helper artifact:
  `tmp/wifi/v1053-execns-helper-v180-build/a90_android_execns_probe`
- Expected sha256:
  `f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641`
- Deploy wrapper:
  `scripts/revalidation/native_wifi_helper_v180_deploy_v1054.py`

## Method

1. Verify local helper sha/marker/flag/order tokens.
2. Verify native health, actor-clean state, and Wi-Fi-link-clean state.
3. Replace only `/cache/bin/a90_android_execns_probe` via approved serial
   appendfile when remote sha is not current.
4. Recheck remote sha/usage contract and native health.

## Hard Gates

No service-manager, CNSS daemon, Wi-Fi HAL, `wificond`, scan/connect,
credentials, DHCP/routes, external ping, eSoC ioctl, subsystem open, GPIO write,
sysfs write, debugfs write, boot image write, partition write, or firmware
mutation. Only `/cache/bin/a90_android_execns_probe` may be replaced.

## Success Criteria

- Remote sha256 equals the V1053 v180 artifact sha256.
- Remote helper usage contains marker `a90_android_execns_probe v180` and the PM
  full-contract-with-modem-holder order token.
- Native health remains clean and no Wi-Fi link appears.

## Next

V1055 should rerun the bounded live gate and classify whether the plain fallback
open succeeds, blocks, or returns a new errno.
