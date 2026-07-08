# S22+ M34 S7A Session Producer Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: LIVE CONSUMED. S7A survived the full observation window without a boot
loop, but it did not expose any Samsung USB endpoint or ACM. Rollback returned
Android/Magisk cleanly. No active live authorization remains.

## Scope

M34 S7A tested the corrected "session before descriptors" hypothesis on top of
S6:

- kept S6's minimal ACM-only configfs recipe
- kept `ssusb/mode=peripheral`
- kept `soft_connect` disabled
- restored the stock max77705/PDIC/altmode session-producer module chain:
  `qcom-i2c-pmic.ko`, `mfd_max77705.ko`, `max77705_charger.ko`,
  `max77705-fuelgauge.ko`, `pdic_max77705.ko`, `charger-ulog-glink.ko`, and
  `altmode-glink.ko`
- added read-only TypeC/UDC state markers before and after UDC bind

S7A did not write EUD sysfs knobs, charge-current controls, OTG/VBUS boost,
regulators, GDSC, GPIO, display, raw PMIC knobs, FunctionFS, `conn_gadget`, or
any persistent partition.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s7a_session_producer_live_gate.py`

Run directory:

`workspace/private/runs/s22plus_m34_s7a_session_producer_live_gate_20260708T224815Z/`

Pins:

- AP.tar.md5 SHA256:
  `b533d8e218aa4842c941f86075ce770cf60a67a179939dd4d552d22767376267`
- padded `boot.img` SHA256:
  `5e1a0758008651eb5a22b82fd91d4c2549ba756a4ed885779a0934688e129e49`
- direct `/init` SHA256:
  `22e1f7e9346c61c876253a6e194d64d55adc3e24571ed2b10d76e4c09cef1914`
- template source SHA256:
  `388d9f187bb1dfa1877c99cc2f8481bb2f191aec2ac66131785e9d70e17e71ad`
- module-list SHA256:
  `eb1ddfe7ac9a481b9dacae696c72b876e82d6e8ac4681772df825995a162001c`
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
- candidate reached the park observation loop
- S7A survived the full 90 second observation window
- the operator observed no boot loop
- 18 candidate snapshots showed no Samsung `04e8:*` endpoint at all
- stock Android `04e8:6860` was absent
- CDC ACM was absent from `lsusb -d 04e8:6860 -v` and `lsusb -t`
- `/dev/ttyACM*` was absent
- ADB was absent during candidate park
- Odin/upload/download endpoints were absent during the candidate park window

Operator-side observation after the survival window: RDX/PMIC appeared, then
manual Download mode was entered for rollback.

Interpretation:

- S7A kept the S6 survival improvement: adding the full session-producer module
  chain did not reintroduce the earlier pre-90-second boot loop.
- S7A is not a USB success: it exposed no host-visible Samsung USB device
  during the observation window.
- The narrower missing max77705/PDIC/altmode producer module hypothesis is now
  retired as a sufficient explanation for the absent pullup/enumeration.
- The remaining blocker is likely stock Android USB orchestration beyond direct
  PID1 module loading plus minimal configfs: init rc/property choreography,
  FunctionFS readiness, `conn_gadget`/stock composite services, descriptor
  parity, TypeC/PD userspace state, or controller/service ordering.

## Rollback

Because S7A survived the observation window with no host-visible endpoint, the
helper requested manual Download rollback. The operator entered RDX/PMIC, then
Download mode. The helper flashed the pinned Magisk boot-only rollback AP from
the returned Odin endpoint.

Final baseline:

- Android returned
- `sys.boot_completed=1`
- model/device `SM-S906N` / `g0q`
- build/bootloader `S906NKSS7FYG8`
- vbstate `orange`
- `boot_recovery=0`
- Magisk root present
- boot partition SHA256 restored to
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The helper verified the restored boot hash with rc=0.

## Retained Evidence

- pstore files: empty
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- M34 S7A marker in retained evidence: absent

Marker absence is not treated as proof of non-execution because the helper
observed candidate boot/disconnect, a full park window, and later clean manual
rollback.

## Timeline

Canonical timeline shape:

```json
{
  "events": [
    {"name": "live_session_start", "timestamp_utc": "2026-07-08T22:48:27.235676Z"},
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-08T22:48:38.796421Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-08T22:48:40.260341Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-08T22:48:41.532655Z"},
    {"name": "manual_after_survival_rollback_flash_start", "timestamp_utc": "2026-07-08T22:51:38.721708Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-08T22:51:38.721910Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-08T22:51:40.081439Z"},
    {"name": "manual_after_survival_rollback_flash_done", "timestamp_utc": "2026-07-08T22:51:40.081689Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-08T22:52:13.245668Z"},
    {"name": "manual_after_survival_rollback_boot_ready", "timestamp_utc": "2026-07-08T22:52:13.245826Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-08T22:52:13.522877Z"}
  ]
}
```

Timing summary:

- candidate flash: 1.464 s
- candidate flash done to boot-ready observation start: 1.272 s
- candidate boot-ready to manual rollback flash start: 177.189 s
- rollback flash: 1.360 s
- rollback flash done to Android boot-ready: 33.164 s
- full live session: 226.287 s

Timeline file:

`workspace/private/runs/s22plus_m34_s7a_session_producer_live_gate_20260708T224815Z/timeline.json`

## Authorization State

The S7A one-shot exception is consumed and retired in `AGENTS.md`; the live and
rollback tokens are intentionally omitted as active authorization. No active
S22+ native-init live flash is authorized by this result.

Next work should be host-only. Highest-value targets:

- diff S7A's direct PID1 ordering against stock Android USB init rc/property
  choreography
- inspect stock `init.*.usb*.rc`, `android.hardware.usb@1.3-service.coral`,
  `ss_conn_daemon2`, FunctionFS mount timing, and `sys.usb.*` property gates
- design S7B as a stock-composite/userspace-readiness unit only if it explains
  why S7A still presents no host-visible Samsung USB endpoint
- avoid another live boot candidate until the next hypothesis accounts for
  both survival and complete absence of host-visible `04e8:*`
