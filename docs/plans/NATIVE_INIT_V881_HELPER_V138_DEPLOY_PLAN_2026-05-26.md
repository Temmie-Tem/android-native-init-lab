# V881 Helper v138 Deploy-only Plan

## Goal

Deploy helper `v138` to `/cache/bin/a90_android_execns_probe` and prove
checksum/version/mode parity. This step prepares the next bounded eSoC gate but
does not execute live eSoC ioctls or open `/dev/subsys_esoc0`.

## Inputs

- V880 build artifact:
  `tmp/wifi/v880-execns-helper-v138-build/a90_android_execns_probe`
- V880 manifest:
  `tmp/wifi/v880-execns-helper-v138-build/manifest.json`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v138_deploy_preflight.py`

## Method

1. Run plan mode without bridge/device contact.
2. Run read-only preflight against native init.
3. Deploy helper only after explicit apply gates.
4. Verify remote sha256, helper marker, and mode token.
5. Verify post-deploy native health, actor-clean, and Wi-Fi-link-clean.

## Hard Gates

- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `CMD_EXE`, explicit userspace `PWR_ON`, `WAIT_FOR_REQ`, or `NOTIFY`.
- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.
- No boot image, partition, firmware, GPIO, sysfs, debugfs, module, or reboot
  action.

## Success Criteria

- Decision is `execns-helper-v138-deploy-pass`.
- Remote helper sha256 equals
  `2ac8c6730768f86a221722a6ff259e3a4617134221498bd1956a63980a22a9b5`.
- Remote helper output includes `a90_android_execns_probe v138`.
- Remote helper output includes
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`.
- Post-deploy selftest stays `fail=0`.
- Service-manager actor hits and Wi-Fi netdev hits remain `0`.

## Next

If V881 passes, V882 should first add passive `ESOC_WAIT_FOR_REQ` observation
support to the helper before running the next live hold window. V882 must still
avoid Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
