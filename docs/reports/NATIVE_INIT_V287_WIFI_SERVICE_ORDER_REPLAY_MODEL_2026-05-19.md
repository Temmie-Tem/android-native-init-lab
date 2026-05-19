# Native Init v287 Wi-Fi Service-Order Replay Model Report

- date: `2026-05-19`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- result: PASS
- decision: `wifi-service-order-replay-model-ready`

## Summary

v287 adds a no-execution Android Wi-Fi service-order replay model.

It merges the v216 Android service graph, the v228 controlled CNSS start plan,
and the v286 Android/TWRP/native timing comparison.  The tool does not talk to
the device, start services, send QRTR/QMI packets, change rfkill/sysfs, or bring
up any Wi-Fi interface.

The output confirms that the first missing native boot-window boundary is the
Android Wi-Fi service-order transition:

```text
first missing native event: android_wifi_action
first service boundary: vendor.wifi_hal_ext
```

## Implemented

- Plan:
  - `docs/plans/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_PLAN_2026-05-19.md`
- Tool:
  - `scripts/revalidation/wifi_service_order_replay_model.py`
- Evidence:
  - `tmp/wifi/v287-wifi-service-order-replay-model/manifest.json`
  - `tmp/wifi/v287-wifi-service-order-replay-model/service-order.json`
  - `tmp/wifi/v287-wifi-service-order-replay-model/replay-stages.json`
  - `tmp/wifi/v287-wifi-service-order-replay-model/summary.md`

## Static Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_service_order_replay_model.py \
  scripts/revalidation/wifi_icnss_boot_timing_compare.py \
  scripts/revalidation/wifi_service_replay_model.py
git diff --check
```

Result: PASS.

## Model Validation

```bash
python3 scripts/revalidation/wifi_service_order_replay_model.py \
  --out-dir tmp/wifi/v287-wifi-service-order-replay-model
```

Result:

```text
decision: wifi-service-order-replay-model-ready
pass: True
out_dir: /home/temmie/dev/A90_5G_rooting/tmp/wifi/v287-wifi-service-order-replay-model
```

## Replay Stages

The model maps Android timing evidence to these boundaries:

| # | event | Android time | boundary | policy |
| --- | --- | --- | --- | --- |
| 1 | `android_wifi_action` | `7.021s` | `vendor.wifi_hal_ext` | blocked HAL service |
| 2 | `wifi_hal_start` | `7.021s` | `vendor.wifi_hal_ext` | blocked HAL service |
| 3 | `cnss_diag_start` | `7.820s` | `cnss_diag` | blocked diagnostic daemon |
| 4 | `wificond_start` | `7.899s` | `wificond` | blocked framework service |
| 5 | `cnss_daemon_start` | `8.090s` | `cnss-daemon` | bounded start-only candidate, not executed |
| 6 | `wlfw_start` | `8.220s` | checkpoint | observe-only |
| 7 | `qmi_server_connected` | `9.435s` | checkpoint | observe-only; no QMI payload |
| 8 | `bdf_download` | `9.509s` | checkpoint | observe-only |
| 9 | `wlan_fw_ready` | `14.511s` | checkpoint | observe-only |
| 10 | `firmware_load` | `14.518s` | checkpoint | observe-only |
| 11 | `wlan_driver_log` | `14.525s` | checkpoint | observe-only |
| 12 | `fw_ready_event` | `14.596s` | checkpoint | observe-only |
| 13 | `wlan_netdev` | `14.815s` | checkpoint | observe-only; no link-up |
| 14 | `wiphy_rfkill` | untimestamped Android evidence | checkpoint | observe-only; no rfkill write |

## Service Classification

- `vendor.wifi_hal_ext`: blocked. Needs binder/hwbinder/hwservicemanager,
  VINTF/interface, property, namespace, capability, and SELinux context review.
- `vendor.wifi_hal_legacy`: blocked sibling candidate with `SYS_MODULE`
  capability risk.
- `cnss_diag`: blocked diagnostic path. Do not start before the primary
  `cnss-daemon` path has a reproducible readiness signal.
- `wificond`: blocked framework service. Needs Android framework/binder/socket
  boundary inventory.
- `cnss-daemon`: only existing bounded start-only candidate, but v287 does not
  execute it.
- `wpa_supplicant` and `hostapd`: blocked until scan/connect/link-up and
  credential policy exists.

## Interpretation

v287 confirms that repeating `cnss-daemon -n -l` in isolation is not the best
next step. Android starts HAL/framework/diagnostic services before and around
`cnss-daemon`, and those services have Android init/HAL context that native init
does not currently reproduce.

The next useful step is to inventory the HAL/framework boundary before trying
to execute any Wi-Fi HAL or `wificond` component.

## Guardrails

- No device command execution.
- No service start.
- No `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd
  execution.
- No QMI payload.
- No QRTR nameservice packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind or `driver_override`.
- No firmware path mutation.
- No reboot/recovery/poweroff.
- No Android partition write.

## Next

Recommended v288:

```text
HAL/framework boundary inventory
```

Scope:

- binder and hwbinder device visibility;
- servicemanager and hwservicemanager assumptions;
- VINTF/interface declarations for Wi-Fi HALs;
- property service assumptions;
- socket paths;
- SELinux/domain assumptions;
- user/group/capability requirements;
- vendor/system linker namespace and library requirements.
