# Native Init V1171 PM Receiver Callback Live Report

Date: `2026-05-27`

## Result

- Decision: `v1171-state2-cnss-callback-dispatched-no-esoc0`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1171_PM_RECEIVER_CALLBACK_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1171-retry-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1171-retry-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1171-retry-pm-receiver-callback-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1171-retry-pm-receiver-callback-live-after-v490/summary.md`

## Summary

V1171 traced the receiver side of the successful V1170 PM `state=2` Binder
callback.  The receiver-side callback is not `pm-proxy`; it is dispatched
inside `cnss-daemon`.

| key | value |
| --- | --- |
| receiver thread | `Binder:4130_2`, `Binder:4130_3` |
| receiver handler | non-virtual thunk at `libperipheral_client.so+0x82cc` |
| decoded PM state sequence | `2, 3, 0, 1` |
| `state=2` read | `true` |
| `state=2` notify call | `true` |
| receiver callback pointer | `0x558e20b340` |
| mapped receiver target | `cnss-daemon` file offset `0xc340` |
| callback mapped to `pm-proxy` | `false` |
| `/dev/subsys_esoc0` | not opened |

This closes the Binder receiver-delivery branch: `pm-service` sends the
`state=2` callback, Binder delivers it, the receiver decodes state `2`, and
the receiver calls its local EventNotifier callback.  The remaining blocker is
inside the mapped `cnss-daemon` callback function or the action branch below
that callback, because `/dev/subsys_esoc0`, MHI, WLFW, BDF, and `wlan0` still
do not appear.

## Key Evidence

| key | value |
| --- | --- |
| receiver event count | `28` |
| receiver thunk entries | `4` |
| receiver thunk returns | `4`, all `0x0` |
| receiver state reads | `4` |
| receiver notify calls | `4` |
| EventNotifier branch calls | `4` |
| `cnss-daemon` maps samples | `6`, with entries in `5` samples |
| `pm-proxy` maps samples | `6`, with entries in `3` samples |
| Wi-Fi HAL/scan/connect/credentials | not executed |
| DHCP/route/external ping | not executed |

The unique mapped callback is:

| pointer | binary | perms | file offset | receiver |
| --- | --- | --- | --- | --- |
| `0x558e20b340` | `/tmp/a90-v231-924/root/vendor/bin/cnss-daemon` | `r-xp` | `0xc340` | `cnss-daemon` |

## Next Gate

V1172 should trace the mapped `cnss-daemon` callback body at file offset
`0xc340` and its PM/eSoC action branch:

- identify whether the callback evaluates state `2` as actionable
- trace any branch toward PM client, eSoC, MHI, or subsystem open logic
- keep the gate bounded and stop before Wi-Fi HAL, scan/connect, credentials,
  DHCP, route, external ping, boot image write, or partition write

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_pm_receiver_callback_live_v1171.py`
- `python3 scripts/revalidation/native_wifi_pm_receiver_callback_live_v1171.py plan`
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1171 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
