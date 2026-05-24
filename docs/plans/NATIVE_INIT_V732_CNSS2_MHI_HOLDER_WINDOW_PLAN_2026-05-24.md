# Native Init V732 CNSS2/MHI Holder-window Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py`
- evidence target: `tmp/wifi/v732-cnss2-mhi-holder-window/`
- prerequisite: V731 `v731-firmware-mounted-modem-holder-qrtr-rx-pass`

## Goal

Rebase the Wi-Fi bring-up model on the SM8250 CNSS2/PCIe path and observe the
lowest still-missing edge inside the known-good V731 firmware-mounted
`subsys_modem` holder window.

The test answers four questions:

1. does the current firmware-mounted holder still move `mss` ONLINE and produce
   modem QRTR RX;
2. does `wlan` look like a built-in/static kernel surface or a missing loadable
   `wlan.ko`;
3. does CNSS2/QCA6390/MHI/WLFW/service `69` progress while modem QRTR readiness
   exists;
4. are global WLAN firmware paths visible in the current namespace.

## Architecture Correction

Treat service `180/74` as side evidence for this device family, not the primary
SM8250 CNSS2 trigger. The working model for this gate is:

```text
firmware partitions visible
  -> subsys_modem holder
    -> MPSS modem QRTR readiness
      -> CNSS2/QCA6390 PCIe/MHI progression
        -> WLFW service 69
          -> BDF/fw-ready/wlan0
```

## Allowed Actions

- run normal read-only status, selftest, dmesg, procfs, sysfs, and stat checks;
- mount `/vendor/firmware_mnt` and `/vendor/firmware-modem` read-only as in V731;
- open only a temporary `subsys_modem` cdev holder;
- reboot after the holder-window proof as the cleanup boundary.

## Forbidden Actions

- no `esoc0` node creation/open;
- no subsystem state write such as `echo online`;
- no module load/unload;
- no lower companion service start;
- no CNSS daemon, service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- no scan/connect, credential use, DHCP, route change, external ping, or boot
  partition write.

## Success Criteria

| class | criteria |
| --- | --- |
| `wlfw-advance` | WLFW/service `69`, BDF, or `wlan0` appears without forbidden actions |
| `mhi-advance` | MHI/QCA6390 appears but WLFW/service `69` does not |
| `cnss2-gap-classified` | modem ONLINE and QRTR RX return, but MHI/WLFW/service `69` stay absent |
| `blocked` | firmware mount, holder, native health, or reboot cleanup fails |

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py

python3 scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py \
  --out-dir tmp/wifi/v732-cnss2-mhi-holder-window-plan plan

python3 scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py \
  --out-dir tmp/wifi/v732-cnss2-mhi-holder-window run
```
