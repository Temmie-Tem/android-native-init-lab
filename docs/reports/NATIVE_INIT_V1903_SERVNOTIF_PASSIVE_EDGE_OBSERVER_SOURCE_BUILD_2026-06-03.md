# Native Init V1903 Service-notifier Passive-edge Observer Source Build

## Summary

- Cycle: `V1903`
- Type: source/build-only rollbackable internal-modem service-notifier passive-edge observer test boot artifact
- Decision: `v1903-servnotif-passive-edge-observer-source-build-pass`
- Result: PASS
- Reason: V1902 selected the internal modem service-notifier root-service state-up edge as the remaining boundary; this artifact keeps the proven post-PM lower observer and updates it to helper v359 without SDX50M, PCIe, eSoC, delayed degraded-boot sampler, or GDSC paths.
- Manifest: `tmp/wifi/v1903-servnotif-passive-edge-observer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1903-servnotif-passive-edge-observer-test-boot/boot_linux_v1903_servnotif_passive_edge_observer.img`
- Boot SHA256: `eb6539ccc4603bfc0e0372fbde53eb0bc4e5b56c0ba4bff2453c183b6bca25ba`
- Init: `A90 Linux init 0.9.172 (v1903-servnotif-passive-edge-observer)`
- Helper marker: `a90_android_execns_probe v359`
- Helper SHA256: `6d69287158a12b47b8e8d795e9ee3cc3401380a9c905adf5cd5f3e2b75f7711c`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1903/dev/__properties__`
- Internal modem route only: `/dev/subsys_modem` post-vote observer, service-locator domain-list, service-notifier listener, WLFW QRTR readback, and bounded AF_QIPCRTR passive poll/recv surfaces.
- Klog discriminator fields retained: `wlan_pd_post_pm_lower_handoff_klog.*.raw_count_service_notifier_new_server`, `raw_count_180_service_text`, `raw_count_74_service_text`, `raw_count_wlan_pd_text`, and last-line snapshots.
- Helper v359 disables the V1880 delayed `post_powerup_delayed` sampler by default; this keeps V1903 anchored to the normal internal-modem boot window instead of the degraded 257s SDX50M/PCIe/MHI path.
- Stop condition: service 74, `wlan_pd`, WLFW service 69, requested `wlanmdsp`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.
- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- `servnotif-passive-edge-progress-readonly-stop`: service74, `wlan_pd`, WLFW service 69, requested `wlanmdsp`, or `wlan0` appears; stop before connect.
- `servnotif-new-server-180-only-stateup-edge-absent`: service-notifier new-server/service180 is visible, but service74/`wlan_pd`/WLFW69/`wlan0` stay absent and listener state remains `uninit`.
- `servnotif-passive-edge-incomplete`: bounded fields were collected but do not match a fixed absence/progress discriminator.
- `safety-regression`: any hard-stop side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
