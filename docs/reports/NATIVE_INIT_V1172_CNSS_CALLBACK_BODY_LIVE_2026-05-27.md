# Native Init V1172 CNSS Callback Body Live Report

Date: `2026-05-27`

## Result

- Decision: `v1172-cnss-state2-ack-only-no-esoc0`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1172_CNSS_CALLBACK_BODY_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1172-rerun2-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1172-rerun2-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1172-rerun2-cnss-callback-body-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1172-rerun2-cnss-callback-body-live-after-v490/summary.md`

## Summary

V1172 traced the mapped V1171 target in `cnss-daemon` at file offset `0xc340`.
The `state=2` receiver callback enters `cnss-daemon`, loads the PM handle, calls
`pm_client_event_acknowledge`, and returns `0x0`.  It does not open
`/dev/subsys_esoc0` and does not branch toward MHI/WLFW bring-up.

| key | value |
| --- | --- |
| callback thread | `Binder:4140_2` |
| callback entry count | `4` |
| decoded state sequence | `2, 3, 0, 1` |
| acknowledge state sequence | `2, 3, 0, 1` |
| callback returns | `4`, all `0x0` |
| state `2` entry | `true` |
| state `2` acknowledge call | `true` |
| `/dev/subsys_esoc0` | not opened |

This closes the `cnss-daemon` receiver callback body as an eSoC action source.
The callback is an ack-only path for the PM notification.  The remaining blocker
is either below `pm_client_event_acknowledge` on the PM-service side, or another
Android actor that independently advances eSoC after the PM callback/ack
sequence.

## Key Evidence

| label | count |
| --- | --- |
| `cnss_pm_callback_entry` | `4` |
| `cnss_pm_callback_meta_loaded` | `4` |
| `cnss_pm_callback_handle_loaded` | `4` |
| `cnss_pm_callback_ack_call` | `4` |
| `cnss_pm_callback_ret` | `4` |

For the primary `state=2` callback:

| key | value |
| --- | --- |
| object | `0x558559e9d8` |
| object id | `0x1` |
| PM handle | `0xb400007f7e20a060` |
| ack call state | `0x2` |
| return | `0x0` |

## Next Gate

V1173 should classify the PM acknowledge side or the next Android actor:

- trace `pm_client_event_acknowledge` and the corresponding PM-service ack
  handler to see whether ack completion should trigger eSoC
- compare Android-good PM/eSoC timing for any actor after CNSS ack but before
  `/dev/subsys_esoc0`
- keep the next gate bounded; do not start Wi-Fi HAL, scan/connect, credentials,
  DHCP, route, external ping, boot image write, or partition write

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_cnss_callback_body_live_v1172.py`
- `python3 scripts/revalidation/native_wifi_cnss_callback_body_live_v1172.py plan`
- Collector generation sanity confirmed `CNSS_BIN`, `cnss` binary-key handling,
  and `cnss_pm_callback_entry` registration.
- `git diff --check`
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1172 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
