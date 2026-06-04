# Native Init V2086 Macloader MAC-Source Bridge Source Build

## Summary

- Cycle: `V2086`
- Type: source/build-only native route that adds one Android-parity `macloader` active driver-start child before `cnss-daemon` and exposes read-only EFS/persist plus ICNSS sysfs to `macloader`.
- Decision: `v2086-mac-source-bridge-source-build-pass`
- Result: PASS
- Reason: helper v406 keeps the V2082 light internal-modem route and adds `/vendor/bin/hw/macloader` with Android init parity before `cnss-daemon`, wiring `/mnt/vendor/efs/wifi/.mac.info`, `/sys/wifi`, `/sys/kernel/boot_wlan`, and `/persist/WCNSS_qcom_wlan_nv.bin` into the private namespace (`user wifi`, `group wifi inet net_raw net_admin`, `NET_ADMIN NET_RAW SYS_MODULE`, `u:r:macloader:s0`). This is an explicit active driver-start gate with read-only EFS/persist exposure, not a read-only observer; it still excludes Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, eSoC/PCIe/GDSC/PMIC/GPIO paths, and firmware/partition writes.
- Manifest: `tmp/wifi/v2086-mac-source-bridge-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2086-mac-source-bridge-test-boot/boot_linux_v2086_mac_source_bridge.img`
- Boot SHA256: `bbe3370ff2986985a1ab6ced25ff0d9f3991dbbd18a69d6e1c20d292ffdc2e8d`
- Init: `A90 Linux init 0.9.222 (v2086-mac-source-bridge)`
- Helper marker: `a90_android_execns_probe v406`
- Helper SHA256: `e57b01e33ddcf317a6e81edc8f4e97cafcfce55edcc72bc2daa6713aa78b4106`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2086/dev/__properties__`
- Light firmware trace: `True`
- Order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,macloader,cnss_daemon`.
- Kept: clean-DSP companion, `pm-service`, read-only MAC-source bridge, `/dev/subsys_modem` holder, stock `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, PerMgr/WLFW compact summaries, post-BDF surface summary, and long lower-window hold.
- Excluded: Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, external ping, DIAG mask/log-mode, passive DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, and firmware/partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual V2087 live handoff is rollbackable and intentionally permits the Android `macloader` driver-start action while still forbidding Wi-Fi HAL/scan/connect/credentials/DHCP/routes/external ping and off-path modem/PCIe/GDSC/PMIC/GPIO actions.
