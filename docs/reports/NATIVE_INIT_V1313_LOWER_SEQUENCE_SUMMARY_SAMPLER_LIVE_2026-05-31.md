# Native Init V1313 Lower-Sequence Summary Sampler Live

## Summary

- Cycle: `V1313`
- Type: bounded live observation
- Decision: `v1313-lower-sequence-full-window-no-transition`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1313-lower-sequence-summary-sampler-live/manifest.json`
  - `tmp/wifi/v1313-lower-sequence-summary-sampler-live/summary.md`
- Script: `scripts/revalidation/native_wifi_lower_sequence_summary_sampler_live_v1313.py`
- Helper: `a90_android_execns_probe v275`

V1313 ran the stdout-reduced lower-sequence summary sampler with the deployed helper `v275`. It completed the intended full summary window without helper stdout truncation.

## Result

| field | value |
| --- | --- |
| helper stdout truncated | `false` |
| summary mode | `late-per-proxy-lower-sequence-summary` |
| summary sample count | `81` |
| summary end marker | `true` |
| `mdm_subsys_powerup` seen | `true` |
| max powerup thread count | `1` |
| max MDM status count | `0` |
| max PCI devices | `0` |
| max MHI bus devices | `0` |
| MHI pipe fd count | `0` |
| `ks` process count | `0` |
| `wlan0` | absent |
| PCIe1 GDSC | `0mV` |
| PCIe0 GDSC | `0mV` |
| PMIC soft-reset pinmux | `MUX UNCLAIMED` |
| TLMM GPIO135 | `gpio135 : out 0 16mA no pull` |
| TLMM GPIO142 | `gpio142 : in  0 8mA no pull` |

The full lower-sequence window confirms the current boundary:

```text
pm-service → /dev/subsys_esoc0 → mdm_subsys_powerup
  → no PCIe GDSC voltage
  → no GPIO142/MDM2AP response
  → no PCIe RC1 / MHI / ks / WLFW / wlan0
```

## Safety

The helper summary markers report:

| marker | value |
| --- | --- |
| GPIO line request | `0` |
| PMIC write | `0` |
| direct eSoC ioctl | `0` |

No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write occurred. Debugfs was mounted read-only for observation and unmounted during cleanup. Post-run selftest remained `fail=0`.

## Cleanup Note

The PM observer reported `observer-reboot-required` because one process was not proven stopped inside the observer's conservative postflight check. The harness performed its cleanup path, and post-run device health was verified with native selftest.

## Next

V1314 should classify the exact safe dynamic GDSC/eSoC prerequisite. At this point, static PMIC/TLMM shape and stdout-cap ambiguity are closed; the remaining gap is the internal lower power sequence that Android reaches but native init does not.
