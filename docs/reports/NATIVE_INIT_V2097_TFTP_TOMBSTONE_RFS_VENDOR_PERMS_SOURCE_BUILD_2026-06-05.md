# Native Init V2097 TFTP Tombstone-RFS Vendor-Perms Source Build

## Summary

- Cycle: `V2097`
- Type: source/build-only follow-up to V2096, fixing the tombstone-RFS bridge ownership to match live `tftp_server` (`uid/gid vendor_rfs=2903`) and adding the observed `tn` directory.
- Decision: `v2097-tftp-tombstone-rfs-vendor-perms-source-build-pass`
- Result: PASS
- Reason: helper v410 keeps the V2095 light internal-modem route but creates `/data/vendor/tombstones/rfs/{modem,lpass,tn}` as namespace-local directories owned by `vendor_rfs:vendor_rfs`. This only corrects the V2096 setup miss where root-owned `0770` dirs still produced `EACCES`; it still does not create `ota_firewall/ruleset`, ptrace `tftp_server`, retry macloader, send QMI, use DIAG, use Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or touch SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO.
- Manifest: `tmp/wifi/v2097-tftp-tombstone-rfs-vendor-perms-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2097-tftp-tombstone-rfs-vendor-perms-test-boot/boot_linux_v2097_tftp_tombstone_rfs_vendor_perms.img`
- Boot SHA256: `5c1c1cfa30f5820983628c45edffe4fad266f411561d51eb2f9cdb27c9adcb04`
- Init: `A90 Linux init 0.9.226 (v2097-tftp-tombstone-rfs-vendor-perms)`
- Helper marker: `a90_android_execns_probe v410`
- Helper SHA256: `6b243cde11b152f56a8d83628c3c1010c1750368947ec29fccd7d6839d593397`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2097/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2095 route, Android-parity RFS readonly/readwrite bridges, `tftp_server` logdw sink, PerMgr/WLFW focused summaries, post-BDF surface summary, and long lower-window hold.
- Added: namespace-local `vendor_rfs:vendor_rfs` permission parity for `/data/vendor/tombstones/rfs/{modem,lpass,tn}` only.
- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The live handoff should decide whether clearing the tombstone auto-dir setup failure changes the Android-order `server_check -> ota_firewall -> wlanmdsp` branch.
