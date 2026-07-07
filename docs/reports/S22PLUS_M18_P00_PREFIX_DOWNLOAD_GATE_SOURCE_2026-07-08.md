# S22+ M18 P00 Prefix-Download Gate Source (2026-07-08)

## Verdict

Host-only source for the next no-UART fallback live gate is ready. No live flash,
reboot, ADB action, Odin transfer, partition write, EUD sysfs write, or OpenOCD
init was performed.

The gate is intentionally limited to P00. P00 loads no modules; it only proves
that the minimal native-init runtime reaches the checkpoint and can request
Download mode. P10 remains unavailable as a live target until P00 self-download
is observed and rollback is clean.

## Added

- `workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py`
- `docs/operations/S22PLUS_M18_P00_PREFIX_DOWNLOAD_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`
- `tests/test_s22plus_m18_p00_prefix_download_live_gate.py`

## Safety Shape

Default/offline-check mode:

- verifies the inert policy draft marker coverage;
- verifies the pinned P00 AP SHA256;
- verifies the P00 manifest safety fields and boot-only tar member;
- verifies pinned Magisk and stock boot rollback APs;
- performs no device action.

Live mode is fail-closed unless the draft is promoted into `AGENTS.md` and the
exact ack token is supplied. If later authorized, the proof rule is:

```text
candidate Odin endpoint disconnects
later Odin endpoint appears within the bounded observation window
=> P00 reached checkpoint and requested Download mode
```

The original Odin endpoint after flashing is not counted as proof.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m18_p00_prefix_download_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py \
  --offline-check

offline-check ok: M18 P00 candidate and rollback APs verified; no device action; log=workspace/private/runs/...

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py \
  --live --ack S22PLUS-M18-P00-PREFIX-DOWNLOAD-LIVE-GATE

AGENTS.md missing M18 P00 live authorization markers: [...]
```

## Next Gate

Do not run live until a fresh AGENTS exception is promoted and the operator is
present. The first supervised run must be P00 only. If P00 passes, the next
host-only unit can prepare P10 live policy; if P00 fails, stop this fallback and
return to UART/raw-assembly checkpoint design.
