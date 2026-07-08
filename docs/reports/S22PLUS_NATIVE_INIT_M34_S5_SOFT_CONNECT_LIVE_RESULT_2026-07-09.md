# S22+ M34 S5 Soft Connect Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: LIVE CONSUMED. S5 did not expose ACM. It returned to Odin before the
90 second survival window, and rollback returned Android/Magisk cleanly. No
active live authorization remains.

## Scope

M34 S5 tested one change on top of S4:

```text
/sys/class/udc/a600000.dwc3/soft_connect = connect
```

The candidate kept S4's `ssusb/speed=high-speed`,
`ssusb/mode=peripheral`, and final `UDC=a600000.dwc3` sequence. It did not
change descriptors, strings, companion functions, module closure, or boot
construction.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py`

Run directory:

`workspace/private/runs/s22plus_m34_s5_soft_connect_live_gate_20260708T210259Z/`

Pins:

- AP.tar.md5 SHA256:
  `3a63dc339577d4aaf550159743b81edd9c1318ef5c6c4b745ed363f171d30d5e`
- padded `boot.img` SHA256:
  `09751f5fce9f25be3ce7b814f00c04cafd22ae9a96d8c69ab9d52b6274951a95`
- direct `/init` SHA256:
  `efecaf1842aff95907b2f2780dc12531b0980acff6cbe64f789e9ad4b6c3c55c`
- template source SHA256:
  `bf90fbadbaf72bb9287150d769104b97ec8faaae0ce1c0591aaafdeb88004fb8`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The AP contained exactly one Odin tar member: `boot.img.lz4`.

## Result

Result string:

```text
unexpected_odin_before_survival_window
```

Key observations:

- candidate boot-only flash succeeded
- original Download endpoint disconnected
- candidate reached the park observation loop
- 15 host snapshots through 73.950 seconds all showed no S5 ACM endpoint
- during all candidate snapshots, Samsung Android `04e8:6860` was absent
- CDC ACM was absent from `lsusb -d 04e8:6860 -v` and `lsusb -t`
- `/dev/ttyACM*` was absent
- ADB was absent during candidate park
- Odin returned at 73.950 seconds, before the 90 second survival window

Post-run host-log review found an important endpoint distinction: the candidate
did not expose the stock Android `04e8:6860` composite gadget, but Samsung
`04e8:685d` appeared near the end of the observation window:

- observe 013, elapsed 62.987 s: `04e8:685d`, product `MSM_UPLOAD`, USB2/480M,
  CDC-class interfaces, no host `cdc_acm` driver
- observe 015, elapsed 73.950 s: `04e8:685d`, product `SAMSUNG USB`,
  USB3/5000M, CDC-class interfaces, no host `cdc_acm` driver; `odin4 -l`
  reported the same bus device and rollback proceeded from it

This means the S5 symptom is not simply "no electrical USB ever appeared". It
is "no intended `04e8:6860` Android/ACM gadget appeared; the device later fell
through to a Samsung upload/download endpoint."

Interpretation:

- S5 `soft_connect=connect` did not make the ACM endpoint enumerate.
- S5 is not a survival pass, because Odin returned before 90 seconds.
- The currently visible host `04e8:6860` / ADB / `/dev/ttyACM0` endpoint is the
  restored Android/Magisk baseline after rollback, not the S5 candidate.
- Future helpers must summarize all Samsung `04e8:*` endpoints, not only
  `04e8:6860`, so upload/download leakage is not hidden behind an ACM-negative
  summary.

## Rollback

Because Odin returned during observation, the helper immediately flashed the
pinned Magisk boot-only rollback AP from that Odin endpoint. No manual Download
step was needed.

Final baseline:

- Android returned
- `sys.boot_completed=1`
- model/device `SM-S906N` / `g0q`
- build/bootloader `S906NKSS7FYG8`
- vbstate `orange`
- Magisk root present
- boot partition SHA256 restored to
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The helper verified the restored boot hash with rc=0. A post-live independent
`dd if=/dev/block/by-name/boot | sha256sum` check also returned the same SHA256.

## Retained Evidence

- pstore files: empty
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- M34 S5 marker in retained evidence: absent

Marker absence is not treated as proof of non-execution because the candidate
entered the host observation loop and later returned to Odin.

## Timeline

Canonical timeline shape:

```json
{
  "events": [
    {"name": "live_session_start", "timestamp_utc": "2026-07-08T21:03:11.520994Z"},
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-08T21:03:23.099727Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-08T21:03:24.580153Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-08T21:03:25.839091Z"},
    {"name": "unexpected_endpoint_rollback_flash_start", "timestamp_utc": "2026-07-08T21:04:40.735806Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-08T21:04:40.736074Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-08T21:04:42.074253Z"},
    {"name": "unexpected_endpoint_rollback_flash_done", "timestamp_utc": "2026-07-08T21:04:42.074409Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-08T21:05:27.480532Z"},
    {"name": "unexpected_endpoint_rollback_boot_ready", "timestamp_utc": "2026-07-08T21:05:27.480740Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-08T21:05:27.698518Z"}
  ]
}
```

Timeline file:

`workspace/private/runs/s22plus_m34_s5_soft_connect_live_gate_20260708T210259Z/timeline.json`

## Authorization State

The S5 one-shot exception is consumed and retired in `AGENTS.md`; the live and
rollback tokens are intentionally omitted as active authorization. No active
S22+ native-init live flash is authorized by this result.

Next work should be host-only analysis of why S5 returns to Odin around 74
seconds and why no host USB device appears before that point. Candidate classes
to compare next are descriptor/config/function parity, stock composite
companion functions, and whether Android performs additional controller or UDC
setup not represented by configfs plus `soft_connect`.
