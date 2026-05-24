# Native Init V730 Modem Trigger Reconcile Plan

- date: `2026-05-24 KST`
- cycle: `v730`
- runner: `scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py`
- evidence target: `tmp/wifi/v730-modem-trigger-reconcile/`
- gate: reconcile V729 open-pending with V594/V595/V596 firmware-mounted modem readiness

## Goal

V729 showed that a current-build temporary `subsys_modem` cdev open attempt can
remain pending while `mss/mdm3` stay `OFFLINING`. That result must be reconciled
with older V594/V595/V596 evidence where global firmware mount parity plus a
`subsys_modem` holder reached modem PIL, QRTR RX/TX, and `sysmon-qmi`.

V730 classifies whether the next gate should be:

- Android `mdm_helper`/ioctl/property start-only analysis; or
- restoring global firmware mount parity before any modem holder retry.

## Scope

Allowed:

- read native baseline with `version`, `status`, and `selftest`;
- read `/sys/module/firmware_class/parameters/path`;
- read `/proc/mounts`;
- stat the known global modem blob paths:
  - `/vendor/firmware_mnt/image/modem.b00`;
  - `/vendor/firmware-modem/image/modem.b00`;
  - `/firmware/image/modem.b00`;
- read `subsys_modem` cdev major/minor and `mss/mdm3` state;
- compare existing V592, V594/V595, V596, V622, V623, and V729 evidence;
- write private host-side evidence.

Blocked:

- cdev node creation or subsystem open;
- creating/opening `esoc0`;
- subsystem state writes;
- mount/umount;
- daemon start, service-manager start, Wi-Fi HAL start, supplicant, hostapd,
  wificond, or `qcwlanstate`;
- scan/connect/link-up, credentials, DHCP, routes, or external ping;
- boot image or partition writes.

## Success Criteria

V730 passes if it proves:

- current native baseline is healthy;
- current global firmware mounts/blobs are absent;
- V729 matches the previous no-firmware open-pending class;
- V594/V595 show firmware-mounted `subsys_modem` can reach modem readiness;
- V596 shows firmware-mounted holder can reach QRTR TX and `sysmon-qmi`;
- V622 keeps `mdm_helper` excluded as the first lower trigger;
- next live gate is defined without `esoc0`, deliberate close, daemon/HAL,
  scan/connect, credentials, DHCP, routes, or external ping.

Expected decision:

```text
v730-global-firmware-mounted-modem-holder-required
```

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py

python3 scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py \
  --out-dir tmp/wifi/v730-modem-trigger-reconcile-plan plan

python3 scripts/revalidation/native_wifi_modem_trigger_reconcile_v730.py \
  --out-dir tmp/wifi/v730-modem-trigger-reconcile run

python3 scripts/revalidation/a90ctl.py --timeout 20 status

git diff --check
```

## Next Gate

If V730 passes, V731 should recreate the known-good lower window on the current
build:

1. mount only the required firmware partitions read-only;
2. open/hold only `subsys_modem`;
3. avoid deliberate close if possible and use an explicit cleanup boundary;
4. observe QRTR RX/TX, `sysmon-qmi`, service-notifier, MHI/QCA6390, WLFW, BDF,
   and `wlan0`;
5. keep daemon/HAL, scan/connect, credentials, DHCP, routes, and external ping
   blocked until the lower modem window is restored.
