# Native Init V1608 per_mgr Early-exit Trace Source Build

## Summary

- Cycle: `V1608`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1608-per-mgr-early-exit-trace-test-boot-source-build-pass`
- Result: PASS
- Reason: built the V1604 route with helper v299 and a bounded `per_mgr`-only ptrace/syscall/exit tracer
- Manifest: `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/boot_linux_v1608_wifi_test.img`
- Boot SHA256: `6eb8f218b2bc7a7cfdd7c2f27cba290643149e0de4631de89574c9ac255cf076`
- Init: `A90 Linux init 0.9.107 (v1608-per-mgr-early-exit-trace)`
- Init SHA256: `bdad16758b6ef2beca70ee9ce171346360900ae3d37db497063976a63b020d9c`
- Helper marker: `a90_android_execns_probe v299`
- Helper SHA256: `c5ecbd41c06943f88c88f32fbdacdcd28d5d46c62fbcceb159de4f269619389b`

## Delta From V1604

- Bumps `a90_android_execns_probe` to v299.
- Preserves the PM-first late-per-proxy PPH-gated lower-marker route.
- Keeps the V1604 startup sampler and adds `--capture-mode ptrace-lite` plus `--allow-android-wifi-service-window-per-mgr-early-exit-trace`.
- Traces only `/vendor/bin/pm-service`; it does not ptrace `mdm_helper` or broaden the lower hardware path.
- Records selected `openat`, stat/access/readlink, socket/bind/connect, ioctl, read/write, futex, wait, and exit syscalls plus the ptrace exit snapshot.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1608.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1608.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1608-helper.result`
- Supervisor timeout sec: `130`
- Helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`
- Firmware mounts: `True`
- Android service window: `True`

## Safety Scope

This build script was source/build-only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device partitions.

## Next

V1609 should run local artifact sanity over this exact manifest. If it passes, a later rollbackable live handoff can collect the per_mgr syscall/exit records and roll back to `stage3/boot_linux_v724.img`.
