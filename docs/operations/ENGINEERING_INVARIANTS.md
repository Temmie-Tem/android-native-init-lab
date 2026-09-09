# Cross-target engineering invariants

Adopted: `2026-09-09`. These are the build, addressing and record-keeping
practices this repository holds across every target. They were carried in
`README.ko.md` and had no authoritative home; this document is that home, and
the README now links here instead of restating them.

This document defines engineering practice only. It authorizes no device
action, no replay, no resident installation, no rollback-destination change and
no new execution path. [`AGENTS.md`](../../AGENTS.md) and its
[device details](DEVICE_ACTION_CONTRACT_DETAILS.md) remain the binding safety
contract, and where a target contract is stricter, the target contract governs.

Permanent device safety boundaries — no writes to `/efs`, modem, RPMB,
keymaster, keystore or bootloader-class partitions, and the rest of that list —
live in the contract, not here. Nothing below relaxes them.

## 1. Every target keeps a known-good image and a verified recovery path

A target is only worked on while a known-good boot image and a recovery path
that has actually been exercised are both retained for it. The recovery path is
verified, not assumed: it must have been used, or checked, on that target.

**Why:** an experiment that cannot be undone is not an experiment. This is what
makes a failed candidate a recoverable event rather than a dead device.

## 2. Isolate the variable when the run has to attribute a cause

When a run exists to establish *why* something happens, hold everything else
constant and change one requested variable.

**Scope.** This is a causal-attribution principle, not a size limit on bounded
units. A unit may legitimately bundle a coherent capability — P375 qualified a
root command console, and P376 added a HUD child beside it in one candidate —
because those runs were establishing that a capability works, not why an effect
occurs. The principle binds when the question is causal.

**It is also a target, not a guarantee.** P357 and P358 differ in one requested
variable, the buffer attribute, but that single flag moves the cache attribute
and the early DMA-map path together. When a change cannot be cleanly isolated,
record that it was not, rather than reporting the comparison as if it had been.

## 3. Record the provenance of every new boot image

A new boot image is recorded with its version, its source path, its SHA-256, and
what was observed when it ran on the device.

**Why:** an image whose inputs are not recorded cannot be rebuilt, compared, or
ruled out later. The hash is what makes a later claim about "the same build"
checkable instead of remembered.

## 4. Address partitions by name, never by major/minor

Partitions are identified by name and through `/sys/class/block/<name>/dev`.
Major/minor numbers are never hardcoded.

**Why:** major/minor assignments are not stable across kernels, boots or
targets. A hardcoded pair silently addresses the wrong block device instead of
failing, which is the worst available failure mode for a write path.

## 5. Raw evidence stays private; only redacted summaries are published

Raw logs and experiment artifacts stay under `workspace/private/`. Only
redacted, publishable summaries go to `docs/reports/`, `docs/artifacts/` and
`workspace/public/`.

**Why:** raw capture carries device identifiers and host detail that the public
tree must not hold. The identifier boundary itself is defined in the
[public tree sanitization policy](PUBLIC_TREE_SANITIZATION_POLICY.md) and is
checked on every push by the `Repository boundary` workflow.

## Related

- [`AGENTS.md`](../../AGENTS.md) — binding safety contract and absolute boundaries
- [Device action contract details](DEVICE_ACTION_CONTRACT_DETAILS.md) — permanent device safety boundaries
- [Device action risk tiers](DEVICE_ACTION_RISK_TIERS.md) — proportional validation by action
- [Public tree sanitization policy](PUBLIC_TREE_SANITIZATION_POLICY.md) — identifier boundary and the boundary check
- [A90 development loop standard](DEVELOPMENT_LOOP_STANDARD.md) — the A90-specific loop, which these invariants sit under rather than replace
