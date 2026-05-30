# Native Init V1218 PM/CNSS SDXPRAIRIE Observer Report

Date: `2026-05-31`

## Result

- Decision: `v1218-peripheral-modem-unexpected`
- Pass: `false`
- Helper: `a90_android_execns_probe v252`
- Helper SHA256: `4511f11399d4f86f5265d79eb57b2db04ae5ad869ab543565f2c657b97af8587`
- Runner: `scripts/revalidation/native_wifi_pm_esoc_sdxprairie_name_v1218.py`
- Evidence: `tmp/wifi/v1218-pm-cnss-sdxprairie-observer/manifest.json`

## Summary

V1218 reran the bounded PM/CNSS observer with helper `v252`, carrying forward the
V1217 fake `esoc_name=SDXPRAIRIE` readback proof into the PM/CNSS window.

The fake path is still visible inside the private namespace:

| key | value |
| --- | --- |
| fake bind rc | `0` |
| fake content | `SDXPRAIRIE` |
| direct platform readback | `SDXPRAIRIE` |
| bus alias readback | `SDXPRAIRIE` |
| `/sys/class/esoc-dev` opendir | `0` |
| `/sys/class/esoc-dev` entries | `1` |

Despite that, `cnss-daemon` still registered only `peripheral='modem'`.
No `SDXPRAIRIE` PM client registration was observed, `per_mgr` held only
`/dev/subsys_modem`, and no MDM/WLFW/`wlan0` progress occurred.

## Key Evidence

| key | value |
| --- | --- |
| cnss registered peripherals | `['modem']` |
| `cnss_registered_sdxprairie` | `false` |
| `per_mgr_esoc0_any` | `false` |
| `wlan0_up` | `false` |
| PM thread wchans | `do_sigtimedwait`, `do_select`, `binder_ioctl_write_read` |
| tracefs `pm_client_register_entry` | `pm-proxy peripheral="modem"`, `cnss-daemon peripheral="modem"` |
| `pm_client_register_ret` | both `ret=0` |
| `pm_ack_state2_open_result` | `fd=0x8`, matching the modem path |

The post-run dmesg tail also captured a cleanup/safety anomaly:

- `subsystem_put(): subsystem_put: esoc0 count:0`
- `esoc0: subsystem_put: Reference count mismatch`
- `subsystem_put(): subsystem_put: modem count:2`

The device remained healthy after cleanup (`selftest fail=0`), but this warning
means V1219 should avoid interpreting a transient eSoC reference as a successful
or persistent `/dev/subsys_esoc0` hold.

## Interpretation

V1218 closes the simple "fake file is not readable in the daemon namespace"
hypothesis.  The same PM/CNSS run has positive readback for both expected
`esoc_name` paths, yet `cnss-daemon` still chooses `modem`.

The remaining blocker is therefore inside the `cnss-daemon` / `libmdmdetect.so`
selection path after the readback point.  More bind-path work is unlikely to be
useful until the second type-0 `SDXPRAIRIE` selection path is directly traced or
classified.

## Safety

- Wi-Fi HAL start: blocked.
- Scan/connect/link-up: blocked.
- Credentials, DHCP/routes, and external ping: blocked.
- Boot image and partition writes: not performed.
- Postflight: `selftest fail=0`; netservice cleanup left `ncm0=absent` and
  `tcpctl=stopped`.

## Next Gate

V1219 should focus on why positive `SDXPRAIRIE` readback does not produce the
expected `cnss-daemon` `peripheral='SDXPRAIRIE'` registration.

Candidate scope:

1. Trace or classify the `cnss-daemon` / `libmdmdetect.so` selection path after
   `get_system_info()`.
2. Distinguish the first type-1 `modem` registration from the expected second
   type-0 `SDXPRAIRIE` registration.
3. Keep PM/CNSS live gates bounded and keep Wi-Fi HAL, scan/connect,
   credentials, DHCP/routes, external ping, boot image writes, and partition
   writes blocked.
