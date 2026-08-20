# S20+ G986N N3-U0 attended F1 concrete backend primitives H0

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **H0 PASS_GO - NOT ACTIVE**

## Scope

This unit implements one no-input `FixedBackend` for the reviewed N3-U0
consumer protocol. It binds and calls the exact current Android/Download/Odin/
root helper, N3-U0 USB observer, attended owner artifact definitions, and Odin
classifier. It has no live CLI. The only CLI is `--render-plan`, and
`BACKEND_ACTIVE`, `active`, `live_authority`, and `backend_exposed` are false.
Rendered device-command and partition-transfer lists are empty.

The binding S20+ target contract still defines no N3-U0 F1. This H0 primitive
set grants no prepare, approval, ADB, USB, Odin, reboot, transfer, rollback,
root, physical action, or activation authority.

## Frozen candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_backend_h0.py` | 30,896 | `0d8a752e94ea34f5130a53fe2747c7e949561db54ba661d55c4af2db0a19e27b` |
| `tests/test_s20plus_n3u0_attended_f1_backend_h0.py` | 19,885 | `6514f1040d9d911e248d8a1f6a3b12a6e578aa680a60e94db84d4bf118eb30d2` |

The normalized runner SHA-256 is
`8ac9dcac66196ec7a1585ae6e1e4ba9c2c3ed75f7d573aca0d90049bbb0bc8c6`.
The deterministic backend binding is
`5561aabc35f20752702b8ef12ec6f8d4669bbef8b022ff5557c7925c34b9704b`.
It pins consumer integration binding
`2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6`
and the exact source identities listed by that closure, plus the reviewed owner
source `db1b282e33218ea9f7a48b8b90b28b50a121dab3429b3f642ebf0e90ff940eca`.

All sources are read from bounded `O_NOFOLLOW` descriptors, require one direct
regular link and exact size/SHA-256, and are executed from the already verified
bytes. The bootstrap's inventory, routine, transport, transport raw-capture,
boot verifier, and Odin
classifier dependencies are loaded into a controlled import context; ambient
modules cannot substitute for the bound objects actually retained by the
bootstrap. The unmocked render-plan test loads the real dataclass-based
observer through this path.

## Fixed primitives

`FixedBackend` accepts no constructor path, command, executable, serial,
artifact, endpoint, partition, or shell input. Its operations are:

1. exact healthy Android/root preflight, fixed `get-devpath`, and empty Download
   baseline;
2. current source-identity revalidation, a fresh empty Download baseline, and
   fixed `adb -s <selected> reboot download`;
3. a bounded 180-second empty-to-one Download endpoint observation with stable
   listing and exact bootstrap endpoint identity;
4. candidate or resident rollback boot-only Odin using only the owner model's
   fixed AP path/size/SHA-256 and the endpoint derived from the durable intent;
5. candidate USB baseline before candidate transfer and exact N3-U0 banner
   receipt validation afterward; and
6. bounded resident Android return plus exact Magisk-root proof.

The candidate transfer re-audits the fixed N3-U0 AP and the rollback transfer
re-audits only the fixed resident Magisk AP. Both call the reviewed
`execute_odin_exact()` path, which pins Odin and the AP and revalidates the
endpoint around dispatch. `odin_local_parse_failure` is translated to the
journal's exact `local_parse_failure` token; completed and device-session-
unknown classifications remain distinct.

## Hostile coverage

The focused suite passes **17/17**. It proves:

- every primitive rejects while dormant before a device command;
- the directly callable candidate-observer helper rejects while dormant before
  baseline validation or endpoint open;
- the real render plan loads the exact closure and remains non-authorizing;
- forged ambient classifier, transport, inventory, and routine modules cannot
  replace the verified transitive bootstrap closure;
- preflight binds root, identity, devpath, and empty Download state;
- devpath/identity drift rejects;
- reboot revalidates its exact source boot and uses only the fixed ADB shape;
- Download observation requires one stable listing and matching endpoint;
- candidate transfer uses only the candidate AP and captures one N3 baseline;
- foreign endpoint rejects before observer baseline, AP audit, or Odin;
- rollback transfer uses only the resident AP;
- local-parse classification maps to the journal grammar;
- candidate observation requires a prebound baseline and exact receipt fields;
- final health requires exact root output/type evidence;
- the unimplemented physical-entry bridge performs no command; and
- source drift rejects the binding.

Independent review first rejected ambient substitution of the bootstrap's
transitive imports, then rejected a directly callable candidate-observer helper
that lacked its own dormant gate. The exact controlled-import closure and
helper-first activation check above closed both findings. Fresh exact-byte
review returned `PASS_GO`; the status rotation changes no activation boolean or
live surface.

On 2026-08-20 the shared S22 transport gained a reviewed raw-first capture
dependency. The N3 backend now pins the new transport bytes and exact
`device_action_raw_capture_v1.py` object in the controlled import context. This
is a dependency-only H0 rotation. Fresh independent review confirmed that all
N3-consumed transport definitions are AST-identical across the rotation and
returned `PASS_GO`; no activation surface changed.

The later evidence-execution integration rotation adds a gated actual-command
return collector and a bounded Android-return observation after the exact ACM
banner. This changed execution-critical bytes, so the current candidate is
again `REVIEW_PENDING_NOT_ACTIVE`; earlier `PASS_GO` applies only to the prior
frozen source. No activation surface changed.

A second review found that the first Odin capture wrapper recursively routed
`streaming_command -> _captured_command -> bounded_command -> streaming_command`.
The current wrapper closes over and directly invokes the exact original
streaming implementation, then records its returned bytes. The fake bootstrap
now models the real mutable streaming delegation and rejects recursion.
Fresh exact-byte review returned `PASS_GO` for this inactive rotation.

## Deliberate non-claims and remaining gates

The separate dormant execution join can now pass this backend's command
returns to the evidence owner during H0 tests, but this backend itself still
renders `raw_evidence_durable=false` and `physical_entry_bridge=false`. It is
not a connected executable closure, and candidate observer topology/baseline
remains process memory rather than a restartable effect authority.

A later unit must:

1. complete independent review of the evidence-execution integration;
2. add the attended physical-entry intent/arrival bridge without caller paths
   or generic confirmation input;
3. amend the binding target contract and perform a
   separately reviewed mechanical activation; and
4. only then create a fresh connected prepare/approval.

No device, USB endpoint, ADB, `su`, Odin, network, private run, reboot, or
partition transfer was contacted by this H0 unit.
