# S22+ Native-Init M26 HS Prefix-Download Live Gate (2026-07-08)

## Verdict

PRE-LIVE PASS: M26 first-live batch gate is implemented, SHA-pinned in
`AGENTS.md`, statically validated, and dry-run verified against the attached
S22+ Android/Magisk baseline. No live flash had been performed at the time this
report was written.

## Scope

Authorized first-live batch only:

- `P00`
- `P24`
- `P27`
- `P30`

The helper rejects `P25`, `P28`, `P33`, and `P40` under this exception. The
batch uses the pinned M25 DTBO high-speed cap, rolls boot back to the Magisk
baseline after each prefix, and restores stock DTBO at session end.

## Files

- Live helper:
  `workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py`
- Tests:
  `tests/test_s22plus_m26_hs_prefix_download_live_gate.py`
- Host-build manifest:
  `workspace/private/outputs/s22plus_native_init/m26_hs_prefix_download_v0_1/manifest.json`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py \
  tests/test_s22plus_m26_hs_prefix_download_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m26_hs_prefix_download_live_gate

python3 workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py \
  --offline-check

python3 workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py \
  --serial RFCT519XWGK

git diff --check
```

Results:

- Bytecode compile passed.
- Unit tests passed: `Ran 8 tests ... OK`.
- Offline check passed: M26 candidates, M25 DTBO cap, and rollback APs verified
  without device action.
- Device dry-run passed against `RFCT519XWGK`: AGENTS exception, Android
  stability, boot hash, vendor_boot hash, and stock DTBO hash verified.
- `git diff --check` passed.

## Live Command

Operator-approved live command:

```bash
python3 workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py \
  --serial RFCT519XWGK \
  --live \
  --ack S22PLUS-M26-HS-PREFIX-DOWNLOAD-LIVE-GATE
```

Rollback-only rescue command if a candidate leaves the phone in Download mode:

```bash
python3 workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M26-HS-PREFIX-ROLLBACK-FROM-DOWNLOAD
```
