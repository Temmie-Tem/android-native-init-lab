# S20+ G986N N3-U0 attended F1 consumer-integration H0 harness

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **H0 PASS_GO - NOT ACTIVE**

## Scope

This unit connects the reviewed dormant N3-U0 journal state transitions to one
closed consumer protocol and proves ordering and effect counts with a fake
backend. It does not implement or expose a live backend. The only CLI is
`--render-plan`; `INTEGRATION_ACTIVE`, `active`, `live_authority`, and
`backend_exposed` are false, while device-command and partition-transfer lists
are empty.

The binding S20+ target contract still defines no N3-U0 F1. This harness grants
no prepare, approval, ADB, USB, Odin, reboot, transfer, rollback, root, or
activation authority.

## Frozen candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_integration_h0.py` | 18,516 | `4b5234f818306ffc8d361ee8b14b15c74702b23b05f752c5acef5171071bc3a0` |
| `tests/test_s20plus_n3u0_attended_f1_integration_h0.py` | 16,146 | `bb212f575b967acea38777e93bcfa8501150f38154d80a45f2562e15a4e442f0` |

The runner normalized SHA-256 is
`efbbc9c0640ffa531ed4c9416c46683904212bde094c1cfbe535a7eebc2560ab`.
The deterministic harness binding is
`2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6`.

It pins:

- journal binding
  `4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945`;
- journal source
  `2c4d7335211ade6c25540782148f44c309da6373d8ad495a5904d43714a01e86`,
  55,803 bytes;
- Android/Download/Odin/root helper
  `11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f`,
  161,259 bytes;
- N3-U0 USB observer
  `f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f`,
  16,713 bytes; and
- Odin classifier
  `4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290`,
  80,851 bytes.

Each source is read through a bounded `O_NOFOLLOW` descriptor, requires one
direct regular link and exact size/SHA-256, and the journal module is executed
from the already validated bytes rather than reopened by path. Any source or
journal-binding drift expires the harness.

## Closed consumer protocol

The protocol accepts only these named operations and typed receipts:

1. exact prepared Android identity plus empty Download baseline;
2. initial or automatic-rollback Download reboot from the identity already in
   the durable intent;
3. exact Download endpoint observation;
4. candidate or resident rollback boot-only transfer to the endpoint already
   in the durable intent;
5. bounded candidate banner/Android observation;
6. attended physical Download entry after its durable intent; and
7. final exact resident Android/root health.

No path, executable, shell fragment, partition name, command, serial, endpoint,
or artifact is accepted from a CLI caller. This candidate nevertheless has no
concrete live backend: the protocol is exercised only by the fake test backend.

## Ordering and hostile coverage

The focused suite passes **16/16**. It proves:

- the inactive gate rejects before any backend read;
- an existing guard blocks a second prepare before preflight;
- initial reboot intent exists before the only reboot call;
- candidate and rollback intents exist and exactly bind the endpoint before
  their only transfer calls;
- the internal rollback helper is itself inactive-gated and derives its backend
  endpoint only from the newly published rollback intent;
- automatic recovery performs one rollback-mode reboot and no physical entry;
- physical recovery performs one attended entry and no rollback-mode reboot;
- candidate-effect failure consumes the candidate intent and never replays;
- foreign Download endpoint rejects before candidate transfer;
- uncertain resident rollback never replays, never reads final health, and
  retains the guard;
- missing guard rejects before any candidate backend read;
- malformed typed backend output leaves the prior intent consumed;
- completed final-health and terminal reporting cuts resume with zero backend
  calls; and
- consumer-source drift rejects the binding.

The complete automatic fake path has exactly one initial Download reboot, one
candidate transfer, one rollback-mode reboot, one resident rollback transfer,
and one final-health read. The physical fake path replaces the rollback-mode
reboot with one baseline read and one attended physical entry.

## Remaining gates

This is not the integrated executable closure. A later unit must:

1. implement one fixed concrete backend from the pinned helper functions;
2. persist bounded raw command output and full transfer/observer receipts in a
   strict atomic journal linked to the state core;
3. make every command-return/publication cut resumable without effect replay,
   including consumed-unproved rollback transfer;
4. test the concrete backend command shapes, artifact paths, endpoint identity,
   source-boot revalidation, timeouts, and output classifiers;
5. obtain independent review of this harness and then the executable closure;
6. amend the binding S20+ target contract; and
7. perform a separately reviewed mechanical activation followed by a fresh
   connected prepare and approval.

No device, USB endpoint, ADB, `su`, Odin, network, private run, reboot, or
partition transfer was contacted by this H0 unit.

## Independent review disposition

The first independent review returned `NO_GO`. It found that the internal
rollback helper omitted its own activation gate and accepted a separate
endpoint argument after publishing the rollback intent. A direct call could
therefore reach a fake backend while dormant, and a mismatched caller endpoint
could differ from the durable intent.

The rotated candidate gates the helper itself, removes the endpoint argument,
and passes only `journal.begin_rollback()`'s returned intent endpoint to the
backend. Hostile tests call the helper directly while dormant and compare the
backend endpoint to the durable rollback intent. Fresh independent review
returned `PASS_GO` for the immediately prior frozen H0 harness. The table above
is the mechanical status/identity rotation that records the verdict. Narrow
post-rotation review exactly reconstructed the prior bytes, confirmed the
current GOAL/plan/report state, and returned `PASS_GO`. It grants no executable
backend or live authority.
