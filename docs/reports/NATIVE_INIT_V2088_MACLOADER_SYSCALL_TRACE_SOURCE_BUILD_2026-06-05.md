# Native Init V2088 Macloader Syscall Trace Source Build

## Summary

- Cycle: `V2088`
- Type: source/build-only bounded `macloader` syscall discriminator over the V2086 MAC-source bridge route.
- Decision: `v2088-macloader-syscall-trace-source-build-pass`
- Result: PASS
- Reason: helper v407 keeps the light internal-modem route and adds single-child `macloader` ptrace only, proving whether `macloader` opens/reads `.mac.info` and writes the real `/sys/wifi/mac_addr` node. It hashes short read/write payload samples and records colon/hex shape only; it does not emit raw MAC bytes.
- Manifest: `tmp/wifi/v2088-macloader-syscall-trace-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2088-macloader-syscall-trace-test-boot/boot_linux_v2088_macloader_syscall_trace.img`
- Boot SHA256: `7300e9ec65b9f1360bba28ca98acdc0912e879f637a7159b23b56aaa673f89ad`
- Init: `A90 Linux init 0.9.223 (v2088-macloader-syscall-trace)`
- Helper marker: `a90_android_execns_probe v407`
- Helper SHA256: `313315ff66d23c1f19993f1ed487763bc3f5d9e1c2768014b96d74eeb1868b92`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2088/dev/__properties__`
- Light firmware trace: `True`
- Order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,macloader,cnss_daemon`.
- Added: real-node `statfs` snapshots for `/sys/wifi/mac_addr`, `/sys/kernel/boot_wlan/boot_wlan` existence/writability, `/data/vendor/conn` namespace availability, and focused `macloader` syscall records.
- Kept: clean-DSP companion, `pm-service`, read-only MAC-source bridge, `/dev/subsys_modem` holder, stock `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, PerMgr/WLFW compact summaries, post-BDF surface summary, and long lower-window hold.
- Excluded: Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, external ping, DIAG mask/log-mode, passive DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, `cnss-daemon` ptrace, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, raw MAC payload logging, and firmware/partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual V2089 live handoff is rollbackable and intentionally permits only the Android `macloader` driver-start action plus single-child `macloader` ptrace. EFS/persist exposure remains read-only, RFS bridges are namespace-local, and MAC assignment is treated as a bounded downstream/cosmetic falsifier rather than the primary modem producer gate.
