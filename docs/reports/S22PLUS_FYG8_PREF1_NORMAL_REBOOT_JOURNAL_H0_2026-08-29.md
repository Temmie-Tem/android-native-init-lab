# S22+ FYG8 pre-F1 normal-reboot journal H0 report

Date: 2026-08-29

Status: **INDEPENDENTLY REVIEWED / PASS_GO / NOT ACTIVE**

## Purpose

The reviewed pre-F1 policy and pure coordinator still had no durable journal or
fixed action descriptor. The first useful integration slice is the least
privileged D1 class already backed by a reviewed implementation: one normal
Android reboot followed by exact-target, changed-boot health.

This unit binds only `normal_android_reboot_health` to the reviewed
`d1-fresh-baseline-3` source and binding. It derives `new_boot_health` in code;
there is no caller-supplied class, proof mode, command, path, or value.

## Implementation

`s22plus_fyg8_pref1_normal_reboot_journal_h0.py` binds these exact inputs:

- coordinator: 23,764 bytes / `c0d56417`;
- D1 V3 source: 73,125 bytes / `cb13236e`;
- reviewed D1 V3 binding: 6,705 bytes / `dcb869ae`; and
- review verdict:
  `PASS_GO_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_H0_CAPABILITY_V1`.

The fixed descriptor is `fe16838a`. It retains only the future invocation
shape and a digest of the exact authority form; it does not publish an approval
token.

The journal has one ordinary exclusive `flock`, one `journal/` directory, and
monotonic six-digit record names. Complete canonical bytes are written to an
unnamed `O_TMPFILE`, file-fsynced, linked once into the final name with
`linkat(AT_EMPTY_PATH)`, then directory-fsynced. Final records are direct
mode-0400, link-count-one regular files. Each record binds the previous record,
its canonical payload, time, kind, and sequence.

Restart reconstruction replays every state transition through the exact bound
coordinator rather than trusting a mutable head. The campaign-open record binds
the complete activation-model value and descriptor digest. The intent record
can only be the fixed D1/new-boot descriptor. A same-boot result rejects before
publication; an uncertain post-intent cut becomes terminal
`UNCERTAIN_CONSUMED_NO_REPLAY`.

## Proportional boundary

This is one class and one journal, not a generic device framework. It adds no
per-command approval ladder, background daemon, database, multi-host lease,
cryptographic signer, or enterprise threat model. The single local `flock`,
atomic no-replace publication, exact input hashes, and restart replay are the
minimum mechanisms required by the reviewed policy's existing single-owner,
intent-before-effect, and no-replay rules.

The CLI accepts only `--self-test`. It has no activation-file loader, target
enumerator, subprocess, ADB, USB, Odin, executor, or live entry point. No
activation manifest exists, no approval was created, and there was no device
contact. The autonomous catalog remains `DEFINED_NOT_ACTIVE`; machine
integration remains blocked by `FRESH_BASELINE_MISSING`.

## Validation

The repaired implementation is 32,123 bytes with SHA-256
`0d13c6216c1c6a11795911daefe53ea35ee803f3e5b718b26e839a99599fedf6`.
The final hostile test module is 17,279 bytes with SHA-256
`e2b8ed12a264232810c122973643c77d42df5c43de023b1b4ce1a5eef36a8857`.

The deterministic self-test output is `4e8a933a`; it reopens the journal four
times and produces exactly:

1. `CAMPAIGN_OPEN`;
2. `EFFECT_INTENT`;
3. `EFFECT_HEALTHY_RETURN`; and
4. `CAMPAIGN_CLOSE`.

Its final phase is `CLOSED`, and its last record is `b6d462e4`. The first
independent review correctly rejected the predecessor because `_read_regular()`
opened a validly named FIFO before checking its type. The repair performs a
direct `lstat` rejection and uses `O_NONBLOCK` on the subsequent no-follow open,
so both a present FIFO and a replacement race fail without waiting.

Hostile tests
cover exact descriptor drift, activation mismatch, proof-mode non-selectability,
same-boot rejection, uncertain-consumed parking, time regression, link failure,
no-clobber, exclusive ownership, symlink/extra-file/mode/gap attacks, strict
JSON, restart reconstruction, and the absent live CLI. Independent changed-
closure review remains required before any activation or executor integration.

The repaired journal suite passes 18/18; the existing policy and coordinator suites pass
20/20; and common Process-v2 passes 142/142. A direct full-tail taxonomy audit
passes with 394 rows and review accounting 65 total / 47 resolved / 18 open.
The isolated worktree does not contain the historical private taxonomy receipt,
so the receipt-dependent 39-test wrapper is reserved for the evidence-bearing
main tree after integration rather than being misreported as a product failure.

Independent read-only review of implementation `70b1157013`, FIFO repair
`61543c98b7`, and report correction `8bfc6b6dab` found no remaining blocker. It
approved only the exact fixed-descriptor journal H0 capability. Activation,
target observation, descriptor execution, and live authority remain separate
unimplemented work.
