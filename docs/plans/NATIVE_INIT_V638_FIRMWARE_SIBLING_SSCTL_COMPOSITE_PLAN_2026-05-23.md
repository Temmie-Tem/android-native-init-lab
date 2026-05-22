# Native Init V638 Firmware-Backed Sibling SSCTL Composite Plan

- date: `2026-05-23 KST`
- cycle: `v638`
- scope: planned bounded live observer
- target: test whether firmware-backed per-node ADSP/CDSP/SLPI sibling SSCTL
  writes can publish Android-like sibling `sysmon-qmi` and service `74`
  without starting Wi-Fi HAL or connecting Wi-Fi

## Background

V637 classified the current blocker:

- Android V622 publishes SLPI/CDSP/ADSP sibling `sysmon-qmi`, then service
  `180`, then service `74` within `6.561ms`.
- V635 fixes CDSP boot-node timeout under read-only firmware mounts, but CDSP
  PIL/reset/power-clock/`ONLINE` does not create `sysmon_cdsp`.
- V636 combines CDSP-online with the V598 modem-holder path and still reaches
  only service `180`.

Therefore the next useful live gate is not Wi-Fi credentials, HAL, or
connectivity. It is a lower sibling-SSCTL publication observer.

## Guardrails

V638 may:

- require a fresh native v319 baseline;
- refresh current-boot V401/V490 prerequisites;
- mount `apnhlos` and `modem` read-only using the V634/V635 cleanup pattern;
- write ADSP, CDSP, and SLPI boot nodes in per-node bounded children;
- continue after an individual node timeout only if the child is killed and
  reaped;
- capture dmesg and subsystem state for sibling `sysmon-qmi`, service `74`,
  WLAN-PD, WLFW/BDF, firmware-ready, `wlan0`, and kernel warnings;
- optionally run the no-HAL V598-class observer only if the sibling write phase
  is warning-free.

V638 must not:

- touch `boot_wlan`, `qcwlanstate`, or `shutdown_wlan`;
- start service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- leave firmware mounts, holder processes, or child processes behind.

## Stop Conditions

Stop and classify immediately if any of these occurs:

- `pm_qos_add_request`, reference-count mismatch, WARN/OOPS, or subsystem
  restart warning;
- any child cannot be reaped after timeout;
- firmware mounts cannot be unmounted;
- native post-health is not `fail=0`;
- service-manager/HAL/Wi-Fi link surface appears unexpectedly.

## Success Criteria

V638 passes if it classifies one of these outcomes with cleanup evidence:

- `v638-sibling-sysmon-service74-advanced`
- `v638-sibling-sysmon-only`
- `v638-service180-only`
- `v638-sibling-write-warning-blocked`
- `v638-sibling-write-timeout-blocked`
- `v638-firmware-sibling-composite-inconclusive`

Only service `74`, WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0` advancement can
justify moving toward CNSS/HAL/qcwlanstate. Wi-Fi credentials and external ping
remain blocked until a later link/scan gate explicitly permits them.
