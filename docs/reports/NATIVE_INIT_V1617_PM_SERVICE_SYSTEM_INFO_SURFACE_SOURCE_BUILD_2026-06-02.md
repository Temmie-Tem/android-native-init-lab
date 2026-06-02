# Native Init V1617 pm-service System-info Surface Source Build

## Summary

- Cycle: `V1617`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1617-pm-service-system-info-surface-test-boot-source-build-pass`
- Result: PASS
- Reason: built the V1612 route with helper v301 and non-ptrace `pm-service` system-info surface snapshots
- Manifest: `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/boot_linux_v1617_wifi_test.img`
- Boot SHA256: `7d9b60862a8eab04e0a0fe35b929ace255f0de669412a0cbe6262f6f0495419d`
- Init: `A90 Linux init 0.9.109 (v1617-pm-service-system-info-surface)`
- Init SHA256: `1cd6967d597a73e6b99b762f32e67fcaba11436c0b2697c1be10a4626ff209f6`
- Helper marker: `a90_android_execns_probe v301`
- Helper SHA256: `1b870e4244ba2794ee30bc113d6aa421f66dfea55a9c116139978b1b4b9e787e`

## Delta From V1612/V1616

- Bumps `a90_android_execns_probe` to v301.
- Preserves the PM-first late-per-proxy PPH-gated lower-marker route.
- Keeps the non-ptrace `per_mgr` startup/context branch.
- Adds `--allow-android-wifi-service-window-per-mgr-system-info-surface`.
- Captures read-only `pm_service_system_info_surface.*` snapshots before and after `per_mgr` startup tracing.

## Captured Surface

- `/sys/bus/msm_subsys/devices`
- `/sys/bus/esoc/devices`
- `/sys/class/esoc-dev`
- `/dev/subsys_*`, `/dev/esoc-*`, `/dev/vndbinder`, `/dev/binder`, `/dev/hwbinder`
- private property root and service-manager sockets

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1617.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1617.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1617-helper.result`
- Supervisor timeout sec: `130`
- Helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`
- Firmware mounts: `True`
- Android service window: `True`

## Safety Scope

This build script was source/build-only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device partitions.

## Next

V1618 should run local artifact sanity over this exact manifest. If it passes, V1619 can perform a rollbackable live handoff to collect the `pm_service_system_info_surface.*` snapshots and roll back to `stage3/boot_linux_v724.img`.
