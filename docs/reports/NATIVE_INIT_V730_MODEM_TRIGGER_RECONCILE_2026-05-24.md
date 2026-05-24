# Native Init V730 Modem Trigger Reconcile Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py`
- evidence: `tmp/wifi/v730-modem-trigger-reconcile/`
- latest pointer: `tmp/wifi/latest-v730-modem-trigger-reconcile.txt`
- decision: `v730-global-firmware-mounted-modem-holder-required`
- status: `pass`

## Scope Result

V730 ran only read-only native captures and host-side evidence comparison. It
did not create a cdev node, open `subsys_modem`, create/open `esoc0`, write
subsystem state, mount/umount, start daemon/service-manager/Wi-Fi HAL, run
`qcwlanstate`, scan/connect, use credentials, run DHCP, change routes, external
ping, write a boot image, or write a partition.

## Current Native State

| item | value |
| --- | --- |
| native baseline | healthy; V724, `fail=0` |
| `firmware_class.path` | `/vendor/firmware_mnt/image` |
| `/vendor/firmware_mnt` mounted | `false` |
| `/vendor/firmware-modem` mounted | `false` |
| `/firmware` mounted | `false` |
| `/vendor/firmware_mnt/image/modem.b00` | absent |
| `/vendor/firmware-modem/image/modem.b00` | absent |
| `/firmware/image/modem.b00` | absent |
| `subsys_modem` cdev | `236:0` |
| `mss` state | `OFFLINING` |
| `mdm3` state | `OFFLINING` |

## Evidence Matrix

| source | classification | result |
| --- | --- | --- |
| V592 | no-firmware open-pending class | `subsys_modem` open entered firmware wait while global firmware visibility was not ready |
| V729 | same class reproduced on V724 | holder started, open stayed pending, `mss/mdm3=OFFLINING`, QRTR/sysmon/MHI/WLFW/BDF/`wlan0=0` |
| V594/V595 | firmware mount prerequisite proven | global firmware mounts made modem PIL reach `mss=ONLINE` and QRTR RX |
| V596 | firmware-mounted holder progressed further | `subsys_modem` only, no `esoc0`, QRTR RX/TX and `sysmon-qmi` observed |
| V622 | `mdm_helper` not first trigger | same-boot Android `mdm_helper` starts after first service-notifier publication |

## Interpretation

V729 does not contradict V594/V595/V596. It recreated the older no-global-
firmware state: the kernel firmware loader still points at
`/vendor/firmware_mnt/image`, but no global firmware mount or modem blob is
visible in the current native namespace.

Therefore the next lower modem gate should not be `mdm_helper` start-only or
another CNSS/HAL retry. The immediate prerequisite is restoring Android-style
global firmware mount parity before opening/holding `subsys_modem`.

The safety caveat remains from V595: deliberate raw close produced an
`esoc0` reference mismatch/kernel warning. V731 must avoid `esoc0`, avoid a
deliberate close during the live window, and use an explicit cleanup boundary.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py

python3 scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py \
  --out-dir tmp/wifi/v730-modem-trigger-reconcile-plan plan

python3 scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py \
  --out-dir tmp/wifi/v730-modem-trigger-reconcile run

python3 scripts/revalidation/a90ctl.py --timeout 20 status
```

Result: pass.

Post-run native status remained healthy:

```text
init: A90 Linux init 0.9.68 (v724)
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped
```

## Next Gate

V731 should be a current-build firmware-mounted modem-holder gate:

1. mount `/vendor/firmware_mnt` and `/vendor/firmware-modem` read-only;
2. confirm `modem.b00` visibility under the global firmware paths;
3. open/hold only `subsys_modem`;
4. observe QRTR RX/TX, `sysmon-qmi`, service-notifier, MHI/QCA6390, WLFW, BDF,
   and `wlan0`;
5. keep `esoc0`, deliberate close, daemon/HAL, scan/connect, credentials, DHCP,
   routes, and external ping blocked until the lower modem window is restored.
