# Native Init V2313 USB Status Inventory Live Validation

## Summary

- Cycle: `V2313`
- Artifact: `A90 Linux init 0.9.277 (v2313-usb-status-inventory)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2313_usb_status_inventory.img`
- Boot SHA256: `28f944b2663f191c41457215c9c8732cc40f5d1ec93dcc5bf1a960000b3e9cdb`
- Decision: `v2313-usb-status-inventory-live-pass`
- Result: PASS
- Scope: U1 of the USB gadget runtime-control epic: read-only topology inventory.
- Rollback checkpoint remains: `v2237-supplicant-terminate-poll`.

## Validation

- Static validation:
  - `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2313_usb_status_inventory.py tests/test_build_native_init_boot_v2313_usb_status_inventory.py`
  - `PYTHONPATH=tests python3 -m unittest tests.test_build_native_init_boot_v2313_usb_status_inventory`
  - `python3 -m unittest discover -s tests -p 'test_*.py'` → 987 tests PASS.
  - `git diff --check` PASS.
- Flash path:
  - Used only `workspace/public/src/scripts/revalidation/native_init_flash.py`.
  - Reconfirmed `v2237` rollback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
  - Reconfirmed fallback `boot_linux_v48.img` exists.
  - Boot partition write/readback SHA256 matched the V2313 image.
- Device health:
  - `version` matched `A90 Linux init 0.9.277 (v2313-usb-status-inventory)`.
  - `status` returned `selftest: pass=11 warn=1 fail=0`.
  - `selftest verbose` returned `fail=0`.

## USB Status Findings

`usb status` was run over the serial bridge after V2313 boot. It performed no mutation.

| Field | Value |
| --- | --- |
| `version` | `a90-native-usb-status-v1` |
| `read_only` | `1` |
| `mutation_attempted` | `0` |
| `configfs.root` | `/config/usb_gadget/g1` |
| `gadget.udc` | `a600000.dwc3` |
| `gadget.bound` | `1` |
| `idVendor` / `idProduct` | `0x04e8` / `0x6861` |
| `bcdUSB` / `bcdDevice` | `0x0320` / `0x0100` |
| `strings.manufacturer` | `samsung` |
| `strings.product` | `SM8150-ACM` |
| `strings.serialnumber` | present, redacted, length-only |
| `udc.count` | `1` |
| `udc.0.state` | `configured` |
| `udc.0.current_speed` | `super-speed` |
| `config.count` | `1` |
| `config.0.name` | `b.1` |
| `config.0.configuration` | `serial` |
| `config.0.max_power` | `900` |
| `function.count` | `2` |
| `control.acm.present` | `1` |
| `control.ncm.present` | `1` |
| `control.ok` | `1` |
| `decision` | `usb-status-control-topology-read` |

Linked functions:

- `configs/b.1/f2` → `ncm.usb0`, classified as `control-ncm`.
- `configs/b.1/f1` → `acm.usb0`, classified as `control-acm`.

## Safety Result

- No UDC unbind/rebind.
- No configfs/sysfs writes.
- No USB function add/remove.
- No adb-over-ffs, HID, BadUSB, mass-storage, Wi-Fi scan/connect/DHCP/ping, or forbidden partition work.
- Host-side USB enumeration is intentionally parked for U2/U3; U1 is serial-self-validatable.

## Next Unit

Proceed only to U2 in a later iteration: atomic auxiliary function add/remove, starting with `mass_storage.0`, with all configs preserving `ncm.usb0` + `acm.usb0`, an auto-rebind watchdog, known-good restore, and host-side control-return validation.
