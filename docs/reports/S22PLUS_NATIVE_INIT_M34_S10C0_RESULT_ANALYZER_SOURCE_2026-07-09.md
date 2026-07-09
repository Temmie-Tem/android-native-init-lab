# S22+ M34 S10C0 Result Analyzer Source

Date: 2026-07-09 21:02 KST / 2026-07-09 12:02 UTC

## Verdict

S10C0 now has a host-only post-live analyzer. It does not talk to the device,
does not authorize a live run, and does not perform Odin/reboot/partition
actions.

The live gate is still not run. This source unit only prepares deterministic
interpretation of the future S10C0 `result.json` + `timeline.json`.

## Files

```text
workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py
tests/test_analyze_s22plus_m34_s10c0_result.py
```

## Analyzer Contract

Input:

```text
result.json
timeline.json
```

The analyzer verifies:

```text
schema=s22plus_m34_s10c0_result_v1
stage=S10C0
target=SM-S906N/g0q/S906NKSS7FYG8
candidate_ap_sha256=9221cfa3ea3ce0776860a5041981e23a84d0be9b833203401dab771897266c6f
candidate_boot_sha256=8d77e1434cd47fe47f4723c948e4ff6db759cbe4bf75dd21e9e0c265d928c6df
candidate_init_sha256=cd80d5923c94f8a423821bc6dee4547f22763e177fbcc637d1bcb101c4b8c39b
base_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
module_load_probe=finit_cmd_db_accepted
probe_module=cmd-db.ko
probe_proc_name=cmd_db
```

It also verifies canonical `timeline.json` shape:

```text
events:[{name,timestamp_utc}]
```

For complete live proof, the required event sequence is:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
rollback_boot_ready
live_session_end
```

The analyzer rejects missing, duplicated, out-of-order, or non-monotonic
required events.

## Decisions

Clean HIT:

```text
s22plus-m34-s10c0-cmd-db-finit-accepted-proceed-s11
```

Meaning: `cmd-db.ko` direct `finit_module` was accepted under native-init.
Next S11 should distinguish load-loop skip from `/proc/modules` observation
artifact.

Clean MISS:

```text
s22plus-m34-s10c0-cmd-db-finit-miss-proceed-s11-errno-capture
```

Meaning: `cmd-db.ko` direct `finit_module` was not accepted or was not reached.
Next S11 should surface attempted/rc/errno and include a positive-control
module.

Invalid or incomplete evidence:

```text
s22plus-m34-s10c0-invalid-result-evidence
s22plus-m34-s10c0-no-direct-finit-proof
s22plus-m34-s10c0-rollback-incomplete-recovery-required
```

The analyzer redacts Android serials in generated analysis JSON.

## CLI

Write analysis next to a live result:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py \
  workspace/private/runs/<s10c0-live-run>/result.json \
  --write-report
```

Require enough evidence to proceed to S11 host-only design:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py \
  workspace/private/runs/<s10c0-live-run>/result.json \
  --require-advance
```

Require evidence plus Magisk rollback baseline for the next live gate:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py \
  workspace/private/runs/<s10c0-live-run>/result.json \
  --require-live-next-stage
```

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py \
  tests/test_analyze_s22plus_m34_s10c0_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_analyze_s22plus_m34_s10c0_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_analyze_s22plus_m34_s10c0_result.py \
  tests/test_s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py \
  tests/test_s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  tests/test_s22plus_m34_runtime_gadget_split_build.py
```

Results:

```text
S10C0 analyzer tests: Ran 22, OK
Combined focused tests: Ran 39, OK, skipped=2
```

Negative control:

```text
analyze_s22plus_m34_s10c0_result.py \
  workspace/private/runs/s22plus_m34_s10b0_live_20260709T103800Z/result.json \
  --timeline-json workspace/private/runs/s22plus_m34_s10b0_live_20260709T103800Z/timeline.json \
  --json
```

Result: rc `1`, decision
`s22plus-m34-s10c0-invalid-result-evidence`, with schema/stage/hash/probe
mismatches. This confirms S10B0 evidence cannot be accidentally promoted as
S10C0 proof.
