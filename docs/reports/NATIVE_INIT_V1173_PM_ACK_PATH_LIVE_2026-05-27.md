# Native Init V1173 PM Ack Path Live Report

Date: `2026-05-27`

## Result

- Decision: `v1173-state2-ack-client-server-success-no-esoc0`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1173_PM_ACK_PATH_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1173-rerun-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1173-rerun-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1173-rerun-pm-ack-path-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1173-rerun-pm-ack-path-live-after-v490/summary.md`

## Summary

V1173 traced the PM acknowledge path below V1172.  The primary `state=2`
acknowledge leaves `cnss-daemon`, reaches the PM-service Binder transaction
code `5` handler, calls the PM-service ack implementation, and returns `0x0`
on both client and server sides.  It still does not open `/dev/subsys_esoc0`.

| key | value |
| --- | --- |
| event count | `50` |
| client ack states | `2, 3, 0, 1` |
| server transaction codes | `0x5f4e5446, 1, 3, 5, 5` repeated |
| server ack states | `2, 3, 0, 1` |
| client ack returns | `4`, all `0x0` |
| server ack write returns | `2`, all `0x0` |
| server onTransact returns | `10`, all `0x0` |
| `/dev/subsys_esoc0` | not opened |

This closes the PM acknowledge path as the missing eSoC trigger.  The blocker is
not CNSS callback delivery and not PM ack completion.  The remaining gap is
below, or adjacent to, the mapped PM-service ack implementation body or another
Android actor that runs after PM notification/ack and before eSoC power-up.

## Key Evidence

| label | count |
| --- | --- |
| `pm_client_ack_entry` | `4` |
| `pm_client_ack_match` | `4` |
| `pm_client_ack_virtual_call` | `4` |
| `pm_client_ack_ret` | `4` |
| `pm_server_ontransact_entry` | `10` |
| `pm_server_ack_read_handle` | `4` |
| `pm_server_ack_read_state` | `4` |
| `pm_server_ack_impl_call` | `4` |
| `pm_server_ack_write_ret` | `2` |
| `pm_server_ontransact_ret` | `10` |

For the primary `state=2` path:

| key | value |
| --- | --- |
| client virtual target | `libperipheral_client.so+0x915c` |
| server implementation target | `pm-service+0x63f4` |
| client ack return | `0x0` |
| PM-service code `5` branch | observed |
| PM-service ack state | `0x2` |
| PM-service onTransact return | `0x0` |

`pm_client_ack_virtual_ret` did not fire in the live trace.  The classifier no
longer treats that return-site miss as a blocker because the enclosing
`pm_client_event_acknowledge` uretprobe returned `0x0`, and the PM-service code
`5` branch plus ack implementation call were directly observed.

## Next Gate

The next unit should trace or classify the mapped PM-service ack implementation
body at file offset `0x63f4`, then compare Android-good post-ack actor timing:

- disassemble `pm-service+0x63f4` and select low-risk uprobe offsets
- verify whether the ack implementation only updates PM state or invokes a
  delayed action path
- compare Android-good timing after PM ack and before `/dev/subsys_esoc0`
- keep the next gate bounded; do not start Wi-Fi HAL, scan/connect, credentials,
  DHCP, route, external ping, boot image write, or partition write

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_pm_ack_path_live_v1173.py`
- `python3 scripts/revalidation/native_wifi_pm_ack_path_live_v1173.py plan`
- Existing raw V1173 trace re-parsed to the success classification.
- `git diff --check`
- Secret scan over V1173 script, plan, report, and `docs/README.md`.
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1173 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
