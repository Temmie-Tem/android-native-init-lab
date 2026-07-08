# S22+ M34 S3 Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: LIVE CONSUMED. M34 S3 survived the full observation window and rolled
back cleanly. No active M34 S3 live authorization remains.

## Summary

The guarded S3 live gate ran once with:

`workspace/public/src/scripts/revalidation/s22plus_m34_s3_runtime_gadget_live_gate.py`

Candidate:

- AP.tar.md5 SHA256: `0ef55db2d38bec3df83cb77cd83f8ee6644054447ae7da10f8ecaecc8faa2957`
- padded `boot.img` SHA256: `87351f4955740aa4d83567406567c1ef4d6fcfa217d9ee5b0d7c446f2db09142`
- direct `/init` SHA256: `2f391e50ff271b2dfe14dce31dbfdd0f0fb2b6d353ae89a2079acad5b46e668f`
- run directory: `workspace/private/runs/s22plus_m34_s3_runtime_gadget_live_gate_20260708T200449Z`

Result:

- candidate Odin flash rc=0
- original Download endpoint disconnected
- observation window passed: `m34_s3_survival_window_pass=1`
- final result: `survived-observation-window-manual-download-required`
- host saw no ADB, no Odin, and no Samsung `04e8:6860` `/dev/ttyACM*` ACM tty
  endpoint during the 90 second window
- manual rollback was required
- operator observed RDX while entering manual rollback
- normal Download endpoint later appeared
- Magisk boot rollback Odin rc=0
- final Android/Magisk baseline clean

## Evidence

Preflight:

- `agents_exception_missing=[]`
- Android boot complete before flash
- Magisk root present before flash
- current boot hash matched the known Magisk baseline:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Candidate flash:

- candidate AP member set: `['boot.img.lz4']`
- candidate Odin rc: `0`
- original Download endpoint absent after flash:
  `post-candidate-disconnect_odin_absent=1`

Observation:

- host snapshots: 18
- last snapshot before pass: elapsed `86.558` seconds
- all snapshots showed empty ADB/Odin endpoint state
- all snapshots showed `m34_s3_park_observe_NNN_acm_devices=[]`
- S3 did not capture `lsusb`, `usb-devices`, or host dmesg deltas, so
  USB-device-level enumeration without an ACM tty remains unverified
- final result:
  `m34_s3_result=survived-observation-window-manual-download-required`

Rollback:

- manual Download endpoint appeared at `2026-07-08T20:07:50Z`
- Magisk boot rollback Odin rc: `0`
- Android returned with `sys.boot_completed=1`
- bootanim stopped
- vbstate `orange`
- bootloader/build `S906NKSS7FYG8`
- Magisk root present
- boot partition hash:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Retained evidence:

- pstore files: `[]`
- `/proc/last_kmsg` readable: `2,097,136` bytes
- M34 S3 marker absent from pstore/last_kmsg

Timeline file:

`workspace/private/runs/s22plus_m34_s3_runtime_gadget_live_gate_20260708T200449Z/timeline.json`

The timeline uses the required single `events:[{name,timestamp_utc}]` shape and
contains candidate flash, boot-ready, rollback flash, rollback boot-ready, and
live session end events.

## Interpretation

M34 S3 closes the reset-boundary bisection for the current runtime-gadget split:

- S1 survived configfs gadget/function/config + `UDC=none`.
- S2 survived S1 plus `g1/max_speed=high-speed` and `usb_role=device`.
- S3 survived S2 plus final `UDC=a600000.dwc3` bind/pullup.

So the runtime-gadget sequence, including final UDC pullup, is not by itself
causing the previously observed reset/bootloop boundary in this bounded
configuration.

The remaining issue is different: S3 did not expose a host ACM tty endpoint.
That means survival is solved, but transport usability is not proven. Because
the S3 helper did not collect USB-device-level host evidence, the next unit
must distinguish complete no-enumeration from non-ACM or descriptor-level
enumeration.

## Next

Do not repeat S3 under the consumed authorization. The next unit should be
host/read-only first and compare S3 against stock Android gadget state. That
read-only follow-up found the real missing role lever:
`/sys/devices/platform/soc/a600000.ssusb/mode=peripheral`, while S3's
`/sys/class/usb_role/*/role=device` path was empty/no-op on this device. So the
next host-build candidate should be S4: write `ssusb/speed=high-speed` and
`ssusb/mode=peripheral` before UDC bind, with enhanced host USB observation.

- verify actual gadget descriptors and function naming expected by Samsung
  stock for `04e8:6860`
- check whether S3 needs config `MaxPower`, strings, `bcdDevice`, config name,
  or function symlink order/details beyond the current stock subset
- check whether `ss_acm.0` requires companion Samsung configfs attributes or a
  userspace daemon action before host enumeration
- inspect host `lsusb`, `usb-devices`, udev, and kernel dmesg/usbmon if a
  future live run is authorized

No live flash is authorized by this result report.
