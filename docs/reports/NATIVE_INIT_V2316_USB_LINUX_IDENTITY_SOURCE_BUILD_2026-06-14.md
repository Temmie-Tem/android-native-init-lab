# Native Init V2316 USB Linux Identity Source Build

## Summary

- Cycle: `V2316`
- Track: active USB gadget runtime-control epic layer 1, identity hygiene + rollback-checkpoint promotion candidate.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2316-usb-linux-identity-source-build-pass`
- Result: PASS
- Reason: present an honest ARM-Linux USB identity and redacted serial; promote as resident rollback checkpoint after live validation.
- Manifest: `workspace/private/builds/native-init/v2316-usb-linux-identity/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2316_usb_linux_identity.img`
- Boot SHA256: `cf54ff0ae3cca4af31263140e588920296abecdb0ffb690a807b3d8b393f452a`
- Init: `A90 Linux init 0.9.280 (v2316-usb-linux-identity)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Identity Change

- `manufacturer`: `samsung` -> `A90 NativeInit`.
- `product`: `SM8150-ACM` -> `A90 Linux (ARM)`.
- `serialnumber`: real device serial -> placeholder `A90NATIVE001`.
- `idVendor`/`idProduct` kept at `0x04e8`/`0x6861` so NCM host-side transport detection and the udev rules continue to bind; only the human-readable strings change.
- Applied in all three identity-write sites: boot ACM setup, the NCM/usbnet boot gadget, and the reconfigure control-base rebuild path (so personas do not revert the identity).

## Command Scope

- No command surface change. Inherits the full V2313-V2315 USB control surface (`usb status`, `usb mass-storage add/remove/expose`).
- Reconfigure still uses the V2314 detached worker, NCM+ACM preservation, watchdog, and known-good restore path.

## Helper Flags

- `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1`
- `-DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1`
- `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`

## Safety Scope

This source build performed host-side build work only. It changes only USB gadget identity strings; no command behavior, partition write, kernel module/code, adb-over-ffs, HID, or BadUSB change. Wi-Fi both-band validation is performed live at the device step as the rollback-checkpoint promotion bar.

## Required Device Step (rollback-checkpoint promotion bar)

- Boot-only flash through `native_init_flash.py`, pinned SHA, auto-rollback to `v2237` on any failure.
- `version` / `status` / `selftest fail=0`.
- `usb status`: host-visible `product` reads `A90 Linux (ARM)`, `manufacturer` reads `A90 NativeInit`, serial is the placeholder, `idVendor=0x04e8`, `control.ok=1`.
- USB persona regression: `usb mass-storage expose` then `remove`; confirm the control channel returns and the identity strings persist across the reconfigure.
- Wi-Fi both-band end-to-end: associate -> DHCP -> external ping on 2.4 GHz and 5 GHz (credentials from `workspace/private/secrets/`; redact SSID/BSSID/IP/MAC; never log PSK).
