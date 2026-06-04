# Native Init V2090 Macloader Property Service Source Build

## Summary

- Cycle: `V2090`
- Type: source/build-only bounded `macloader` syscall discriminator over the V2086 MAC-source bridge route.
- Decision: `v2090-macloader-property-service-source-build-pass`
- Result: PASS
- Reason: helper v408 keeps the light internal-modem route and adds single-child `macloader` ptrace plus compile-gated property-service ACK only, proving whether macloader was stalled by denied property_set calls before boot_wlan/MAC writes. It also keeps hashed short read/write payload samples and records colon/hex shape only; it does not emit raw MAC bytes.
- Manifest: `tmp/wifi/v2090-macloader-property-service-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2090-macloader-property-service-test-boot/boot_linux_v2090_macloader_property_service.img`
- Boot SHA256: `015e8339d790c77810d8fcf6b8d7f951b24555af19cbfc84449d24d714c49e9a`
- Init: `A90 Linux init 0.9.224 (v2090-macloader-property-service)`
- Helper marker: `a90_android_execns_probe v408`
- Helper SHA256: `1892ec3b528937079dcb9cd97fb8cc4b95c68d7a623599be61b8d8af30373fb0`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2090/dev/__properties__`
- Light firmware trace: `True`
- Order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,macloader,cnss_daemon`.
- Added: compile-gated ACK for `vendor.wifi.dualconcurrent.interface=swlan0` and `ro.vendor.wifi.sap.interface=swlan0`, real-node `statfs` snapshots for `/sys/wifi/mac_addr`, `/sys/kernel/boot_wlan/boot_wlan` existence/writability, `/data/vendor/conn` namespace availability, and focused `macloader` syscall records.
- Kept: clean-DSP companion, `pm-service`, read-only MAC-source bridge, `/dev/subsys_modem` holder, stock `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, PerMgr/WLFW compact summaries, post-BDF surface summary, and long lower-window hold.
- Excluded: Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, external ping, DIAG mask/log-mode, passive DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, `cnss-daemon` ptrace, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, raw MAC payload logging, and firmware/partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual V2091 live handoff is rollbackable and intentionally permits only the Android `macloader` driver-start action, the compile-gated private property-service ACK for two interface properties, and single-child `macloader` ptrace. EFS/persist exposure remains read-only, RFS bridges are namespace-local, and MAC assignment is treated as a bounded downstream/cosmetic falsifier rather than the primary modem producer gate.
