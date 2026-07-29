# S22+ FYG8 P2.86 successor change-closure freeze H0

Date: 2026-07-29 KST

## Verdict

`PASS_P286_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY`

The complete successor candidate change list and the separate stock-D1 runner
repair list are frozen before intent derivation. The candidate inherits all 60
P2.84 SOURCE_KEYS byte-for-byte and permits candidate changes only in 20 new
versioned overlay paths. The D1 repairs are confined to four files under one
private v3 output root. A mechanical ancestor/equality check reports zero
candidate/D1 path overlaps.

This is deliberately not pre-intent readiness. Only this freeze module and
report exist; the other 18 planned overlays are missing. Therefore no P2.86
intent may be derived and no Full-LTO build may begin. If implementation needs
another candidate file or semantic requirement, update and revalidate this
freeze before intent. Any addition after intent invalidates the A/B pair.

This unit is H0 only. It performs no build, image/package creation, device
contact, D0, D1, F1, reboot, transfer, or partition action and grants no live
authority.

## PM-order correction

P2.84 `0xc18` proves the child-suspend pair used `stop_pid` and was nested
strictly between the actual `dwc3_otg_start_peripheral(..., 0)` entry and
return counters. Stock and bare PID1 therefore selected different runtime-PM
paths because their reference and child-count state differed.

Waiting for exact parent `runtime_status=suspended` remains necessary: PM core
publishes that state after the parent callback returns, so it proves
`dwc3_msm_suspend()` returned and released `suspend_resume_mutex`. It is not an
outer-work completion fence. The enclosing `dwc3_otg_sm_work` can still have
requeue bookkeeping and its return tail after parent state publication. The
stock trace's next observed boundary was `0.019 ms` later, which suggests a
large reduction from the callback-body window but does not prove a zero or
bounded bare-PID1 tail.

Accordingly the successor combines the parent-status gate with actual outer
entry/return probes and a closed PERIPHERAL-helper deadline. Parent suspended
removes the callback/mutex portion of the overlap; bounded helper
classification handles the residual tail.

## Frozen candidate-identity requirements

All seven requirements are inside the future SOURCE_KEYS and consume one new
Full-LTO A/B pair only after the pre-intent gate passes:

1. wait for exact parent `runtime_status=suspended` on the existing stop
   deadline after child suspended and before PERIPHERAL;
2. replace blocking post-kill `wait4` with publish-before-reap, `WNOHANG`, an
   auxiliary reap deadline, and explicit unreaped-child classification;
3. add `outer_sm_work_in/out` probes attached to the actual
   `dwc3_otg_sm_work` symbol;
4. distinguish helper dispatch from helper completion;
5. distinguish flush timeout, completed mode write, start-peripheral entry
   without return, and later role/readback failure;
6. retain a bounded classified PERIPHERAL write for the residual
   requeue-and-return tail after parent suspended; and
7. bind every implementation, source contract, selector, intent verifier,
   decoder, builder, packager, linked/static verifier, qualification tool, and
   this freeze document into the identity closure before intent.

No existing P2.84 direct path is a permitted mutation target.

## Planned SOURCE_KEY partition

The frozen inventory is:

```text
inherited P2.84 SOURCE_KEYS       60
  inherited direct paths         55
  inherited generated inputs      5
new P2.86 versioned overlays      20
planned P2.86 SOURCE_KEYS total   80
candidate/D1 path overlaps         0
```

The 20 candidate mutation paths are:

```text
docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md
workspace/public/src/native-init/s22plus_fyg8_p286_classifier.inc.c
workspace/public/src/native-init/s22plus_fyg8_p286_e3_runtime.inc.c
workspace/public/src/scripts/revalidation/build_s22plus_fyg8_p286_candidate.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_boot_only_packager.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build_repro_check.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_intent.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_static_checker.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_contract_spec.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_e1_decoder.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_e2_stock_closure.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_linked_audit.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_pre_lto_qualification.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contracts.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_trace_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_userspace_build.py
```

The freeze gate prints every planned source key and its direct or
`generated://` path:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
```

Implementation and D1 tooling must also pass each actual changed path through
the repeatable `--candidate-changed-path` or `--d1-changed-path` arguments.
The gate rejects an inherited P2.84 candidate path, a public D1 path, an
unlisted path, and any candidate/D1 ancestor overlap.

Before intent, the same command with `--require-pre-intent-ready` must return
zero. Before each Full-LTO build it must be run again and its 80 rows compared
with `git status --short`. After intent, any byte change in those receipts
invalidates the candidate pair.

## Frozen private D1-runner repairs

The D1 list is separate and does not consume a candidate build:

1. parse trace-instance spelling without requiring the absent group prefix;
2. terminate and reap watchdogs immediately on disarm instead of waiting for
   their sleep deadline;
3. write `/proc/self/comm` without embedding a newline in the trace header;
4. remove the endpoint-count predicate that was absent from the approved
   identity contract.

Only these private paths may implement those repairs:

```text
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/device_runner.sh
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/host_runner.sh
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/control_analyzer.py
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/runner_manifest.json
```

The public P2.84 D1 spec and all planned candidate SOURCE_KEY paths are
forbidden D1 repair targets. This separation does not authorize another D1.

## Intent and build stop gate

Intent derivation and Full-LTO are forbidden until all of the following hold:

- all 20 planned overlays exist as bounded regular files;
- the freeze validator reports `pre_intent_ready: true`;
- the successor source contract reports exactly the frozen 80 SOURCE_KEYS;
- current P2.84 receipts still match its frozen intent `60/60`;
- candidate mutation paths are a subset of the 20 overlay paths;
- D1 repair paths remain under the frozen private root with overlap count zero;
- focused semantic/fault-injection tests cover all seven candidate
  requirements; and
- `git status --short` is clean.

After intent, the 80 receipts become immutable. If a verifier, decoder,
builder, packager, report, or runtime file must change, stop and discard both
builds; derive a fresh intent only after updating this pre-intent freeze.

## Static validation

At freeze publication:

- the P2.84 partition is exactly `55 direct + 5 generated = 60`;
- the P2.86 plan is exactly `60 inherited + 20 overlays = 80`;
- all inherited P2.84 direct paths are disjoint from candidate mutations;
- all four D1 files are below the one private root;
- candidate/D1 equality and ancestor overlap count is zero;
- the pre-intent gate correctly reports false with 18 overlays still missing;
- current P2.84 receipts match its frozen intent `60/60`;
- seven focused freeze tests and eight active-contract tests pass;
- Python compilation and `git diff --check` pass; and
- active `AGENTS.md` and `GOAL.md` are 217 and 189 lines respectively.
