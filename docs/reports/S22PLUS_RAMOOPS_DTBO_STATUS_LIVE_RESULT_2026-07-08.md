# S22+ — Ramoops DTBO Status Live Result (2026-07-08)

## Summary

The attended DTBO status-only live gate was authorized and executed.

Result: pass. The patched DTBO booted Android/root, the live DTBO hash matched
the pinned patched image, `/proc/device-tree/reserved-memory/ramoops_region/status`
changed to `okay`, and the helper then restored stock DTBO and re-verified live
status back to `disabled`.

No boot, recovery, vendor_boot, vbmeta, M13, M15, M18, QMP, or native-init
candidate was flashed in this run.

## Command

Pre-live read-only dry-run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py
```

Observed:

```text
dry-run ok: DTBO status candidate, rollback AP, AGENTS exception, Android stability, boot hash, stock DTBO hash, and live disabled status verified
```

Attended live:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py \
  --live \
  --ack S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE
```

Observed:

```text
ramoops DTBO status live gate completed rc=0
```

Private run log:

`workspace/private/runs/s22plus_ramoops_dtbo_status_20260707T191547Z/s22plus_ramoops_dtbo_status_live_gate.txt`

Device serials and transient USB paths are intentionally not copied into this
public report.

## Verified Facts

Pinned artifacts:

- patched DTBO AP SHA256:
  `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`
- stock DTBO rollback AP SHA256:
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`
- patched raw DTBO SHA256:
  `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`
- stock raw DTBO SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- DTBO AP tar member: exactly `dtbo.img.lz4`

Live sequence evidence:

- `agents_exception_missing=[]`
- preflash live ramoops status: `disabled`
- patched DTBO Odin flash: `rc=0`
- Android/root returned after patched DTBO
- patched DTBO hash readback matched
  `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`
- patched live ramoops status: `okay`
- stock DTBO rollback Odin flash: `rc=0`
- Android/root returned after stock DTBO restore
- final stock DTBO hash readback matched
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- final live ramoops status: `disabled`

## Interpretation

The active-DTB provenance model is confirmed live. Stock DTBO really was the
piece overriding the base vendor DTB ramoops node, and the patched DTBO overlay
is sufficient to enable the live ramoops node.

This closes the status-only gate and unlocks the next observability unit:
combine the proven patched-DTBO enable step with an M13 positive-control boot,
then roll back boot and collect pstore. That next unit needs its own scoped
helper/policy path; the retired vendor_boot-only positive-control path should
not be reused as-is.

## Final State

The helper restored stock DTBO before exit. Final verified state:

- Android/root returned.
- DTBO hash is stock FYG8.
- live `ramoops_region/status=disabled`.
- helper exit code was `0`.
