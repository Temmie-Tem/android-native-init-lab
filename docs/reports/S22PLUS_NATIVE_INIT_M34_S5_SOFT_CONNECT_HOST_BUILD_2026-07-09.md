# S22+ M34 S5 Soft Connect Host Build

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: HOST BUILD PASS. No live flash is authorized by this report.

## Scope

M34 S4 survived the full observation window but produced no host-visible USB
device: Samsung `04e8:6860`, CDC ACM, `/dev/ttyACM*`, ADB, and Odin were all
absent during the candidate park. Since the host never saw a device, descriptor
or composite-function parity is secondary. The next single-variable test is to
keep S4's real stock role lever and explicitly request the UDC soft-connect
fallback after the UDC bind.

S5 changes only this:

- keep the S4 stock configfs ACM-only gadget
- keep `g1/max_speed=high-speed`
- keep `/sys/devices/platform/soc/a600000.ssusb/speed=high-speed`
- keep `/sys/devices/platform/soc/a600000.ssusb/mode=peripheral`
- keep final `UDC=a600000.dwc3`
- add `/sys/class/udc/a600000.dwc3/soft_connect=connect` after UDC bind
- do not change descriptors, strings, companion functions, module closure, or
  boot construction in the same candidate

## Artifacts

Output directory:

`workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_4/`

S5 pins:

- AP.tar.md5 SHA256:
  `3a63dc339577d4aaf550159743b81edd9c1318ef5c6c4b745ed363f171d30d5e`
- padded `boot.img` SHA256:
  `09751f5fce9f25be3ce7b814f00c04cafd22ae9a96d8c69ab9d52b6274951a95`
- direct `/init` SHA256:
  `efecaf1842aff95907b2f2780dc12531b0980acff6cbe64f789e9ad4b6c3c55c`
- `boot.img.lz4` SHA256:
  `80a3f9945ad0f59a84c26ad856a1f72e17ba352824990f941e65ae7033b1d38b`
- raw AP.tar SHA256:
  `0cfb3d5fc88dbb731292f92744ed232cc229d8c69da21b6d29d14809de5b96b7`
- template source SHA256:
  `bf90fbadbaf72bb9287150d769104b97ec8faaae0ce1c0591aaafdeb88004fb8`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The S5 AP contains exactly one Odin tar member: `boot.img.lz4`.

## Matrix

The v0.4 build matrix is now:

```text
S1: configfs gadget/function/config + UDC=none
S2: S1 + g1/max_speed=high-speed + legacy usb_role=device, no UDC bind
S3: S2 + UDC=a600000.dwc3
S4: S3-style UDC bind, but replace legacy usb_role with ssusb speed/mode
S5: S4 + /sys/class/udc/a600000.dwc3/soft_connect=connect after UDC bind
```

S5 runtime steps in the generated manifest:

```json
{
  "configfs_gadget": true,
  "max_speed_high_speed": true,
  "soft_connect": true,
  "ssusb_mode_peripheral": true,
  "ssusb_speed_high_speed": true,
  "udc_bind": true,
  "udc_none": true,
  "usb_role_force": false
}
```

## Static Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --force
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_s4_role_lever_live_gate.py
```

Results:

- builder `py_compile`: pass
- unit test before manifest: pass, 5 tests, 1 skipped
- v0.4 build: pass
- unit test after manifest: pass, 5 tests
- existing S4 live-gate tests still pass, 8 tests
- no-change MagiskBoot repack remained byte-identical to the base boot
- AP member set remained `['boot.img.lz4']`
- module closure remained the P30/M32 45-module closure
- QMP/EUD modules remained excluded
- S5 `/init` contains the `ssusb` speed/mode paths, `a600000.dwc3`, and
  `/sys/class/udc/a600000.dwc3/soft_connect`
- S5 manifest requires `soft_connect=1`, `phase=soft_connect`, and
  `value=connect`
- S4 remains `soft_connect=0`
- no reboot syscall, Android/Magisk handoff, persistent mount, block write, or
  module binary injection was introduced

## Next

The next unit should prepare an S5 live-gate helper, policy-inert by default,
using the S5 pins above. The live gate should retain S4's enhanced host USB
observation:

- `lsusb -d 04e8:6860 -v`
- `lsusb -t`
- `usb-devices`
- `/dev/ttyACM*` and `/dev/serial/by-*`
- udev properties for detected Samsung ACM candidates
- host dmesg or journal delta

Only after that helper passes offline/default fail-closed checks should a fresh
SHA-pinned `AGENTS.md` exception and explicit operator approval be used for
live. The operator has given in-thread pre-approval, but this report alone does
not activate a live flash gate.

## Authorization State

No active live authorization exists. This report does not authorize S5 live
flash, S4 repeat, DTBO, vendor_boot, recovery, vbmeta, non-boot flash, raw host
`dd`, fastboot, EUD writes, RDX PC dump retrieval, Magisk modules, format data,
or any A90 action.
