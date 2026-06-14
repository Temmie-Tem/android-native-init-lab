# NATIVE_INIT V2358 — AUD-3C tinyalsa installer toybox semantics repair

Date: 2026-06-15

## Scope

Host-only repair after V2357. No flash, no ADSP command, no `/dev/snd` command, no tinyalsa execution, no mixer write, no PCM playback/write, no audio HAL, and no `adsprpc` path.

## Problem

V2356 changed the AUD-3C runner to pass `/cache/bin/busybox` through `tcpctl_host.py --toybox`. V2357 proved that path exists, but the installer still failed because `tcpctl_host.py` generates a toybox-style netcat listener:

```text
netcat -l -p PORT COMMAND...
```

BusyBox `nc` does not execute trailing `COMMAND...` in that form; it requires `-e PROG`. The command exited immediately and the host transfer failed with `ECONNREFUSED`.

Read-only help on the rollback V2321 runtime confirmed `/bin/toybox netcat` supports the exact listener child-command form expected by `tcpctl_host.py`, and `/bin/toybox` is present.

## Change

- Changed `DEFAULT_DEVICE_TOOLBOX` in `native_audio_tinyalsa_inventory_live_handoff_v2349.py` from `/cache/bin/busybox` to `/bin/toybox`.
- Kept the shared `tcpctl_host.py` installer unchanged.
- Updated dry-run regressions to require `--toybox /bin/toybox`.
- Added regression coverage that stale `/cache/bin/toybox` and incompatible `/cache/bin/busybox` do not appear in the AUD-3C install/inventory plan.
- Updated `GOAL.md` and `CLAUDE.md` with the V2357/V2358 state.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_tinyalsa_inventory_live_handoff_v2349 -v`
- AUD-3C dry-run:
  - decision: `v2349-audio-tinyalsa-inventory-live-dry-run`
  - `ok=True`
  - `/bin/toybox` present in the plan,
  - `/cache/bin/toybox` absent,
  - `/cache/bin/busybox` absent.

## Next step

A fresh exact AUD-3C live approval is required before retrying. The next live retry should remain read-only inventory only: `tinymix` list / all-values and `tinypcminfo`, with no `tinyplay`, no mixer set, no PCM playback/write, no audio HAL, and rollback to V2321.
