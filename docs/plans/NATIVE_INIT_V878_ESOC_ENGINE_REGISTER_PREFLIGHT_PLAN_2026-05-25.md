# V878 eSoC Engine Register Preflight Plan

## Goal

Use deployed helper `v137` to run the first bounded mutating eSoC gate:
`REG_CMD_ENG` and `REG_REQ_ENG` registration on `/dev/esoc-0`. This is still
not an mdm3 power-on attempt and not a Wi-Fi bring-up attempt.

## Inputs

- V877 report: `docs/reports/NATIVE_INIT_V877_HELPER_V137_DEPLOY_2026-05-25.md`
- Live runner: `scripts/revalidation/native_wifi_esoc_engine_register_preflight_v878.py`
- Helper mode: `wifi-companion-esoc-engine-register-preflight`
- eSoC research: `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`

## Method

1. Verify helper `v137` local and remote SHA/mode parity.
2. Materialize Android-equivalent private eSoC nodes for the helper namespace.
3. Open `/dev/esoc-0` twice, once for CMD engine and once for REQ engine.
4. Issue only no-argument `REG_CMD_ENG` and `REG_REQ_ENG`.
5. Hold the fds briefly, close both fds, clean up nodes, and capture postflight
   health plus actor/network surfaces.

## Hard Gates

- Allowed mutating eSoC ioctls: `REG_CMD_ENG` and `REG_REQ_ENG` only.
- No `CMD_EXE`, no `PWR_ON`, no `WAIT_FOR_REQ`, no `NOTIFY`, and no
  `/dev/subsys_esoc0` open.
- No `mdm_helper`, no `ks`, no `pm_proxy_helper`, no CNSS, no service-manager
  trio, no Wi-Fi HAL.
- No scan/connect, credentials, DHCP/routes, or external ping.
- No module load/unload, boot image write, partition write, or firmware
  mutation.

## Success Criteria

- Decision is `v878-esoc-engine-register-preflight-pass`.
- Helper reports `engine-register-preflight-complete`.
- `REG_CMD_ENG` and `REG_REQ_ENG` both return rc `0`.
- Both fds are closed, created nodes are removed, and postflight selftest stays
  `fail=0`.
- Actor process hits and Wi-Fi link hits remain empty.

## Next

If V878 passes, V879 should classify the request-loop and `PWR_ON` guardrails
before any `CMD_EXE(ESOC_PWR_ON)` attempt.
