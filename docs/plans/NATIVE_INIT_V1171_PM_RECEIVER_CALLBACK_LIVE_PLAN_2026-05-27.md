# Native Init V1171 PM Receiver Callback Live Plan

Date: `2026-05-27`

## Goal

Trace the receiver side of the successful V1170 `state=2` Binder callback.
The purpose is to determine which PM client receives the callback and whether
it dispatches its local callback function before any Wi-Fi HAL or scan/connect
action.

## Preconditions

- Native v724 is healthy.
- Serial bridge is available on `127.0.0.1:54321`.
- V401 selinuxfs mount and V490 policy-load proof are rerun in the same boot.
- Helper `a90_android_execns_probe v217` remains deployed.
- V1170 proved the primary `state=2` Binder transact returns `0x0`.

## Added Uprobes

| label | binary | offset | fetch |
| --- | --- | --- | --- |
| `pm_receiver_cb_ontransact_entry` | `libperipheral_client.so` | `0x824c` | `this=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4` |
| `pm_receiver_cb_read_state_return` | `libperipheral_client.so` | `0x8284` | `this=%x20 data=%x19 state=%x0` |
| `pm_receiver_cb_notify_call` | `libperipheral_client.so` | `0x8294` | `this=%x20 state=%x1 notify_target=%x8` |
| `pm_receiver_cb_ontransact_ret` | `libperipheral_client.so` | `0x824c` | `ret=$retval` |
| `pm_receiver_cb_ontransact_thunk_entry` | `libperipheral_client.so` | `0x82cc` | `this=%x0 code=%x1 data=%x2 reply=%x3 flags=%x4` |
| `pm_receiver_cb_thunk_read_state_return` | `libperipheral_client.so` | `0x8304` | `this=%x20 data=%x19 state=%x0` |
| `pm_receiver_cb_thunk_notify_call` | `libperipheral_client.so` | `0x8314` | `this=%x20 state=%x1 notify_target=%x8` |
| `pm_receiver_cb_ontransact_thunk_ret` | `libperipheral_client.so` | `0x82cc` | `ret=$retval` |
| `pm_event_notifier_entry` | `libperipheral_client.so` | `0x6d84` | `object=%x0 state=%x1` |
| `pm_event_notifier_callback_ready` | `libperipheral_client.so` | `0x6d8c` | `object=%x0 state=%x1 callback=%x2` |
| `pm_event_notifier_callback_branch` | `libperipheral_client.so` | `0x6d90` | `callback_arg=%x0 state=%x1 callback=%x2` |

## Success Criteria

- Manifest decision is one of:
  - `v1171-state2-cnss-callback-dispatched-no-esoc0`
  - `v1171-state2-receiver-callback-dispatched-no-esoc0`
  - `v1171-state2-receiver-callback-dispatched-unmapped`
  - `v1171-state2-receiver-ontransact-no-notifier-branch`
  - `v1171-receiver-callback-not-observed-after-state2-transact`
- Receiver event count and `state=2` decode/branch status are recorded.
- `cnss-daemon` and `pm-proxy` maps samples are recorded so callback branch
  pointers can be mapped to the receiver process image.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, or flash is performed.

## Next Branches

- Receiver callback dispatched and mapped: trace the mapped receiver callback
  function body and its PM/eSoC action branch.
- Receiver onTransact without notifier branch: classify Parcel decode or
  interface-check path.
- No receiver event: classify Binder one-way delivery timing or target-process
  lifetime before changing PM ordering.
