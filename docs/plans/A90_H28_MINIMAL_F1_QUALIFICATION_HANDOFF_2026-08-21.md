# A90 H28 minimal F1 qualification handoff — 2026-08-21

Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 public-scope independent review
Authority: none; no D0, approval, ordinal, F1, transfer, reboot, or live action

## Review subject

Review the reusable minimal boot-only owner after its one candidate-neutral
scope repair, together with the exact H28 review input at
`docs/reports/A90_H28_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json`.

The repair changes no target, transport, command, partition, retry, journal,
guard, health, or rollback behavior. It replaces the H27-only review-scope
literal with
`A90_MINIMAL_BOOT_ONLY_F1_EXECUTION_AND_CANDIDATE_HAZARD`. The old H27 scope
remains readable only when candidate SHA-256, hazard object, and enable/latch
tuple all equal the exact consumed H27 generation. A non-H27 candidate cannot
use that legacy scope.

The resulting 13-file execution closure is
`0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f`.
Recompute it through `execution_closure_sha256()`; do not accept this declaration
without recomputation.

## Exact H28 claim

H28 is version `0.11.195`, build
`phase3-minimal-h28-stock-rebuild-1007-cfp`, size `58,372,096`, SHA-256
`aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b`.
The A and B host materializations are byte-identical. The public build report
and focused test bind those declarations; the independent reviewer must not
open `workspace/private`.

The bounded experiment asks only whether that exact boot image reaches fresh
H28 Native health. The kernel was rebuilt from A908N OSRC with the published
Snapdragon LLVM 10.0.7 generation and preserves `CONFIG_UH_RKP`,
`CONFIG_RKP_CFP`, `CONFIG_RKP_CFP_JOPP`, and `CONFIG_RKP_CFP_ROPP`. It carries a
non-stock build certificate. Android/vendor external-module compatibility,
stock byte equality, full build reproducibility, and the H27 boot-loop cause
remain unproved.

The starting resident and rollback are both exact V2321 `0.9.285 /
v2321-usb-clean-identity-rodata`. The candidate state paths are the H28-only
`.enable` and `.done` paths in the review input. Candidate replay is forbidden;
ambiguity enters the exact one-shot V2321 rollback path.

## Required checks

1. Read `AGENTS.md`, `A90_TARGET_CONTRACT.md`, and `GOAL_A90.md` in order.
2. Recompute the execution closure and confirm the scope repair does not admit
   a legacy H27 review for any changed candidate, hazard, or fresh-state tuple.
3. Confirm the review parser still binds exact candidate/rollback SHA-256,
   recovery object, hazard object, fresh state, zero findings/contacts, and
   `liveAuthority=false`.
4. Confirm H28 uses only `boot`, one candidate attempt, one V2321 rollback,
   runtime artifact rehash, intent-before-effect, no replay, and bounded final
   Native health.
5. Confirm the hazard statement SHA-256 is over the exact UTF-8 statement bytes
   with no trailing newline.
6. Attack candidate substitution, H27-scope reuse, changed fresh-state paths,
   review substitution, manifest drift, and unknown hazard spelling.
7. Run public focused tests only. Device, `/dev`, USB, network, other targets,
   workspace/private, and repository writes must remain zero.

## Expected review artifact

On `PASS_GO`, publish one canonical JSON at
`docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H28_INDEPENDENT_REVIEW_2026-08-21.json`
using schema `a90-boot-only-f1-minimal-independent-review-v1`. It must carry the
exact generic scope, execution closure, candidate/rollback hashes, recovery,
hazard and fresh-state objects from the input; `findings` must be three empty
lists, every contact counter zero, and `liveAuthority=false`.

Do not create or inspect the private H28 manifest during this review. After a
valid independent artifact exists, the operator-side builder will bind its
path, size, and SHA-256 into one canonical private manifest. That later step
still grants no D0 or F1; a fresh connected D0 and attended approval remain
separate.
