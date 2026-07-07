# S22+ Bootloop Manual Download Recovery Check (2026-07-08)

## Verdict

RECOVERED to the rooted Magisk boot baseline.

The operator reported a bootloop and manual entry to download mode. On host
inspection after the report, the phone was no longer in Odin/download mode; it
was reachable as normal Android over ADB.

No new flash was performed during this check.

## Current Device State

Captured at `2026-07-07T17:07:21Z` into private directory:

`workspace/private/runs/s22plus_bootloop_manual_download_20260707T170721Z`

Read-only facts:

- Model/device: `SM-S906N` / `g0q`
- Bootloader/build: `S906NKSS7FYG8`
- Verified boot state: `orange`
- `sys.boot_completed=1`
- `ro.boot.bootreason=reboot,download`
- Magisk root available: `uid=0(root) ... context=u:r:magisk:s0`
- Current boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

That boot SHA matches the pinned Magisk boot-only rollback baseline used by the
S22+ live gates.

## Retained Evidence

Private retained files:

- `android_identity.txt`
- `block_by_name.txt`
- `current_boot_sha256.txt`
- `pstore_list.txt`
- `last_kmsg.bin`

Retained log scan:

- `/sys/fs/pstore`: empty
- `/proc/last_kmsg`: 2,097,136 bytes
- `S22_NATIVE_INIT`: absent
- `Kernel panic`: absent
- `not syncing`: absent
- `Unable to mount root`: absent
- `Oops`: absent
- `reboot,download`: present
- `reboot_reason`: present

Interpretation: the host-visible state is clean recovery to the rooted baseline,
but the retained log still does not localize the native-init failure. Marker
absence must not be treated as proof that `/init` did not run.

## Operational Decision

Stop cascading live flashes after this bootloop report. The next S22+ native-init
work remains host-only unless a new SHA-pinned boot-only exception and guarded
live gate are added for a single selected candidate.

M19 is currently only a host-built checkpoint matrix. It has not been live
flashed and has no live authorization.
