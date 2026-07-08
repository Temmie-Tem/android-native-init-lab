# S22+ M34 S6 Stock Softdep Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: LIVE CONSUMED. S6 survived the full observation window without a boot
loop, but it did not expose any Samsung USB endpoint or ACM. Rollback returned
Android/Magisk cleanly. No active live authorization remains.

## Scope

M34 S6 tested two changes on top of S5:

- removed USB2 high-speed forcing (`g1/max_speed=high-speed` and
  `ssusb/speed=high-speed`)
- restored stock `dwc3_msm` softdep parity in the native-init module list:
  QMP, EUD, `ucsi_glink`, and their dependency-complete closure

S6 did not write EUD sysfs knobs, did not use `soft_connect`, did not change
descriptors/strings/companion functions, and did not request a reboot or
Android/Magisk handoff.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py`

Run directory:

`workspace/private/runs/s22plus_m34_s6_stock_softdep_live_gate_20260708T214510Z/`

Pins:

- AP.tar.md5 SHA256:
  `f1ff77b7df434536029db417291689bff8b3a7dcdf4fda38fef5322475daad39`
- padded `boot.img` SHA256:
  `b1bfc4ece7ece60af752bc570e0ae4ce76230d13b129b1c58d4e840cd92225f6`
- direct `/init` SHA256:
  `ca3eb2b5a0fedff73cfb0aaa249d42f4b92fcb99b360e9ec5a041649dcd7dd8c`
- template source SHA256:
  `ce023ba98006e49839433ce16ec8321bd9003b74151f39879fcecb682fef9ecc`
- module-list SHA256:
  `51ba77aeed1966a2de8c78d307ca3d6fe5440daa2b96488679446f6056142515`
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
- S6 survived the full 90 second observation window
- the operator observed no boot loop
- 17 candidate snapshots showed no Samsung `04e8:*` endpoint at all
- stock Android `04e8:6860` was absent
- CDC ACM was absent from `lsusb -d 04e8:6860 -v` and `lsusb -t`
- `/dev/ttyACM*` was absent
- ADB was absent during candidate park
- Odin/upload/download endpoints were absent during the candidate park window

Operator-side observation after the survival window: RDX/PMIC appeared, then
manual Download mode was entered for rollback.

Interpretation:

- S6 is a survival improvement over S5: removing high-speed forcing and adding
  QMP/EUD/UCSI softdep parity avoided the earlier pre-90-second Odin return.
- S6 is not a USB success: it exposed no host-visible Samsung USB device during
  the observation window.
- The current blocker is no longer "S5 fell into upload/download before the
  survival window"; it is "direct native-init can survive while still failing to
  make the stock Android USB composite path enumerate."
- The missing piece is likely stock Android USB orchestration beyond this
  minimal configfs setup: init rc/property choreography, descriptor/function
  parity, companion functions, controller/role state, or a still-missing vendor
  userspace/kernel handshake.

## Rollback

Because S6 survived the observation window with no host-visible endpoint, the
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

The helper verified the restored boot hash with rc=0. A post-live independent
`su -c 'sha256sum /dev/block/by-name/boot'` check also returned the same SHA256.

## Retained Evidence

- pstore files: empty
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- M34 S6 marker in retained evidence: absent

Marker absence is not treated as proof of non-execution because the helper
observed candidate boot/disconnect, a full park window, and later clean manual
rollback.

## Timeline

Canonical timeline shape:

```json
{
  "events": [
    {"name": "live_session_start", "timestamp_utc": "2026-07-08T21:45:21.541852Z"},
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-08T21:45:33.118569Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-08T21:45:34.603164Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-08T21:45:35.886696Z"},
    {"name": "manual_after_survival_rollback_flash_start", "timestamp_utc": "2026-07-08T21:48:12.893904Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-08T21:48:12.894111Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-08T21:48:14.260291Z"},
    {"name": "manual_after_survival_rollback_flash_done", "timestamp_utc": "2026-07-08T21:48:14.260454Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-08T21:48:59.568024Z"},
    {"name": "manual_after_survival_rollback_boot_ready", "timestamp_utc": "2026-07-08T21:48:59.568327Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-08T21:49:00.004370Z"}
  ]
}
```

Timeline file:

`workspace/private/runs/s22plus_m34_s6_stock_softdep_live_gate_20260708T214510Z/timeline.json`

## Authorization State

The S6 one-shot exception is consumed and retired in `AGENTS.md`; the live and
rollback tokens are intentionally omitted as active authorization. No active
S22+ native-init live flash is authorized by this result.

Next work should be host-only. Highest-value targets:

- extract or inspect stock Android USB init rc/property choreography from the
  FYG8 firmware and rooted Android baseline
- capture the live stock Android configfs/sysfs USB state from Android, then
  diff it against S6's native-init sequence
- compare descriptor/function parity beyond `ss_acm.0`, especially MTP, ADB,
  `conn_gadget`, Microsoft OS descriptors, strings, configs, and symlink order
- avoid another live boot candidate until the next S7 hypothesis explains why
  a surviving direct PID1 still presents no host-visible Samsung USB endpoint
