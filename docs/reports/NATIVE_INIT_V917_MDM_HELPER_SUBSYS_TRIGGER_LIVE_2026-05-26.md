# Native Init V917 mdm_helper Subsys Trigger Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper v150 deploy | `tmp/wifi/v917-execns-helper-v150-deploy-preflight/manifest.json` | `execns-helper-v150-deploy-pass` |
| bounded trigger live gate | `tmp/wifi/v917-mdm-helper-subsys-trigger-capture-live/manifest.json` | `v917-trigger-not-attempted-no-esoc-fd` |

V917 deployed helper `v150` and ran the corrected bounded `mdm_helper` runtime-subsys-trigger capture. The run was safe and clean, but the trigger child did not execute because the current helper gates only on the first window snapshot.

## Evidence

- Helper deploy used serial transfer because host NCM lacked `192.168.7.1/24` and noninteractive sudo was unavailable.
- Serial transfer used safe chunk size `1850`: `chunks_written=837`, `max_cmdv1_line_bytes=3890`, `safe_line_limit=3968`.
- Remote helper v150 deploy passed.
- `mdm_helper` started and was observable.
- Window snapshot: `/dev/esoc-0` fd count `0`.
- Final snapshot: `/dev/esoc-0` fd count `1`.
- Because the gate checked only the first window, `subsys_trigger.started=0` and `/dev/subsys_esoc0` was not opened.
- `all_postflight_safe=1`; no cleanup reboot was required.

## Guardrails

- `pm_proxy_helper_start_executed=0`.
- `service_manager_start_executed=0`.
- `cnss_start_executed=0`.
- `wifi_hal_start_executed=0`.
- `scan_connect_linkup=0`.
- `credentials=0`.
- `dhcp_routing=0`.
- `external_ping=0`.
- `notify_attempted=0`.
- `boot_done_attempted=0`.

## Interpretation

V917 shows the next blocker is not absence of `mdm_helper` `/dev/esoc-0` usage. It appears after the initial observation window. The helper must wait for `/dev/esoc-0` to appear within the bounded runtime window, then trigger `/dev/subsys_esoc0` immediately when the gate becomes true.

## Next

V918 should update helper logic from single-window gating to bounded wait-until-`/dev/esoc-0` gating, rebuild as helper `v151`, deploy, and rerun the same live proof. Primary review remains WLFW/BDF/wlan0 progression; lower eSoC markers remain diagnostic.
