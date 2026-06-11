# Native Init V2228 Service-Object-Visible Observer Source Build

## Summary

- Cycle: `V2228`
- Type: source/build-only rollbackable service-object-visible observer test boot.
- Decision: `v2228-service-object-visible-observer-source-build-pass`
- Result: PASS
- Reason: V2228 keeps the V2189 security P0 baseline and V2226 property-root fix, but enables service-manager/PM service-object-visible startup after V2227 proved CNSS stalled at libperipheral_client defaultServiceManager().
- Manifest: `workspace/private/builds/native-init/v2228-service-object-visible-observer/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2228_service_object_visible_observer.img`
- Boot SHA256: `195d23e02cfd54bfb2c82aba3bba47ec108bbeac7d3f8d4b16ef18d84b32294a`
- Init: `A90 Linux init 0.9.264 (v2228-service-object-visible-observer)`
- Helper marker: `a90_android_execns_probe v427`
- Helper SHA256: `a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44`

## Observer Route

- Helper mode: `wlan-pd-service-object-visible-trigger`
- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Supervisor timeout: `95`
- Watch window: `70` seconds
- Helper result: `/cache/native-init-wifi-test-boot-v2228-helper.result`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Expected discriminator: `periph_default_service_manager_call -> service-manager get-service/pm_client_register return -> wlfw_service_request`; downstream pass continues toward `wlfw_cap_qmi -> wlfw_bdf_entry`.

## Safety Scope

- This build script is host-only and does not flash, reboot, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write device partitions.
- The eventual live run still requires explicit approval and should immediately postprocess the helper result with `a90_kernel_v2220_helper_summary_trace_parser.py` plus the nonlog control-flow classifier.
- Keep the V2222/V2223 blocks: no dynamic `a90*` BPF attach, no PMIC/GPIO/GDSC/eSoC/PCI path, no platform bind/unbind, and no `sda29` writes.
