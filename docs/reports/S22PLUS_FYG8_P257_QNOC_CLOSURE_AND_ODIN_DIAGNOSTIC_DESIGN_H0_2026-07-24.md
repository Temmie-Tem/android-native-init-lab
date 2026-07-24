# S22+ FYG8 P2.57 QNOC Closure And Odin Diagnostic Design (H0)

Date: 2026-07-24 KST
Tier: H0 host-only
Status: `DESIGN_COMPLETE_IMPLEMENTATION_PENDING`
Device contact: none
Live authority: none

## Decision

P2.57 is two independent implementation units. Unit A is conditional on one
preceding stock D0 measurement:

1. a minimal host-validated reader directly measures the stock target's
   `PART_DISPLAY` state;
2. only a display-enabled result promotes a new versioned E2 source contract
   that adds the one omitted stock `dispcc-waipio.ko` module and three
   display-chain classifier coordinates; and
3. independently, an Odin observer change records a bounded diagnostic receipt
   only when the final P2.55 `observer.evidence()` construction boundary fails.

The qnoc and Odin changes do not depend on each other and must be reviewable,
testable, and revertible independently. Neither is a reason to widen the
candidate into DRM, panel, display userspace, deferred-probe tracing, or USB
gadget work.

This document defines implementation. It does not modify source, build a
kernel, create an image, contact a device, or authorize F1.

## Evidence Boundary

P2.55 retained:

```text
generation 76: stage 0x83, gate item 8, gcc-waipio progress
generation 77: stage 0x84, gate item 9, failure detail 0xa04
detail meaning: qnoc-mc-virt-bind-absent
```

P2.56 established the following exact static chain:

```text
missing dispcc-waipio.ko
  -> /soc/clock-controller@af00000 has no matching provider
  -> strict fw_devlink holds /soc/rsc@af20000
  -> display RSC does not populate its bcm_voter child
  -> the "disp" BCM voter is absent
  -> mc_virt returns -EPROBE_DEFER when that voter is enabled
```

The condition is `socinfo_get_part_info(PART_DISPLAY) == false`. Exact FYG8
source also proves that stock socinfo format 0.14 and later exports:

```text
/sys/devices/soc0/display
/sys/devices/soc0/subset_parts
```

`display` is the raw display-subpart entry. `subset_parts` is the bitmask
consumed by `socinfo_get_part_info()`, where `PART_DISPLAY == 4`.

P2.56 separately showed why the rollback observer lost its inner error:
`enumerate_odin()` converted the final measured-evidence exception to the
generic `measured USB endpoint evidence failed` before
`_snapshot_and_record()` had an `OdinSnapshot` to persist.

## Unit A: Versioned QNOC Display Closure

### A1. Contract identity

Do not edit P2.54 behavior in place. Add a new source contract:

```text
contract id: s22plus-fyg8-p257-e2-qnoc-display-closure-v1
profile:     E2
```

It receives a new run-ID domain, decoder policy identity, candidate intent
schema, preimage schema, and contract schema. P2.45, P2.48, P2.52, and P2.54
generation and decoding must remain byte-exact under their historical
selectors.

The new descriptor is the only authority for the changed module insertion,
stage sequence, classifier priority, and accepted structured details.
Independent handwritten stage ranges, module-count constants, broad
`0xa00..0xaff` acceptance, and duplicate path maps are forbidden.

### A2. Exact module insertion

Start from the P2.54 effective 59-module plan and insert exactly:

```c
{"dispcc-waipio.ko", "dispcc_waipio", ""}
```

between:

```text
icc-rpmh.ko
dispcc-waipio.ko
qnoc-waipio.ko
```

This position is after all four exact ELF hard dependencies
(`clk-qcom.ko`, `debug-regulator.ko`, `gdsc-regulator.ko`, and
`proxy-consumer.ko`) and after the apps RPMh clock/regulator providers used by
the DT path. It does not add any DRM, DSI, panel, SDE, backlight, firmware, or
display userspace module.

The module plan becomes exactly 60 entries:

```text
dispcc module item index = 33, stage = 0x61
qnoc module item index   = 34, stage = 0x62
last module item index   = 59, stage = 0x7b
```

An ordinary module-load failure at item 33 remains an errno-form retained
failure. It must not be collapsed into the later SSUSB classifier.

### A3. Derived stage contract

The eight local steps and 12 gate identities remain unchanged. The additional
module shifts the gate stage values by one while retaining their gate and item
indices:

| Region | P2.54 | P2.57 |
|---|---|---|
| Local steps | unchanged, 8 | unchanged, 8 |
| Module stages | `0x40..0x7a`, 59 | `0x40..0x7b`, 60 |
| Gate stages | `0x7b..0x86`, 12 | `0x7c..0x87`, 12 |
| Terminal | `0x8f`, generation 80 | `0x8f`, generation 81 |

The frontier coordinates become:

| Gate | Gate/item index | Stage | Generation |
|---|---:|---:|---:|
| `gcc-waipio` | 8 | `0x84` | 77 |
| `ssusb` | 9 | `0x85` | 78 |
| `dwc3-core` | 10 | `0x86` | 79 |
| `udc` | 11 | `0x87` | 80 |
| terminal success | 0 | `0x8f` | 81 |

Generation remains `stage ordinal + 1`; it is not derived from the numeric
stage value. Regression/read-error low bytes remain gate indices, and the gate
count remains 12.

### A4. Classifier extension

The SSUSB classifier moves from stage `0x84` to `0x85`. Preserve every existing
P2.52/P2.54 detail value and meaning. Add only these unused values:

| Evaluation priority | Detail | Meaning | Exact path |
|---:|---:|---|---|
| after qnoc aggre1 | `0xa0e` | display clock bind absent | `/sys/bus/platform/drivers/disp_cc-waipio/af00000.clock-controller` |
| next | `0xa0f` | display RSC bind absent | `/sys/bus/platform/drivers/rpmh/af20000.rsc` |
| next | `0xa11` | display BCM voter bind absent | `/sys/bus/platform/drivers/bcm_voter/af20000.rsc:bcm_voter` |
| next | existing `0xa04` | qnoc MC virtual bind absent | `/sys/bus/platform/drivers/qnoc-waipio/soc:interconnect@1` |

The relevant priority prefix is therefore:

```text
0xa01 usb3 GDSC
0xa02 PDC
0xa03 qnoc aggre1
0xa0e display clock
0xa0f display RSC
0xa11 display BCM voter
0xa04 qnoc mc_virt
```

Numeric value does not define evaluation order. The remaining existing bind,
PHY, waiting-state, and grace-exhausted checks retain their relative order.
The classifier has 18 bind descriptors and two state descriptors, for 20 exact
structured values.

Every new path uses the existing no-follow symlink and exact-target-basename
contract. The three new values are accepted only as failure details at P2.57
SSUSB stage `0x85`. All other reserved values remain rejected.

### A5. Source and proof closure

Implementation should add one P2.57 specification, decoder, and source
contract, then connect that contract through the existing build architecture.
The bounded closure is:

- generate the 60-entry plan, 81-step stage table, and 20-detail classifier
  from the P2.57 descriptor;
- register one new source-contract selector without changing historical
  selector behavior;
- add a proof-bound stock-closure entrypoint that derives the effective
  rootfs from the generated 60-entry plan;
- add a P2.57 linked-audit adapter that compares final linked tables against
  P2.57 bytes and preserves the P2.54 CFG dominance proof;
- register the new adapter in reproducibility checking and candidate
  enforcement; and
- refuse P2.57 if any generated plan, linked table, effective rootfs, or
  candidate receipt still reports 59 modules or the P2.54 stage sequence.

Do not copy the complete P2.52 or P2.54 adapter. Extract or parameterize only
the pure render/audit helper needed by both contracts, with tests proving
historical generated bytes are unchanged.

### A6. Static validation gate

Unit A implementation is complete only when H0 proves:

1. P2.45/P2.48/P2.52/P2.54 generated outputs and decoder behavior are
   unchanged.
2. The new plan differs by exactly one module row at the defined position.
3. The exact pinned `dispcc-waipio.ko` is regular, non-empty, uniquely
   materialized, hash-receipted, and present in the effective rootfs.
4. Module count is 60 and no module other than the one insertion changes.
5. The derived sequence has 81 steps and the exact coordinates above.
6. Existing classifier values retain their names and paths; only the three
   exact new values are added.
7. Runtime, checkpoint validator, kernel validator, decoder, and linked audit
   consume the same P2.57 descriptor-derived bytes.
8. Every unlisted reserved detail is rejected at every stage.
9. The kernel patch clean-applies and two static AArch64 userspace links are
   byte-identical.
10. No Full-LTO, image, candidate, manifest, binding, or device action occurs.

## Stock D0 Pivot Before Full-LTO

This is a focused connected read-only measurement, not a change to the
candidate-bound `device_action_d0_v2` result schema.

### Exact reads

After the minimal stock-pivot reader passes H0 and before Unit A
implementation:

1. identify one exact healthy stock FYG8 S22+ target using existing read-only
   target and health checks;
2. read each path twice with a 32-byte bound:

```text
/sys/devices/soc0/display
/sys/devices/soc0/subset_parts
```

3. require byte-identical first/second reads;
4. parse `display` only as exact `0x[0-9a-f]+\n`;
5. parse `subset_parts` only as exact `[0-9a-f]+\n`; and
6. persist target-bound raw evidence only under `workspace/private/`.

These attributes are source-defined mode `0444`; no root-only fallback,
debugfs mount, dmesg scraping, write, reboot, or Download transition is part of
this measurement.

### Decision table

| `display` | `subset_parts & 0x10` | Decision |
|---:|---:|---|
| `0` | `0` | `DISPLAY_ENABLED_VERIFIED`; the disp-voter condition is measured and Unit A may proceed to implementation and final qualification |
| nonzero | set | `NO_DISPLAY_SUBSET_VERIFIED`; stop the dispcc-as-qnoc-fix branch before Full-LTO |
| mismatch | either | `INCONSISTENT`; no inference and no automatic Full-LTO |
| unavailable/malformed/changed | unknown | `INCONCLUSIVE`; no inference and no automatic Full-LTO |

Stock qnoc bind or BCM-voter presence may be captured as supporting topology,
but neither substitutes for these two socinfo values.

This measurement verifies the load-bearing subset condition. It does not by
itself prove that the P2.55 qnoc return was `-EPROBE_DEFER`; that remains a
source-derived causal conclusion until a later candidate observes the
intermediate bind sequence.

## Unit B: Odin Measured-Evidence Diagnostic Receipt

### B1. Preserved behavior

The following behavior is immutable:

- USBFS identity acceptance and transition evidence;
- exact single-arrival retry behavior;
- exact departure opt-in behavior;
- Odin endpoint ticket issuance;
- successful snapshot sequence and endpoint generation;
- candidate and rollback transfer counts;
- Process v2 journal transitions;
- recovery decisions; and
- the fail-closed outer error.

A diagnostic receipt is evidence only. It cannot authorize, accept, retry, or
advance anything.

### B2. Typed membership exception

Add a bounded `UsbfsInventoryMembershipChanged(UsbfsIdentityError)` carrying:

```text
removed: sorted unique tuple of exact USBFS paths
added:   sorted unique tuple of exact USBFS paths
```

Both sets must be disjoint, each path must pass the existing USBFS path
validator, and the combined count must not exceed the existing inventory
bound. `enumeration_evidence()` raises it when before/after path membership
differs and the existing exact-arrival special case has not already applied.

No raw exception string is a receipt field.

### B3. Core failure envelope

When the final `observer.evidence(live_devices)` call fails,
`enumerate_odin()` raises a typed internal subclass of `OdinTransitionError`
whose externally rendered message remains exactly:

```text
measured USB endpoint evidence failed
```

The internal object carries only:

- observation stage `enumeration-evidence-before-snapshot`;
- fixed failure kind;
- allowlisted inner exception class; and
- the bounded membership delta when available.

`OdinEndpointArrivalRace` remains outside this envelope and keeps its existing
bounded retry behavior.

Normalize only the top-level exception received from this exact final call.
Do not inspect `__cause__`, `__context__`, messages, or platform-specific
`errno` values:

| Caught top-level exception | `failure_kind` | `inner_exception_class` |
|---|---|---|
| `UsbfsInventoryMembershipChanged` | `inventory-membership-changed` | `UsbfsInventoryMembershipChanged` |
| any other `UsbfsIdentityError` subclass | `usbfs-identity-failed` | `UsbfsIdentityError` |
| any `OSError` subclass | `direct-io-failed` | `OSError` |

`UsbfsInventoryArrival` is handled before this normalization and therefore
never becomes a diagnostic failure. A production inventory read that has
already wrapped an `OSError` in `UsbfsIdentityError` is honestly classified as
`usbfs-identity-failed`; the design does not reconstruct a discarded cause.
No other exception class is admitted to this diagnostic envelope.

### B4. Receipt schema and storage

`_snapshot_and_record()` catches only the typed measured-evidence envelope,
builds one canonical diagnostic payload, attempts publication exactly once,
and then re-raises that same envelope. It writes:

```json
{
  "schema": "s22plus_odin_diagnostic_failure_v1",
  "ordinal": 0,
  "timestamp_utc": "...",
  "attempted_snapshot_sequence": 78,
  "observation_stage": "enumeration-evidence-before-snapshot",
  "failure_kind": "inventory-membership-changed",
  "inner_exception_class": "UsbfsInventoryMembershipChanged",
  "removed": ["/dev/bus/usb/NNN/NNN"],
  "added": ["/dev/bus/usb/NNN/NNN"],
  "snapshot_persisted": false
}
```

Allowed failure kinds are exactly:

```text
inventory-membership-changed
usbfs-identity-failed
direct-io-failed
```

Allowed `inner_exception_class` values are exactly:

```text
UsbfsInventoryMembershipChanged
UsbfsIdentityError
OSError
```

Non-membership failures have empty `removed` and `added` arrays. Do not retain
raw exception text, stdout, stderr, serials, or USB metadata beyond the bounded
path delta.

The receipt is an exclusive-create, mode `0400`, fsync-sealed JSON file under:

```text
<run_dir>/diagnostics/odin-diagnostic-failure-<ordinal:06d>.json
```

Diagnostic ordinal is independent of attempted snapshot sequence. At most 64
diagnostic receipts may exist in one run directory.

The diagnostics directory is deliberately outside `receipts/` and the
transaction JSONL index. Recovery and successful snapshot reconciliation do
not consume, index, or require diagnostics. A diagnostic parser failure must
not block rollback or final health, and a reporting failure must never cause a
device transition to repeat.

If diagnostic persistence itself fails, its exception is suppressed and must
not replace, visibly chain into, or change the message of the original
`measured USB endpoint evidence failed` envelope. The original envelope wins
and is re-raised without the publication exception as its visible cause or
context. The publication attempt is not retried. It must not retry
enumeration, issue a ticket, increment snapshot sequence/generation, or alter
the durable Process v2 journal.

If a link succeeded but directory fsync or readback verification failed, the
resulting path is unauthoritative evidence. Recovery ignores it exactly like
an absent or malformed diagnostic, and later code must not overwrite or
promote it.

### B5. Static validation gate

Unit B implementation is complete only when focused tests prove:

1. exact removal plus arrival produces one canonical typed delta;
2. immutable same-path replacement remains rejected without reclassification;
3. unrelated or multiple membership changes remain fail-closed;
4. final evidence I/O and validation failures produce the fixed allowlisted
   class/kind with no raw message;
5. the exact top-level normalization table is exhaustive and cause chains do
   not affect classification;
6. a successful diagnostic write is exclusive, sealed, bounded, and durable;
7. create, serialization, write, fsync, link, directory-fsync, and readback
   publication failures each preserve the exact original outer error after
   exactly one publication attempt;
8. failed publication leaves no accepted final receipt, including an
   unauthoritative post-link path;
9. no diagnostic increments snapshot sequence or endpoint generation;
10. no diagnostic creates or validates an endpoint ticket;
11. only the pre-existing exact-arrival path is retried;
12. recovery from durable `ROLLBACK_FLASHED` makes zero candidate or rollback
    transfer calls even with present, absent, or malformed diagnostic files;
13. all existing transition-core, USBFS identity, and F1 runner tests pass;
    and
14. one independent safety review confirms that endpoint acceptance, retry,
    transfer, and recovery semantics are unchanged.

## Display-Clock Safety Review

Before promoting Unit A to a candidate, an independent review must inspect the
exact shipped module and source closure for these concrete effects:

- `disp_cc_waipio_probe()` maps only the display-clock controller resource;
- its two PLL configurations and clock-gating register writes are bounded to
  that controller;
- `qcom_cc_really_probe()` registers the provider without persistent-storage,
  fuse, PMIC, regulator, bootloader, or partition writes;
- the module is not unloaded in the candidate;
- no DRM/panel/display-userspace actor is introduced;
- candidate failure still leaves the attended physical Download recovery path;
  and
- the reboot preceding exact Magisk rollback removes all RAM/MMIO-only clock
  state before Android health is judged.

Stock use of the same module is supporting evidence, not a substitute for this
review, because direct-PID1 load order differs from Android.

## Implementation Order

The work has two independent dependency chains:

```text
minimal stock-pivot reader H0
  -> focused stock D0 PART_DISPLAY measurement
  -> only DISPLAY_ENABLED_VERIFIED permits Unit A implementation

Unit B implementation and static validation
  -> independent execution-critical review
```

Unit B may proceed without waiting for the stock D0. Unit A may not. After
Unit A exists, its display-clock side-effect closure joins the independent
review. Only then may the project run final clean same-path Full-LTO A/B
qualification, linked proof, effective-rootfs closure, deterministic boot-only
packaging, a new connected candidate-bound D0, and a fresh exact F1 approval.

If a later F1 observes all three display-chain binds and still records
`0xa04`, the next unit is probe-internal/deferred qnoc diagnosis. Do not add
that instrumentation preemptively.

## File Closure

Expected pre-pivot H0 addition:

```text
workspace/public/src/scripts/revalidation/s22plus_fyg8_p257_stock_pivot_d0.py
focused parser and read-bound tests
```

Expected Unit A additions or bounded registrations, only after
`DISPLAY_ENABLED_VERIFIED`:

```text
workspace/public/src/scripts/revalidation/s22plus_fyg8_p257_contract_spec.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p257_e1_decoder.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p257_source_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p257_e2_stock_closure.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p257_linked_audit.py
focused tests and bounded selector/build registrations
```

Expected Unit B changes:

```text
workspace/public/src/scripts/revalidation/s22plus_odin_usbfs_identity.py
workspace/public/src/scripts/revalidation/s22plus_odin_transition_core.py
tests/test_s22plus_odin_usbfs_identity.py
tests/test_s22plus_odin_transition_core.py
focused F1 recovery regression tests
```

Do not modify `AGENTS.md`, permanent partition boundaries, F1 approval
semantics, or the canonical timeline schema.

## Independent Design Review

The first execution-critical review returned `NO-GO` for two ambiguities:

1. the diagnostic kind/class mapping did not define how wrapped I/O failures
   were normalized; and
2. a diagnostic publication failure could replace the preserved outer error.

It also warned that the stock discriminator was sequenced after Unit A and
that the diagnostic claim was broader than the actual final-evidence boundary.
The revised design now uses the exact top-level normalization table in B3,
makes the original envelope win after one publication attempt, moves the stock
D0 before Unit A, and limits Unit B to the final
`observer.evidence(live_devices)` call.

The second independent review found no remaining `MUST-FIX` or `WARN` item and
returned `GO` for implementation. This review grants no device or F1
authority.

## Exit State

This design is `DESIGN_COMPLETE_IMPLEMENTATION_PENDING`.

No kernel, userspace binary, image, candidate, manifest, D0 receipt, approval,
or F1 authority exists from this unit.
