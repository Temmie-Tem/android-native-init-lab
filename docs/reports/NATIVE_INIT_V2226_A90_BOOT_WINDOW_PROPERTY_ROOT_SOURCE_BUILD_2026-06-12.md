# Native Init V2226 A90 Boot-Window Property-Root Source Build

## Summary

- Cycle: `V2226`
- Type: source/build-only rollbackable property-root-fixed observer test boot.
- Decision: `v2226-a90-boot-window-property-root-source-build-pass`
- Result: PASS
- Reason: V2226 keeps the V2189 security P0 baseline and the supervised a90 CNSS/WLFW trace_uprobe route, but points the helper at the existing v726 property root so setup can pass.
- Manifest: `workspace/private/builds/native-init/v2226-a90-boot-window-property-root/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2226_a90_boot_window_property_root.img`
- Boot SHA256: `1f1dd7a12cfddf393e537bd96bc6efe4ecc4b6f809b58e071f60a21bec5c096d`
- Init: `A90 Linux init 0.9.263 (v2226-a90-boot-window-property-root)`
- Helper marker: `a90_android_execns_probe v427`
- Helper SHA256: `a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44`

## Observer Route

- Helper mode: `wlan-pd-cnss-output-visibility`
- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Helper timeout: `75`
- Supervisor timeout: `95`
- Watch window: `70` seconds
- Helper result: `/cache/native-init-wifi-test-boot-v2226-helper.result`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Expected parsed sequence: `wlfw_start -> wlfw_service_request -> wlfw_cap_qmi -> wlfw_bdf_entry`.

## Safety Scope

- This build script is host-only and does not flash, reboot, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write device partitions.
- The eventual live run still requires explicit approval and should immediately postprocess the helper result with `a90_kernel_v2220_helper_summary_trace_parser.py`.
- Keep the V2222/V2223 blocks: no dynamic `a90*` BPF attach, no PMIC/GPIO/GDSC/eSoC/PCI path, no platform bind/unbind, and no `sda29` writes.
