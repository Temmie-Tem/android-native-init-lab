# Native Init V1169 PM-Service Callback Maps Live Report

Date: `2026-05-27`

## Result

- Decision: `v1169-callback-target-mapped-no-esoc0`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1169_PM_CALLBACK_MAPS_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1169-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1169-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1169-pm-callback-maps-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1169-pm-callback-maps-live-after-v490/summary.md`

## Summary

V1169 resolves the V1168 maps gap.  The `pm-service` callback pointer maps to
`libperipheral_client.so`:

| key | value |
| --- | --- |
| callback pointer | `0x7f848eba5c` |
| mapped path | `/tmp/a90-v231-854/root/vendor/lib64/libperipheral_client.so` |
| map perms | `r-xp` |
| map start/end | `0x7f848e9000` / `0x7f848ed000` |
| map offset | `0x6000` |
| file offset | `0x8a5c` |

The branch is therefore not an unknown trampoline.  It is the
`libperipheral_client.so` Binder callback stub that writes the PM state into a
Parcel and calls Binder transact.  Native still does not open
`/dev/subsys_esoc0`, so the next blocker is either Binder callback delivery or
the receiving client-side action after delivery.

## Key Evidence

| key | value |
| --- | --- |
| decision | `v1169-callback-target-mapped-no-esoc0` |
| maps samples | `15` |
| samples with entries | `13` |
| maps entries | `2691` |
| callback branch seen | `true` |
| unique mapped callback | `libperipheral_client.so+0x8a5c` |
| `/dev/subsys_esoc0` | not opened |
| MHI/WLFW/BDF/`wlan0` | all absent |
| Wi-Fi HAL/scan/connect/credentials | not executed |
| DHCP/route/external ping | not executed |

## Disassembly Note

Host-only disassembly of `libperipheral_client.so` around `0x8a5c` shows the
callback stub:

```text
0x8a5c: function entry
0x8ad8: writeInt32(state)
0x8ae0: load remote binder from object+0x10
0x8aec: w1 = 1
0x8af4: w4 = 1
0x8afc: branch through remote binder transact vtable
```

This matches a Binder notification path, not a direct eSoC open path.

## Next Gate

V1170 should trace inside `libperipheral_client.so+0x8a5c`:

- callback entry arguments: object and state
- remote binder pointer from `object+0x10`
- transact call at `0x8afc`
- return path at `0x8b00`

If transact returns success, the next probe moves to the receiving client
process callback handler.  If transact fails, the blocker is Binder callback
delivery.

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_pm_callback_maps_live_v1169.py`
- `python3 scripts/revalidation/native_wifi_pm_callback_maps_live_v1169.py plan`
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1169 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
