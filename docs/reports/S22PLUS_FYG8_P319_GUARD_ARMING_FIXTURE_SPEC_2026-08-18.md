# S22+ FYG8 P3.19 — shared guard-arming fixture specification (v2)

Status: SPECIFICATION_REVIEW_PENDING
Authority: NO DEVICE OR LIVE AUTHORITY. Host-only test fixture code. Creates no
D0, D1, F1, recovery, replay, device, or live authority. Authorizes no change to
`device_action_cdc_acm_observer_v1.py` and no change to any A90 or S20+ byte.

v1 of this document was rejected by independent review. Two of its load-bearing
claims were false and are corrected below; the rejection is recorded rather than
quietly overwritten.

## What v1 got wrong

**v1 said there were two remaining broken consumers, both fixtures. There are
three, and one is not a fixture and not ours.**
`a90_v3403_f1_orchestrator.py:239-250` still defines
`MODEMMANAGER_GUARD_RECEIPT_KEYS` as the obsolete eight-key frozenset while
importing the migrated observer at `:45`, so `require_exact_modemmanager_guard_receipt`
(`:2658`) rejects every real arm. Eight call sites across six A90 UFS F1 runners,
`a90_resident_promotion_v1.py:1611`, and the orchestrator put that defect on a
live F1 corridor. It is out of scope here and is recorded for the A90 contract;
this specification changes no A90 byte.

**v1 said the correct pattern was already implemented twice, so no design was
needed. That is false for the property that matters.**
`s22plus_fyg8_p318_cdc_acm_positive_control.py:292` and
`s22plus_fyg8_p318_selector_negative_control.py:229` both write
`"output_sha256": hashlib.sha256(guard_payload).hexdigest()` — the in-memory
payload. Neither file calls `read_stdout` at all. The precedents supply the
receipt *shape* only. Only the observer itself (`:757`, `:764`) does the round
trip. Treat both precedents as shipped, not reviewed.

## Scope

Two S22+ fixtures, both building the obsolete eight-key guard with
`"output_sha256": "4" * 64`:

| Consumer | Current failure |
|---|---|
| `s22plus_fyg8_p318_cdc_acm_qemu_guest.py:188-197` (dict built in `persist_session`, rejected later in the forked `child_observe` via `validate_receipt`) | `ObserverError: candidate observer guard semantics mismatch` |
| `s22plus_fyg8_p313_guard_lifetime_fixture.py:89-98` | `FAIL_CLOSED`, `P3.13 lifetime receipts did not reopen` |

## The contract

Two validators, not one. v1 cited only the first.

- `validate_receipt`, `device_action_cdc_acm_observer_v1.py:1405-1459` — nine
  keys `schema, status, spec_sha256, topology_sha256, rule_sha256,
  instance_sha256, output_sha256, raw_capture_receipt, child_alive`;
  `raw_capture_receipt` exactly `{path, size, sha256}`.
- `read_guard_release`, `:1549-1576` — `current_arm_keys` re-validates the same
  nine keys on the release path and additionally requires
  `value["instance_sha256"] == arm["instance_sha256"]`. It does **not** re-check
  the raw binding. This is the path the P3.13 fixture actually dies on.

Four bindings at `:1451-1459`, all required:

1. `arm_raw_path.parent.parent == path.parent` — receipt must sit at
   `run_dir/<one-subdir>/<receipt>`. `prepare_capture_dir(run_dir, name)` yields it.
2. `size` = byte length of the **receipt file** (`guard-arm.capture.json`).
3. `sha256` = digest of the **receipt file bytes**.
4. `output_sha256` = digest of **`read_stdout(handle, maximum=16*1024)`**, the
   stdout stream file.

2/3 and 4 digest different objects. That is the likeliest implementation error.

`topology_sha256` digests `TOPOLOGY_RE.fullmatch(topology).group(1)` (the bus-port
group, `"1-1"`), not the full `"usb:1-1"` string. See `:58` and `:1241-1243`.

## What a fixture may claim

- **(A) Raw-first evidence.** Bytes persisted through
  `device_action_raw_capture_v1` before parse, under its `O_EXCL`, mode `0400`,
  `fsync`, single-link guarantees, with `output_sha256` derived by reading them
  back through the handle. **Required in full.**
- **(B) Guard efficacy.** The arming really inhibited root udev/ModemManager.
  **Impossible in a fixture** and must never be implied.

Publishing an explicitly synthetic payload through the real writer is honest;
asserting `"4" * 64`, which no bytes produced, is not.

**The label must be enforced, not merely written.** v1 asked for the fixture name
inside the payload bytes; that is evidence hygiene, not enforcement. The real
enforcement already exists at
`tests/test_s22plus_fyg8_p318_cdc_acm_qemu_e2e.py:56`,
`assertFalse(value["scope"]["actual_root_udev_guard"])`. Every consumer of the
helper must carry an equivalent machine-checked `actual_root_udev_guard: False`
marker. The P3.13 fixture has none today and must gain one.

Note the QEMU guard was never real, before or after the migration:
`s22plus_fyg8_p318_cdc_acm_qemu_guest.py:34-42` `HealthyFixtureGuard` returns
`True` unconditionally. Restoring (A) does not weaken what the control proves; it
restores it at a higher standard than `"4" * 64`.

**Forbidden:** relaxing `current_guard_keys` or `current_arm_keys`, re-admitting
the eight-key shape, or adding any fixture bypass to the observer. The observer is
correct; the fixtures are wrong.

## Required implementation

One shared helper,
`workspace/public/src/scripts/revalidation/device_action_cdc_acm_guard_fixture_v1.py`,
sibling of the observer.

```python
def arm_fixture_guard(
    observer, run_dir, spec, topology, *,
    label,                      # names the fixture inside the payload bytes
    instance_sha256="5" * 64,   # constant on purpose: release-path continuity
    capture_name="raw-cdc-guard",
    arm_name="guard-arm",       # MUST be caller-varyable; see O_EXCL below
) -> tuple[dict, object]:
    """Publish a real raw capture and return (guard_value, guard_handle)."""
```

- `payload = f"{label} fixture guard armed\n".encode("ascii")`.
- `prepare_capture_dir(run_dir, capture_name)`, then
  `publish_captured_bytes(capture_dir, arm_name, stdout=payload)`.
- `output_sha256` from `raw_capture.read_stdout(handle, maximum=16*1024)`, **not**
  from the in-memory `payload`. This is the one place the precedents are wrong; do
  not copy them.
- `topology_sha256` from the bus-port group; `rule_sha256` from
  `observer._guard_rule(spec, topology)`.
- Nine keys, no others.
- `instance_sha256` stays a constant. `read_guard_release:1576` requires arm and
  release to match, and P3.13 embeds the fixture's `audit()` return into a
  byte-pinned intent, so a derived or random value would break both.

### Known collision

`s22plus_fyg8_p313_guard_lifetime_fixture.py:176,181` constructs `_Guard()` twice
(`arm_receipt`, then `release()`). A second
`publish_captured_bytes(dir, "guard-arm", …)` raises
`RawCaptureError: raw capture receipt already exists` under `O_EXCL`. Either
restructure so one `_Guard` instance serves both, or vary `arm_name`. Decide
explicitly; do not discover it at runtime.

### Also required, and missed by v1

- `s22plus_fyg8_p313_guard_lifetime_fixture.py:136-148` — `_v2_default_fixture`
  *asserts* the eight-key set. It is a validator, not a builder, so "delete the
  inline dicts" does not cover it. It fires the moment `_Guard` emits nine keys.
- QEMU staging is three edits, not one: add the helper to `SOURCE_PATHS`, add an
  explicit `write_snapshot(rootfs / <helper>, source_data[<key>])` beside
  `s22plus_fyg8_p318_cdc_acm_qemu_e2e.py:1007-1011`, and add it to the
  `source_copies` verification map at `:2201-2204`, which today lists only
  `guest` and `observer` and would not notice a missing helper.
- `s22plus_fyg8_p313_overlay_contract.py:43-69` `SOURCE_PATHS` must pin the
  helper, or it becomes unpinned executed source.

## Two decisions required before implementation

These are not edits and are not mine to make.

**Decision 1 — P3.13 overlay intent.** The migration already invalidated it,
independently of the fixture. Measured:

| pinned in `workspace/private/outputs/s22plus_fyg8_p313/intent/overlay-intent.json` | current |
|---|---|
| `process_v2_cdc_observer` 51508 / `764d9852` | 58773 / `a1fa4dc1` |
| `process_v2_live_adapter` 132460 / `cc71ca88` | (differs) |
| `p313_guard_lifetime_fixture` 8525 / `500a70f6` | changes when repaired |

Repairing the fixture moves the failure to `"P3.13 overlay intent content
differs"`, not to green. Regenerating the intent re-pins post-migration bytes into
a closed campaign whose intent sha is published as a closure fact in
`docs/reports/S22PLUS_FYG8_P313_POST_BIND_RESUME_CYCLE_DESIGN_H0_2026-08-10.md:686`.
Choose: regenerate and record as an expected invalidation per the P3.16 precedent,
or leave P3.13 red and documented.

**Decision 2 — QEMU preserved output.** The e2e test does not fail on guard
semantics today. It fails at `s22plus_fyg8_p318_cdc_acm_qemu_e2e.py:2042-2043`,
`ControlError: preserved source receipts absent`, because the preserved
2026-08-15 output predates `raw_capture` joining `SOURCE_PATHS` — it never reaches
the guest. Adding the helper to `SOURCE_PATHS` makes that fire harder. The entry
can only leave the expected-failure manifest after the control is re-run **into**
`workspace/private/outputs/s22plus_fyg8_p318_cdc_acm_qemu_e2e`, overwriting the
artifact `d7e4b0e6fa` deliberately preserved. Choose: regenerate it, or keep the
manifest entry with a corrected reason string.

The manifest's current reason at
`s22plus_fyg8_consumed_suite_expected_failures.py:55-60` says the control fails on
guard semantics. That is wrong today and must be corrected regardless of which
choice is made.

## Acceptance criteria

1. `s22plus_fyg8_p313_guard_lifetime_fixture.py` run standalone exits 0 with
   `PASS_P313_GUARD_LIFETIME_AND_V2_COMPATIBILITY_HOST_ONLY`.
2. `tests/test_s22plus_fyg8_p313_process_v2.py` imports and runs with no zero-test
   collection error. **Blocked by Decision 1.**
3. The QEMU control reaches `observer=PASS classification=accepted` at 49 bytes and
   prints its terminal `result=PASS`.
4. **Round-trip discriminator.** A test in which the published stdout bytes and the
   in-memory payload differ must show the helper produced the *published* digest.
   Achieve it by reading the handle after publication and asserting
   `guard["output_sha256"] == sha256(read_stdout(handle))` **and** that the helper
   never receives the payload for digesting. v1's "mutate the file and expect
   rejection" is not a discriminator: both implementations pass untampered and both
   fail tampered, and mode `0400` with `nlink == 1` means a naive mutation trips
   `RawCaptureError` and surfaces as `"guard raw receipt is invalid"`, a different
   branch.
5. Assert `raw_capture_receipt["sha256"] != guard["output_sha256"]` for a non-empty
   payload, proving receipt-file and payload digests are distinct objects.
6. A receipt written directly into `run_dir` is rejected with
   `candidate observer guard raw binding differs`.
7. Assert `topology_sha256 == sha256(TOPOLOGY_RE.fullmatch(topology).group(1).encode())`.
   Nothing else in these criteria would catch the full-string error.
8. Every consumer of the helper carries a machine-checked
   `actual_root_udev_guard: False`, including P3.13.
9. Single definition **within the change set**: no remaining `"4" * 64` guard
   `output_sha256` in the two target fixtures, and no new inline nine-key dict.
   This is deliberately not tree-wide: `tests/test_device_action_f1_live_v2.py:108-129`
   and the two migrated controls also build guards inline and are out of scope.
10. Expected-failure manifest: correct the QEMU reason string; remove the entry only
    per Decision 2. Do not cite "0 unaccounted, 0 stale" as evidence the P3.13
    repair worked — `DEFAULT_PATTERN = "*p318*"` cannot see P3.13.
11. No source change to `device_action_cdc_acm_observer_v1.py`, and no A90 or S20+
    byte changed.

## Authority boundary

Host-only. No device, ADB, USB, Odin, transfer, recovery, replay, live authority,
A90, or S20+ action is authorized or implied. Physical ACM remains 0/16; until
criterion 3 holds, the ACM evidence channel stays supplemental and must not gate
any campaign result.
