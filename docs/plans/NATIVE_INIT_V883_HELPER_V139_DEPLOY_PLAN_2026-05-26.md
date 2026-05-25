# V883 Helper v139 Deploy-only Plan

## Goal

Deploy helper `v139` to `/cache/bin/a90_android_execns_probe` and prove
checksum/version/mode parity. This prepares the bounded REQ-registered
subsystem-hold observer gate, but V883 itself does not execute any live eSoC
ioctl or open `/dev/subsys_esoc0`.

## Inputs

- V882 build artifact:
  `tmp/wifi/v882-execns-helper-v139-build/a90_android_execns_probe`
- V882 manifest:
  `tmp/wifi/v882-execns-helper-v139-build/manifest.json`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v139_deploy_preflight.py`

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

- Decision is `execns-helper-v139-deploy-pass`.
- Remote helper sha256 equals
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`.
- Remote helper output includes `a90_android_execns_probe v139`.
- Remote helper output includes
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`.
- Post-deploy selftest stays `fail=0`.
- Service-manager actor hits and Wi-Fi netdev hits remain `0`.

## Next

If V883 passes, V884 should run a bounded live REQ-registered subsystem-hold
observer preflight. V884 must still avoid Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, and external ping.
