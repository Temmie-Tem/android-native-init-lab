# Native Init V726 CNSS2/PCIe Prerequisite Plan

- date: `2026-05-24 KST`
- cycle: `v726`
- runner: `scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py`
- evidence target: `tmp/wifi/v726-cnss2-pcie-prereq/`
- gate: read-only SM8250 CNSS2/PCIe prerequisite classifier

## Goal

V725 showed that V724 reaches service-locator but lacks QRTR RX/TX, sysmon,
ONLINE modem state, and service `180/74`.

V726 updates the model for SM8250:

```text
cnss2 probe -> QCA6390 PCIe/MHI power-up -> WLFW service 69 -> BDF -> wlan0
```

Service `180/74` is a side signal, not the primary CNSS2 trigger. The practical
preconditions to classify first are:

1. modem MPSS/MDM3 ONLINE state, because WLAN-PD and `wlanmdsp` are modem-side;
2. `wlan.ko` load state, because PCIe/MHI completion may depend on the WLAN
   driver module path;
3. CNSS2/MHI/QCA6390 dmesg progression;
4. `wlanmdsp` firmware visibility on mounted Android/firmware surfaces.

## Scope

Allowed:

- `mountsystem ro`;
- temporary read-only firmware mounts for `apnhlos` and `modem`, with cleanup;
- read `/proc/modules`, dmesg, CNSS2/sysfs paths, subsystem state, and bounded
  firmware paths;
- write private host-side evidence.

Blocked:

- `subsys_modem` hold/open;
- `esoc0` open/hold;
- subsystem state writes such as `echo online > state`;
- CNSS daemon or `cnss_diag` start;
- service-manager, hwservicemanager, or vndservicemanager start;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- `qcwlanstate` or WLAN driver-state writes;
- scan/connect/link-up;
- credential use;
- DHCP, route changes, and external ping;
- boot image or partition writes.

## Success Criteria

V726 passes as a classifier if it safely records:

- V724 native health;
- read-only mount cleanup result;
- `wlan` module loaded or absent;
- CNSS2/platform device surface;
- `mss` and `mdm3` states;
- CNSS2/MHI/QCA6390/WLFW/BDF/`wlan0` dmesg counts;
- `wlanmdsp` and modem firmware visibility.

Expected current decision:

```text
v726-cnss2-pcie-modem-and-wlan-module-prereq-gap-classified
```

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py

python3 scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py \
  --out-dir tmp/wifi/v726-cnss2-pcie-prereq-plan plan

python3 scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py \
  --out-dir tmp/wifi/v726-cnss2-pcie-prereq run

git diff --check
```

## Next Gate

If modem remains OFFLINING, V727 should focus on the smallest safe modem ONLINE
trigger proof. If `wlan.ko` is absent or unloaded, V727 must also distinguish
built-in vs loadable vs missing WLAN driver before CNSS daemon, HAL, scan, or
connect attempts.
