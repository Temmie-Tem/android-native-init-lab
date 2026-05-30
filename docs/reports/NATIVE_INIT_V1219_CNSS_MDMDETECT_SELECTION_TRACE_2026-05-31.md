# Native Init V1219 CNSS mdmdetect Selection Trace Report

Date: `2026-05-31`

## Result

- Decision: `v1219-mdmdetect-entry-not-sdxprairie`
- Pass: `false`
- Helper: `a90_android_execns_probe v252`
- Runner: `scripts/revalidation/native_wifi_cnss_mdmdetect_selection_trace_v1219.py`
- Evidence: `tmp/wifi/v1219-cnss-mdmdetect-selection-trace/manifest.json`

## Summary

V1219 reused the V1218 bounded PM/CNSS observer with fake
`esoc_name=SDXPRAIRIE`, then added tracefs uprobes on `cnss-daemon` and
`libmdmdetect.so`.

The result narrows the blocker from "cnss-daemon still chooses modem" to the
exact selection gap:

1. `cnss-daemon` does call the first PM vote with `vote_type=0x1`,
   `vote_name=(fault)` and registers `peripheral="modem"`.
2. `cnss-daemon` then does call the expected second vote with `vote_type=0x0`,
   `vote_name="SDXPRAIRIE"`.
3. `libmdmdetect::get_system_info()` returns success for that second vote.
4. The type-0 search loop sees only `entry_type=0x1`, `entry_name="modem"`.
5. `strcmp("SDXPRAIRIE", candidate)` is never reached, so no
   `peripheral="SDXPRAIRIE"` PM client registration occurs.

## Key Evidence

| item | value |
| --- | --- |
| `cnss_pm_vote_entry` | `2` |
| vote types | `0x1`, `0x0` |
| vote names | `(fault)`, `SDXPRAIRIE` |
| `mdm_get_system_info_entry` | `6` |
| `mdm_success_return` | `6` |
| second vote type compare | `request_type=0x0 entry_type=0x1 entry_name="modem"` |
| `cnss_strcmp_call` | `0` |
| `cnss_named_register_call` | `0` |
| `cnss_nullname_register_call` | `1`, `peripheral="modem"` |
| `per_mgr_esoc0_any` | `false` |
| `wlan0_up` | `false` |

Focused trace lines:

```text
cnss_pm_vote_entry: vote_type=0x1 vote_name=(fault)
cnss_nullname_loop_entry: request_type=0x1 entry_name="modem"
cnss_nullname_register_call: peripheral="modem" client="cnss-daemon"
cnss_pm_vote_entry: vote_type=0x0 vote_name="SDXPRAIRIE"
mdm_success_return: ret=0x0
cnss_type_compare: request_type=0x0 entry_type=0x1 entry_name="modem"
```

## Interpretation

The fake `esoc_name=SDXPRAIRIE` bind is visible, but it is the wrong repair
point.  `libmdmdetect.so` filters eSoC devices before filling the output array.
When `esoc_name` is faked to `SDXPRAIRIE`, the eSoC entry does not survive that
supported-device filter, so the array visible to `cnss-daemon` contains only the
MSM subsystem fallback entry:

```text
type=1 name="modem"
```

This explains why V1218 had positive readback but still registered only
`modem`.  The type-0 `SDXPRAIRIE` vote is not skipped; it runs, but there is no
type-0 output entry to compare against.

The likely next repair is not another sysfs bind.  The better candidate is a
private, non-persistent `cnss-daemon` runtime patch that changes the expected
selection string from `SDXPRAIRIE` to the real supported eSoC name `SDX50M`, or
an equivalent private wrapper/hook that leaves `libmdmdetect` seeing the real
supported name while making `cnss-daemon` request that same name.

## Safety

- Wi-Fi HAL start: blocked.
- Scan/connect/link-up: blocked.
- Credentials, DHCP/routes, and external ping: blocked.
- Boot image and partition writes: not performed.
- Tracefs uprobes were cleaned up.
- Postflight: `selftest pass=11 warn=1 fail=0`; netservice cleanup left
  `ncm0=absent` and `tcpctl=stopped`.
- Dmesg again showed cleanup-time `subsystem_put(esoc0) count:0` reference
  mismatch.  Device postflight stayed healthy, but this remains a safety signal
  to avoid overclaiming transient eSoC progress.

## Next Gate

V1220 should be a host/build-only gate first:

1. Verify the exact `SDXPRAIRIE` string offset in `cnss-daemon`.
2. Build or stage a private copy where only that runtime selection literal is
   changed to `SDX50M\0`.
3. Prove the patched binary hash and diff are limited to the private artifact.
4. Plan a live PM/CNSS observer that bind-mounts or executes only the private
   patched `cnss-daemon`, with no vendor partition writes and still no Wi-Fi
   HAL, scan/connect, credentials, DHCP/routes, or external ping.
