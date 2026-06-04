# Native Init V2095 TFTP Tombstone-RFS Parity Source Build

## Summary

- Cycle: `V2095`
- Type: source/build-only light internal-modem route with one namespace-local TFTP tombstone-RFS parity bridge.
- Decision: `v2095-tftp-tombstone-rfs-parity-source-build-pass`
- Result: PASS
- Reason: helper v409 keeps the V2082 light route and adds only private-root `/data/vendor/tombstones/rfs/{modem,lpass}` directories so `tftp_server` no longer fails its Android tombstone auto-dir setup before the lower-window vote. It does not create `ota_firewall/ruleset`, does not ptrace `tftp_server`, and does not add macloader, AP QMI captures, DIAG, QRTR matrix, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or off-path SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO actions.
- Manifest: `tmp/wifi/v2095-tftp-tombstone-rfs-parity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2095-tftp-tombstone-rfs-parity-test-boot/boot_linux_v2095_tftp_tombstone_rfs_parity.img`
- Boot SHA256: `61a286433a52af5bf1462d07fc476886294aef1ed41bee65ff4ed8438a2b9093`
- Init: `A90 Linux init 0.9.225 (v2095-tftp-tombstone-rfs-parity)`
- Helper marker: `a90_android_execns_probe v409`
- Helper SHA256: `4740f435dabb54a046af205aad8dfef2b3e0d125a5b70c8787019fbf464b42d5`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2095/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS readonly/readwrite bridges, cap/BDF/cal probes, PerMgr compact summary, late `msg_id=0x21` compact summary, read-only ICNSS/QCACLD post-BDF summary, and long lower-window hold.
- Added: namespace-local private-root `/data/vendor/tombstones/rfs/modem` and `/data/vendor/tombstones/rfs/lpass` directories only; `sda29` remains read-only and the helper reports `ota_ruleset_created=0`.
- Excluded: macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, private SDX50M route, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual live handoff remains rollbackable and should classify only whether removing the `tftp_server` tombstone auto-dir failure changes the early `server_check -> ota_firewall -> wlanmdsp` branch.
