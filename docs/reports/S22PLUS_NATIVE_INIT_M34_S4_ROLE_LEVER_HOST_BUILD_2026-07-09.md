# S22+ M34 S4 Role Lever Host Build

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: HOST BUILD PASS. No live flash is authorized by this report.

## Scope

S4 is the next candidate after M34 S3 survived final UDC bind but exposed no
host ACM tty. The stock-kernel read-only answer is that S3's
`/sys/class/usb_role/*/role=device` path is empty/no-op on this device, while
the actual stock role lever is:

```text
/sys/devices/platform/soc/a600000.ssusb/mode  = peripheral
/sys/devices/platform/soc/a600000.ssusb/speed = high-speed
```

S4 keeps the S3 configfs/UDC sequence and changes only the role lever:

- keep `g1/max_speed=high-speed`
- remove the dead `/sys/class/usb_role/*/role=device` runtime path
- add `/sys/devices/platform/soc/a600000.ssusb/speed=high-speed`
- add `/sys/devices/platform/soc/a600000.ssusb/mode=peripheral`
- keep final `UDC=a600000.dwc3`
- do not change descriptors, strings, companion functions, module closure, or
  boot construction in the same candidate

## Artifacts

Output directory:

`workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_3/`

S4 pins:

- AP.tar.md5 SHA256:
  `9d93eb5c3c4fec3c02c920b2c80435a76b7c161079d906940a3279fc77495cc9`
- padded `boot.img` SHA256:
  `153ceff9877351d55448de7839ec52f7631485c006a68971ca7ea14fc9dd11c5`
- direct `/init` SHA256:
  `ee73a26d65649346e8cae830ee9bb229152d0a8001c2bc8fc48e536fdc08fb96`
- `boot.img.lz4` SHA256:
  `3ae1f4ce380edc3d3d504ee662ba84e1080f7aa4b09498442374b799547d3ba1`
- raw AP.tar SHA256:
  `e5898ef605dfaa22dae30d5cf44b2474376a083660fc5ceb58c3cd1508e489fb`
- template source SHA256:
  `51ec34f669f35f81a41411c82613ece65924c3a16b4bc5619e670e05b3231065`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The S4 AP contains exactly one Odin tar member: `boot.img.lz4`.

## Matrix

The v0.3 build matrix is now:

```text
S1: configfs gadget/function/config + UDC=none
S2: S1 + g1/max_speed=high-speed + legacy usb_role=device, no UDC bind
S3: S2 + UDC=a600000.dwc3
S4: S3-style UDC bind, but replace legacy usb_role with ssusb speed/mode
```

S4 runtime steps in the generated manifest:

```json
{
  "configfs_gadget": true,
  "udc_none": true,
  "max_speed_high_speed": true,
  "usb_role_force": false,
  "ssusb_speed_high_speed": true,
  "ssusb_mode_peripheral": true,
  "udc_bind": true
}
```

## Static Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --force
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py
```

Results:

- builder `py_compile`: pass
- unit test before manifest: pass, 5 tests, 1 skipped
- v0.3 build: pass
- unit test after manifest: pass, 5 tests
- no-change MagiskBoot repack remained byte-identical to the base boot
- AP member set remained `['boot.img.lz4']`
- module closure remained the P30/M32 45-module closure
- QMP/EUD modules remained excluded
- S4 `/init` contains the `ssusb` speed/mode paths and `a600000.dwc3`
- S4 `/init` does not contain `/sys/class/usb_role`
- no reboot syscall, Android/Magisk handoff, persistent mount, block write, or
  module binary injection was introduced

## Next

The next unit should prepare the S4 live gate helper, still policy-inert by
default. The helper must add USB-device-level host observation beyond the S3
helper:

- `lsusb -d 04e8:6860 -v`
- `lsusb -t`
- `usb-devices`
- `/dev/ttyACM*` and `/dev/serial/by-*`
- udev properties for detected Samsung ACM candidates
- host dmesg or journal delta

Only after that helper passes offline/default fail-closed checks should a fresh
SHA-pinned `AGENTS.md` exception and explicit operator approval be considered.

## Authorization State

No active live authorization exists. This report does not authorize S4 live
flash, S3 repeat, DTBO, vendor_boot, recovery, vbmeta, non-boot flash, raw host
`dd`, fastboot, EUD writes, RDX PC dump retrieval, Magisk modules, format data,
or any A90 action.
