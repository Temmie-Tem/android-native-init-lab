# Native Init V1315 Tracefs Lower-Event Preflight

## Summary

- Cycle: `V1315`
- Type: bounded live preflight
- Decision: `v1315-tracefs-lower-event-preflight-pass`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1315-tracefs-lower-event-preflight/manifest.json`
  - `tmp/wifi/v1315-tracefs-lower-event-preflight/summary.md`
- Script: `scripts/revalidation/native_wifi_tracefs_lower_event_preflight_v1315.py`

V1315 validates the V1314-selected tracefs event path before any PM-service trigger or lower mutation. It temporarily mounted tracefs, read `available_events` and target event `format` files, then unmounted tracefs.

## Result

| field | value |
| --- | --- |
| tracefs mounted before | `false` |
| tracefs mounted after cleanup | `false` |
| `available_events` readable | `true` |
| available events total | `1250` |
| regulator target formats | `4/4` |
| GPIO target formats | `2/2` |
| IRQ target formats | `2/2` |
| clock target formats | `4/4` |
| power target formats | `3/3` |
| PIL target formats | `3/3` |
| post selftest | pass |

Target event groups are available and have readable format files:

- `regulator:regulator_enable`, `regulator_enable_complete`, `regulator_set_voltage`, `regulator_set_voltage_complete`
- `gpio:gpio_direction`, `gpio_value`
- `irq:irq_handler_entry`, `irq_handler_exit`
- `clk:clk_enable`, `clk_enable_complete`, `clk_prepare`, `clk_prepare_complete`
- `power:power_domain_target`, `device_pm_callback_start`, `device_pm_callback_end`
- `msm_pil_event:pil_event`, `pil_notif`, `pil_func`

## Next

V1316 can build/run a bounded tracefs event collector around the existing late `per_proxy` PM-service path. The collector should enable only the selected tracefs events for the bounded window, collect event lines, disable them, and clean up tracefs. It must still avoid Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC writes, GPIO line requests/holds, direct eSoC ioctls, flash, boot image writes, and partition writes.

## Safety

No PM-service trigger, PMIC write, GPIO line request/hold, direct eSoC ioctl, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred. No tracefs control writes occurred; V1315 read only event availability and format files after mounting tracefs.
