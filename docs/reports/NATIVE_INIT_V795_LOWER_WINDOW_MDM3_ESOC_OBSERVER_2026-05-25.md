# Native Init V795 Lower-Window mdm3/esoc Observer Report

## Result

- decision: `v795-holder-modem-online-mdm3-offlining-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py`
- evidence: `tmp/wifi/v795-lower-window-mdm3-esoc-observer/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py
python3 scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py --out-dir tmp/wifi/v795-static-plan-check plan
python3 scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py run \
  --assume-yes \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-cleanup-reboot
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V794 reference | pass |
| firmware mounts | `/vendor/firmware_mnt=true`, `/vendor/firmware-modem=true` |
| holder opened | `true` |
| `mss` | `OFFLINING -> ONLINE` |
| `mdm3` | `OFFLINING -> OFFLINING` |
| observed modem/esoc0 | `ONLINE / OFFLINING` |
| ICNSS device / driver | `true / true` |
| QRTR RX | `true` |
| QRTR services `180/69/74` | `0 / 0 / 0` |
| WLFW / BDF / `wlan0` | `0 / 0 / false` |
| cleanup | v724 `version` seen and `selftest`/status healthy |

## Classification

V795 proves that the lower firmware-backed `subsys_modem` holder window is
sufficient to bring `mss` ONLINE and produce QRTR RX, but it is not sufficient
to advance mdm3/esoc0 or Wi-Fi firmware publication. Service `69`, WLFW/BDF, and
`wlan0` remain absent without starting lower companions, CNSS daemons,
service-manager, Wi-Fi HAL, or `boot_wlan`.

This narrows the current blocker below the HAL/connect layer and below the
basic modem holder path:

```text
firmware mounts
  -> subsys_modem holder
    -> mss ONLINE + QRTR RX
      -> mdm3/esoc0 still OFFLINING
        -> no service 69 / WLFW / BDF / wlan0
```

The next gate should focus on the mdm3/esoc trigger contract or Android
vendor-init delta, not on credentials, scan/connect, DHCP, or external ping.

## Safety

- Firmware mounts and `subsys_modem` holder only.
- Cleanup reboot restored v724 health.
- No lower companion, CNSS daemon, service-manager, Wi-Fi HAL, `boot_wlan` or
  qcwlanstate write, scan/connect, credential use, DHCP/routes, external ping,
  `esoc0` open/hold, module bind/unbind, boot image write, partition write, or
  custom kernel flash.

## Next

V796 should stay bounded and classify what Android does to move mdm3/esoc0 after
`mss` becomes ONLINE. Candidate directions:

1. compare Android vendor-init/service order around mdm3/esoc readiness;
2. inspect mdm_helper/esoc contract without raw `esoc0` open;
3. use stock tracepoint/BPF evidence only if it can observe mdm3/PIL movement
   without triggering Wi-Fi bring-up.
