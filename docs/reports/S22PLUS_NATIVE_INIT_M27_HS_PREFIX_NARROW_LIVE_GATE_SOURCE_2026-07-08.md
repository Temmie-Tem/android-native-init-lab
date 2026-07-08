# S22+ Native-Init M27 HS Prefix-Narrow Live Gate Source (2026-07-08)

## Verdict

SOURCE READY / LIVE NOT AUTHORIZED: the guarded M27 prefix-narrow live helper is
implemented and validates the pinned M27 artifacts offline. No flash, reboot,
rollback, partition write, sysfs write, or Android device action was performed.

Default execution currently fails closed before Android/device access because
`AGENTS.md` does not contain a fresh M27 live exception.

## Scope

Prepared M27 batch:

- `P08`
- `P12`
- `P16`
- `P20`
- `P22`
- `P23`
- `P24`

The helper rejects prefixes outside this set, including `P00` and `P25`. Live
execution, once separately authorized, is designed to start at `P08`, keep the
M25 DTBO high-speed cap in place across successful prefixes, roll boot back to
the pinned Magisk baseline after each self-download hit, and stop on the first
no-hit/manual-download result.

## Files

- Live helper:
  `workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py`
- Tests:
  `tests/test_s22plus_m27_hs_prefix_narrow_live_gate.py`
- Host-build manifest:
  `workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1/manifest.json`

## Pins

- M27 source SHA256:
  `44b3111652cbd64561f4b5eee5413864df44422e28f905ce6dc42aa618f951cd`
- M27 manifest SHA256:
  `e44776fd55ff66eb6b4a197f351cc129000e7120b5ceeab91dd36d88c1988e63`
- M25 HS-only module-list SHA256:
  `00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496`
- M25 DTBO high-speed cap AP SHA256:
  `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`
- Stock DTBO rollback AP SHA256:
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`

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
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py
```

Results:

- Bytecode compile passed.
- Unit tests passed: `Ran 9 tests ... OK`.
- Offline check passed for `P08/P12/P16/P20/P22/P23/P24` and rollback APs
  with no device action.
- Default execution failed closed with rc `1` on missing M27 `AGENTS.md`
  authorization markers before Android/device access.

## Next

Live still requires a fresh SHA-pinned `AGENTS.md` exception for exactly this
M27 helper, candidate set, DTBO cap, rollback APs, and stop-on-first-no-hit
policy. Without that exception, the helper remains source/offline only.
