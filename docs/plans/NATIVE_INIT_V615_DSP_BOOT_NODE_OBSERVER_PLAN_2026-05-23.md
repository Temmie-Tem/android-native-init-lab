# Native Init V615 DSP Boot-Node Observer Plan

- date: `2026-05-23 KST`
- prerequisite: V614 decision `v614-dsp-boot-trigger-gap-classified`
- target: test Android-equivalent ADSP/CDSP/SLPI boot-node sequence before any
  CNSS/HAL/scan/connect retry

## Objective

Determine whether native init can advance from V613's modem-only lower path:

```text
MSS ONLINE → QRTR RX/TX → modem sysmon-qmi
```

to the Android-equivalent lower publication path:

```text
ADSP/CDSP/SLPI PIL → sibling sysmon-qmi → service-notifier 180/74
```

without starting CNSS daemon, service-manager, Wi-Fi HAL, supplicant, hostapd,
scan/connect/link-up, credentials, DHCP, routes, or external ping.

## Live Contract

Allowed:

- read-only firmware surface mounts already used by V613
- write `1` to `/sys/kernel/boot_adsp/boot`
- write `1` to `/sys/kernel/boot_cdsp/boot`
- write `1` to `/sys/kernel/boot_slpi/boot`
- open and hold only `subsys_modem`
- start no-CNSS companion window: `qrtr-ns`, `rmt_storage`, `tftp_server`,
  `pd-mapper`
- reboot cleanup

Forbidden:

- raw `subsys_esoc0` open/close
- `boot_wlan` write
- CNSS daemon or `cnss_diag`
- service-manager or HAL
- qcwlanstate write
- scan/connect/link-up
- credentials, DHCP, routing, external ping

## Success Criteria

`v615-dsp-boot-publication-advanced` if all are true:

- ADSP/CDSP/SLPI PIL markers appear without kernel WARNING;
- native rollback after reboot is healthy;
- at least one sibling `sysmon-qmi` marker appears; and
- service-notifier `180` or `74` appears, or the result clearly advances the
  lower publication boundary.

`v615-dsp-boot-sibling-only` if DSP PIL and sibling sysmon appear but
service-notifier remains absent.

`v615-dsp-boot-no-publication-change` if DSP boot nodes are written but no
sibling sysmon or service-notifier appears.

`v615-cleanup-review` or `v615-unsafe` if rollback fails, kernel WARNING appears,
or subsystem state regresses unexpectedly.

## Evidence

Capture:

- pre/post dmesg delta
- ADSP/CDSP/SLPI/MSS subsystem state and PIL markers
- sibling `sysmon-qmi` markers
- service-notifier `180/74`
- `rmt_storage`, `tftp_server`, `pd-mapper`, and QRTR markers
- `mdm3` state
- process table before reboot
- native version/status after reboot cleanup

## Next Decision

If V615 advances to service-notifier `180/74`, the next gate can be a CNSS-only
WLFW/BDF observer. If V615 only reaches sibling sysmon, classify the remaining
gap before CNSS. If no lower marker advances, do not retry Wi-Fi HAL or
scan/connect.
