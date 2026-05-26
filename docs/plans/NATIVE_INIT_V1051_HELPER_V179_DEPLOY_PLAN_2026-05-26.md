# V1051 Helper v179 Deploy Plan

## Goal

Deploy the V1050 `a90_android_execns_probe v179` helper to
`/cache/bin/a90_android_execns_probe` and verify it without starting Android
services or Wi-Fi bring-up.

## Inputs

- V1050 source/build report:
  `docs/reports/NATIVE_INIT_V1050_PM_MODEM_PRE_HOLDER_PRIVATE_ROOT_REPAIR_2026-05-26.md`
- Local helper artifact:
  `tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe`
- Expected sha256:
  `9cb6d49849af181a87a5619e7b3ed7f0f513223ef97ce8b0599ce43694453a7b`
- Deploy wrapper:
  `scripts/revalidation/native_wifi_helper_v179_deploy_v1051.py`

## Method

1. Verify native health, selftest, service-manager/CNSS/Wi-Fi actor clean state,
   local helper sha, marker, flag, order token, and compact mode token.
2. Deploy only `/cache/bin/a90_android_execns_probe` with serial appendfile when
   the exact V1051 approval phrase is present.
3. Recheck remote sha, helper usage contract, native health, actor-clean state,
   and Wi-Fi link-clean state.
4. Add busy-menu retry to the shared deploy preflight reader so `status` output
   cannot poison the following read-only checks.

## Hard Gates

- No service-manager, CNSS daemon, Wi-Fi HAL, `wificond`, scan/connect,
  credentials, DHCP/routes, external ping, eSoC ioctl, subsystem open, GPIO
  write, sysfs write, debugfs write, boot image write, partition write, or
  firmware mutation.
- Only `/cache/bin/a90_android_execns_probe` may be replaced.

## Success Criteria

- Remote sha256 equals the V1050 v179 artifact sha256.
- Remote helper usage contains the v179 marker, allow flag, and service-manager
  order token.
- Native `bootstatus`/`selftest` stay clean.
- No service-manager/CNSS/Wi-Fi actor remains running.
- No Wi-Fi link surface appears.

## Next

V1052 should rerun the bounded PM full-contract-with-modem-holder live gate using
helper `v179` after current-boot SELinux preconditions are refreshed.
