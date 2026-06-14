# NATIVE_INIT V2356 — AUD-3C tinyalsa install toolbox repair

Date: 2026-06-15

## Scope

Host-only repair after V2355. No flash, no ADSP command, no `/dev/snd` command, no tinyalsa execution, no mixer write, no PCM playback/write, no audio HAL, and no `adsprpc` path.

## Problem

V2355 proved the V2354 NCM repair works and reached post-materialization tool staging, but `install-tinymix` failed because the shared `tcpctl_host.py` install path defaulted to `/cache/bin/toybox`:

```text
execve(/cache/bin/toybox): No such file or directory
ConnectionRefusedError: [Errno 111] Connection refused
```

A post-rollback path check on V2321 showed `/cache/bin/busybox`, `/bin/busybox`, and `/bin/toybox` are available, while `/cache/bin/toybox` is absent. The install helper already exposes a `--toybox` option, so the correct fix is to pass the native-init runtime toolbox path explicitly from the AUD-3C runner instead of changing the shared helper default globally.

## Change

- Added `DEFAULT_DEVICE_TOOLBOX = "/cache/bin/busybox"` to `native_audio_tinyalsa_inventory_live_handoff_v2349.py`.
- Added `--device-toolbox`, defaulting to `/cache/bin/busybox`.
- Made all `tcpctl_host.py` invocations from the AUD-3C runner pass `--toybox <device_toolbox>` before the subcommand.
- Exposed `preflight.device_toolbox` in the dry-run payload.
- Added focused regressions that:
  - install commands include `--toybox /cache/bin/busybox`,
  - the dry-run plan includes `/cache/bin/busybox`,
  - the dry-run plan does not contain `/cache/bin/toybox`.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_tinyalsa_inventory_live_handoff_v2349 -v` — 10 tests passed.
- Dry-run:
  - decision: `v2349-audio-tinyalsa-inventory-live-dry-run`
  - `ok=True`
  - `/cache/bin/busybox` present in the plan,
  - `/cache/bin/toybox` absent from the plan.

## Next step

A fresh exact AUD-3C live approval is required before retrying. The next live retry should remain read-only inventory only: `tinymix` list / all-values and `tinypcminfo`, with no `tinyplay`, no mixer set, no PCM playback/write, no audio HAL, and rollback to V2321.
