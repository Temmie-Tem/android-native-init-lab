# Native Init V808 Overlap Companion Boot WLAN Report

## Result

- decision: `v808-overlap-service69-still-absent`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py`
- evidence: `tmp/wifi/v808-overlap-companion-boot-wlan/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py

python3 scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py \
  --out-dir tmp/wifi/v808-overlap-companion-boot-wlan-plan-check \
  plan

python3 scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py run

python3 scripts/revalidation/a90ctl.py --hide-on-busy --json selftest
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V807 route input | pass |
| current boot prep | pass |
| V401 SELinuxfs mount | pass |
| V490 policy load | pass |
| QRTR RX before overlap | seen |
| helper alive before `boot_wlan` | `true` |
| final service74 gate | `open=1`, `seen=1`, `wait_ms=15` |
| provider-first query | exact provider seen |
| CNSS retry | started |
| `boot_wlan` write | executed by `a90_wlanbootctl boot-observe` |
| `wlan: Loading driver` | `1` |
| `qcwlanstate` readbacks | `34` |
| `icnss: Modules not initialized` | repeated |
| WLFW/service69 | absent |
| ICNSS QMI connected / FW ready | absent |
| BDF / wiphy / `wlan0` | absent |
| forbidden HAL/scan/connect/network actions | false |
| postflight cleanup | rebooted, native selftest OK |

The helper log is buffered when redirected to a device file, so the live
gate-wait loop did not observe `service74_gate.open` before `boot_wlan`.
However, the helper process was alive when `boot_wlan` began, and the final
helper output proves the provider-first/service74/CNSS-retry contract was
present during this overlap attempt.

## Classification

V808 closes the V807 lifetime-gap question. The previous sequential path was
not the sole reason for WLFW absence: even with provider-first companion context
alive when `boot_wlan` begins, the kernel still reaches only HDD/qcwlanstate
surface and repeatedly logs `icnss: Modules not initialized just return`.

That puts the next blocker below HAL and before WLFW publication:

```text
provider-first companion + service74 + peripheral manager + CNSS retry
  overlaps boot_wlan
    -> wlan: Loading driver
    -> qcwlanstate remains OFF
    -> icnss: Modules not initialized
    -> no WLFW service69 / FW_READY / BDF / wiphy / wlan0
```

The next gate should not use credentials or start Wi-Fi HAL. It should classify
the ICNSS module-initialized prerequisite that makes `boot_wlan` return early
despite service74/provider-first context.

## Safety

- No custom kernel flash, boot image write, or partition write.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `esoc0` open, bind/unbind, driver override, or module load/unload.
- Runner-owned reboot cleanup completed and native selftest passed.
- No Wi-Fi secret material was written to tracked output.

## Next

V809 should be a host-first classifier over V808/V752/V795/V797 evidence and
Samsung OSRC source to map the exact `icnss: Modules not initialized` return
condition. The useful output is the smallest safe live gate that can prove or
disprove the missing ICNSS module-initialized prerequisite without Wi-Fi HAL,
scan/connect, credentials, DHCP, routes, or external ping.
