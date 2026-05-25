# V899 Helper v144 Deploy-only Plan

## Goal

Deploy helper `v144` to `/cache/bin/a90_android_execns_probe` and prove remote
checksum/version/mode parity before any live `mdm_helper`/`ks` contract proof.

## Inputs

- V898 helper build:
  `tmp/wifi/v898-mdm-helper-ks-contract-helper-build/manifest.json`
- local helper artifact:
  `tmp/wifi/v898-mdm-helper-ks-contract-helper-build/a90_android_execns_probe`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v144_deploy_preflight.py`

## Method

1. Run wrapper `plan`.
2. Run wrapper `preflight` to verify native health, local helper sha/mode,
   actor-clean state, and Wi-Fi-link-clean state.
3. Run approved deploy with serial transfer if NCM is unavailable.
4. Run post-deploy preflight to prove remote sha/mode parity.

## Hard Gates

- Deploy-only write to `/cache/bin/a90_android_execns_probe`.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `mdm_helper` start.
- No `ks` start.
- No `REG_REQ_ENG`, `ESOC_NOTIFY`, or `BOOT_DONE`.
- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or Wi-Fi
  link-up.

## Success Criteria

- Approved deploy returns `execns-helper-v144-deploy-pass`.
- Remote `/cache/bin/a90_android_execns_probe` sha256 equals
  `c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e`.
- Remote helper exposes marker `a90_android_execns_probe v144`.
- Remote helper exposes mode
  `wifi-companion-mdm-helper-ks-image-contract-preflight`.
- Post-deploy native health remains `selftest fail=0`.
- Service-manager and Wi-Fi link surfaces remain clean.

## Next

If V899 passes, V900 can run the first bounded live
`mdm_helper`/`ks` contract proof. V900 must still block Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, and external ping.
