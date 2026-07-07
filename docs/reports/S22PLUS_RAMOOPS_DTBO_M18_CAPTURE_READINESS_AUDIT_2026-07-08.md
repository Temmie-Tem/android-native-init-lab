# S22+ Ramoops DTBO + M18 Capture Readiness Audit (2026-07-08)

## Scope

Host-only audit. No device action, no reboot, no flash, no partition write, and
no edit to `AGENTS.md`.

This unit adds a repeatable readiness auditor so the capture stack can be
checked for drift before any future attended approval/run.

## Added

`workspace/public/src/scripts/revalidation/s22plus_ramoops_capture_readiness_audit.py`

The auditor checks:

- active `AGENTS.md` capture markers;
- inert exception draft marker coverage;
- capture gate `--offline-check`;
- current fail-closed behavior of the default capture-gate dry-run while
  `AGENTS.md` remains inactive.

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_capture_readiness_audit.py

python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_capture_readiness_audit.py \
  > /tmp/s22plus_ramoops_capture_readiness_audit.json
```

Summary:

```json
{
  "result": "pass",
  "agents": false,
  "draft": true,
  "offline_rc": 0,
  "dryrun_rc": 1,
  "failures": []
}
```

Interpretation:

- `agents=false`: active `AGENTS.md` does not contain the live capture
  authorization markers. That is expected; live remains disabled.
- `draft=true`: the inert operations draft contains every marker the capture
  gate requires.
- `offline_rc=0`: all candidate/rollback APs and manifests still verify.
- `dryrun_rc=1`: the capture gate still stops at the policy marker gate before
  Android/device action while the exception is inactive.

## Current State

The stack is ready for policy review, not for live execution. A future live run
still requires explicit operator approval and then copying the reviewed exception
block into `AGENTS.md`. Until that happens, the helper remains fail-closed before
device action.
