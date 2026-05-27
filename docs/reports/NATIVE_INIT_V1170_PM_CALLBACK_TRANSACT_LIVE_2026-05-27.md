# Native Init V1170 PM-Service Callback Transact Live Report

Date: `2026-05-27`

## Result

- Decision: `v1170-state2-transact-success-no-esoc0`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1170_PM_CALLBACK_TRANSACT_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1170-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1170-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1170-pm-callback-transact-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1170-pm-callback-transact-live-after-v490/summary.md`

## Summary

V1170 traced the `libperipheral_client.so+0x8a5c` callback stub mapped by
V1169.  The primary PM `state=2` notification reaches Binder transact and
returns success:

| key | value |
| --- | --- |
| callback entry | `libperipheral_client.so+0x8a5c` |
| `state=2` remote binder | `0xb400007f00200280` |
| `state=2` transact code | `0x1` |
| `state=2` transact flags | `0x1` |
| `state=2` transact return | `0x0` |

This closes the callback-delivery failure branch for the first bring-up
notification.  Native still does not open `/dev/subsys_esoc0`, and
MHI/WLFW/BDF/`wlan0` are still absent.  The next blocker is therefore the
receiving client-side Binder callback handler or the action it should perform
after receiving `state=2`.

## Key Evidence

| key | value |
| --- | --- |
| transact event count | `36` |
| callback entries | `6` |
| transact calls | `6` |
| transact returns | `6` |
| state values | `2, 3, 0, 1` |
| `state=2` returns | `0` |
| non-primary nonzero return | `state=1`, `0xffffffe0` (`-32`) |
| `/dev/subsys_esoc0` | not opened |
| MHI/WLFW/BDF/`wlan0` | all absent |
| Wi-Fi HAL/scan/connect/credentials | not executed |
| DHCP/route/external ping | not executed |

The nonzero `0xffffffe0` return belongs to a later `state=1` notification on a
second remote binder.  It is recorded, but it is not the blocker for the
primary `state=2` bring-up signal because the `state=2` transact returned
success.

## Next Gate

V1171 should trace the receiver side of the successful `state=2` Binder
callback:

- identify the target process/thread for remote binder `0xb400007f00200280`
- trace its callback handler entry and decoded state value
- verify whether the receiver attempts `/dev/subsys_esoc0`, MHI, or any
  intermediate PM action

No Wi-Fi HAL, scan/connect/link-up, credentials, DHCP, route, external ping, or
boot/partition write should be added to this next gate.

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_pm_callback_transact_live_v1170.py`
- `python3 scripts/revalidation/native_wifi_pm_callback_transact_live_v1170.py plan`
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1170 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
