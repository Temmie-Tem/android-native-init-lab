# Native Init V1173 PM Ack Path Live Plan

Date: `2026-05-27`

## Goal

Trace the PM acknowledge path below V1172.  V1172 proved
`cnss-daemon+0xc340` only calls `pm_client_event_acknowledge`; V1173 verifies
whether that acknowledge reaches the PM-service Binder handler and whether the
server ack path opens eSoC or only returns.

## Preconditions

- Native v724 is healthy.
- Serial bridge is available on `127.0.0.1:54321`.
- V401 selinuxfs mount and V490 policy-load proof are rerun in the same boot.
- Helper `a90_android_execns_probe v217` remains deployed.
- V1172 proved `cnss-daemon` receives `state=2` and calls
  `pm_client_event_acknowledge`.

## Host Classification

`libperipheral_client.so` disassembly shows:

| offset | meaning |
| --- | --- |
| `0x76f0` | `pm_client_event_acknowledge` entry |
| `0x7754` | client record matched; per-client mutex lock path |
| `0x7780` | virtual call through client manager object |
| `0x7784` | virtual call return |
| `0x85bc` | `BnPeripheralManager::onTransact` entry |
| `0x8728` | transaction code `5` branch; read PM handle and state |
| `0x8760` | server virtual ack implementation call |
| `0x8814` | write server method return to reply |

## Added Uprobes

| label | binary | offset | fetch |
| --- | --- | --- | --- |
| `pm_client_ack_entry` | `libperipheral_client.so` | `0x76f0` | `pm_handle=%x0 state=%x1` |
| `pm_client_ack_match` | `libperipheral_client.so` | `0x7754` | `pm_handle=%x20 state_saved=%x19` |
| `pm_client_ack_virtual_call` | `libperipheral_client.so` | `0x7780` | `manager=%x0 pm_handle_arg=%x1 state_arg=%x2 target=%x8` |
| `pm_client_ack_virtual_ret` | `libperipheral_client.so` | `0x7784` | `ret=%x0 state_saved=%x19` |
| `pm_client_ack_ret` | `libperipheral_client.so` | `0x76f0` | `ret=$retval` |
| `pm_server_ontransact_entry` | `libperipheral_client.so` | `0x85bc` | `this=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4` |
| `pm_server_ack_read_handle` | `libperipheral_client.so` | `0x8744` | `this=%x20 handle=%x22` |
| `pm_server_ack_read_state` | `libperipheral_client.so` | `0x8750` | `this=%x20 handle=%x22 state=%x0` |
| `pm_server_ack_impl_call` | `libperipheral_client.so` | `0x8760` | `this=%x0 handle=%x1 state=%x2 target=%x8` |
| `pm_server_ack_write_ret` | `libperipheral_client.so` | `0x8814` | `ret=%x0` |
| `pm_server_ontransact_ret` | `libperipheral_client.so` | `0x85bc` | `ret=$retval` |

## Success Criteria

- Manifest decision is one of:
  - `v1173-state2-ack-client-server-success-no-esoc0`
  - `v1173-state2-ack-client-no-server`
  - `v1173-state2-ack-client-missing`
  - `v1173-ack-path-opened-esoc0`
- Client `state=2` ack entry/call/return status is recorded.
- Server transaction code `5` ack branch status is recorded.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, or flash is performed.

## Next Branches

- Client and server ack success with no eSoC: trace the mapped PM-service ack
  implementation body or compare Android actor timing after ack.
- Client ack with no server ack: classify Binder transaction target/timing.
- eSoC opens: move to bounded MHI/WLFW/BDF publication gate.
