# Native Init V752 CNSS then Boot WLAN Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss_then_boot_wlan_v752.py`
- plan evidence: `tmp/wifi/v752-cnss-then-boot-wlan-plan2/`
- preflight evidence: `tmp/wifi/v752-cnss-then-boot-wlan-preflight-retry/`
- run evidence: `tmp/wifi/v752-cnss-then-boot-wlan/`
- decision: `v752-cnss-then-boot-wlan-hdd-init-still-stalls`
- status: `pass`

## Summary

V752 tested the V751 ordering hypothesis:

```text
firmware ro mounts
  -> subsys_modem holder
  -> QRTR RX/TX + sysmon-qmi
  -> qrtr-ns/rmt_storage/tftp_server/pd-mapper/cnss_diag/cnss-daemon
  -> bounded boot_wlan observe
```

The ordering executed safely, but it did not advance native Wi-Fi beyond the
same HDD/qcwlanstate boundary:

```text
wlan: Loading driver ✓
wlan_hdd_state wlan major(...) initialized ✓
wlan: driver loaded ✗
ICNSS-QMI connected ✗
WLAN FW ready ✗
WLFW/service 69/BDF ✗
wiphy / wlan0 ✗
```

## Checks

| check | result |
| --- | --- |
| V751 reference | pass; `v751-boot-wlan-hdd-init-stalls-before-driver-loaded` |
| V490 policy-load reference | pass; refreshed in `tmp/wifi/v752-v490-current-run/` |
| firmware ro mounts | pass; `/vendor/firmware-modem` and `/vendor/firmware_mnt` mounted |
| modem holder window | pass; `mss` reached `ONLINE` and QRTR RX was observed |
| CNSS companion contract | pass; six children started and were postflight-safe |
| forbidden helper actions | pass; no service-manager/HAL/connect/DHCP/external ping |
| `boot_wlan` after CNSS | pass; write executed and observe completed |
| driver readiness progression | finding; no driver-loaded/QMI/FW-ready/netdev progression |
| kernel warning review | pass; no warning marker found |
| reboot cleanup | pass; native version and status verified after reboot |

## Key Signals

| signal | value |
| --- | --- |
| helper marker | `a90_android_execns_probe v124` |
| wlanbootctl marker | `a90_wlanbootctl v2` |
| helper mode | `wifi-companion-start-only` |
| helper order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| helper children started | `6` |
| `cnss_diag` started | `true` |
| `cnss-daemon` started | `true` |
| service-manager started | `false` |
| Wi-Fi HAL started | `false` |
| scan/connect executed | `false` |
| credential use executed | `false` |
| DHCP/routes executed | `false` |
| external ping executed | `false` |
| `boot_wlan` write executed | `true` |
| `qcwlanstate` after observe | `OFF` |
| `/dev/wlan` after observe | `false` |
| ICNSS net child after observe | `false` |
| wiphy after observe | `false` |
| `wlan0` after observe | `false` |
| QRTR service `69` after observe | `0` |

## Marker Counts

| marker | count |
| --- | --- |
| QRTR RX | `1` |
| QRTR TX | `1` |
| `sysmon-qmi` | `1` |
| service-notifier | `0` |
| WLAN-PD | `0` |
| MHI | `0` |
| QCA6390 | `0` |
| WLFW | `0` |
| BDF | `0` |
| `wlan: Loading driver` | `1` |
| `wlan_hdd_state wlan major` | `1` |
| `wlan: driver loaded` | `0` |
| ICNSS-QMI connected | `0` |
| firmware-ready | `0` |
| wiphy | `0` |
| kernel warning | `0` |

## Interpretation

The CNSS companion ordering hypothesis is now falsified for the current native
state. `cnss_diag` and `cnss-daemon` can be started before `boot_wlan`, but that
does not move the static WLAN driver past HDD init. Repeating the same ordering
is unlikely to add information.

The next useful gate is deeper HDD/PLD prerequisite instrumentation: capture the
driver path between `__hdd_module_init`, PLD/ICNSS registration, and the missing
driver-loaded / ICNSS-QMI transition without starting service-manager, Wi-Fi
HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Safety Result

V752 remained below connection-level behavior. It did mutate runtime state by
read-only firmware mounts, `subsys_modem` holder open, companion start-only, and
`boot_wlan` observe, then performed reboot cleanup. No persistent partition or
boot image writes were executed.

## Next Gate

V753 should be a read-only/diagnostic HDD/PLD prerequisite classifier. It should
not repeat CNSS plus `boot_wlan` ordering unless new evidence identifies a
specific missing prerequisite inside that ordering.

## Evidence

- `tmp/wifi/v752-cnss-then-boot-wlan/manifest.json`
- `tmp/wifi/v752-cnss-then-boot-wlan/summary.md`
- `tmp/wifi/v752-cnss-then-boot-wlan/native/dmesg-delta.txt`
- `tmp/wifi/v752-cnss-then-boot-wlan/native/cnss-companion-start-only.txt`
- `tmp/wifi/v752-cnss-then-boot-wlan/native/boot-wlan-observe-after-cnss.txt`

## Source References

- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266>
