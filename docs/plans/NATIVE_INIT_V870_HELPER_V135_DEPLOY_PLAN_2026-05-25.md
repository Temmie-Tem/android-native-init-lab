# V870 Helper v135 Deploy-only Plan

## Goal

Deploy helper `v135` to `/cache/bin/a90_android_execns_probe` and prove remote
checksum/version/mode parity without starting Android actors or bringing up
Wi-Fi.

## Inputs

- V869 report: `docs/reports/NATIVE_INIT_V869_ESOC_CONTROL_PREFLIGHT_HELPER_BUILD_2026-05-25.md`
- Local helper: `tmp/wifi/v869-execns-helper-v135-build/a90_android_execns_probe`
- Deploy wrapper: `scripts/revalidation/wifi_execns_helper_v135_deploy_preflight.py`
- Remote target: `/cache/bin/a90_android_execns_probe`

## Method

1. Run plan and preflight.
2. Verify native health: version, status, selftest, no active actor surface.
3. Install only the helper binary with the approved deploy phrase.
4. Verify remote SHA-256, helper marker, and mode token.
5. Capture post-deploy selftest, actor process surface, and Wi-Fi link surface.

## Hard Gates

- No `mdm_helper`, no `ks`, no `pm_proxy_helper`, no CNSS, no service-manager
  trio, no Wi-Fi HAL.
- No scan/connect, credentials, DHCP/routes, or external ping.
- No live eSoC control preflight, no `ESOC_PWR_ON`, no eSoC mutating ioctl.
- No module load/unload, boot image write, partition write, or firmware
  mutation.

## Transfer

NCM was not active in the current native state, so V870 uses the proven serial
appendfile/uudecode path with `--serial-chunk-size 1850`.

## Success Criteria

- Deploy manifest decision is `execns-helper-v135-deploy-pass`.
- Remote SHA-256 equals
  `ad1bbbf295be61ef612406091ccd469c4ef45ab44c0f753c4de034e487ddaad1`.
- Remote helper usage includes `a90_android_execns_probe v135` and
  `wifi-companion-esoc-control-preflight`.
- Post-health selftest has `fail=0`.
- Actor process count and Wi-Fi link count remain zero.

## Next

If V870 passes, V871 may run a bounded live eSoC control preflight. That next
gate must still avoid `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`,
`NOTIFY`, `PWR_ON`, `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, HAL,
scan/connect, credentials, DHCP/routes, and external ping unless separately
approved and implemented.
