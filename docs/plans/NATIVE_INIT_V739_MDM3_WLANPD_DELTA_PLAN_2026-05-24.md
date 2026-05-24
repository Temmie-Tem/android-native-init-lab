# Native Init V739 MDM3/WLAN-PD Delta Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py`
- evidence target: `tmp/wifi/v739-mdm3-wlanpd-delta/`

## Goal

Compare existing Android lower-surface evidence with the latest native V738
observer:

```text
Android: mss=ONLINE + mdm3=ONLINE + WLAN-PD/WLFW/BDF/wlan0
Native:  mss=ONLINE + mdm3=OFFLINING + no MHI/WLFW/BDF/wlan0
```

V739 decides the next gate without another live mutation.

## Inputs

| input | purpose |
| --- | --- |
| Android V590 | direct Android read-only `mss`/`mdm3` subsystem state sample |
| Android V611 | lower-surface recapture with `mss/mdm3`, sibling sysmon, WLAN-PD/BDF/`wlan0` |
| Android V622 | successful WLAN-PD/WLFW/BDF/`wlan0` timing reference |
| V614 | native/Android `mdm3` trigger-path classifier |
| V620 | safety classifier blocking raw `esoc0` and direct DSP boot-node retries |
| V738 | latest native modem/WLAN/MHI observer |

## Scope

V739 is host-only.

It does not contact the device, open `subsys_modem`, open `esoc0`, write sysfs,
write DSP boot nodes, start daemons, start service-manager, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, external ping, write a
boot image, or write a partition.

## Expected Classification

V739 passes if it confirms:

1. Android direct samples show `mss=ONLINE` and `mdm3=ONLINE`;
2. Android has WLAN-PD/WLFW/BDF/`wlan0` continuation;
3. V738 reaches `mss=ONLINE` but leaves `mdm3=OFFLINING` and has no MHI/WLFW;
4. raw `esoc0` and direct ADSP/CDSP/SLPI boot-node retries remain blocked by
   prior safety evidence;
5. `mdm_helper` is not proven as a first-notifier trigger.

The next gate should be a host-only `mdm_helper`/baseband contract classifier,
not a live trigger or Wi-Fi connect attempt.

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py \
  --out-dir tmp/wifi/v739-mdm3-wlanpd-delta-plan plan

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py \
  --out-dir tmp/wifi/v739-mdm3-wlanpd-delta run
```
