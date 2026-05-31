# V1229 ESOC WAIT_FOR_REQ / ks-MHI Contract Classifier

- date: 2026-05-31
- runner: `scripts/revalidation/native_wifi_esoc_wait_req_ks_mhi_contract_v1229.py`
- evidence: `tmp/wifi/v1229-esoc-wait-req-ks-mhi-contract/manifest.json`
- summary: `tmp/wifi/v1229-esoc-wait-req-ks-mhi-contract/summary.md`
- result: `v1229-esoc-wait-req-ks-mhi-contract-classified`
- pass: `true`

## Purpose

V1228 proved the non-ptrace native path reaches `mdm_helper` blocked inside
`ESOC_WAIT_FOR_REQ`, but still lacks `ks`, MHI, WLFW, BDF, FW-ready, and
`wlan0`. V1229 is a host-only classifier that reconciles that result with older
native eSoC negative controls and Android positive evidence.

## Evidence Matrix

| evidence | result |
|---|---|
| V1228 natural `mdm_helper` wait | `ESOC_WAIT_FOR_REQ`, `wchan=esoc_dev_ioctl`, `/dev/esoc-0` fd present |
| V1228 PM trigger | `pm-service` attempts `/dev/subsys_esoc0` |
| V1228 lower result | no `ks`, no MHI pipe, no WLFW/BDF/FW-ready/`wlan0` |
| V891 controller path | `ESOC_WAIT_FOR_REQ` returns rc `4`, value `1` = `ESOC_REQ_IMG`; `ESOC_IMG_XFER_DONE` succeeds |
| V891 status result | `ESOC_GET_STATUS` remains `0`; no blind `ESOC_BOOT_DONE` |
| V1199 observe path | `ESOC_IMG_XFER_DONE` alone does not create MHI readiness |
| V896 Android positive | Android success includes `mdm_helper` + `/vendor/bin/ks` + `/dev/mhi_0305_01.01.00_pipe_10` |

## Interpretation

The native blocker is now specifically the request/image-link handoff around
Android's `ks`/MHI contract:

1. The eSoC request boundary is real.
2. The request value is expected to be `ESOC_REQ_IMG`.
3. A bare `ESOC_IMG_XFER_DONE` response is insufficient.
4. Android reaches readiness only when the `mdm_helper` / `ks` / MHI transfer
   path is active.

Therefore the next unit should not retry blind `ESOC_NOTIFY`,
`ESOC_BOOT_DONE`, service-manager expansion, or Wi-Fi HAL start. It should first
capture the `ESOC_WAIT_FOR_REQ` return or immediate post-return branch in the
V1228 non-ptrace path, and sample `/vendor/bin/ks` plus
`/dev/mhi_0305_01.01.00_pipe_10`.

## Safety Audit

- host-only: `true`
- device commands executed: `false`
- live eSoC ioctl / notify: `false`
- PM/CNSS actor start: `false`
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`
- boot image write / flash / partition write: `false`

## Next

V1230 should add source/build-only support for a bounded `mdm_helper`
request-return / `ks` observer. The implementation should preserve the V1228
non-ptrace behavior and keep `ESOC_NOTIFY`, `ESOC_BOOT_DONE`, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, and external ping blocked.
