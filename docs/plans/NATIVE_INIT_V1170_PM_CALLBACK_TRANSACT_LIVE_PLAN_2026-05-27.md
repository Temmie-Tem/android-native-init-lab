# Native Init V1170 PM-Service Callback Transact Live Plan

Date: `2026-05-27`

## Goal

Trace inside the `libperipheral_client.so+0x8a5c` callback stub mapped by
V1169.  The purpose is to determine whether the PM state callback Binder
transaction succeeds or fails before native attempts any Wi-Fi HAL or
scan/connect action.

## Preconditions

- Native v724 is healthy.
- Serial bridge is available on `127.0.0.1:54321`.
- V401 selinuxfs mount and V490 policy-load proof are rerun in the same boot.
- Helper `a90_android_execns_probe v217` remains deployed.
- V1169 mapped callback pointer to `libperipheral_client.so+0x8a5c`.

## Added Uprobes

| label | binary | offset | fetch |
| --- | --- | --- | --- |
| `pm_client_callback_stub_entry` | `libperipheral_client.so` | `0x8a5c` | `object=%x0 state=%x1` |
| `pm_client_callback_write_state` | `libperipheral_client.so` | `0x8adc` | `parcel=%x0 state=%x1` |
| `pm_client_callback_remote_binder` | `libperipheral_client.so` | `0x8ae4` | `object=%x20 remote_binder=%x0 state_saved=%x19` |
| `pm_client_callback_transact_call` | `libperipheral_client.so` | `0x8afc` | `remote_binder=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4 transact_target=%x8 state_saved=%x19` |
| `pm_client_callback_transact_return` | `libperipheral_client.so` | `0x8b00` | `transact_ret=%x0 state_saved=%x19` |
| `pm_client_callback_function_ret` | `libperipheral_client.so` | `0x8a5c` | `ret=$retval` |

## Success Criteria

- Manifest decision is one of:
  - `v1170-state2-transact-success-no-esoc0`
  - `v1170-state2-callback-transact-failed`
  - `v1170-callback-transact-failed-nonprimary`
  - `v1170-callback-transact-success-no-esoc0`
  - `v1170-callback-transact-return-missing`
  - `v1170-callback-transact-call-missing`
- Callback transact event count is greater than zero.
- Primary `state=2` transact result is classified separately from later
  non-primary state notifications.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, or flash is performed.

## Next Branches

- Transact success with no eSoC: trace the receiving client-side Binder
  callback handler.
- Transact failure: classify Binder status and object lifetime.
- Transact call without return: classify blocking inside Binder transact.
