# Native Init V2077 Remote-MDM DIAG Bridge Poll Source Build

## Summary

- Cycle: `V2077`
- Type: source/build-only rollbackable internal-modem route with V2073 WLAN-PD memory session masks plus a query-only remote-MDM DIAG bridge poll
- Decision: `v2077-remote-mdm-diag-bridge-poll-source-build-pass`
- Result: PASS
- Reason: helper v402 keeps the V2073 light observer route and polls borrowed-fd `DIAG_IOCTL_REMOTE_DEV` across the lower window. It records whether the MDM data bridge ever becomes active before any future remote-MDM mask attempt, and does not send remote masks, QMI, USB/PCIE restore, DCI stream config, ptrace, AP-side strace, or QRTR matrices.
- Manifest: `tmp/wifi/v2077-remote-mdm-diag-bridge-poll-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2077-remote-mdm-diag-bridge-poll-test-boot/boot_linux_v2077_remote_mdm_diag_bridge_poll.img`
- Boot SHA256: `b02dbca299f161340c29fc9648291071577f15bd1104d5caddaff453c62f3d15`
- Init: `A90 Linux init 0.9.217 (v2077-remote-mdm-diag-bridge-poll)`
- Helper marker: `a90_android_execns_probe v402`
- Helper SHA256: `68cb51de7685425e5e43346aae21aa9491e8da90291d1dc1ec3caa241433c5a6`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2077/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote summary retained only as a closed baseline; private `/dev/diag` DCI support/register/read/deinit; bounded WLAN target masks; WLAN-PD memory-device session; session-scoped regular WLAN log/event masks; query-only `DIAG_IOCTL_REMOTE_DEV` remote bridge polling.
- Remote discriminator: `DIAG_IOCTL_REMOTE_DEV` number `32`, `DIAGFWD_MDM` slot `0`, success if any returned remote-device mask has bit `0` set during the lower window.
- Branch: if MDM data bridge is never active, do not send remote masks and close this transport. If it becomes active, a later unit can target that time window with one bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write under a separate report.
- Excluded: remote DIAG mask writes, USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
