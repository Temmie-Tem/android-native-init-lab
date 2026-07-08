# S22+ M34 S1 Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Result: PASS for the S1 discriminator. The stock-ordered configfs gadget
creation path with `UDC=none` and the `ss_acm.0` link survived the full
observation window. Rollback completed cleanly. No active live authorization
remains.

## Scope

This was the one-shot M34 S1 boot-only live gate for:

- target: `SM-S906N/g0q/S906NKSS7FYG8`
- helper: `workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py`
- run dir: `workspace/private/runs/s22plus_m34_s1_runtime_gadget_live_gate_20260708T192613Z`
- timeline: `workspace/private/runs/s22plus_m34_s1_runtime_gadget_live_gate_20260708T192613Z/timeline.json`

Candidate pins:

- AP.tar.md5 SHA256: `77e8858ea6becc3e988232d464f97827f55594f16ed6edebd23c3529c972d237`
- padded `boot.img` SHA256: `bb46233068890bb6849c63b4dab845ca48b65a9ffeac9e24ad08e81416b63f85`
- direct `/init` SHA256: `5339170f3138843a8f8da6cfd5f20f85696d3a9d18ae22bda439e21d0dd259cd`
- template source SHA256: `ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`
- module-list SHA256: `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- known-booting Magisk boot base SHA256: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The AP contained exactly one tar member, `boot.img.lz4`.

## Candidate Contract

M34 S1 was deliberately limited to the stock configfs setup subset:

- create the stock-ordered gadget/function/config path
- write `UDC=none`
- use stock IDs `0x04E8:0x6860`
- link `functions/ss_acm.0`
- no `max_speed=high-speed`
- no `usb_role=device`
- no final UDC bind
- no `UDC=a600000.dwc3`

It also had no reboot syscall, no Download beacon, no Android/Magisk handoff,
no persistent partition mount, no block write, no boot-ramdisk module binary
injection, and no non-boot partition payload.

## Timeline

The run produced the required single `events` timeline schema.

- `live_session_start`: 2026-07-08T19:26:24.471648Z
- `candidate_flash_start`: 2026-07-08T19:26:35.254586Z
- `candidate_flash_done`: 2026-07-08T19:26:36.731409Z
- `candidate_boot_ready`: 2026-07-08T19:26:38.001882Z
- `rollback_flash_start`: 2026-07-08T19:28:59.464308Z
- `rollback_flash_done`: 2026-07-08T19:29:00.824095Z
- `rollback_boot_ready`: 2026-07-08T19:29:34.292886Z
- `live_session_end`: 2026-07-08T19:29:34.639675Z

The helper also recorded `manual_after_survival_*` aliases for the manual
Download rollback path.

## Live Evidence

Preflight:

- Android ADB online as `RFCT519XWGK`
- `model=SM-S906N`
- `device=g0q`
- `bootloader=S906NKSS7FYG8`
- `incremental=S906NKSS7FYG8`
- `vbstate=orange`
- `boot_completed=1`
- Magisk root present: `uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0`
- current boot hash matched the known-booting Magisk boot:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Candidate flash:

- Download endpoint selected: `/dev/bus/usb/002/074`
- candidate Odin return code: `0`
- original Download endpoint disconnected after flash
- host observation started at `2026-07-08T19:26:38Z`

Observation:

- observation window: 90 seconds
- 18 snapshots taken about every 5 seconds
- no ADB endpoint returned during the window
- no Odin endpoint returned during the window
- `m34_s1_survival_window_pass=1`
- `m34_s1_result=survived-observation-window-manual-download-required`

Rollback:

- the operator observed RDX while entering manual recovery
- normal Download endpoint then appeared as `/dev/bus/usb/002/075`
- Magisk boot rollback Odin return code: `0`
- Android returned and reached boot complete
- restored boot hash matched:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Post-run ADB recheck confirmed:

- boot hash:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- root: `uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0`
- `sys.boot_completed=1`
- `init.svc.bootanim=stopped`
- `ro.boot.verifiedbootstate=orange`
- `ro.boot.bootloader=S906NKSS7FYG8`
- `ro.build.PDA=S906NKSS7FYG8`

## Retained Evidence

Post-rollback retained evidence:

- pstore files: `[]`
- pstore marker found: `0`
- `/proc/last_kmsg` read return code: `0`
- `/proc/last_kmsg` bytes: `2097136`
- `/proc/last_kmsg` M34 S1 marker found: `0`
- overall retained marker found: `0`

Marker absence is not a failure for S1 because the positive proof is survival
past the reset window plus clean rollback.

## Interpretation

S1 removes these from the likely reset boundary:

- the 45-module closure including `dwc3-msm.ko` and `usb_f_ss_acm.ko`
- stock-ordered configfs gadget/function/config creation
- `UDC=none`
- stock IDs `0x04E8:0x6860`
- `functions/ss_acm.0` link

The remaining isolated pullup path is now:

1. S2: add only `g1/max_speed=high-speed` and `usb_role=device`, still no UDC
   bind.
2. S3: add only the final `UDC=a600000.dwc3` bind/pullup, only after S2 result.

S2 is the next high-information unit. S3 remains blocked until S2 is proven.

## Authorization State

The M34 S1 one-shot exception is consumed and retired in `AGENTS.md`. Its live
and rollback ack tokens are omitted as active authorization. No S1 repeat, S2,
S3, final pullup, DTBO, vendor_boot, recovery, vbmeta, non-boot flash, raw host
`dd`, fastboot, EUD write, RDX PC dump retrieval, or A90 action is authorized by
this result.

