# v346 Handoff Preflight Output Isolation Report

- date: `2026-05-19`
- scope: host-side V317 handoff command safety
- device command: none
- device mutation: none
- result: `PASS / HOST-ONLY`

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

## Post-commit Validation

After commit, ran V344 refresh and then executed the generated V340 preflight
command itself. Observed result:

```text
V344 refresh: v317-gate-refresh-ready / pass=True
V340 handoff: v317-handoff-awaiting-approval / pass=True
preflight-command-contract: pass
preflight-output-isolated: pass
generated V340 preflight: private-property-namespace-proof-preflight-ready / pass=True
preflight_only: true
device_commands_executed: false
device_mutations: false
commands: []
```

Evidence:

- V344 refresh manifest: `tmp/wifi/v344-v317-gate-refresh/manifest.json`
- V340 handoff manifest: `tmp/wifi/v340-v317-final-handoff-packet/manifest.json`
- generated preflight manifest: `tmp/wifi/v317-private-property-namespace-proof-preflight/manifest.json`

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.
