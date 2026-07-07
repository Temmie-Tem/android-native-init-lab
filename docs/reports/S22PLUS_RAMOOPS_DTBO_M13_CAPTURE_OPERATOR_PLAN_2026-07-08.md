# S22+ — Ramoops DTBO + M13 Capture Operator Plan Mode (2026-07-08)

## Scope

Host-only helper ergonomics. No device action, reboot, flash, partition write,
ADB live operation, or Odin live operation was performed by this unit.

Updated helpers:

- `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py`
- `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_readiness_audit.py`

## Change

The DTBO+M13 capture helper now has a host-only `--print-plan` mode. It verifies
the pinned DTBO/M13/rollback artifacts through the same preflight used by other
host-only modes, then prints the operator-facing sequence:

1. inactive-policy readiness audit;
2. active-policy readiness audit after any future `AGENTS.md` promotion;
3. default dry-run;
4. attended live command;
5. expected live sequence;
6. manual Download-mode rollback command;
7. stock DTBO cleanup commands.

The printed paths are repo-relative where possible, so copied output does not
carry unnecessary host absolute paths.

The readiness auditor now also runs `--print-plan` and asserts that the output
contains the live ack token, boot-rollback token, DTBO restore token, rollback
mode, stock-DTBO restore modes, and `ramoops_region/status=okay`.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_readiness_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py \
  --print-plan

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_readiness_audit.py \
  --out workspace/private/runs/s22plus_ramoops_dtbo_m13_readiness_20260707T193000Z/readiness.json
```

Observed:

```text
py_compile: pass
print-plan: pass; host-only plan printed
readiness audit: result=pass
readiness audit print_plan.returncode=0
```

No live policy was activated. `AGENTS.md` remains inactive for the DTBO+M13 live
gate.
