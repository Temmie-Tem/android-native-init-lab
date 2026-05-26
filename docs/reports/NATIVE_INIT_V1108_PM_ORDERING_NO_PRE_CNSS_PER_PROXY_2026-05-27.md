# V1108 PM Ordering No Pre-CNSS `per_proxy` Report

Date: 2026-05-27

## Result

- Decision: `v1108-no-pre-cnss-per-proxy-cnss-connect-path-reached`
- Pass: `true`
- Evidence: `tmp/wifi/v1108-pm-ordering-no-pre-cnss-per-proxy-live/manifest.json`
- Helper: `a90_android_execns_probe v207`

## Key Evidence

- PM observer order was `servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,pm_proxy_helper,per_mgr,vndservice_query,per_proxy_skipped,cnss_daemon,vndservice_query`.
- `per_proxy_start_executed=0`
- `child.per_proxy.start_skipped=1`
- `start_cnss_before_per_proxy=1`
- `cnss_daemon_start_executed=1`
- `child.cnss_daemon.post_start_ready=1`
- `pm_client_register_ret=['0x0']`
- `pm_client_connect_ret=['0x0']`
- PM server Binder path returned `pm_server_register_ret=['0x0']` and `pm_server_connect_ret=['0x0']`.
- `mdm3_state=OFFLINING`

## Safety

- `wifi_hal_start_executed=0`
- `scan_connect_linkup=0`
- `external_ping=0`
- `subsys_esoc0_open_attempted=0`
- `all_postflight_safe=1`
- Postflight showed no forbidden Wi-Fi link or actor hits.
- Final `selftest` remained `pass=11 warn=1 fail=0`.

## Interpretation

Skipping pre-CNSS `per_proxy` removes the V1106/V1107 CNSS mutex wait blocker. CNSS now reaches both PM register and PM connect, and both return success. The blocker moved downward: even after a successful CNSS PM connect, `mdm3` remains `OFFLINING`, so the next gate should classify lower PM/eSoC side effects after the successful CNSS connect before any Wi-Fi HAL, scan, or connect attempt.

## Next Step

V1109 should trace or snapshot the lower PM/eSoC state immediately after successful CNSS PM connect:

- PM server pending main-thread raw mutex lock state;
- `pm-service` thread `wchan`/syscall samples after connect return;
- `/sys/bus/msm_subsys/devices/subsys9/state`;
- eSoC/sysfs read-only status;
- dmesg delta for PM/eSoC/modem/firmware markers.

