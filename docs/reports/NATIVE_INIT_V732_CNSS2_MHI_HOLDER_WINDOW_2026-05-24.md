# Native Init V732 CNSS2/MHI Holder-window Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py`
- evidence: `tmp/wifi/v732-cnss2-mhi-holder-window/`
- latest pointer: `tmp/wifi/latest-v732-cnss2-mhi-holder-window.txt`
- decision: `v732-cnss2-mhi-holder-window-cnss2-gap-classified`
- status: `pass`

## Scope Result

V732 ran a bounded live proof in the V731 firmware-mounted `subsys_modem`
holder window.

It did not create/open `esoc0`, write subsystem state, load/unload modules,
start lower companion services, start CNSS daemon, start service-manager, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, external
ping, write a boot image, or write a partition.

Post-run reboot cleanup returned to `A90 Linux init 0.9.68 (v724)` with
`selftest fail=0`; follow-up `/proc/mounts` showed no V732 firmware/proof mount
leftovers.

## Key Results

| item | result |
| --- | --- |
| firmware mounts | pass; `/vendor/firmware_mnt` and `/vendor/firmware-modem` mounted read-only during proof |
| `subsys_modem` holder | pass; holder opened |
| `mss` state | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` state | `OFFLINING -> OFFLINING -> OFFLINING` |
| QRTR RX | pass; `qrtr: Modem QMI Readiness RX` observed |
| QRTR TX/sysmon/rpmsg | absent |
| MHI/QCA6390/WLFW/BDF/`wlan0` | absent |
| QRTR service `69/74/180` | all `0` in `/proc/net/qrtr` snapshot |
| `wlan` load semantics | `/sys/module/wlan` exists, `/proc/modules` has no `wlan` entry |
| CNSS surface | CNSS device exists; `/sys/bus/platform/drivers/cnss2` path absent on this kernel view |
| global WLAN firmware | no checked `wlanmdsp`, `bdwlan.bin`, or `regdb.bin` path visible |
| kernel warning markers | `0` |

Marker counts from the proof window:

| marker | count |
| --- | ---: |
| `qrtr_rx` | `1` |
| `qrtr_tx` | `0` |
| `sysmon_qmi` | `0` |
| `rpmsg` | `0` |
| `mhi` | `0` |
| `qca6390` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `wlan0` | `0` |
| `kernel_warning` | `0` |

## Interpretation

The new SM8250 model is partially confirmed and narrowed:

```text
firmware mounts + subsys_modem holder
  -> MPSS mss ONLINE
  -> modem QRTR RX
  -> no QRTR TX/sysmon/rpmsg
  -> no MHI/QCA6390/WLFW/service 69/BDF/wlan0
```

This means the immediate blocker is below HAL/scan/connect and still below
CNSS daemon retry. V732 also keeps the V727 conclusion intact: `wlan` looks like
a built-in/static kernel surface rather than a missing loadable `wlan.ko`.

The remaining actionable gap is the namespace/runtime layer that would expose
real vendor WLAN firmware and provide the companion/TFTP path, or a separate
exact CNSS2 trigger still not represented by the read-only holder window.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py

python3 scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py \
  --out-dir tmp/wifi/v732-cnss2-mhi-holder-window-plan plan

python3 scripts/revalidation/native_wifi_cnss2_mhi_holder_window_v732.py \
  --out-dir tmp/wifi/v732-cnss2-mhi-holder-window run
```

Post-run spot checks:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 status

python3 scripts/revalidation/a90ctl.py --timeout 20 cat /proc/mounts \
  | rg '/vendor/firmware_mnt|/vendor/firmware-modem|/tmp/a90-v732| /sys/fs/selinux'
```

The status check returned native V724 healthy, and the mount grep returned no
leftover V732 firmware/proof mount.

## Next Gate

V733 should stay below HAL/scan/connect and test the smallest lower runtime
addition that V732 did not exercise:

1. use the V731 firmware-mounted `subsys_modem` holder window;
2. expose the real `sda29` vendor WLAN firmware through the private runtime
   namespace proven in V727/V728;
3. start only the lower companion/TFTP stack needed for firmware serving
   (`qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`) in bounded mode;
4. observe QRTR TX/sysmon/rpmsg/service `69`, MHI/QCA6390, BDF, fw-ready, and
   `wlan0`;
5. keep CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, credentials,
   DHCP, routes, and external ping blocked.
