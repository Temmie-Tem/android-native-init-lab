# S22+ FYG8 P2.86 successor change-closure freeze H0

Date: 2026-07-29 KST

## Verdict

`PASS_P286_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY`

P2.86 inherits all 60 P2.84 SOURCE_KEYS byte-for-byte. Ten new files that can
affect `boot.img` bytes join the source preimage, producing 70 planned
SOURCE_KEYS. Ten verifier/evidence files that cannot affect those bytes stay
outside SOURCE_KEYS and must instead be bound by the final approval
`bundle.sha256`.

The freeze gate is fail-closed against undeclared tracked changes. It derives
the actual set from committed changes since the reviewed base plus current
tracked/untracked worktree state, then requires exact bidirectional equality
with the declaration frozen in the gate. The old caller-supplied mutation
arguments are removed, so an empty or incomplete CLI declaration cannot hide
a changed file.

This is still not pre-intent readiness. Ten payload sources and eight support
files do not yet exist, so no P2.86 intent or Full-LTO build may begin.
This H0 unit performs no build, package creation, device contact, D0, D1, F1,
reboot, transfer, or partition action and grants no live authority.

## Stage A decision

This unit implements the P2.64 Stage A documentation and change-window gate:

- separate payload identity from non-identity verification/evidence;
- derive tracked mutations from Git instead of trusting caller-supplied path
  lists;
- reject both missing declarations and overdeclarations; and
- keep P2.84 receipts immutable.

P2.64 Stage C, including the wider execution-identity split and independent
execution-critical review, is deferred until after P2.86. It is not a
prerequisite for this successor.

## PM-order correction

P2.84 `0xc18` proves the child-suspend pair used `stop_pid` and was nested
strictly between the actual `dwc3_otg_start_peripheral(..., 0)` entry and
return counters. Stock and bare PID1 therefore selected different runtime-PM
paths because their reference and child-count state differed.

Waiting for exact parent `runtime_status=suspended` remains necessary: PM core
publishes that state after the parent callback returns, so it proves
`dwc3_msm_suspend()` returned and released `suspend_resume_mutex`. It is not an
outer-work completion fence. The enclosing `dwc3_otg_sm_work` can still have
requeue bookkeeping and its return tail after parent state publication.

Accordingly the successor combines the parent-status gate with actual outer
entry/return probes and a closed PERIPHERAL-helper deadline. Parent suspended
removes the callback/mutex portion of the overlap; bounded helper
classification handles the residual tail.

## Frozen candidate requirements

The seven requirements are:

1. wait for exact parent `runtime_status=suspended` on the existing stop
   deadline after child suspended and before PERIPHERAL;
2. replace blocking post-kill `wait4` with publish-before-reap, `WNOHANG`, an
   auxiliary reap deadline, and explicit unreaped-child classification;
3. add `outer_sm_work_in/out` probes attached to actual
   `dwc3_otg_sm_work`;
4. distinguish helper dispatch from helper completion;
5. distinguish flush timeout, completed mode write, start-peripheral entry
   without return, and later role/readback failure;
6. retain a bounded classified PERIPHERAL write for the residual
   requeue-and-return tail after parent suspended; and
7. bind payload-determining inputs in the source preimage and bind
   non-identity verifier/evidence support in `bundle.sha256`.

No existing P2.84 direct path is a permitted mutation target.

## Payload source preimage

The identity partition is:

```text
inherited P2.84 SOURCE_KEYS       60
  inherited direct paths         55
  inherited generated inputs      5
new payload SOURCE_KEYS           10
planned P2.86 SOURCE_KEYS total   70
```

The ten new payload paths are:

```text
workspace/public/src/native-init/s22plus_fyg8_p286_classifier.inc.c
workspace/public/src/native-init/s22plus_fyg8_p286_e3_runtime.inc.c
workspace/public/src/scripts/revalidation/build_s22plus_fyg8_p286_candidate.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_boot_only_packager.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_intent.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_contract_spec.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_trace_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_userspace_build.py
```

These are the only P2.86 additions whose receipts may enter the candidate run
ID preimage.

## Bundle-bound non-identity support

These ten files cannot alter `boot.img` bytes and must not enter SOURCE_KEYS:

```text
docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build_repro_check.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_static_checker.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_e1_decoder.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_e2_stock_closure.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_linked_audit.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_pre_lto_qualification.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contracts.py
```

The selector is deliberately non-identity. A later P2.88 registration must be
able to edit it without changing P2.86's historical run ID or invalidating
P2.86 evidence receipts. The candidate preimage records `source_contract_id`
explicitly, while `p286_source_contract` and `p286_contract_spec` remain
payload-bound and catch a redirected contract implementation.

This follows the P2.82 retirement-guard precedent: a guard or verifier may
remain outside the source preimage while its exact final bytes are still
approval-bound. Fixing one of these files after intent does not invalidate an
otherwise byte-identical A/B pair, but every affected validation must be rerun
and final support bytes must be rebound before approval.

## Git-derived change window

The reviewed base is pinned in the validator with no CLI override:

```text
7929e9f7d7fea1eb99ab43dcd841c5a9c3b6ef94
```

The validator takes the union of:

```text
git diff --name-only -z <base>..HEAD --
git status --porcelain=v1 -z --untracked-files=all
```

It parses rename/copy records without dropping either path. The derived set
must equal the declared set exactly. It then rejects any derived path outside
the frozen payload, support, or Stage A governance sets.

The current Stage A declaration contains exactly:

```text
AGENTS.md
GOAL.md
docs/reports/S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_2026-07-29.md
docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md
tests/test_s22plus_fyg8_p286_change_freeze.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
```

The default command performs the Git derivation; no empty declaration path
exists:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
```

## Frozen private D1 runner

The D1 repair list remains separate from candidate identity:

1. parse trace-instance spelling without requiring the absent group prefix;
2. terminate and reap watchdogs immediately on disarm;
3. write `/proc/self/comm` without embedding a newline; and
4. remove the endpoint-count predicate absent from the approved contract.

Only these private paths may implement the repairs:

```text
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/device_runner.sh
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/host_runner.sh
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/control_analyzer.py
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/runner_manifest.json
```

They are deliberately outside the tracked Git set. Their final runner
manifest and approval bundle must bind their bytes. All payload-source paths
and the public P2.84 D1 spec remain forbidden repair targets. This separation
does not authorize another D1.

## Intent and build stop gate

Intent derivation and Full-LTO are forbidden until all of the following hold:

- all 10 payload sources and all ten bundle-bound support files exist;
- the freeze validator reports `pre_intent_ready: true`;
- the successor source contract reports exactly 70 SOURCE_KEYS;
- current P2.84 receipts still match its frozen intent `60/60`;
- Git-derived and declared tracked change sets match exactly;
- focused semantic/fault-injection tests cover all seven requirements;
- the four D1 repair paths remain private with overlap count zero; and
- `git status --short` is clean at intent derivation.

After intent, the 70 source receipts are immutable. Any payload-source byte
change invalidates the A/B pair. Support-file correction does not change
candidate identity, but it remains blocked from approval until validation and
bundle binding are refreshed.

## Static validation

At publication:

- the P2.84 partition is `55 direct + 5 generated = 60`;
- the P2.86 identity plan is `60 inherited + 10 payload = 70`;
- ten non-identity support paths are disjoint from SOURCE_KEYS;
- candidate and private-D1 ancestor/equality overlap count is zero;
- pre-intent readiness is false with `10 + 8 = 18` files missing;
- the Git derivation test covers committed, dirty, and untracked changes;
- bidirectional tests reject omission, overdeclaration, and an unfrozen path;
- rename parsing retains both source and destination; and
- current P2.84 receipts, focused tests, Python compilation, line limits, and
  `git diff --check` pass.
