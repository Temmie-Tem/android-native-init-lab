# Native Init V596 Modem Holder Companion Plan

- date: `2026-05-22 KST`
- status: `executed`; live evidence is in the matching report
- scope: global firmware mounts + `subsys_modem` holder + bounded companion start-only

## Objective

Use the V594/V595 finding that Android-style global firmware visibility lets
modem PIL load, then keep only `subsys_modem` open while replaying the bounded
companion daemon stack.

## Required Sequence

1. Confirm native baseline is healthy.
2. Confirm current-boot V490 SELinux policy-load proof is present.
3. Resolve and mount both firmware partitions read-only:
   - `apnhlos` -> `/vendor/firmware_mnt`
   - `modem` -> `/vendor/firmware-modem`
4. Create a temporary char node only from `/sys/class/subsys/subsys_modem/dev`.
5. Open and hold only the modem subsystem fd; do not open `esoc0`.
6. Wait for `qrtr: Modem QMI Readiness RX`.
7. Start the companion stack in V525/V526 contract order:
   - `qrtr-ns`
   - `rmt_storage`
   - `tftp_server`
   - `pd-mapper`
   - `cnss_diag`
   - `cnss-daemon`
8. Capture dmesg, subsystem states, QRTR/protocol surface, process table, and
   helper transcript.
9. Reboot as the cleanup boundary.

## Guardrails

- No `esoc0` open.
- No service-manager, hwservicemanager, or vndservicemanager.
- No Wi-Fi HAL or `IWifi.start()`.
- No `qcwlanstate` or driver-state sysfs write.
- No supplicant, hostapd, or wificond.
- No scan/connect/link-up.
- No credentials, DHCP, routing, or external ping.
- No boot image or persistent partition writes.

## Success Markers

The proof should at minimum reproduce modem readiness RX before companion
start. Stronger advancement markers are:

- `qrtr: Modem QMI Readiness TX`
- `sysmon-qmi: ... Connection established`
- `service-notifier`
- `wlan_pd`
- `WLFW` / QMI server connected
- BDF/regdb/bdwlan evidence
- `wlan0`

## Failure Rules

- If QRTR RX does not appear after the holder opens, skip companion start.
- If a kernel WARNING/reference mismatch appears, stop repeating the raw holder
  pattern and redesign the trigger.
- If reboot cleanup does not return native to the expected version/status, stop
  and recover before any next Wi-Fi gate.
