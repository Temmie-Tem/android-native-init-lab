# Native Init V1172 CNSS Callback Body Live Plan

Date: `2026-05-27`

## Goal

Trace the mapped V1171 receiver target inside `cnss-daemon` at file offset
`0xc340`.  The purpose is to determine whether the `state=2` receiver callback
contains an actionable PM/eSoC branch, or whether it only acknowledges the PM
event and returns.

## Preconditions

- Native v724 is healthy.
- Serial bridge is available on `127.0.0.1:54321`.
- V401 selinuxfs mount and V490 policy-load proof are rerun in the same boot.
- Helper `a90_android_execns_probe v217` remains deployed.
- V1171 proved `state=2` is delivered to `cnss-daemon+0xc340`.

## Host Classification

Host disassembly of `vendor/bin/cnss-daemon` shows the mapped callback body:

| offset | meaning |
| --- | --- |
| `0xc340` | callback function entry, args `object=%x0 state=%x1` |
| `0xc354` | object metadata loaded from `[object+8]` |
| `0xc37c` | PM handle loaded from `[object]` |
| `0xc38c` | tail branch to `pm_client_event_acknowledge@plt` |
| `0xc340` return probe | callback return value after direct return or tail-call completion |

## Added Uprobes

| label | binary | offset | fetch |
| --- | --- | --- | --- |
| `cnss_pm_callback_entry` | `cnss-daemon` | `0xc340` | `object=%x0 state=%x1` |
| `cnss_pm_callback_meta_loaded` | `cnss-daemon` | `0xc354` | `object=%x0 state_arg=%x1 object_id=%x4` |
| `cnss_pm_callback_handle_loaded` | `cnss-daemon` | `0xc37c` | `object=%x20 pm_handle=%x0 state_saved=%x19` |
| `cnss_pm_callback_ack_call` | `cnss-daemon` | `0xc38c` | `pm_handle=%x0 state_arg=%x1` |
| `cnss_pm_callback_ret` | `cnss-daemon` | `0xc340` | `ret=$retval` |

## Success Criteria

- Manifest decision is one of:
  - `v1172-cnss-state2-ack-only-no-esoc0`
  - `v1172-cnss-state2-callback-no-ack`
  - `v1172-cnss-callback-body-not-observed`
  - `v1172-cnss-callback-opened-esoc0`
- `state=2` callback entry and acknowledge-call status are recorded.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, or flash is performed.

## Next Branches

- Ack-only with no eSoC: classify whether `pm_client_event_acknowledge` or a
  different Android actor is responsible for advancing eSoC.
- No ack call: trace callback null/guard branch and object lifetime.
- eSoC open observed: move to bounded MHI/WLFW/BDF publication gate.
