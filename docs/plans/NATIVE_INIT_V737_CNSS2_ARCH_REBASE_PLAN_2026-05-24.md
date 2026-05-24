# Native Init V737 CNSS2 Architecture Rebase Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py`
- evidence target: `tmp/wifi/v737-cnss2-arch-rebase/`

## Goal

Reconcile V735/V736 with the SM8250 CNSS2/PCIe model already established by
V726/V727:

```text
SM8250 Wi-Fi bring-up prerequisite
  = real vendor Wi-Fi firmware namespace
  + modem/WLAN lower runtime readiness
  + static wlan/CNSS2-to-MHI/WLFW progression
  -> service 69 / BDF / wlan0
```

V737 corrects the next-step routing. Service `180/74` publication remains useful
side evidence, but V721 already proved that native service `180/74` can be
present while WLAN-PD, MHI, WLFW, BDF, and `wlan0` stay absent. Therefore the
next gate should not be service-`74`-only and should not start HAL/connect.

## Inputs

| input | purpose |
| --- | --- |
| V726 | SM8250 CNSS2/PCIe prerequisite model correction |
| V727 | real `sda29` vendor firmware visibility and static `wlan` surface |
| V731 | firmware-mounted `subsys_modem` holder proving `mss=ONLINE` and QRTR RX |
| V735 | current CNSS-only live result with service-notifier progress but no MHI/WLFW |
| V736 | service-`180` to service-`74`/MHI host-only classifier to supersede |
| V721 | service `180/74` positive native evidence still lacking WLAN-PD/WLFW |
| Android V622 | successful Android reference continuing to WLAN-PD/WLFW/BDF/`wlan0` |

## Scope

V737 is host-only.

It does not contact the device, open `subsys_modem`, open `esoc0`, write sysfs,
start daemons, start service-manager, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, external ping, write a boot image, or
write a partition.

## Expected Classification

If the evidence still shows:

1. `wlan` is a static/built-in parameter surface rather than a proven missing
   loadable `wlan.ko`;
2. real Wi-Fi firmware exists in the isolated `sda29` vendor view, while the
   default native `/vendor` view lacks it;
3. `subsys_modem` holder can bring `mss` online, but `mdm3`/WLAN-PD/MHI/WLFW do
   not continue;
4. native service `180/74` publication is insufficient by itself;

then V737 routes V738 to a bounded modem+WLAN/MHI prerequisite observer below
HAL/connect.

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py

python3 scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py \
  --out-dir tmp/wifi/v737-cnss2-arch-rebase-plan plan

python3 scripts/revalidation/native_wifi_cnss2_arch_rebase_v737.py \
  --out-dir tmp/wifi/v737-cnss2-arch-rebase run
```
