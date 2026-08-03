# A90 unattended resident D1 runner H0 implementation

Status: `H0_IMPLEMENTED_STATIC_PASS_CAPABILITY_REVIEW_PASS_GO`

Date: 2026-08-03

## Outcome

`workspace/public/src/scripts/server-distro/a90_unattended_resident_d1_v1.py`
implements the policy-named `A90_UNATTENDED_RESIDENT_D1_V1` as one transaction
primitive for one ordinal of the already-qualified no-payload
`SWITCHROOT_EXPERIMENT`.

The implementation and review-fix work did not contact a device. A separate
parallel D0 only confirmed the exact A90 resident state; it sent no D1 effect.
This unit created no unattended manifest, live transaction, approval, payload,
partition write, flash, reboot, or recovery action. Independent rereview
produced the canonical reusable capability receipt after the transitive closure
fix.

## Execution shape

The runner has no `--operator-attended`, approval-token, session-resume,
duration, action-budget, or campaign-loop option. Its only live shape is:

```text
current bound attended base manifest and qualification load
-> fresh exact A90 resident D0
-> execution-closure revalidation
-> durable ordinal intent
-> shared handoff/SSH/DRM/return transaction
-> second closure revalidation immediately before dispatch
-> returned/durable outcome equivalence and detailed-result validation
-> one compact durable result
```

It calls the existing `LiveSessionEffects.invoke_action()` implementation for
the actual transition. The existing handoff intent, one-dispatch bound,
ModemManager guard, Debian SSH/display observer, changed USB-epoch return,
exact work cleanup, and final resident-health logic remain shared rather than
being copied into a second backend.

## Presence and isolation

`SessionPreflight` now represents exactly one positive presence proof:

- attended: `operator_attended=true`, unattended qualification false; or
- unattended A90 resident D1: `operator_attended=false`,
  `unattended_resident_d1_qualified=true`.

The attended session engine separately enforces the first form at open,
per-action preflight, postflight, and observer repair. An unattended proof
therefore cannot bypass the attended runner. The unattended CLI contains no
attendance assertion.

The new runner binds only the A90 target profile. It has no S22+ profile,
transport, evidence, or command path.

## Qualification and review binding

Manifest construction requires all of the following:

- a current host-only attended manifest that reopens the canonical
  `PASS_A90_RESIDENT_INSTALLED` journal and exact resident/rollback/rootfs;
- the preserved ordinal-1 intent, observation, action result, engine outcome,
  journal result, and attended operator display observation;
- successful reclassification of that evidence as one handoff, exact automatic
  native return, Debian PID 1, Dropbear SSH, DRM mechanical proof, visible
  `DISPLAY OWNER DEBIAN`, exact cleanup, and final `RESIDENT_HEALTHY`;
- the current common and A90 contracts and policy review;
- the new runner, shared attended transaction, transition contract, and engine;
  the shared backend's remaining eleven transitive source roles for target
  selection, transport, guard, SSH/DRM observation, return, and health; and
- a canonical independent-review JSON receipt whose reviewed source closure
  equals those exact current files and has no unresolved finding. That single
  capability qualification is reusable by every manifest, ordinal, and
  campaign using the unchanged closure; it is not regenerated per run.

The real preserved ordinal-1 evidence passes the new H0 qualification loader:

```text
automatic_native_return_proved=true
debian_pid1_proved=true
dropbear_ssh_proved=true
display_mechanical_proved=true
operator_visibility_proved=true
resident_healthy_proved=true
handoff_dispatch_count=1
action_replay=false
qualification_binding_sha256=d597542cbbe2f5043ac562d3975855a6f693add48afeb604e40d399884a0d8c6
```

The earlier retained-pmsg observer defect remains a warning and cannot erase
the independently preserved exact native-return evidence.

## Failure behavior

- A failed fresh D0 creates no transaction and sends no D1 effect.
- Closure drift after D0 or immediately before dispatch stops before the
  handoff call.
- The current attended base closure must equal every corresponding capability
  source at manifest build, load, and pre-dispatch reload. Any transitive role
  mismatch stops before handoff with dispatch count zero.
- Durable intent is written and fsynced before the shared action backend.
- A transaction directory is exclusive and can never be resumed or replayed.
- An exception or malformed result after durable intent records
  `RECOVERY_PENDING_PARKED`, permits no next ordinal, and never invokes the
  action again.
- A returned engine outcome that differs from its durable JSON, or a malformed
  detailed action result, parks instead of claiming health or experiment
  proof. Dispatch count is exact `0` before the effect, exact `1` with a valid
  detailed result, and unknown only for an already-parked uncertain effect.
- A healthy `PROVED`, `REFUTED`, `NO_PROOF_OBSERVER`, or host-blocked result can
  close the ordinal with `RESIDENT_HEALTHY`; a fresh exact D0 is still required
  before any later ordinal.
- Unattended display visibility remains `unavailable`; mechanical KMS proof is
  observed automatically, while an attended post-action receipt may separately
  bind later physical confirmation.

## Unchanged permanent boundaries

- no host payload transfer or partition write;
- no flash path and no F1 authority;
- no recovery, bootloader, raw-write, userdata, EFS, persist, or security-state
  mutation;
- exact rollback and demonstrated physical recovery remain bound;
- immutable rootfs source remains unchanged; only the existing bound transient
  work copy and exact cleanup are used;
- one durable intent, at most one handoff dispatch, and no automatic replay;
- private run evidence remains below `workspace/private/`; and
- S22+ and every other target remain outside the execution closure.

## Validation

- new unattended runner and adversarial regression: PASS `17/17`;
- existing attended D1 and transition regression: PASS `71/71`;
- related policy, staging, orchestrator, and resident-model regression: PASS
  `195/195` (`283/283` combined);
- real preserved qualification replay: PASS;
- fresh host-only attended base manifest:
  `a90-d1-attended-20260803-04`, mode `0600`, SHA256
  `fcf4d994520742e8d210325b82a9a851f2c09478d74774fc173447b9257da6e2`,
  with no approval receipt, `d1-live`, device effect, or live authority;
- parallel exact-target A90 D0 using fresh base
  `a90-d1-attended-20260803-05`: resident version `0.11.161`, expected build,
  selftest `fail=0`, and source precheck exact; no handoff, `switch_root`,
  payload transfer, partition write, flash, reboot, or S22+ command;
- unattended manifest construction without the canonical independent-review
  receipt: expected fail-closed, with no manifest created;
- touched Python `py_compile`: PASS;
- `git diff --check`: PASS;
- independent execution-machinery rereview: `PASS_GO`, no unresolved finding;
- canonical 18-file capability receipt SHA256:
  `039f3f3d4ce830cf57088af02f254aad5499c05809da02d0e88637188da9a0c0`;
- D0 device contact only; payload transfer, partition write, flash, reboot:
  none.

## Live boundary

The first independent capability review returned `BLOCK_LIVE_USE` with one
High finding: eleven transitive shared-backend sources were absent from the
reusable receipt closure. The runner now directly binds all of them, compares
the attended base closure at build/load/pre-dispatch, and passes role-by-role
mutation plus zero-dispatch regression.

Independent rereview returned `PASS_GO` with no unresolved Critical, High,
Medium, or Low finding. The canonical receipt binds the final 18-file closure
and is reusable across manifests, qualifications, ordinals, and campaigns
until a named execution-critical hash changes or a new hazard/incident occurs.
It permits host-only manifest construction; every live ordinal still starts
with its own fresh exact D0 and retains one-intent/one-dispatch/no-replay and
exact final-health requirements.
