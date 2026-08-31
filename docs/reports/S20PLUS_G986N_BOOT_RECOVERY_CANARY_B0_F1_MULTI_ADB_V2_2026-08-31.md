# S20+ G986N B0 F1 multi-ADB selection v2 review

Date: 2026-08-31

Status: **PASS_GO - EFFECTIVE ONLY AFTER SCOPED COMMIT**

## Trigger and pre-effect result

The operator confirmed that two ADB devices are intentionally attached. The
active v1 owner required the global ADB inventory to contain exactly one row,
so two fresh prepare invocations stopped at their first inventory selection.
They issued only the bounded global `adb devices -l` read. Both allocated run
directories remain empty; the shared guard and global candidate claim are
absent. No serial-selected command, root read, reboot or Download intent, Odin,
candidate/rollback intent, or partition write occurred.

## Revision scope

The v2 owner inventories all ADB rows but selects exactly one row containing
`model:SM_G986N`, then requires state `device` or the branch-specific
`recovery` state plus exact `device:y2q` and `product:y2qksx` metadata. A second
matching model row, selected-serial drift, missing/conflicting exact metadata,
or wrong target state stops. Foreign rows are permitted and never receive a
selected-target command.

Every non-inventory ADB argv remains mechanically fixed to `adb -s <selected
serial> ...`. Root/public-health and recovery transactions repeat global
inventory and require the selected row and complete bounded transaction
inventory to remain unchanged. When the S20+ is in Download, the candidate ADB
baseline may contain foreign rows, but it hashes their sanitized inventory and
requires both the prepared serial and every `model:SM_G986N` row to be absent.
The durable baseline reports `other_target_commands: 0`. Candidate observation
waits through foreign-only inventories and probes only the prepared serial once
the exact S20+ row appears. Every `--execute` invocation also performs a fresh
global inventory after reading or publishing that baseline and immediately
before the global candidate claim. A cut before the claim therefore repeats the
read and cannot reuse stale target-absence evidence.

This revision does not change the candidate, rollback, Odin endpoint binding,
effect order, global candidate claim, no-replay rules, mandatory rollback,
physical fallback, terminal taxonomy, or zero recovery-partition boundary.

## Exact proposed closure

- owner version: `s20plus-g986n-boot-recovery-canary-b0-f1-v2`;
- owner size: `222,832` bytes;
- owner SHA-256:
  `0246014e50b1ff509568ee019f36680694e3a87644ccca8c340767b3dd75445d`;
- owner normalized SHA-256:
  `e2d612fc14549d0b0838ba66473b203126342362480636f3599fd9ea1548ed40`;
- focused test size: `58,443` bytes;
- focused test SHA-256:
  `8a7425b8d63582cda62e55a82c7e2b300990af0fe5809e7e24c5f33f33fb3741`;
- validation: `py_compile`, 54/54 focused tests, and scoped diff checking pass;
- host closure SHA-256:
  `4a28081b9829a8908c079aa110b9e95be20427873367808cd50e81da418502a8`;
- `--validate-host` verdict: `PASS_B0_HOST_CLOSURE_ONLY`,
  `live_authority: false`.

The focused suite adds hostile duplicate-S20, unauthorized exact target,
foreign-row resident health and candidate baseline, malformed sanitized
inventory, foreign-plus-recovery observation, and AST-derived `-s` enforcement
coverage. It also reproduces the first review's stale-baseline cut and proves
that a reappeared selected S20 stops before the global claim. Existing
boot-only, artifact, intent/order, journal, cgroup, fallback, rollback, and
terminal tests remain passing.

## First review correction

The first independent pass returned `NO_GO`, HIGH/MEDIUM/LOW `1/0/0`. It
demonstrated that a cut after durable `candidate-adb-baseline.json` publication
could reuse the old foreign-only receipt without a fresh ADB inventory before
the global candidate claim. A reappeared prepared S20 or second
`model:SM_G986N` row could therefore bypass the intended immediate pre-claim
absence check.

The frozen replacement now executes the bounded global inventory on every
pre-claim `--execute`, whether the durable baseline is new or already present.
The hostile regression starts from a valid old foreign-only receipt, injects a
fresh exact S20 row, and proves the invocation stops with one fresh inventory
and zero global-claim calls. Fresh exact-byte review was still required at that
point.

## Final independent review

Fresh exact-byte review of the corrected complete diff returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0`. It independently reproduced 54/54 tests, the exact
owner/normalized/test identities, host closure, in-memory compilation, and
scoped diff checking. It verified that both new and existing baseline branches
reach fresh inventory immediately before the global claim and that the hostile
stale-baseline regression stops with one inventory and zero claim calls. The
review made no device, ADB, Odin, or USB contact and no edit.

The complete owner, test, target-contract, goal, and this report become
effective only when committed together. Passing review and commit create no
prepared run or candidate approval. A fresh prepare must still bind the exact
current S20+/boot/Download endpoint and stop for its emitted 15-minute exact
approval. S22+, A90, the foreign attached device, and unrelated worktree
changes receive zero commands and no modification.
