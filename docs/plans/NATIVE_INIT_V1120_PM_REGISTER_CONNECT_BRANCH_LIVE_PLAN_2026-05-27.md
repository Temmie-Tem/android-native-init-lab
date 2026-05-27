# Native Init V1120 PM Register Connect Branch Live Plan

Date: `2026-05-27`

## Goal

Turn the V1119 host-only provider lookup classification into live branch
evidence inside `libperipheral_client.so` `pm_register_connect()`.

## Context

V1118 proved the zero-delay PM observer order still returns
`pm_client_register_ret=0xffffffff`. V1119 showed this is pre-server:

- CNSS register args are valid: `peripheral=modem`, `client=cnss-daemon`.
- `pm_server_register_entry=0`.
- `pm_client_connect_entry=0`.
- `vndservice_provider_seen=0`.

The remaining uncertainty is the exact live branch in `pm_register_connect()`:

1. service lookup null,
2. `IPeripheralManager::asInterface` null,
3. remote register transaction failure.

## Trace Additions

V1120 reuses the V1118 global firmware + modem holder + zero-delay CNSS gate and
adds these tracefs uprobes:

| label | offset | purpose |
| --- | --- | --- |
| `pm_register_connect_entry` | `0x612c` | lower helper entry |
| `pm_register_connect_service_null_check` | `0x620c` | provider binder null branch |
| `pm_register_connect_interface_null_check` | `0x6254` | interface conversion null branch |
| `pm_register_connect_remote_register_call` | `0x6274` | remote register attempted |
| `pm_register_connect_remote_register_return_check` | `0x6278` | remote register return |
| `pm_register_connect_ret` | `0x612c` | helper return |

## Live Command

```bash
python3 scripts/revalidation/native_wifi_pm_register_connect_branch_live_v1120.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

## Safety

- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No DHCP, route, credentials, or external ping.
- No partition write or flash.
- Cleanup reboots back into native init and checks `bootstatus`, `selftest`, and
  `netservice status`.

## Success Criteria

- Tracefs collector passes.
- Global firmware mount and `/dev/subsys_modem` holder precondition pass.
- CNSS enters `pm_register_connect()`.
- Branch classification chooses service lookup null, interface null, or remote
  register failure.
