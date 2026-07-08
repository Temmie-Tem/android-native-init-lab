# S22+ Native-Init M27 HS Prefix-Narrow Live Gate (2026-07-08)

## Verdict

PRE-LIVE PASS: M27 prefix-narrow batch gate is implemented, SHA-pinned in
`AGENTS.md`, statically validated, and dry-run verified against the attached
S22+ Android/Magisk baseline. No live flash, reboot, rollback, partition write,
or sysfs write was performed.

## Scope

Authorized M27 batch only:

- `P08`
- `P12`
- `P16`
- `P20`
- `P22`
- `P23`
- `P24`

The helper rejects `P00` and `P25+` under this exception. The batch uses the
pinned M25 DTBO high-speed cap, rolls boot back to the Magisk baseline after
each self-download hit, stops on the first no-hit/manual-download result, and
requires stock DTBO rollback at session end.

## Files

- Live helper:
  `workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py`
- Tests:
  `tests/test_s22plus_m27_hs_prefix_narrow_live_gate.py`
- Host-build manifest:
  `workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1/manifest.json`
- Source-stage report:
  `docs/reports/S22PLUS_NATIVE_INIT_M27_HS_PREFIX_NARROW_LIVE_GATE_SOURCE_2026-07-08.md`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py \
  tests/test_s22plus_m27_hs_prefix_narrow_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m27_hs_prefix_narrow_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py \
  --serial RFCT519XWGK

git diff --check
```

Results:

- Bytecode compile passed.
- Unit tests passed: `Ran 9 tests ... OK`.
- Offline check passed for `P08/P12/P16/P20/P22/P23/P24` and rollback APs
  with no device action.
- Device dry-run passed against `RFCT519XWGK`: AGENTS exception, Android
  stability, boot hash, vendor_boot hash, and stock DTBO hash verified.

## Dry-Run Baseline

Dry-run log:

```text
workspace/private/runs/s22plus_m27_hs_prefix_narrow_live_gate_20260708T133625Z/s22plus_m27_hs_prefix_narrow_live_gate.txt
```

Baseline observed:

- `boot_completed=1`
- `bootanim=stopped`
- `vbstate=orange`
- Magisk root: `uid=0(root)`
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- stock DTBO SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- vendor_boot SHA256:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

## Live Command

Operator-approved live command, not yet executed by this report:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py \
  --serial RFCT519XWGK \
  --live \
  --ack S22PLUS-M27-HS-PREFIX-NARROW-LIVE-GATE
```

Rollback-only rescue command if a candidate leaves the phone in Download mode:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M27-HS-PREFIX-ROLLBACK-FROM-DOWNLOAD
```
