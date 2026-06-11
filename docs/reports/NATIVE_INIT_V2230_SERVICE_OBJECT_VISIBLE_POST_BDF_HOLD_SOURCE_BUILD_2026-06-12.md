# Native Init V2230 Service-Object-Visible Post-BDF Hold Source Build

## Summary

- Cycle: `V2230`
- Type: source/build-only rollbackable service-object-visible post-BDF hold test boot.
- Decision: `v2230-service-object-visible-post-bdf-hold-source-build-pass`
- Result: PASS
- Reason: V2230 keeps the V2228 service-object-visible route that passed the service-manager gate and extends helper watch/supervisor windows after V2229 reached BDF but no wlan0.
- Manifest: `workspace/private/builds/native-init/v2230-service-object-visible-post-bdf-hold/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2230_service_object_visible_post_bdf_hold.img`
- Boot SHA256: `9a596a4f297d15aeec22dabec1ae70f5deaaba1078ea7bb7a2ad04ad2d07f011`
- Init: `A90 Linux init 0.9.265 (v2230-service-object-visible-post-bdf-hold)`
- Helper marker: `a90_android_execns_probe v427`
- Helper SHA256: `a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44`

## Observer Route

- Helper mode: `wlan-pd-service-object-visible-trigger`
- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Supervisor timeout: `185`
- Watch window: `155` seconds
- Helper result: `/cache/native-init-wifi-test-boot-v2230-helper.result`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Expected discriminator: V2229 edges still hit through `wlfw_bdf_result_log`, then the extended post-BDF window either reaches FW_READY/wlan0 or proves a post-BDF blocker.

## Safety Scope

- This build script is host-only and does not flash, reboot, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write device partitions.
- The eventual live run still requires explicit approval and should immediately postprocess the helper result with `a90_kernel_v2220_helper_summary_trace_parser.py` plus the nonlog control-flow classifier.
- Keep the V2222/V2223 blocks: no dynamic `a90*` BPF attach, no PMIC/GPIO/GDSC/eSoC/PCI path, no platform bind/unbind, and no `sda29` writes.
