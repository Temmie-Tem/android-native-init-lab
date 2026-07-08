# S22+ M34 S4 Role Lever Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: LIVE CONSUMED. S4 survived the observation window, but no host ACM
endpoint appeared. Rollback returned Android/Magisk cleanly. No active live
authorization remains.

## Scope

M34 S4 tested the stock-kernel role lever found after S3:

```text
/sys/devices/platform/soc/a600000.ssusb/speed = high-speed
/sys/devices/platform/soc/a600000.ssusb/mode  = peripheral
```

The candidate kept the S3 configfs and final `UDC=a600000.dwc3` sequence, but
removed the dead `/sys/class/usb_role` runtime path.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s4_role_lever_live_gate.py`

Run directory:

`workspace/private/runs/s22plus_m34_s4_role_lever_live_gate_20260708T204102Z/`

Pins:

- AP.tar.md5 SHA256:
  `9d93eb5c3c4fec3c02c920b2c80435a76b7c161079d906940a3279fc77495cc9`
- padded `boot.img` SHA256:
  `153ceff9877351d55448de7839ec52f7631485c006a68971ca7ea14fc9dd11c5`
- direct `/init` SHA256:
  `ee73a26d65649346e8cae830ee9bb229152d0a8001c2bc8fc48e536fdc08fb96`
- template source SHA256:
  `51ec34f669f35f81a41411c82613ece65924c3a16b4bc5619e670e05b3231065`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The AP contained exactly one Odin tar member: `boot.img.lz4`.

## Result

Result string:

```text
survived-observation-window-manual-download-required
```

Key observations:

- candidate boot-only flash succeeded
- original Download endpoint disconnected
- S4 survived the full 90 second observation window
- no unexpected Odin endpoint appeared during the park window
- no ADB endpoint appeared during the park window
- no Samsung `04e8:6860` device appeared during 17 enhanced host USB snapshots
- no CDC ACM descriptor appeared in `lsusb -d 04e8:6860 -v` or `lsusb -t`
- no `/dev/ttyACM*` endpoint appeared
- no matching udev ACM properties appeared

Interpretation:

- S4's stock-kernel `ssusb/speed=high-speed` plus
  `ssusb/mode=peripheral` role lever is not the reset boundary.
- Replacing dead `/sys/class/usb_role` with the real `ssusb` role lever is still
  insufficient to enumerate the current ACM-only M34 gadget.

## Rollback

Manual Download rollback was required after the survival proof. The helper
flashed the pinned Magisk boot-only rollback AP successfully.

Final baseline:

- Android returned
- `sys.boot_completed=1`
- model/device `SM-S906N` / `g0q`
- build/bootloader `S906NKSS7FYG8`
- vbstate `orange`
- Magisk root present
- boot partition SHA256 restored to
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The helper verified the restored boot hash with rc=0, and a post-live
independent helper-path check also passed.

## Retained Evidence

- pstore files: empty
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- M34 S4 marker in retained evidence: absent

Marker absence is not treated as proof of non-execution because S4 survived the
host observation window and rollback path completed.

## Timeline

Canonical timeline shape:

```json
{
  "events": [
    {"name": "live_session_start", "timestamp_utc": "2026-07-08T20:41:14.487137Z"},
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-08T20:41:26.065154Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-08T20:41:27.569492Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-08T20:41:28.848294Z"},
    {"name": "manual_after_survival_rollback_flash_start", "timestamp_utc": "2026-07-08T20:46:09.055383Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-08T20:46:09.055668Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-08T20:46:10.439832Z"},
    {"name": "manual_after_survival_rollback_flash_done", "timestamp_utc": "2026-07-08T20:46:10.440003Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-08T20:46:55.861686Z"},
    {"name": "manual_after_survival_rollback_boot_ready", "timestamp_utc": "2026-07-08T20:46:55.861911Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-08T20:46:56.162616Z"}
  ]
}
```

## Authorization State

`AGENTS.md` now marks the S4 one-shot exception consumed/retired and omits the
live tokens as active authorization.

No active live authorization exists. This report does not authorize S4 repeat,
S1/S2/S3 repeat, S5 live, DTBO, vendor_boot, recovery, vbmeta, non-boot flash,
raw host `dd`, fastboot, EUD writes, RDX PC dump retrieval, Magisk modules,
format data, or any A90 action.

## Next

The reset bisection is now closed for M34 S1/S2/S3/S4 survival. ACM enumeration
is still unsolved.

Next unit should be host-only S5 design from stock Android gadget evidence:

- keep S4's real `ssusb` role lever
- compare descriptor/config/function parity against stock Android
- decide whether to add stock composite companion functions instead of ACM-only
- evaluate `/sys/class/udc/a600000.dwc3/soft_connect` as a bounded fallback
- avoid DTBO/QMP/SSPHY changes until the stock-runtime parity questions are
  exhausted

Any S5 live run needs a fresh SHA-pinned `AGENTS.md` exception and explicit
operator approval.
