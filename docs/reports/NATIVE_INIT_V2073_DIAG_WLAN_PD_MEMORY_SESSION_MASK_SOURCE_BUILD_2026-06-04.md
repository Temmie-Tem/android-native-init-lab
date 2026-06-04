# Native Init V2073 DIAG WLAN-PD Memory Session-Mask Source Build

## Summary

- Cycle: `V2073`
- Type: source/build-only rollbackable internal-modem route with V2071 WLAN-PD memory-device mode plus session-scoped regular DIAG masks
- Decision: `v2073-diag-wlan-pd-memory-session-mask-source-build-pass`
- Result: PASS
- Reason: helper v400 keeps the V2071 route and, after `DIAG_IOCTL_SWITCH_LOGGING` succeeds for `DIAG_CON_UPD_WLAN` in `MEMORY_DEVICE_MODE`, disables HDLC only for that helper-owned memory session, writes `USER_SPACE_DATA_TYPE` normal app masks for exactly three WLAN log codes and three WLAN event IDs, holds them through the lower window, clears them, re-enables HDLC, and closes the fd.
- Manifest: `tmp/wifi/v2073-diag-wlan-pd-memory-session-mask-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2073-diag-wlan-pd-memory-session-mask-test-boot/boot_linux_v2073_diag_wlan_pd_memory_session_mask.img`
- Boot SHA256: `051f4363209b432cf095bea7141cbe0d5874cff9cb0fe8f3a15f812f7101842e`
- Init: `A90 Linux init 0.9.215 (v2073-diag-wlan-pd-memory-session-mask)`
- Helper marker: `a90_android_execns_probe v400`
- Helper SHA256: `4cb7f6f60bc1408edd09b30cdb500c39ee20502447ac7ea20c39d56ca1a2d682`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2073/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote uprobes; private `/dev/diag` DCI support/register/read/deinit plus bounded WLAN target masks; borrowed-fd WLAN-PD memory-device session; session-scoped regular WLAN log/event masks.
- Regular mask scope: `USER_SPACE_DATA_TYPE`, session-local HDLC disabled, `LOG_WLAN_PKT_LOG_INFO_C` (`0x18e0`), `LOG_WLAN_COLD_BOOT_CAL_DATA_C` (`0x1a18`), `LOG_WLAN_DP_PROTO_PKT_INFO_C` (`0x1a1e`), `EVENT_WLAN_BRINGUP_STATUS` (`0x0680`), `EVENT_WLAN_LOG_COMPLETE` (`0x0aa7`), and `EVENT_WLAN_STATUS_V2` (`0x0ab3`).
- Excluded: USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
