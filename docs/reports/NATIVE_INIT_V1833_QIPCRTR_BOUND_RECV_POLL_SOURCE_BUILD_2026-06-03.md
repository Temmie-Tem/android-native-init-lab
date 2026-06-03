# Native Init V1833 QIPCRTR Bound Poll/Recv Source Build

## Summary

- Cycle: `V1833`
- Type: source/build-only rollbackable QIPCRTR bound socket poll/recv observer test boot artifact
- Decision: `v1833-qipcrtr-bound-recv-poll-source-build-pass`
- Result: PASS
- Reason: helper v352 keeps the bounded lower publication route and adds one observed-local-node AF_QIPCRTR bound socket poll/recv snapshot at `net_window`.
- Manifest: `tmp/wifi/v1833-qipcrtr-bound-recv-poll-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1833-qipcrtr-bound-recv-poll-test-boot/boot_linux_v1833_qipcrtr_bound_recv_poll.img`
- Boot SHA256: `eac1a66a49c5a102bd9a2b6c43a21cf7f0addec3202073cec1308d9587ad1f5f`
- Init: `A90 Linux init 0.9.161 (v1833-qipcrtr-bound-recv-poll)`
- Helper marker: `a90_android_execns_probe v352`
- Helper SHA256: `b234d83dc05c170a8d8f4bce6a72845596f3fdc6250d17dfabb543027becf19b`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1833/dev/__properties__`
- Base route remains the bounded lower handoff observer and retains the unbound, node-zero bind, and observed-local-node bind snapshots.
- Added bound poll/recv prefix: `wlan_pd_qipcrtr_bound_recv_poll_state.net_window.*`.
- Added passive operations: protocol summary before open, AF_QIPCRTR/SOCK_DGRAM open, pre-bind `getsockname`, bind using observed local node and port `0`, post-bind `getsockname`, protocol summary before poll, `O_NONBLOCK`, 250 ms `poll(POLLIN)`, `recvfrom` only if `POLLIN`, protocol summary after poll, close, and protocol summary after close.
- Explicit non-actions: `no_connect=1`, `no_send=1`, `no_qrtr_lookup_send=1`, `no_qrtr_control_payload=1`, and `no_service_start=1`.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1834 should run one rollbackable live gate with this artifact only if the bound poll/recv snapshot is accepted as the next bounded surface.
- `qipcrtr-bound-recv-poll-timeout-passive`: bind succeeds, no inbound QRTR datagram arrives during the 250 ms window, and service74/wlan_pd still remain absent.
- `qipcrtr-bound-recv-poll-packet-passive`: bind succeeds and one inbound datagram is observed without connect/send/lookup/control traffic; stop for classification.
- `qipcrtr-bound-recv-poll-error`: bind succeeds but `poll` or `recvfrom` errors; capture errno and stop.
- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
