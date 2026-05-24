# Native Init V737 CNSS2 Architecture Rebase Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py`
- evidence: `tmp/wifi/v737-cnss2-arch-rebase/`
- decision: `v737-route-to-modem-wlan-mhi-prereq-observer`
- pass: `true`

## Summary

V737 was host-only. It reclassified the V736 next step against the V726/V727
SM8250 CNSS2/PCIe model. The result supersedes the service-`74`-centric route:
service publication is side evidence, not the primary trigger model for the next
live unit.

The next useful gate is a bounded modem+WLAN/MHI prerequisite observer below
HAL/connect.

## Key Results

| check | result |
| --- | --- |
| inputs | all present: V726, V727, V731, V735, V736, V721, Android V622 |
| SM8250 model | pass; V726 model correction remains the routing base |
| `wlan` load interpretation | pass; `/sys/module/wlan` exists, `/proc/modules` has no `wlan`, no module-file evidence |
| vendor firmware namespace | pass; default native `/vendor` lacks Wi-Fi firmware, isolated `sda29` has `wlanmdsp.mbn`, `bdwlan.bin`, `regdb.bin` |
| modem holder | pass; `mss` reaches `ONLINE`, but `mdm3` stays `OFFLINING` in the V735 window |
| service publication | pass; V721 had native service `180/74` yet no WLAN-PD/WLFW/`wlan0` |
| MHI/WLFW/`wlan0` | pass as blocker; still absent in V735 while Android V622 has WLAN-PD/WLFW/BDF/`wlan0` |

## Interpretation

V736 correctly observed that current V735 reaches service `180` but not the
Android continuation. The routing error was treating service `74` as the next
primary target. Existing V721 evidence already covers a service `180/74`
positive native window and still shows:

```text
WLAN-PD = 0
MHI/QCA progression = 0
WLFW/service 69 = 0
BDF = 0
wlan0 = 0
```

The corrected model is:

```text
real vendor firmware namespace
  + modem/WLAN lower readiness
  + static wlan/CNSS2-to-MHI/WLFW progression
  -> service 69 / BDF / wlan0
```

This keeps Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, and
external ping unjustified until WLFW/BDF/`wlan0` appears.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py

python3 scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py \
  --out-dir tmp/wifi/v737-cnss2-arch-rebase-plan plan

python3 scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py \
  --out-dir tmp/wifi/v737-cnss2-arch-rebase run
```

The final run returned:

```text
decision: v737-route-to-modem-wlan-mhi-prereq-observer
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V738 should be a bounded modem+WLAN/MHI prerequisite observer:

1. keep the real `sda29` vendor firmware namespace visible;
2. keep `subsys_modem` holder below `esoc0` and below HAL/connect;
3. capture `mss`/`mdm3`, QRTR RX/TX, service publication, `wlan` static surface,
   QCA/MHI/PCI surfaces, WLFW service `69`, BDF, and `wlan0`;
4. classify whether the missing edge is WLAN-PD/modem continuation, CNSS2/MHI
   transition, or vendor firmware namespace visibility;
5. continue blocking Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and
   external ping until WLFW/BDF/`wlan0` appears.
