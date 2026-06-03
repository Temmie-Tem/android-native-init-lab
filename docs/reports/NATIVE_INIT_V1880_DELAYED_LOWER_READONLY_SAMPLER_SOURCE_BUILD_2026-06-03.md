# Native Init V1880 Delayed Lower Read-only Sampler Source Build

## Summary

- Cycle: `V1880`
- Type: source/build-only rollbackable v358 delayed lower-response sampler on the private SDX50M post-PM route
- Decision: `v1880-delayed-lower-readonly-sampler-source-build-pass`
- Result: PASS
- Reason: V1879 selected a delayed read-only window because Android-good lower publication appears around 205-216 seconds after `wlfw_start`, while V1876 only sampled 0-1000 ms after private SDX50M PM powerup.
- Manifest: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/boot_linux_v1880_delayed_lower_readonly_sampler.img`
- Boot SHA256: `70f862e6c48a5aa69f919154ef4b6cb27c26863948271f5cceaf3e90f9f61a20`
- Init: `A90 Linux init 0.9.171 (v1880-delayed-lower-readonly-sampler)`
- Helper marker: `a90_android_execns_probe v358`
- Helper SHA256: `1d6cb4bb16e1b35b86eb0a76381f1651a72d87d760756f33562efe2aeef5d7cc`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1880/dev/__properties__`
- Private CNSS mount: `True` path `/cache/bin/cnss-daemon.sdx50m`
- New helper marker: `a90_android_execns_probe v358`.
- New output namespace: `wlan_pd_lower_response_input_contract.post_powerup_delayed.*`.
- Dense offsets retained: `0,1,2,5,10,20,50,100,150,250,500,1000 ms`.
- Delayed offsets added: `0,1,2,5,10,20,30,60,90,120,150,180,210,240,250,260,300 s`.
- PID1 watch/supervisor seconds: `330` / `360`.
- Each delayed sample reuses existing read-only lower-state and PM/eSoC/GPIO/GDSC/PCIe/MHI/ks surfaces; it does not write rc_sel/case, rescan PCI, bind/unbind, or directly open `/dev/subsys_esoc0`.
- PM-service open-context labels retained: `pm_service_post_ack_power_state_loaded`, `pm_service_post_ack_open_context`, `pm_service_post_ack_open_path_loaded`, `pm_service_post_ack_open_fd_store`, `pm_service_post_ack_open_fd_compare`, `pm_service_post_ack_open_success_counter`.

## Expected Live Discriminator

- `delayed-lower-wifi-prereq-present-readonly-stop`: WLFW service 69 and `wlan0` both exist; run a separate connect prerequisite check before credentials.
- `delayed-lower-mhi-or-wlfw-progress-readonly-stop`: MHI, WLFW service 69, BDF, firmware-ready, or `wlan0` appears; stop before connect.
- `delayed-lower-pcie-l0-no-wlfw-readonly-stop`: PCIe/MHI moves but WLFW/`wlan0` remain absent.
- `delayed-lower-still-power-clock-gap`: no lower progress appears across the Android-good 300 second delayed window.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
