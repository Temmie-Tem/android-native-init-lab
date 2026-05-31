# V1339 Android-order Pre-CNSS Provider Observer

- Date: 2026-05-31
- Scope: native-init Wi-Fi bring-up blocker analysis
- Device baseline: `A90 Linux init 0.9.68 (v724)`
- Helper: `a90_android_execns_probe v278`
- Mode: `wifi-companion-android-order-pre-cnss-provider-observe-only`

## Decision

`v1339-pre-cnss-provider-chain-no-wlfw` — PASS.

The Android-order pre-CNSS provider chain can be started in the native runtime, but it still does not advance to WLFW, `ks`, MHI pipe use, or WLAN netdev creation.

## Build and Deploy

| Step | Result | Evidence |
| --- | --- | --- |
| V1337 source/build | PASS | `tmp/wifi/v1337-android-pre-cnss-provider-support/manifest.json` |
| V1338 helper deploy | PASS | `tmp/wifi/v1338-execns-helper-v278-deploy/manifest.json` |
| V1339 bounded live | PASS | `tmp/wifi/v1339-android-pre-cnss-provider-observer-live/manifest.json` |

V1337 built a static aarch64 helper:

- path: `stage3/linux_init/helpers/a90_android_execns_probe_v278`
- sha256: `dd4f9996f5798a09498d4f7ce2f4e0385c161cc793e0ce0c96db284863f9d1e7`
- size: `1384944`
- static checks: no `INTERP`, no dynamic section

V1338 deployed the helper to `/cache/bin/a90_android_execns_probe`; no daemon start or Wi-Fi bring-up was executed during deploy.

## Live Contract

V1339 started this bounded order:

```text
servicemanager
hwservicemanager
vndservicemanager
pm_proxy_helper
qrtr_ns
rmt_storage
tftp_server
pd_mapper
per_mgr
per_proxy
mdm_helper
cnss_diag
cnss_daemon
```

Observed helper contract:

| Field | Value |
| --- | --- |
| `child_started` | `13` |
| `all_observable` | `1` |
| `all_postflight_safe` | `1` |
| `result` | `start-only-runtime-gap` |
| `reason` | `child-exited-before-observe-window` |
| `manual_subsys_esoc0_open` | `0` |
| `wifi_hal` | `0` |
| `wificond` | `0` |
| `scan_connect_linkup` | `0` |
| `external_ping` | `0` |
| `per_mgr_subsys_esoc0_window` | `-1` |
| `mdm_helper_subsys_esoc0_window` | `0` |
| `mdm_helper_esoc0_window` | `0` |
| `ks_window` | `0` |
| `mhi_cmdline_window` | `0` |

Child lifecycle summary:

- `per_mgr` became observable, then exited `0` before the observe window.
- `per_proxy` became observable, then exited `1` before the observe window.
- `mdm_helper` was started and later stopped cleanly by cleanup, but did not hold `/dev/esoc-0` or `/dev/subsys_esoc0` in the window sample.
- `cnss_daemon` started and was cleaned up; no WLFW/BDF/wlan0 surface appeared.

## Interpretation

V1336 showed that Android starts the PM/provider chain before CNSS. V1339 reproduced that broader order in native init without manually opening `/dev/subsys_esoc0`.

The missing transition is now narrower:

```text
Android-order provider chain starts
  -> per_mgr/per_proxy do not stay alive in native
  -> no provider-triggered subsys_esoc0 fd
  -> no mdm_helper /dev/esoc-0 hold
  -> no ks
  -> no MHI pipe
  -> no WLFW service 69
```

This means the previous V1335 gap was not only "provider chain absent"; the provider chain starts, but one or more PM provider dependencies still differ from Android enough that `per_proxy` exits and `pm-service` does not trigger the SDX50M path.

## Tooling Note

The first V1339 attempt exposed a command transport limit: the helper invocation lost arguments near `--timeout-sec` when wrapped through `toybox timeout`. The live runner was repaired by:

- removing the outer `toybox timeout` wrapper,
- moving allow flags earlier in the argv list,
- reducing optional arguments to stay within the cmdv1 argument window,
- making `/proc/net/qrtr` absence a read-only observation instead of a failing step.

## Guardrails Verified

- No manual `/dev/subsys_esoc0` open.
- No eSoC ioctl, notify, or BOOT_DONE spoof.
- No PMIC/GPIO write.
- No Wi-Fi HAL or `wificond`.
- No scan/connect, credentials, DHCP/routes, or external ping.
- No flash, boot image write, or partition write.
- Cleanup was safe; no reboot cleanup was required.

## Next Gate

V1340 should be a host/live classifier focused on the provider-chain runtime gap:

1. Capture targeted stdout/stderr and exit classification for `pm-service` and `pm-proxy` without 1 MiB generic stderr truncation.
2. Compare `per_proxy` Android argv/environment/properties against the native private namespace.
3. Check whether `pm-service` exit `0` is expected one-shot behavior or early shutdown caused by missing binder/service registration.
4. Keep the same prohibitions: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, manual eSoC open, PMIC/GPIO write, or flash.
