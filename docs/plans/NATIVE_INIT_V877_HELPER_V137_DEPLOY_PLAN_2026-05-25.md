# V877 Helper v137 Deploy-only Plan

## Goal

Deploy helper `v137` to `/cache/bin/a90_android_execns_probe` and prove remote
checksum/version/mode parity without executing the eSoC engine registration
preflight.

## Inputs

- V876 report: `docs/reports/NATIVE_INIT_V876_ESOC_ENGINE_REGISTER_HELPER_BUILD_2026-05-25.md`
- Local helper: `tmp/wifi/v876-execns-helper-v137-build/a90_android_execns_probe`
- Deploy wrapper: `scripts/revalidation/wifi_execns_helper_v137_deploy_preflight.py`
- Remote target: `/cache/bin/a90_android_execns_probe`

## Method

1. Run plan and deploy preflight.
2. Verify native version, status, selftest, helper usage, process surface, and
   network surface.
3. Install only the helper binary with the V877 deploy phrase.
4. Verify remote SHA-256, helper marker, and eSoC engine registration mode token.

## Success Criteria

- Deploy manifest decision is `execns-helper-v137-deploy-pass`.
- Remote SHA-256 equals
  `e47eb52b0b2b2fb601fdbc4ecebdf72e2fda9519eac37e776d62c11d2d469aa3`.
- Remote helper usage includes `a90_android_execns_probe v137` and
  `wifi-companion-esoc-engine-register-preflight`.
- No actor start, no Wi-Fi bring-up, and no live eSoC ioctl occur.

## Hard Gates

- No `REG_CMD_ENG`, `REG_REQ_ENG`, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`,
  `NOTIFY`, or `/dev/subsys_esoc0` open.
- No `mdm_helper`, no `ks`, no `pm_proxy_helper`, no CNSS, no service-manager
  trio, no Wi-Fi HAL.
- No scan/connect, credentials, DHCP/routes, or external ping.

## Next

V878 should run bounded live `REG_CMD_ENG`/`REG_REQ_ENG` registration preflight
using helper `v137`, still without `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`,
`NOTIFY`, `/dev/subsys_esoc0` open, actors, or Wi-Fi bring-up.
