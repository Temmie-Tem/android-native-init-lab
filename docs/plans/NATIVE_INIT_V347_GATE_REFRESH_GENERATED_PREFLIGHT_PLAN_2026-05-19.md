# v347 Plan: Gate Refresh Runs Generated Handoff Preflight

- date: `2026-05-19`
- scope: host-only V317 gate refresh coverage
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending post-commit refresh

## Summary

v346 made the V340 handoff preflight command use an isolated output directory.
However, the V344 refresh helper still validated only its own direct runner
preflight path. That left the exact generated V340 handoff preflight command as a
manual post-commit check.

v347 closes that gap. When `wifi_v317_gate_refresh.py --run-approved-preflight`
is used, the helper now runs both:

1. direct runner preflight in `tmp/wifi/v342-v317-approved-preflight/`
2. generated V340 handoff preflight command from
   `tmp/wifi/v340-v317-final-handoff-packet/manifest.json`

Both are expected to be no-device preflight checks with `commands=[]`.

## Implementation

- Update `scripts/revalidation/wifi_v317_gate_refresh.py`.
- Import `shlex` to parse the generated handoff command safely.
- Add `command_arg()` helper for `--out-dir` extraction.
- Add `generated_handoff_preflight_step()` that:
  - reads V340 handoff manifest
  - extracts `preflight_command`
  - runs that exact command
  - expects `private-property-namespace-proof-preflight-ready`
  - expects the generated command's own output manifest
- Keep V317 live proof unexecuted.

## Validation

Pre-commit validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_gate_refresh.py
python3 scripts/revalidation/wifi_v317_gate_refresh.py \
  --run-approved-preflight \
  --out-dir tmp/wifi/v344-v317-gate-refresh \
  refresh || true
```

Expected pre-commit result:

- dirty tree can block V336/V331/V340 as designed.
- output contains both `v342-approved-preflight` and `v340-generated-preflight`
  steps.
- no device command or mutation is reported.

Post-commit validation:

```bash
python3 scripts/revalidation/wifi_v317_gate_refresh.py \
  --run-approved-preflight \
  --out-dir tmp/wifi/v344-v317-gate-refresh \
  refresh
```

Expected post-commit result:

```text
decision: v317-gate-refresh-ready
v342-approved-preflight: pass
v340-generated-preflight: pass
device_commands_executed: false
device_mutations: false
```

## Acceptance

- `--run-approved-preflight` validates the generated V340 handoff preflight
  command, not only the direct runner preflight.
- Both preflight paths remain no-device checks.
- V317 live `run` remains blocked by the exact approval phrase.
