# V2300 Kernel Security Recon: Binder BB-T live preflight

Date: 2026-06-13

Scope: pre-execution safety check for the V2299 Binder BB-T target
reachability helper. This iteration did **not** run the helper, did **not**
create `/dev/binder`, did **not** open Binder, did **not** call Binder ioctl,
did **not** `mmap` Binder, did **not** register a context manager, and did
**not** send any Binder protocol command or transaction.

## Purpose

V2299 implemented a guarded BB-T helper for one future live target-reachability
check. V2300 verifies that the tracked helper, runner, bridge, resident baseline,
and live preconditions are ready before any execution approval is used.

BB-T remains below BB3. It is only a well-formed two-process, zero-object
transaction delivery gate. It is not a malformed-object cleanup path, UAF
trigger, exploit attempt, privilege escalation attempt, or crash test.

## Static checks

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py \
  --out-dir workspace/private/runs/security/v2300-binder-bbt-live-preflight-build-only

file workspace/private/runs/security/v2300-binder-bbt-live-preflight-build-only/a90_binder_target_bbt
sha256sum workspace/private/runs/security/v2300-binder-bbt-live-preflight-build-only/a90_binder_target_bbt
rg -n 'BINDER_SET_CONTEXT_MGR_EXT|BC_TRANSACTION_SG|BC_REPLY|BC_REPLY_SG|BC_FREE_BUFFER|BC_ACQUIRE|BC_RELEASE|BC_INCREFS|BC_DECREFS|BC_REQUEST_DEATH_NOTIFICATION|BC_CLEAR_DEATH_NOTIFICATION|BINDER_TYPE_|flat_binder_object' \
  workspace/public/src/native-init/helpers/a90_binder_target_bbt.c || true
rg -n 'BBT_CONFIRMATION|Stage B-Binder BB-T go|--run-live|devnode-precheck|devnode-create|selftest|0\.9\.268|v2237|BC_FREE_BUFFER|BC_REPLY|BC_TRANSACTION_SG|BINDER_SET_CONTEXT_MGR_EXT|cleanup|fail=0' \
  workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py
git diff --check
```

Results:

| Check | Result |
| --- | --- |
| Python syntax | pass |
| Build-only runner | pass, `run_live=false` |
| Helper type | AArch64, statically linked, stripped |
| Helper SHA256 | `adb23af13836633b13ab3c61ea8d71d2d567d6b95e996aa33105b5658ac4bbda` |
| Helper forbidden-token scan | pass, no matches |
| Runner exact approval gate | present |
| Runner v2237 / `fail=0` preflight gate | present |
| Runner temp-node cleanup path | present |
| `git diff --check` | pass |

The V2300 build-only output is private:

`workspace/private/runs/security/v2300-binder-bbt-live-preflight-build-only/`

No compiled helper is tracked.

## Live preconditions checked

Only the serial bridge and read-only native-init commands were used.

| Check | Result |
| --- | --- |
| Bridge command path | pass |
| Resident version | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Kernel | Samsung stock `4.14.190` lineage reported by `version` |
| `status` selftest summary | `fail=0` |
| `selftest verbose` | `pass=11 warn=1 fail=0` |
| `/dev/binder` pre-existing | no |
| Stale `/cache/bin/a90_binder_target_bbt` | no |
| Stale `/cache/a90-binder-bbt.out` | no |
| `/proc/misc` Binder minors | `binder=81`, `hwbinder=80`, `vndbinder=79` |
| Existing Binder dmesg tail | no current Binder lines in bounded grep |

The `/proc/misc` result confirms the kernel Binder misc devices are registered.
The absent `/dev/binder` result confirms the future runner may safely create a
temporary `/dev/binder` node without deleting a pre-existing legitimate node.

## Safety boundary for the next step

Future live BB-T execution still requires this exact confirmation phrase:

`Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

The future command shape is:

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py \
  --run-live \
  --confirm 'Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry'
```

This approval phrase is for BB-T only. It does not approve BB3, malformed Binder
objects, failed-cleanup triggering, UAF triggering, crash-only testing, heap
spray, privilege escalation, or retries.

## Decision

Classification:

> `binder-bbt-live-preflight-pass-not-run`

V2300 found no pre-execution blocker for a separately approved BB-T live run.
The next action is either to stop here, or to run exactly one BB-T live attempt
using the exact approval phrase above. If BB-T succeeds, BB3 remains separately
blocked and requires a new design/review/approval gate.
