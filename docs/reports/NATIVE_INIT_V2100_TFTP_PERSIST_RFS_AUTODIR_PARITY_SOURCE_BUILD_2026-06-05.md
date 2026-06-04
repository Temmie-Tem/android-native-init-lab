# Native Init V2100 TFTP Persist-RFS Auto-Dir Parity Source Build

## Summary

- Cycle: `V2100`
- Type: source/build-only follow-up to V2099, fixing the remaining `tftp_server` auto-dir EACCES target after tombstone parity cleared.
- Decision: `v2100-tftp-persist-rfs-autodir-parity-source-build-pass`
- Result: PASS
- Reason: helper v411 keeps the V2097 light internal-modem route and adds only namespace-local persist-RFS auto-dir targets `/mnt/vendor/persist/rfs/{shared,msm/mpss,msm/adsp}` before stock `tftp_server` starts. This does not fabricate `ota_firewall/ruleset`, ptrace `tftp_server`, retry macloader, send QMI, use DIAG, use Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or touch SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO.
- Manifest: `tmp/wifi/v2100-tftp-persist-rfs-autodir-parity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2100-tftp-persist-rfs-autodir-parity-test-boot/boot_linux_v2100_tftp_persist_rfs_autodir_parity.img`
- Boot SHA256: `e5dcdd83d896a7dbab597fbf2d04d2421f720fd93bcf47b99675ceee5fe43f60`
- Init: `A90 Linux init 0.9.227 (v2100-tftp-persist-rfs-autodir-parity)`
- Helper marker: `a90_android_execns_probe v411`
- Helper SHA256: `b3b68a3560f8c16f495e7028922ca5157222c36f56780737e27833a3e02d0f1d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2100/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2097 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, post-BDF surface summary, and long lower-window hold.
- Added: namespace-local persist-RFS auto-dir targets only; `sda29` remains read-only.
- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The live handoff should decide whether clearing the remaining persist-RFS startup auto-dir failures changes the native `server_check -> ota_firewall -> wlanmdsp` producer branch.
