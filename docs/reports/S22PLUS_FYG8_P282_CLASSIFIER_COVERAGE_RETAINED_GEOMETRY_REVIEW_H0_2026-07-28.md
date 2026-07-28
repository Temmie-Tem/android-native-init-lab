# S22+ FYG8 P2.82 Classifier Coverage and Retained Geometry Review H0

Date: 2026-07-28 KST

## Verdict

`DESIGN_REVIEW_COMPLETE_P282_COVERAGE_GEOMETRY_GATES_HOST_ONLY`

The P2.82 mechanism remains selected. Three source premises are now explicit:

1. pre-bind DEVICE child runtime suspend is allowed because
   `dwc3_runtime_checks()` rejects only an already connected child;
2. DEVICE suspend executes `dwc3_gadget_suspend()` and `dwc3_core_exit()`,
   while DEVICE resume executes `dwc3_core_init_for_resume()`; and
3. pre-bind `dwc3_gadget_suspend()` returns zero when no gadget driver is
   bound, so the controlled cycle does not tear down an active function.

The design needs no wider mechanism search. It does need stronger
pre-implementation validation wording:

- exact Qualcomm/S22+ end-to-end execution coverage is honestly `0/46`;
- the shared production C classifier must execute all `46/46` C-band
  classifications under a pinned synthetic AArch64 fixture before Full LTO;
- Python/slot/detail validation remains `46/46`, and final-tuple validation
  remains `567/567`;
- the fixed 45-byte A/B record is sufficient because checkpoints replace one
  of two slots in place rather than append one record per stage; and
- final pair instability is already represented by `0xc4b`, with its deadline
  behavior pinned below.

This unit performed no implementation, build, image generation, D0, approval,
device contact, transfer, reboot, or flash. No S22+ F1 live run is authorized.

## Source Confirmation

The exact FYG8 source snapshot is:

```text
/tmp/p280-postlive-phy-20260728/kernel_platform/msm-kernel/
```

The relevant source behavior is:

```text
drivers/usb/dwc3/core.c
  dwc3_runtime_checks()
    DEVICE returns -EBUSY only when dwc->connected is true

  dwc3_suspend_common()
    DEVICE calls dwc3_gadget_suspend()
    DEVICE synchronizes the gadget IRQ
    DEVICE calls dwc3_core_exit()

  dwc3_resume_common()
    DEVICE calls dwc3_core_init_for_resume()
    DEVICE restores PRTCAP_DEVICE
    DEVICE calls dwc3_gadget_resume()

drivers/usb/dwc3/gadget.c
  dwc3_gadget_suspend()
    returns zero immediately when dwc->gadget_driver is absent
```

These facts make the selected pre-bind cycle structurally valid. They do not
prove that the exact FYG8 runtime will produce any one C-band classification;
that remains the purpose of a later attended F1 after implementation and
qualification.

## Coverage Audit

### What existing QEMU execution proves

The existing P2.60 generic-arm64 harness executes:

- configfs mount and exact filesystem-type check;
- generic ACM gadget construction;
- `ttyGS0` creation and pre-bind banner queueing;
- dummy-UDC bind and configured state; and
- exact host-side banner receipt through `ttyACM0`.

The existing P2.80 Kprobe controls execute:

- tracefs mount and filesystem-type check;
- isolated instance and event ownership;
- entry and return Kprobe registration;
- signed `$retval:s32` capture;
- parser nesting and malformed-record fixtures;
- `nmissed=0`; and
- event, instance, and tracefs cleanup.

Those harnesses deliberately do not instantiate the FYG8 DWC3-MSM parent,
child runtime-PM callbacks, femto PHY, Type-C/VBUS path, or physical USB link.

### Exact answer for the 46 C-band details

P2.82 is still design-only. Therefore the current counts are:

```text
exact FYG8 vendor end-to-end C-band paths:      0 / 46
P2.82 production C classifier fixture paths:   0 / 46
descriptor/decoder design entries:             46 / 46
generated final tuple design entries:         567 / 567
```

Calling the existing tracefs QEMU tests `46/46` coverage would be false. They
validate the transport and parser substrate, not the new P2.82 decisions.

This paragraph records the pre-implementation review state. It is superseded
for production-classifier fixture coverage by the later P2.82 implementation:
the shared generated C classifier now passes `46/46`, and all `567/567`
generated tuples round-trip under pinned AArch64 QEMU. FYG8 vendor
end-to-end C-band coverage remains `0/46` until a separately authorized live
run; the host fixture result must not be reported as device coverage.

### Required pre-LTO correction

Implementation must not encode 46 unrelated test-only predicates. One
authoritative descriptor must generate:

1. the runtime detail definitions;
2. the shared production C classification functions;
3. the retained stage/outcome allowlist;
4. the host decoder table; and
5. synthetic observation fixtures.

The runtime and fixture binary must compile the same production C
classification functions. The fixture supplies synthetic observations at the
classifier boundary; it must not add a test mode, injectable branch, or
fixture selector to the candidate runtime.

Before Full LTO, a pinned generic-arm64 execution receipt must prove:

- each of the 46 C-band details is emitted by exactly one intended fixture;
- each emitted detail has the declared stage and outcome;
- every adjacent-boundary mutation either selects the intended neighboring
  detail or is rejected;
- trace loss cannot become a clean negative claim;
- cleanup loss remains fail-closed;
- all 567 final tuples execute through the same C encoder used by the runtime;
  and
- C output round-trips through the Python decoder and compact-slot validator.

The receipt must publish three separate metrics:

```text
vendor_end_to_end_coverage=0/46
production_c_classifier_fixture_coverage=46/46
decoder_detail_coverage=46/46
final_tuple_coverage=567/567
```

The first metric remains zero until live FYG8 evidence exists. Synthetic
coverage must never be presented as device-path coverage.

## Retained Geometry Audit

The active checkpoint carrier is the proven compact layout:

```text
record bytes: 45
header bytes: 25
slot A bytes: 10
slot B bytes: 10
```

At PID1 entry, the kernel places one 45-byte record immediately before the
existing Samsung-log cursor. It does not advance the Samsung ring index.
Every later checkpoint:

1. selects the inactive A/B slot;
2. writes one 10-byte generation/stage/outcome/item/detail/CRC value;
3. commits that slot;
4. flips the active slot; and
5. increments one `u8` generation counter.

It does not allocate or append another 45-byte record. Therefore seven P2.82
stages consume the same 45 retained bytes as one stage. Generation 92 is
within the `u8` contract.

At success, the two slots contain only adjacent generations 91 and 92. At a
failure, they contain the failing generation and its immediately preceding
generation. Earlier generations are intentionally overwritten.

This is compatible with the P2.82 scope freeze:

- P2.82 proves controlled repair sufficiency;
- it does not prove the original natural boot-time drop;
- the earlier "Window I" was deliberately removed; and
- no decision depends on a checkpoint older than the adjacent A/B pair.

The implementation gate must still regenerate a geometry receipt that proves:

- record size remains exactly 45 bytes;
- the Samsung ring index and header identity remain unchanged;
- every P2.82 success and failure stage leaves valid adjacent slots;
- generation never exceeds 92;
- exact run ID, profile, CRC, stage ordinal, and slot parity are enforced;
- a stale record from another run ID is rejected;
- a stale same-family record cannot satisfy the clean baseline; and
- all already-modeled unsaturated cursor boundaries preserve the same
  visibility/refusal behavior.

This closes retained capacity and baseline-contamination risk without adding
a larger carrier.

## Stable Pair Deadline

The existing `0xc4b final-state-speed-unstable` detail is the defined
non-stabilization result. The implementation state machine is sharpened to:

1. poll exact canonical `(state, current_speed)` pairs until the absolute
   configured deadline;
2. terminate early only when two consecutive byte-identical pairs are
   `configured + high-speed`;
3. otherwise continue through the deadline so a late attach is not discarded;
4. at the deadline, emit a generated nonterminal tuple only if the final two
   exact canonical pairs are byte-identical; and
5. emit `0xc4b` when individually canonical pairs continue to differ.

Malformed, unknown, truncated, or unreadable values use the existing exact
read/validation failure path. They do not become `0xc4b`.

This makes every stable-pair outcome deterministic:

```text
stable configured/high-speed before deadline -> tuple progress + terminal
stable non-success pair at deadline           -> tuple failure
canonical pair still changing at deadline     -> 0xc4b failure
malformed or unreadable pair                   -> exact read/validation failure
```

## Printk Carrier Decision

The vendor `pr_info()` and `pr_err()` calls are useful source landmarks, but
they are not a recoverable carrier in the current native-PID1 environment.
P2.76/P2.77 live evidence found:

```text
Failed to get KlogOffset, Not Found
SamsungLogFlush KlogOffset:0x0
```

There was no candidate-kernel printk segment between candidate bootloader
messages and the compact checkpoint. Matching USB/Max77705 text elsewhere in
the retained read was stale Android or bootloader data.

Consequently, adding host-side printk parsing would provide no cross-check.
Making printk recoverable would require a new retained transport, a larger
carrier, or the retired `sec_log_buf` path. That would enlarge the hazard and
retention surface and violate the current scope. P2.82 will instead use:

- shared production C classifier execution for all 46 details;
- the already-proven tracefs/Kprobe lifecycle;
- exact source and linked-symbol contracts; and
- the unchanged 45-byte checkpoint carrier.

## Host Validation

The documentation and existing geometry model pass:

```text
details=46 unique
tuples=567 unique range=0xd00..0xf36
PASS_S22PLUS_FYG8_RETAINED_SNAPSHOT_MODEL_HOST_ONLY proof_size=45
tests.test_device_action_process_v2_docs: 8 passed
git diff --check: passed
```

The retained model confirms that valid magic plus `idx >= 45` exposes one
unchanged-index 45-byte proof across prefix and rotated snapshot branches.
It also confirms that full ring saturation is not required.

## Disposition

The P2.82 mechanism and 46-detail decision table remain frozen. Implementation
may start only after treating these as hard pre-LTO gates:

1. shared production C classifier fixture coverage `46/46`;
2. generated C/Python detail round-trip `46/46`;
3. generated final tuple round-trip `567/567`;
4. fixed 45-byte A/B geometry and contamination receipt;
5. exact stable-pair deadline semantics; and
6. honest `0/46` FYG8 end-to-end coverage before live execution.

No new mechanism search, printk carrier, module, firmware, power write, build,
image, D0, or F1 follows from this review.
