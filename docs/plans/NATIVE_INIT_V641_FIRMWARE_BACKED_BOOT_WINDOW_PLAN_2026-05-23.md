# Native Init V641 Firmware-Backed Boot-Window Sibling Trigger Plan

- date: `2026-05-23 KST`
- cycle: `v641`
- scope: rollback-ready boot image proof planning
- target: test the only remaining safe service `74` prerequisite class:
  firmware-backed sibling SSCTL trigger in the native boot window

## Why V641

V640 ruled out a new daemon-first path:

- Android service `74` appears after sibling SLPI/CDSP/ADSP `sysmon-qmi`.
- The only non-write Android services before service `74` are `qrtr_ns` and
  `pd_mapper`, and both have already been replayed in native lower-path tests.
- `rmt_storage`, `tftp_server`, `mdm_launcher`, `mdm_helper`, `cnss_diag`, and
  `cnss-daemon` start after service `74` in the Android V622 timing evidence.
- V638/V639 block late all-sibling direct writes because they trigger `pm_qos`
  kernel warnings and still do not publish service `74`.
- V630/V631 proved boot-window one-shot/rollback mechanics, but those attempts
  ran before the V634/V635 firmware mount/CDSP fix was known.

Therefore the next useful mutation is not Wi-Fi HAL, credentials, scan/connect,
or another live sysfs write. It is a disabled-by-default boot-window proof that
adds the missing firmware surface before the sibling trigger sequence.

## Guardrails

V641 must:

- be disabled by default;
- require an explicit one-shot arm flag such as
  `/cache/native-init-sibling-fwssctl-v641`;
- remove the flag before executing any proof action;
- use independent child timeout/reap handling per proof step;
- log every step to `/cache/native-init-sibling-fwssctl-v641.log` and kernel
  log tags;
- keep shell access even after timeout/failure;
- have a known-good v319 rollback image and command path before live use.

V641 must not:

- start service-manager, Wi-Fi HAL, supplicant, hostapd, scan/connect, or
  credential handling;
- write `boot_wlan`, `qcwlanstate`, or `shutdown_wlan`;
- run DHCP, change routes, or ping externally;
- commit or print Wi-Fi credentials;
- leave writeable Android/vendor partitions mounted.

## Proposed Boot-Window Sequence

1. Start from the latest v319-compatible init code plus the V631 per-node
   timeout/reap pattern.
2. After `/cache` is mounted and before the interactive shell handoff, check the
   one-shot arm flag.
3. If unarmed, boot normally and emit only a disabled-smoke marker.
4. If armed:
   - remove the arm flag immediately;
   - create `/vendor`, `/vendor/firmware_mnt`, and `/vendor/firmware-modem`
     mountpoints if absent;
   - resolve `apnhlos` and `modem` block devices using the V634/V638 partition
     discovery pattern;
   - mount `apnhlos` at `/vendor/firmware_mnt` read-only as `vfat`;
   - mount `modem` at `/vendor/firmware-modem` read-only as `vfat`;
   - verify representative firmware files before writing CDSP/ADSP/SLPI nodes;
   - run ADSP, CDSP, and SLPI writes with per-node child timeout/reap;
   - log node state snapshots after each node if readable;
   - continue to shell regardless of result.
5. Host-side live runner captures:
   - `bootstatus`;
   - V641 proof log;
   - timeline;
   - dmesg markers for sibling `sysmon-qmi`, service `74`, WLAN-PD, WLFW/BDF,
     firmware-ready, `wlan0`, and kernel warnings;
   - mount cleanup state.
6. Roll back to v319 and verify native health before any further gate.

## Success Criteria

V641 can pass in one of these bounded ways:

- `v641-disabled-smoke-pass`: unarmed image boots normally and proof is absent.
- `v641-firmware-backed-sibling-sysmon-advanced`: sibling `sysmon-qmi` advances
  without kernel warnings.
- `v641-service74-advanced`: service `74` appears without kernel warnings.
- `v641-warning-or-timeout-blocked`: any timeout, unreaped child, cleanup
  failure, or kernel warning occurs and rollback succeeds.

Only service `74`, WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0` advancement
can justify a later CNSS/HAL/connect plan. V641 itself still does not authorize
credentials or `google.com` ping.

## Validation Plan

Before any live flash:

1. build the V641 image locally;
2. verify string markers:
   - `A90 Linux init 0.9.x (v641)`;
   - `native-init-sibling-fwssctl-v641`;
   - `wifi-v641-fwssctl`;
3. run static grep proving no `boot_wlan`, `qcwlanstate`, Wi-Fi credential,
   DHCP, route, or external ping string is introduced;
4. verify v319 rollback image hash is available;
5. run disabled-smoke first;
6. only then run armed proof once.
