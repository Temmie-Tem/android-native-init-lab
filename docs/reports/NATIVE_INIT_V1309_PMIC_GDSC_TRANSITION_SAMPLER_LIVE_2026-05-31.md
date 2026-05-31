# Native Init V1309 PMIC/GDSC Transition Sampler Live

## Summary

- Cycle: `V1309`
- Type: bounded no-write live sampler
- Decision: `v1309-focused-pmic-gdsc-partial-window-no-transition`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1309-pmic-gdsc-transition-sampler-live/manifest.json`
  - `tmp/wifi/v1309-pmic-gdsc-transition-sampler-live/summary.md`
  - `tmp/wifi/v1309-pmic-gdsc-transition-sampler-live/host/pm-server-wchan-tracefs-observer.txt`
- Script: `scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_live_v1309.py`
- Helper: `a90_android_execns_probe v274`
- Helper SHA256: `eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180`

V1309 ran the focused PMIC/GDSC transition sampler through the existing bounded late-`per_proxy` PM-service path. The helper stdout hit the existing `1MiB` cap before the final sampler end marker, but the partial focused window still covered `76` samples and includes the `mdm_subsys_powerup` boundary.

## Key Findings

| field | value |
| --- | --- |
| focused mode | `late-per-proxy-focused-pmic-gdsc-transition` |
| focused samples | `76` |
| powerup marker | present |
| first syscall path | `/dev/subsys_esoc0` |
| first wchan | `mdm_subsys_powerup` |
| GPIO135 target line | `gpio135 : out 0 16mA no pull` |
| GPIO142 target line | `gpio142 : in  0 8mA no pull` |
| PM8150L soft-reset | `MUX UNCLAIMED` |
| PCIe1 GDSC | `0mV` |
| PCIe0 GDSC | `0mV` |
| MDM status count | `0` |
| MHI bus count | `0` |
| MHI pipe fd count | `0` |
| `ks` process count | `0` |
| `wlan0` | absent |

The useful boundary is now sharper: `pm-service` reaches `/dev/subsys_esoc0` and blocks in `mdm_subsys_powerup`, but PM8150L soft-reset remains unclaimed, PCIe GDSCs remain at `0mV`, and no MHI/`ks`/`wlan0` progress appears during the focused window.

## Output Cap Note

The helper emitted:

- `A90_EXECNS_STDOUT_END truncated=1 bytes=1048576`
- `A90_EXECNS_END rc=0`

Therefore V1309 is classified as a partial-window PASS, not a full-window PASS. If a full `82`-sample end-to-end sampler is required, the next helper should further reduce stdout or move repetitive sample data into a smaller summary.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_live_v1309.py
python3 scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_live_v1309.py plan
python3 scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_live_v1309.py run
python3 scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_live_v1309.py reclassify
python3 scripts/revalidation/a90ctl.py --timeout 10 selftest
```

Post-run health remained `fail=0`.

## Next

V1310 should classify the exact safe lower prerequisite before any PMIC/GPIO/eSoC mutation. The two practical branches are:

1. host-only: compare Android-positive PM8150L soft-reset / PCIe GDSC ownership timing against native V1309 evidence;
2. source/build-only: add a smaller focused summary mode that avoids the `1MiB` stdout cap and preserves full-window end markers.

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
- No PMIC write, userspace GPIO request/hold, or direct eSoC ioctl occurred.
- Debugfs was mounted for read-only observation and unmounted during cleanup.
