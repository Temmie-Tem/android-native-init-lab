# v346 Handoff Preflight Output Isolation Report

- date: `2026-05-19`
- scope: host-side V317 handoff command safety
- device command: none
- device mutation: none
- result: `PRE-COMMIT CONTRACT PASS / POST-COMMIT REFRESH REQUIRED`

## Summary

v346 prevents the V340 handoff preflight command from writing into the live V317
result directory. The preflight command now uses a dedicated output directory:

```text
tmp/wifi/v317-private-property-namespace-proof-preflight
```

The live `run` command continues to use:

```text
tmp/wifi/v317-private-property-namespace-proof
```

## Code Change

- `scripts/revalidation/wifi_v317_handoff_packet.py`
  - added `PREFLIGHT_OUT_DIR`
  - added `command_arg()` helper
  - extended `command_variant()` to optionally rewrite `--out-dir`
  - added `preflight-output-isolated` handoff check
  - records `preflight_out_dir` in the handoff manifest

## Pre-commit Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_v317_handoff_packet.py \
  scripts/revalidation/wifi_v317_gate_refresh.py \
  scripts/revalidation/wifi_v317_live_surface_linter.py
python3 scripts/revalidation/wifi_v317_handoff_packet.py \
  --out-dir tmp/wifi/v340-v317-final-handoff-packet \
  packet || true
```

Observed pre-commit result:

```text
preflight-command-contract: pass
preflight-output-isolated: pass
V340 overall: blocked only by current-tree-clean while source tree is dirty
```

## Post-commit Validation Plan

After commit, run V344 refresh and then execute the generated V340 preflight
command. The generated command must complete as no-device preflight evidence and
must write to the isolated preflight output directory.

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.
