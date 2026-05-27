# Native Init V1119 PM Register Failure Host Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1119-pm-register-pre-server-provider-lookup-gap-classified`
- Pass: `true`
- Evidence: `tmp/wifi/v1119-pm-register-failure-host-classifier/manifest.json`
- Summary: `tmp/wifi/v1119-pm-register-failure-host-classifier/summary.md`
- Classifier:
  `scripts/revalidation/native_wifi_pm_register_failure_host_classifier_v1119.py`

## Summary

V1119 is host-only. It reconciles V1118 tracefs evidence with
`libperipheral_client.so` disassembly.

The V1071 BPF-uprobe direction is not the current blocker anymore: V1083 already
classified the original `pm-service` exit path. The active blocker is now
CNSS `pm_client_register` returning `0xffffffff` under the V1118 zero-delay
PM observer order.

## Evidence

V1118 trace counts:

```text
pm_client_register_entry=1
pm_client_register_ret=1
pm_client_connect_entry=0
pm_client_connect_ret=0
pm_server_register_entry=0
pm_server_register_ret=0
pm_server_connect_entry=0
pm_server_connect_ret=0
```

V1118 captured CNSS register args:

```text
peripheral=modem
client=cnss-daemon
```

V1118 PM contract:

```text
vndservice_provider_seen=0
child.per_mgr.exited=1
child.per_mgr.exit_code=0
child.per_mgr.signal=0
start_cnss_zero_delay_after_per_mgr=1
```

`libperipheral_client.so` model:

```text
pm_client_register      0x6ec8 size=756
pm_register_connect     0x612c size=1492
pm_client_connect       0x7544 size=216
```

The host disassembly shows:

- `pm_client_register` validates args, creates the PM client object, then calls
  `pm_register_connect` at `0x7034`.
- The observed valid CNSS args exclude the argument-validation failure path.
- `pm_client_register` returns `-1` when `pm_register_connect` returns nonzero.
- `pm_register_connect` initializes `/dev/vndbinder`, looks up
  `vendor.qcom.PeripheralManager`, converts the binder to
  `IPeripheralManager`, and only then calls the remote register method.

## Interpretation

The current blocker is pre-server PM provider lookup/interface readiness, not
PM server register rejection:

- `pm_server_register_entry=0` means no server-side register handler was reached.
- `pm_client_connect_entry=0` means the failure happens before connect.
- `vndservice_provider_seen=0` and clean `per_mgr` exit make provider lookup
  the dominant explanation.

V1119 is intentionally host-only, so it does not claim the exact instruction
branch was live-hit. It narrows V1120 to internal `pm_register_connect` tracefs
uprobes only.

## V1120 Trace Candidates

| label | offset | purpose |
| --- | --- | --- |
| `pm_register_connect_entry` | `0x612c` | prove CNSS enters the lower helper |
| `pm_register_connect_service_null_check` | `0x620c` | test `vendor.qcom.PeripheralManager` lookup null |
| `pm_register_connect_interface_null_check` | `0x6254` | test `IPeripheralManager::asInterface` null |
| `pm_register_connect_remote_register_call` | `0x6274` | prove remote register transaction is attempted |
| `pm_register_connect_remote_register_return_check` | `0x6278` | capture remote register return |
| `pm_register_connect_ret` | `0x612c` | record helper return to `pm_client_register` |

## Safety

- `device_commands_executed=False`
- `tracefs_write_executed=False`
- `bpf_attach_executed=False`
- `pm_actor_executed=False`
- `cnss_daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `credential_use_executed=False`
- `dhcp_route_executed=False`
- `external_ping_executed=False`
- `wifi_bringup_executed=False`
- `partition_write_executed=False`
- `flash_executed=False`
- `reboot_executed=False`

## Next

V1120 should add the internal `pm_register_connect` tracefs events above and run
the same zero-delay gate. The goal is to prove whether the live branch is:

1. service lookup null,
2. interface conversion null, or
3. remote register transaction failure.
