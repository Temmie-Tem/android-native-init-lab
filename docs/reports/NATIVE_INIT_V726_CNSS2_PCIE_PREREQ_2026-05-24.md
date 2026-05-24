# Native Init V726 CNSS2/PCIe Prerequisite Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py`
- evidence: `tmp/wifi/v726-cnss2-pcie-prereq/`
- latest pointer: `tmp/wifi/latest-v726-cnss2-pcie-prereq.txt`
- decision: `v726-cnss2-pcie-modem-and-wlan-module-prereq-gap-classified`
- status: `pass`

## Scope Result

V726 was a read-only prerequisite classifier. It used `mountsystem ro` and
temporary read-only firmware mounts, then cleaned them up.

It did not open `subsys_modem`, open `esoc0`, write subsystem state, start
CNSS daemon, start service-manager, start Wi-Fi HAL, run `qcwlanstate`,
scan/connect, use credentials, run DHCP, change routes, external ping, write a
boot image, or write a partition.

Post-run mount readback confirmed no `/vendor/firmware*` proof mounts remained.

## Model Correction

V726 supersedes the earlier service `180/74`-centric interpretation for SM8250:

```text
cnss2 probe -> QCA6390 PCIe/MHI power-up -> WLFW service 69 -> BDF -> wlan0
```

Service `180/74` remains useful as side evidence, but it is not treated as the
primary CNSS2 trigger. The practical prerequisites are modem MPSS/MDM3 online
state, WLAN module/load-state, MHI/QCA6390 progression, and `wlanmdsp`
firmware visibility.

## Key Results

| check | result |
| --- | --- |
| native baseline | V724 healthy |
| firmware cleanup | pass; `/vendor/firmware_mnt` and `/vendor/firmware-modem` read-only mounts cleaned |
| CNSS2/platform surface | present; CNSS/ICNSS platform probe evidence exists |
| WLAN module load | finding; `/sys/module/wlan` exists, but `/proc/modules` has no `wlan` entry |
| modem state | finding; `mss=OFFLINING`, `mdm3=OFFLINING`, crash counts `0` |
| `wlanmdsp` firmware | finding; no `wlanmdsp*` hit in mounted system/firmware surfaces |
| MHI/WLFW progression | finding; MHI/QCA6390/WLFW/BDF/`wlan0` markers absent |

## Evidence Summary

| item | value |
| --- | --- |
| `mss` state | `OFFLINING` |
| `mdm3` state | `OFFLINING` |
| `/proc/modules` has `wlan` | `False` |
| `/sys/module/wlan` exists | `True` |
| CNSS device/sysfs exists | `True` |
| `wlanmdsp` hits | `0` |
| modem blob hits | `2` |
| MHI dmesg markers | `0` |
| QCA6390 dmesg markers | `0` |
| WLFW dmesg markers | `0` |
| `wlan0` dmesg markers | `0` |

Visible modem firmware blobs:

```text
/vendor/firmware-modem/image/modem.b00
/vendor/firmware-modem/image/modem.mdt
```

No `wlanmdsp*` file was found by the bounded path checks.

## Interpretation

Current native init is not ready for CNSS daemon, HAL, scan/connect, or ping:

```text
modem/MDM3 OFFLINING
  + no /proc/modules wlan entry
  + no MHI/QCA6390/WLFW/BDF/wlan0 markers
  + no visible wlanmdsp firmware
  => WLFW service 69 is not expected
```

The immediate blocker is not service-manager/HAL. It is the lower
modem/WLAN-driver prerequisite layer.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py

python3 scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py \
  --out-dir tmp/wifi/v726-cnss2-pcie-prereq-plan plan

python3 scripts/revalidation/native_wifi_cnss2_pcie_prereq_v726.py \
  --out-dir tmp/wifi/v726-cnss2-pcie-prereq run
```

Additional cleanup check:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/vendor/firmware|/tmp/a90-v726|/vendor '
```

No leftover proof mount was returned.

## Next Gate

V727 should stay below CNSS daemon and HAL:

1. classify whether `/sys/module/wlan` with no `/proc/modules` entry means
   built-in/static WLAN support or missing loadable `wlan.ko`;
2. map `wlanmdsp*` source paths from Android reference or a tighter firmware
   inventory;
3. plan the smallest safe modem ONLINE trigger proof;
4. keep CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, credentials,
   DHCP, routes, and external ping blocked.
