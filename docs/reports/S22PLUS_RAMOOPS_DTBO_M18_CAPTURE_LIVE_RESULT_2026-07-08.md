# S22+ Ramoops DTBO + M18 Capture Live Result (2026-07-08)

## Verdict

The attended live gate ran and recovered the device cleanly.

- DTBO candidate flash: passed.
- Patched-DTBO Android return: passed.
- M18 boot flash: passed.
- M18 observation: no ACM, no ADB, Odin/download-mode returned.
- Magisk boot rollback: passed.
- Android return after boot rollback: passed.
- pstore / retained log marker capture: failed, marker not found.
- Stock DTBO restore: passed.
- Final Android baseline preflight: passed.

This is a clean failed-capture result, not a recovery failure.

## Timeline

UTC timestamps from the private live log:

- `2026-07-07T16:44:22Z`: patched DTBO Odin flash completed,
  `dtbo_candidate_odin_rc=0`.
- `2026-07-07T16:44:53Z`: Android/root returned with patched DTBO,
  `patched_dtbo_android_ok`.
- `2026-07-07T16:45:04Z`: M18 boot Odin flash completed,
  `m18_candidate_odin_rc=0`.
- `2026-07-07T16:45:06Z` through `2026-07-07T16:45:46Z`: no ACM and no
  ADB during M18 observation.
- `2026-07-07T16:45:47Z`: Odin/download-mode appeared,
  `m18_odin_seen=1`.
- `2026-07-07T16:45:47Z`: Magisk boot rollback completed,
  `magisk_boot_rollback_odin_rc=0`.
- `2026-07-07T16:46:38Z`: Android/root returned after boot rollback.
- `2026-07-07T16:46:38Z`: pstore files list was empty; `/proc/last_kmsg`
  read returned 2097136 bytes but no M18 marker.
- `2026-07-07T16:46:50Z`: stock DTBO rollback completed,
  `stock_dtbo_rollback_after_capture_odin_rc=0`.
- `2026-07-07T16:47:29Z`: Android/root returned after stock DTBO restore.
- `2026-07-07T16:47:43Z`: final read-only Android baseline preflight passed.

## Evidence

Private run directory:

`workspace/private/runs/s22plus_ramoops_dtbo_m18_capture_20260707T164400Z`

Private retained artifacts:

- `s22plus_ramoops_dtbo_m18_capture_live_gate.txt`
- `android_pstore/post_m18_boot_rollback_last_kmsg.bin` (2097136 bytes)
- host observation snapshots for M18 observe intervals

Committed public reports intentionally omit raw logs, device serials, and private
binary captures.

Host-side scan of the retained `last_kmsg` found zero occurrences of the M18
markers (`S22M18`, `full_firststage`, `module_group`). It did show repeated ABL
download-mode records including `bootloader_mode = 1`, `reboot_reason = 0x9`,
and `Failed to get KlogOffset`.

Final read-only preflight confirmed:

- model/build target remained `SM-S906N` / `S906NKSS7FYG8`;
- `vbstate=orange`;
- root available;
- boot SHA256 restored to
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- DTBO SHA256 restored to
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- `ramoops` status back to `disabled`.

## Interpretation

The DTBO write path itself is not the immediate blocker: the device booted
Android with the patched DTBO before the M18 boot flash.

The M18 candidate still fails before exposing ACM or ADB. The capture path did
not find the expected marker in pstore or retained last-kmsg. The retained log
looks more like ABL/download-mode retention than the M18 native-init printk
stream. That leaves two host-side questions before another live candidate:

- Did M18 reset before emitting the marker?
- Or did the DTBO ramoops node not create a retained pstore path for this boot
  failure mode?

Next work should analyze the private 2 MiB `last_kmsg` and the exact M18
marker/printk ordering before designing another device action.
