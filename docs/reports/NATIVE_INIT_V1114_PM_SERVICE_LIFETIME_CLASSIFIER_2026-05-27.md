# V1114 PM-Service Lifetime Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1114-select-immediate-cnss-after-per-mgr-start-gate`
- Pass: `true`
- Evidence: `tmp/wifi/v1114-pm-service-lifetime-classifier/manifest.json`
- Collector: `scripts/revalidation/native_wifi_pm_service_lifetime_classifier_v1114.py`

## Summary

V1114 parsed V1113 evidence host-only and classified the missing CNSS PM
register/connect returns.

Key facts:

```text
global_ok=true
per_mgr_start_executed=1
per_mgr_post_start_probe_wait_ms=1000
per_mgr_post_start_observable=0
per_mgr_post_start_ready=0
per_mgr_exited=1
per_mgr_exit_code=0
per_mgr_signal=0
per_mgr_subsys_modem_seen=0
pm_proxy_helper_subsys_modem_seen=1
pm_client_register_entry_count=0
pm_client_register_ret=[]
pm_client_connect_entry_count=0
pm_client_connect_ret=[]
cnss_daemon_hit_count=0
vendor_qcom_peripheral_manager_seen=0
```

The current V1113 observer starts `per_mgr`, waits 1000 ms, runs a `vndservice`
query, skips `per_proxy`, and then starts `cnss-daemon`. By the time the 1000 ms
post-start probe runs, `pm-service` is already not observable and later appears
as exited with `exit_code=0`.

## Interpretation

The V1113 failure is now a timing/lifetime problem, not a lower firmware holder
problem:

- global firmware + modem holder succeeds;
- `pm_proxy_helper` holds a private `/dev/subsys_modem` fd;
- `pm-service` does not survive long enough to be ready for CNSS;
- CNSS PM client uprobes have zero hits.

Therefore the next useful gate is not Wi-Fi HAL and not a wider scan/connect
test. The next gate should remove the current 1000 ms delay before CNSS and
sample `pm-service` immediately after fork.

## Safety

- `device_commands_executed=false`
- `tracefs_write_executed=false`
- `pm_actor_executed=false`
- `cnss_daemon_start_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `reboot_executed=false`

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_service_lifetime_classifier_v1114.py
python3 scripts/revalidation/native_wifi_pm_service_lifetime_classifier_v1114.py plan
python3 scripts/revalidation/native_wifi_pm_service_lifetime_classifier_v1114.py run
```

Run result:

```text
decision: v1114-select-immediate-cnss-after-per-mgr-start-gate
pass: True
```

## Next

V1115 should be source/build-only first:

- add a helper flag/order for immediate CNSS after `per_mgr` start;
- skip the current 1000 ms `per_mgr` settle wait before CNSS;
- skip the pre-CNSS `vndservice` query in that immediate branch;
- capture sub-1000 ms `pm-service` observable/fd/exit state;
- keep `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  and external ping forbidden.
