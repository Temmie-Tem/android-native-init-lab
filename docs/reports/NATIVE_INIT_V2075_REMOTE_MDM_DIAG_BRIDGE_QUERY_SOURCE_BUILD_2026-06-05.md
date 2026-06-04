# Native Init V2075 Remote-MDM DIAG Bridge Query Source Build

## Summary

- Cycle: `V2075`
- Type: source/build-only rollbackable internal-modem route with V2073 WLAN-PD memory session masks plus a query-only remote-MDM DIAG bridge discriminator
- Decision: `v2075-remote-mdm-diag-bridge-query-source-build-pass`
- Result: PASS
- Reason: helper v401 keeps the V2073 light observer route and adds one borrowed-fd `DIAG_IOCTL_REMOTE_DEV` query before DCI registration/mask writes. It records whether the MDM data bridge is active before any future remote-MDM mask attempt, and does not send remote masks, QMI, USB/PCIE restore, DCI stream config, ptrace, AP-side strace, or QRTR matrices.
- Manifest: `tmp/wifi/v2075-remote-mdm-diag-bridge-query-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2075-remote-mdm-diag-bridge-query-test-boot/boot_linux_v2075_remote_mdm_diag_bridge_query.img`
- Boot SHA256: `b5bad8ea95836c2256ba02e73dba8969ed702ee110ca3fecbf1138eb8b57cbee`
- Init: `A90 Linux init 0.9.216 (v2075-remote-mdm-diag-bridge-query)`
- Helper marker: `a90_android_execns_probe v401`
- Helper SHA256: `056f0d21b08384a8278d828723c8efd9ead2365f355185c1365ba046ecd0a130`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2075/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote summary retained only as a closed baseline; private `/dev/diag` DCI support/register/read/deinit; bounded WLAN target masks; WLAN-PD memory-device session; session-scoped regular WLAN log/event masks; query-only `DIAG_IOCTL_REMOTE_DEV` remote bridge status.
- Remote discriminator: `DIAG_IOCTL_REMOTE_DEV` number `32`, `DIAGFWD_MDM` slot `0`, success if the returned remote-device mask has bit `0` set.
- Branch: if MDM data bridge is inactive, do not send remote masks and pivot away from remote-MDM DIAG. If active, the next live unit can consider one bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write under a separate approval/report.
- Excluded: remote DIAG mask writes, USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
