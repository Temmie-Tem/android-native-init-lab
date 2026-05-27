# Native Init V1120 PM Register Connect Branch Live Report

Date: `2026-05-27`

## Result

- Decision: `v1120-pm-register-connect-service-lookup-null`
- Pass: `true`
- Evidence: `tmp/wifi/v1120-pm-register-connect-branch-live/manifest.json`
- Summary: `tmp/wifi/v1120-pm-register-connect-branch-live/summary.md`
- Runner:
  `scripts/revalidation/native_wifi_pm_register_connect_branch_live_v1120.py`

## Summary

V1120 added internal `pm_register_connect()` uprobes to the V1118 zero-delay
gate. The live branch is now proven:

```text
pm_register_connect_entry=1
pm_register_connect_service_null_check=1
service_binder_values=['0x0']
pm_register_connect_interface_null_check=0
pm_register_connect_remote_register_call=0
pm_register_connect_ret=['0xffffffff']
```

This means `cnss-daemon` reaches `pm_register_connect()`, but
`defaultServiceManager()->getService("vendor.qcom.PeripheralManager")` returns
null. The call does not reach `IPeripheralManager::asInterface()`, the remote
register transaction, PM server register handling, or PM connect.

## Branch Evidence

| event | CNSS count |
| --- | --- |
| `pm_client_register_entry` | `1` |
| `pm_client_register_ret` | `1` |
| `pm_client_connect_entry` | `0` |
| `pm_server_register_entry` | `0` |
| `pm_register_connect_entry` | `1` |
| `pm_register_connect_service_null_check` | `1` |
| `pm_register_connect_interface_null_check` | `0` |
| `pm_register_connect_remote_register_call` | `0` |
| `pm_register_connect_remote_register_return_check` | `0` |
| `pm_register_connect_ret` | `1` |

Branch values:

```json
{
  "interface_values": [],
  "pm_client_register_ret": [
    "0xffffffff"
  ],
  "pm_register_connect_ret": [
    "0xffffffff"
  ],
  "remote_register_return_values": [],
  "service_binder_values": [
    "0x0"
  ]
}
```

## Contract

```text
start_cnss_zero_delay_after_per_mgr=1
per_mgr_exited=1
per_mgr_exit_code=0
vndservice_provider_seen=0
per_proxy_start_executed=0
child.per_proxy.start_skipped=1
```

Global holder preconditions passed:

```text
firmware_mounts_executed=True
global_modem_holder_opened=True
tracefs_write_executed=True
cnss_daemon_start_executed=True
```

Cleanup returned to healthy native init:

```text
version_seen=True
status_healthy=True
selftest: pass=11 warn=1 fail=0
netservice: disabled tcpctl=stopped
```

## Interpretation

The active blocker is no longer ambiguous. It is provider lifetime/readiness:

- `pm-service` exits cleanly before the provider remains available.
- `vendor.qcom.PeripheralManager` is not visible to `cnss-daemon` at PM
  register time.
- `per_proxy` was intentionally skipped before CNSS, so V1120 does not test the
  Android `init.svc.vendor.per_mgr=running -> per_proxy` provider lifetime
  sequence.

The next gate should keep `vendor.qcom.PeripheralManager` registered long enough
for `cnss-daemon` to resolve it, while avoiding the earlier pre-CNSS `per_proxy`
mutex wait regression.

## Safety

- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `credential_use_executed=False`
- `dhcp_route_executed=False`
- `external_ping_executed=False`
- `wifi_bringup_executed=False`
- `partition_write_executed=False`
- `flash_executed=False`

## Next

V1121 should define the smallest provider-lifetime repair. Candidate directions:

1. start `cnss-daemon` only after `vendor.qcom.PeripheralManager` is visible,
2. keep `per_mgr` alive by reproducing the required Android service lifecycle,
3. reintroduce only the minimal `per_proxy`/provider readiness step after
   proving it does not recreate the pre-CNSS mutex wait blocker.
