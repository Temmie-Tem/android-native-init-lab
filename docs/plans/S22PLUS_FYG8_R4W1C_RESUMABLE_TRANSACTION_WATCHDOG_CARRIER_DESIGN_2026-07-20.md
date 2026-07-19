# S22+ FYG8 R4W1-C Resumable Transaction / Watchdog Carrier Design

Date: 2026-07-20 KST

Status: host-only design. No candidate, live helper, ACTIVE policy, device
contact, or flash authorization exists.

## Objective

Close the R4W1-B proof-pipeline failure without mutating retired evidence, then
prepare a bounded R4W1-C candidate that can both preserve the direct-PID1
exec-accept witness and survive long enough for deterministic attended recovery.

## Non-goals

- No R4W1-B rerun or helper modification.
- No candidate build or transfer in this unit.
- No A/B slot emulation, SQLite database, pstore dependency, USB gadget bring-up,
  Debian handoff, partition expansion, or persistent device write.
- No watchdog disable, broad module replay, or retained-marker cache change.

## Architecture

### 1. Endpoint evidence core

Introduce a target-neutral host module that converts each `odin4 -l` call into
an immutable snapshot:

```text
raw paths -> filesystem existence split -> live paths + stale paths
          -> immutable JSON receipt -> append-only JSONL index
```

Rules:

- nonzero Odin enumeration is fatal;
- stale-only output means no live endpoint and is not fatal;
- more than one live endpoint is ambiguous and fatal;
- one live endpoint yields a generation-bound ticket;
- transfer revalidation requires the same single live path in a fresh snapshot;
- all snapshots are bounded and durably flushed;
- immutable receipts are load-bearing; the JSONL file is a recoverable index.

### 2. Independent deadlines

The next target helper must expose separate bounds:

```text
endpoint_wait_sec      poll until exactly one live endpoint
confirmation_wait_sec full fresh human-confirmation window after discovery
```

Endpoint wait must never subtract from confirmation time. Confirmation remains
fresh TTY input, then a fresh same-generation endpoint snapshot is required
immediately before transfer.

### 3. Forward-only transaction

The consumed state binds one transaction ID, candidate, rollback artifacts,
helper, and run directory. Each phase writes an immutable receipt before moving
forward:

```text
prepared
candidate_transfer_started   <- one-shot consumption point
candidate_transfer_finished
candidate_observation_closed
rollback_endpoint_observed
rollback_confirmed
rollback_transfer_finished
rollback_android_ready
first_rollback_observer_captured
classified
```

Recovery mode reopens the same consumed transaction and appends missing phases.
It must not create an unrelated evidence session. Retry remains limited to the
exact policy-bound rollback rules.

The public `timeline.json` remains the canonical eight-event
`events:[{name,timestamp_utc}]` schema. Internal receipts do not alter that
schema.

### 4. Observer-before-classification

After exact Magisk Android returns, the next helper must capture two bounded,
EOF-complete, byte-identical `/proc/last_kmsg` reads before declaring rollback
health complete. A recovery-resume invocation performs the same observer step.

Classification remains:

- exact marker present with clean family integrity: direct `/init` exec accepted;
- exact marker absent after a complete rollback observer: `NO_PROOF`;
- malformed, foreign, or partial family: integrity failure;
- observer missing: observer-capture failure, never candidate failure.

### 5. Watchdog-managed carrier

Keep the kernel-side R4W1-B witness placement semantics, but replace the raw
544-byte infinite park carrier with the smallest M31B-derived loader that:

1. mounts only the ramdisk-local prerequisites needed by `finit_module()`;
2. loads exactly `smem.ko`, `minidump.ko`, `qcom-scm.ko`,
   `qcom_wdt_core.ko`, and `gh_virt_wdt.ko` in the live-proven order;
3. verifies expected module visibility;
4. performs no USB/configfs, Android handoff, persistent mount, block write, or
   reboot; and
5. enters bounded park after watchdog ownership is established.

This carrier does not strengthen the exec-accept proof. It removes the known
post-exec survival confounder so attended recovery and retained observation are
repeatable.

Converting the vendor watchdog closure to built-ins is deferred. The M31B
userspace loader is already live-proven and has a smaller compatibility delta.

## Rollout

1. Implement and test the endpoint evidence core host-only.
2. Add deterministic fault tests for stale, disappearing, changed, and
   ambiguous endpoints plus interrupted receipt indexing.
3. Independently review the core and this design.
4. Build a new R4W1-C carrier from the M31B closure without changing the kernel
   witness contract.
5. Reproduce candidate artifacts and independently check the final rootfs,
   module closure, kernel marker, rollback artifacts, and policy inactivity.
6. Only then design a new connected read-only gate and separate one-shot live
   exception.

## Stop Conditions

- Any mutation of retired R4W1-B files or states.
- Any endpoint ambiguity at transfer time.
- Any transaction phase without a durable receipt.
- Any observer path that can be skipped by recovery mode.
- Any watchdog closure larger than the exact M31B-proven set without a new
  dependency proof.
- Any request to contact the device before a new exact policy is committed.

## Current Unit Exit

Host-only PASS requires the new endpoint core and focused tests to prove stale
endpoint tolerance, ambiguity rejection, generation revalidation, immutable
receipts, and parseable append-only indexing. It authorizes no device action.
