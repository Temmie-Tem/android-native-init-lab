# Native Init V800 Provider-first ICNSS Edge v124 Replay Report

## Result

- decision: `v800-provider-first-icnss-edge-captured-gap-persists`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py`
- evidence: `tmp/wifi/v800-provider-first-icnss-edge-v124-live/`
- helper: `a90_android_execns_probe v124`
- native image: `A90 Linux init 0.9.68 (v724)`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_icnss_edge_v800.py \
  scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py \
  --out-dir tmp/wifi/v800-provider-first-icnss-edge-v124-plan-check \
  plan

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py \
  --out-dir tmp/wifi/v800-provider-first-icnss-edge-v124-live \
  --arm-companion-runtime-sec 30 \
  --apply --assume-yes \
  run

python3 scripts/revalidation/a90ctl.py selftest
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| cleanup native version | v724 observed |
| cleanup status | healthy |
| selftest | `pass=11 warn=1 fail=0` |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |
| service `74` gate | open |
| initial CNSS daemon | suppressed |
| PeripheralManager query | exact match |
| post-provider CNSS retry | started |
| CNSS netlink | `5` |
| `cld80211` | `2` |
| Binder transaction failure | `0` |
| ICNSS edge capture | present |
| QCA6390 driver link | absent |
| service `69` / WLFW | absent |
| BDF / FW ready | absent |
| wiphy / `wlan0` | absent |
| Wi-Fi HAL / scan / connect / DHCP / external ping | not executed |

## Interpretation

V800 confirms that the v124/v724 current state can still reproduce the strongest
known below-HAL path:

```text
service 180/74 positive
  -> PeripheralManager registration confirmed
  -> provider-first CNSS retry starts without Binder transaction failure
  -> ICNSS edge capture is present
  -> QCA6390/WLFW/BDF/wlan0 still absent
```

This keeps the blocker below connection-level behavior. The immediate missing
edge is no longer service-manager startup, PeripheralManager registration, or
CNSS daemon Binder failure. The remaining blocker is between ICNSS platform
state and QCA6390/WLFW publication.

## Safety

- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `esoc0` open/hold, subsystem state write, bind/unbind, module load/unload,
  boot image write, or partition write.
- Runtime cleanup reboot returned native v724 to healthy status.
- No Wi-Fi secret material was written to tracked output.

## Next

V801 should be host-only first: classify the V800 ICNSS edge surface and dmesg
delta against Android/native references. Focus on why the ICNSS platform link
exists while QCA6390 driver link, WLFW service `69`, BDF, firmware-ready, wiphy,
and `wlan0` remain absent. Do not move to Wi-Fi HAL, scan/connect, credentials,
DHCP, routes, or external ping until WLFW or a netdev surface appears.
