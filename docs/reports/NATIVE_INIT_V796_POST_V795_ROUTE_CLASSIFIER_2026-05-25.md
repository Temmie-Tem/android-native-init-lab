# Native Init V796 Post-V795 Route Classifier Report

## Result

- decision: `v796-pil-notif-payload-capture-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py`
- evidence: `tmp/wifi/v796-post-v795-route-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py
python3 scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py --out-dir tmp/wifi/v796-static-plan-check plan
python3 scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py run
```

## Evidence Matrix

| Source | `mss` | `mdm3` | service `69` | WLFW | `wlan0` | Interpretation |
| --- | --- | --- | ---: | ---: | --- | --- |
| V795 holder-only | `ONLINE` | `OFFLINING` | `0` | `0` | `false` | holder proves `mss`/QRTR but not mdm3 |
| V792 CNSS readback | `ONLINE` | `OFFLINING` | `0` | `0` | `0` | service `180/74` and CNSS still no WLFW |
| V782 BPF `boot_wlan` | `ONLINE` | `OFFLINING` | `0` | `0` | `false` | PIL count `8`, but no payload fields |

## Classification

V796 selects a payload-capture gate instead of repeating an already-demoted
trigger branch.

Known facts:

- V795 proves `subsys_modem` holder is enough for `mss=ONLINE` and QRTR RX, but
  not for mdm3/service `69`/WLFW/BDF/`wlan0`.
- V792 proves lower companion + CNSS can reach service-notifier/sysmon markers,
  but still has no WLFW/BDF/`wlan0`.
- V782 proves real `msm_pil_event:pil_notif` events occur during the lower
  transition, but only counted them.
- V764 already started `mdm_helper` and did not advance mdm3/WLFW.
- V785 demoted memshare/CMA failure as the sole blocker.
- V768 closed the raw `esoc0` and repeated mdm_helper branches as best next
  actions.

Therefore the next useful information is not another blind trigger. It is the
PIL notification payload: `event_name`, `code`, and `fw_name`. That can show
which firmware/subsystem notifications occur during the native lower transition
and whether the mdm3/WLAN-PD-relevant notification is missing.

## Safety

- V796 was host-only.
- No device command, reboot, mount, trace control write, daemon start,
  service-manager, Wi-Fi HAL, `boot_wlan`, scan/connect, credential use,
  DHCP/routes, external ping, raw `esoc0`, module bind/unbind, boot image write,
  partition write, or custom kernel flash.

## Next

V797 should be a bounded tracefs/BPF PIL payload capture around the already
tested lower-window transition:

1. enable only `msm_pil_event:pil_notif` payload capture;
2. run the proven lower-window transition with the same no-HAL/no-connect
   boundary;
3. collect `event_name`, `code`, and `fw_name` lines;
4. cleanup trace controls and reboot/health-check if the lower transition uses
   the reboot-cleanup path;
5. still block scan/connect, credentials, DHCP/routes, external ping, custom
   kernel, and raw `esoc0`.
