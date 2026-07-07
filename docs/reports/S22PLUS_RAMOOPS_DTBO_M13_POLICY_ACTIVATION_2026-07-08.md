# S22+ Ramoops DTBO + M13 Policy Activation (2026-07-08)

## Scope

Activate the previously inert DTBO+M13 positive-control policy block in
`AGENTS.md` after operator live approval. This report covers policy activation
and pre-live gate validation only. It is not the live capture result.

## Change

Copied the inert exception draft from
`docs/operations/S22PLUS_RAMOOPS_DTBO_M13_CAPTURE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`
into `AGENTS.md` after the DTBO status-only exception and before the retired
vendor_boot+M13 block.

The active exception authorizes only the bounded attended helper:

```text
workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py
S22PLUS-RAMOOPS-DTBO-M13-CAPTURE-LIVE-GATE
```

It keeps the path limited to the pinned patched `dtbo` AP, pinned M13 boot AP,
pinned Magisk/stock boot rollback APs, and pinned stock-DTBO rollback AP. It
does not authorize vendor_boot, vbmeta, recovery, BL, CP, CSC, super, userdata,
EFS, RPMB, keymaster, modem, bootloader, raw host `dd`, fastboot, Magisk
modules, additional candidates, or A90 actions.

## Validation

Commands:

```sh
PYTHONPATH=workspace/public/src/scripts/revalidation PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_readiness_audit.py \
  --expect-agents-active --no-default-dryrun-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py
```

Results:

```text
active-policy readiness: pass; agents.complete=true, missing=[]
py_compile: pass
git diff --check: pass
default pre-live dry-run: pass; Android/root stability, boot hash, stock DTBO
  hash, and live ramoops_region/status=disabled verified
```

The pre-live dry-run log was written under `workspace/private/runs/` and is not
committed.
