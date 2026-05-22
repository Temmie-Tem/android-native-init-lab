# Native Init V641 Firmware-Backed Boot-Window Prep Report

- date: `2026-05-23 KST`
- cycle: `v641`
- status: `prep/build-ready`; Wi-Fi external ping is **not** complete
- builder: `scripts/revalidation/build_native_init_boot_v641.py`
- local boot image: `stage3/boot_linux_v641.img`
- rollback image: `stage3/boot_linux_v319.img`

## Scope

V641 prepares a rollback-ready native init image for the next bounded live gate.
It is disabled by default and only runs the proof when the one-shot arm flag
`/cache/native-init-sibling-fwssctl-v641` contains `run`.

No device command, boot partition write, reboot, daemon start, service-manager
start, Wi-Fi HAL start, scan/connect/link-up, credential handling, DHCP, route
change, or external ping was executed during this prep step.

## Implementation

- Adds `stage3/linux_init/init_v641.c` and `stage3/linux_init/v641/90_main.inc.c`.
- Bumps PID1 metadata to `A90 Linux init 0.9.67 (v641)`.
- Adds `scripts/revalidation/build_native_init_boot_v641.py`.
- Preserves the V631 per-node child timeout/reap pattern for ADSP/CDSP/SLPI.
- Before any sibling SSCTL write, creates `/vendor`, `/vendor/firmware_mnt`,
  and `/vendor/firmware-modem`, resolves `apnhlos`/`modem` partitions by
  `PARTNAME` with `sda20`/`sda21` fallback, and mounts both read-only as `vfat`.
- Logs firmware stat probes for `image`, `modem.b00`, and `cdsp.mdt` surfaces
  into `/cache/native-init-sibling-fwssctl-v641.log`.
- Stops the proof if firmware mount setup fails, but continues into the normal
  serial shell path.

## Validation

```text
python3 -m py_compile scripts/revalidation/build_native_init_boot_v641.py
python3 scripts/revalidation/build_native_init_boot_v641.py
strings stage3/boot_linux_v641.img | rg 'A90 Linux init 0\.9\.67 \(v641\)|A90v641: sibling fwssctl proof armed|A90v641: firmware mounts ready|native-init-sibling-fwssctl-v641|wifi-v641-fwssctl'
git diff --unified=0 -- scripts/revalidation/build_native_init_boot_v641.py stage3/linux_init/init_v641.c stage3/linux_init/v641/90_main.inc.c stage3/linux_init/a90_changelog.c stage3/linux_init/a90_config.h | rg '^\+.*(boot_wlan|qcwlanstate|shutdown_wlan|google\.com|wpa_supplicant|hostapd|dhcp|route add|ip route|SSID|password|PASSWORD|PASSWD)' || true
git diff --check
```

Result:

```text
markers: pass
init_sha256=fd00ad98fe8f8f8b73af1cea5a68cbea04a564c2c97ab910bcc10e01ad4493ca
ramdisk_sha256=bc00d5a7d501c6e595ac105a6bfdebf11dd2bba0eda6197e06117b321082f3e2
boot_sha256=f957e1db0a270f71af4273072a5ca61772cd738ab86954f48ce4f74861064e15
introduced forbidden active strings: none
diff check: pass
```

Generated boot/ramdisk/binary artifacts are local ignored build outputs. The
committed unit should contain source, builder, and documentation only.

## Next Gate

Run V641 live in two stages:

1. disabled-smoke flash and boot, with no arm flag, then verify bootstatus and
   that the proof did not run;
2. if disabled-smoke passes, set the one-shot arm flag and run the armed proof
   once, capturing proof log, timeline, dmesg markers, kernel warnings, mount
   state, and rollback to v319.

Only service `74`, WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0` advancement
without kernel warnings justifies moving toward CNSS/HAL/connect work. V641
still does not authorize credentials or external ping.
