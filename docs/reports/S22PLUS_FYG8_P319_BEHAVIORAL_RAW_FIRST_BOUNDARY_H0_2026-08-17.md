# S22+ FYG8 P3.19 behavioral raw-first boundary H0

Date: 2026-08-17 KST
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only. A90 and S20+
inputs, authority, endpoints, artifacts, and device actions are out of scope.
Status: **IMPLEMENTED_REVIEW_PENDING; H0 ONLY; NO DEVICE OR LIVE AUTHORITY**

## Result first

Commit `c41fd1ddf7` installed the raw-first observer boundary and a source
auditor. The auditor's enforcement was keyed on the literal substring `d0`
in a filename, so it did not cover the source whose loss motivated the
boundary and could not stop a successor.

Demonstrated against the shipped auditor, with a synthetic observer that parses
`result.stdout` before persisting raw:

| Injected source name | `c41fd1ddf7` | this unit |
|---|---|---|
| `s22plus_fyg8_p319_max77705_control1_stage_b.py` | PASS | **REJECTED** |
| `s22plus_fyg8_p320_mux_read.py` | PASS | **REJECTED** |
| `max77705_stage_b_probe.py` | PASS | **REJECTED** |
| `totally_unrelated_name.py` | PASS | **REJECTED** |
| `s22plus_fyg8_p320_mux_d0_read.py` | REJECTED | REJECTED |

The P3.19 Stage A observer is `s22plus_fyg8_p319_max77705_attribute_stage_a.py`.
It contains no `d0`, so neither `_candidate_d0_sources` nor `OBSERVER_FILE_RE`
matched it. It was covered only because a person hand-listed it in
`ACTIVE_FILES`. A successor named `..._stage_b.py` would have been outside
every enforcement path.

## What replaced the filename rule

`_device_acquisition_sources` now enforces the boundary by behavior:

1. a cheap identifier-boundary transport match, then
2. the existing AST acquisition test, then
3. either active-and-raw-first, or explicitly frozen pre-boundary, or reject.

Transport detection uses identifier boundaries rather than quoted literals,
because a real observer passes the transport in as a variable far more often
than as the bare string. `(?<![A-Za-z0-9])adb(?![A-Za-z0-9])` matches `adb`,
`adb_path`, `ADB`, and `/platform-tools/adb`, and does not match `readback`.
The earlier quoted-literal marker set missed the synthetic observer entirely.

Populations under the current tree:

| Set | Count |
|---|---:|
| revalidation `*.py` scanned | 1,718 |
| acquiring **and** device-facing | 177 + 15 active |
| S22+-scoped, byte-frozen | 127 |
| other-target, membership-only | 50 |

Ordering matters for cost as well as meaning: the substring test runs before the
AST parse, which keeps a full audit at about 7 seconds instead of parsing all
1,718 files.

## Target isolation

Membership is checked for every target so a new acquiring source always stops
the audit. Only S22+-scoped bytes are frozen. A90 and S20+ sources appear in the
membership set but not in the byte-frozen inventory, so an ordinary edit on
either parallel target does not fail this S22+ contract. Regression tests pin
both directions:

- `a90_repl_resident_session.py` and `s20plus_g986n_d0_inventory.py` accept a
  harmless edit;
- `s22plus_p0_recon_collect.py` rejects one;
- a new `build_*` source that runs `gcc` and parses stdout is not treated as a
  device observer.

## Stated limit

One residual hole is accepted deliberately. Other-target members are held by
name only, so deleting such a file is invisible to this audit and its name stays
pre-authorized; a new unmigrated observer created under exactly that recycled
name would pass. Closing it would require freezing A90 and S20+ bytes here,
which is the cross-target coupling this unit exists to avoid. S22+-scoped
members are byte-frozen, so their deletion or edit does stop the audit.

## Correction to an earlier objection

An earlier review of `c41fd1ddf7` asserted that the fail-closed
`s22plus_fyg8_p318_baseline_rotation_d1.py` blocked the next D0, on the evidence
that it is the only `*rotation*` adapter in the tree. That conclusion was wrong.

The campaign ledger records `2026-08-16T07:24:34Z | s22plus-fyg8-p318 |
baseline-rotation-1 | D1 | NORMAL_REBOOT_BASELINE_ROTATION | HEALTHY`, and the
run directory and its mode-0400 arm are present. That adapter is consumed and
cannot be replayed. The ledger further shows one fresh wrapper per campaign
(P2.96, P2.98, P3.00, P3.01, P3.03 twice, P3.04 through P3.08, P3.10, P3.12
through P3.16, P3.18); the reusable primitive is the private P2.96 base, not the
public wrapper. Its twelve failing tests are designed rejects, not a blocker.

## Proven forward defect for the next rotation wrapper

The observation underneath that objection does survive, in a different form.
`_load_base` injects a stub for `device_action_f1_v2` and execs the pinned D0
bytes, but does not make `device_action_raw_capture_v1` importable. The migrated
`device_action_d0_v2.py` imports it at module scope (line 23). Reproducing the
exact injection sequence against the current bytes gives:

```
ModuleNotFoundError: No module named 'device_action_raw_capture_v1'
```

So the next campaign's rotation wrapper must pin and inject the raw-capture
source alongside the D0 runtime. A hash bump alone will not work. This is a
forward design boundary; it reclassifies no historical campaign and creates no
authority.

## Consumed-suite expected failures

`c41fd1ddf7` left the P3.18 discovery set permanently red and recorded the count
only in its commit message. A future "P3.18 N/N" report would lose meaning and a
new regression would hide inside the designed rejects.

`s22plus_fyg8_consumed_suite_expected_failures.py` freezes the expected set by
exact test identity and stated reason, and fails closed in both directions: an
unexpected failure is a regression, and an expected failure that starts passing
must leave the manifest. Current state:

- tests run: 209;
- distinct expected failures: 20;
- unaccounted failures: 0;
- stale manifest entries: 0.

The 21 raw `FAIL`/`ERROR` lines collapse to 20 identities because two subTest
parameters of one method fail; identities collapse to the owning test method so
a new parameter cannot look unaccounted.

Reasons, all four designed:

| Reason | Count |
|---|---:|
| consumed P3.18 D1 rotation adapter pins the pre-migration D0 runtime | 12 |
| consumed P3.18 post-rollback finalizer and close audit pin the pre-migration D0 adapter | 6 |
| documentation pins `D0_STOP_VERSION` v1; the migration deliberately bumped it to v2 | 1 |
| P3.18 QEMU control preserved the pre-migration observer bytes | 1 |

The `D0_STOP_VERSION` entry was checked rather than assumed: the constant went
from `device-action-d0-stop-v1` to `device-action-d0-stop-v2`, and the migrated
adapter added a version equality check. The bump is correct; the documentation
pin is the stale side.

## Blocked: the ACM channel has no current positive control

`device_action_cdc_acm_observer_v1.py` is a common forward primitive and was
rewritten by the migration. Its only qualification was the host-only QEMU
control `PASS_GO_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0_CAPABILITY_V1`
(2026-08-15T09:15:50Z), which preserved the pre-migration observer bytes and now
stops with `preserved source differs: observer`. Physical ACM remains 0/16, so
the migrated observer currently has no positive control at all.

Three fresh control runs first stopped before QEMU with
`bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` and
`ControlError: QEMU sandbox root did not become ready`, under
`kernel.apparmor_restrict_unprivileged_userns = 1`. Host load was ruled out by
retrying at load average 0.26. The operator then lifted that restriction, which
let the control run for the first time since the migration. The historical
2026-08-15 output directory was never modified; every run wrote to a separate
path.

What the control then found is worse than a stale pin, and is the real state of
this channel. The guest boots, loads all nine USB and ACM kernel modules `PASS`,
writes the 49-byte pre-bind banner, and reaches `dummy-configured`. The migrated
observer then fails, in three distinct ways found in sequence:

1. `P318_QEMU result=FAIL error=ModuleNotFoundError` — the observer now imports
   `device_action_raw_capture_v1` at module scope, and the control shipped only
   six sources into the rootfs. The dependency was not among them.
2. After shipping it, still `ModuleNotFoundError` — `init` runs the interpreter
   with `-I`, which implies `-P`, so the rootfs root is absent from `sys.path`.
   The guest loads the observer by absolute path, but the observer's own import
   resolves through `sys.path`.
3. After making that one import resolvable:
   `error=ObserverError detail=candidate observer guard semantics mismatch`.

The third failure is semantic, not plumbing. The migration added a
`raw_capture_receipt` key to the required guard-receipt key set and redefined
`output_sha256` as the digest of really captured bytes:

```python
current_guard_keys = {..., "raw_capture_receipt", "child_alive"}
...
hashlib.sha256(arm_payload).hexdigest() != guard["output_sha256"]
```

The control's guest fixture still builds an eight-key guard with a synthetic
`output_sha256 = "4" * 64`, so the observer correctly rejects it.

So the migrated common CDC-ACM observer has no passing positive control, and the
reason is a real interface change, not an environment problem. Physical ACM
remains 0/16.

This unit repaired the two plumbing failures and deliberately stopped at the
third. Shipping the pinned dependency and making exactly one import resolvable
are forced, with no semantic choice in them. Re-deriving the fixture's guard
arming is a different kind of change: a positive control earns its value by being
able to fail, and hand-fitting the fixture until the observer passes would
produce green by construction rather than by evidence. That redesign should be
specified and independently reviewed, not tuned by whoever wants the control to
pass.

Until it passes, the ACM channel must stay supplemental and must not gate any
campaign result.

Reproduce with:

```
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_cdc_acm_qemu_e2e.py \
  --output workspace/private/outputs/s22plus_fyg8_p319_cdc_acm_qemu_e2e_rawfirst
```

The guest now also prints `detail=` alongside the exception type. Without it the
guard mismatch was indistinguishable from a missing guest module, which cost a
full control cycle to separate.

## Four consumers, one cause

This section first said three. That was an undercount. The fourth was found by a
machine sweep of the two migrated interfaces, not by eye, which is the only
reason the count can now be stated at all. No consumer was updated with the
migration:

| Consumer | Failure |
|---|---|
| `s22plus_fyg8_p318_baseline_rotation_d1.py::_load_base` | `ModuleNotFoundError: No module named 'device_action_raw_capture_v1'` |
| `s22plus_fyg8_p318_cdc_acm_qemu_e2e.py` rootfs and `-I` guest | same import, twice, for two different reasons |
| the same control's guard fixture | `candidate observer guard semantics mismatch` |
| `s22plus_fyg8_p313_guard_lifetime_fixture.py` | `FAIL_CLOSED`, `P3.13 lifetime receipts did not reopen` |

The fourth is the third's defect in a different campaign. Lines 89-98 of
`s22plus_fyg8_p313_guard_lifetime_fixture.py` build the same eight-key guard
(`schema`, `status`, `spec_sha256`, `topology_sha256`, `rule_sha256`,
`instance_sha256`, `output_sha256`, `child_alive`) with
`"output_sha256": "4" * 64` and no `raw_capture_receipt`, and line 169 persists
it as `candidate-observer-guard.json`.

Its cause is proved by substitution, not inferred. With only
`device_action_cdc_acm_observer_v1.py` replaced by its `c41fd1ddf7^` bytes and
the rest of the tree unchanged, the fixture returns
`PASS_P313_GUARD_LIFETIME_AND_V2_COMPATIBILITY_HOST_ONLY`. With the current
observer it returns `FAIL_CLOSED` and exits 1. The file was restored and its
digest reverified afterwards.

The count is bounded rather than asserted, and a reviewer can recheck the bound.
The sweep enumerated both migrated interfaces: the sources importing
`device_action_raw_capture_v1`, and the sources that build or validate the
observer's guard receipt. Every guard consumer was then executed.
`s22plus_fyg8_p318_cdc_acm_positive_control.py` and
`s22plus_fyg8_p318_selector_negative_control.py` already carry
`raw_capture_receipt` and both still pass, and `device_action_f1_live_v2.py`
validates that key without building a guard. A search for consumers that
materialize observer source into another filesystem found only the QEMU rootfs,
so no path stages it onto a device. That is a search result over the current
tree, not a proof that no fifth consumer exists.

This one is worse than the ACM control in two respects. It fails in a clean tree
with no lowered host boundary, so observing it required nothing but running it.
And it regressed a campaign the ledger already carries as `PROVED | HEALTHY`
(`s22plus-fyg8-p313`, `postlive-h0-2` and `postlive-h0-3`).

It stayed invisible for a reason worth recording separately from the defect
itself. `tests/test_s22plus_fyg8_p313_process_v2.py` does fail on it, but the
fixture raises in `setUpClass`, so the failure reports as `Ran 0 tests ...
errors=1` rather than as a failing test. A suite summary that counts tests
absorbs it. The consumed-suite manifest does not cover it either: that manifest
discovers `*p318*`. It should not be added there, because it is a regression
rather than a designed reject, and the manifest's contract is that anything it
lists is accounted for.

This class of event already has a correct procedure in this repository. The P3.16
row of `docs/operations/CAMPAIGN_LEDGER_S22PLUS.md` records that "historical
P3.13/P3.14 intents remain immutable expected invalidations after the common
live-observer SOURCE_KEY change". A common observer change that invalidates a
closed campaign gets recorded as an expected invalidation. This migration
produced the invalidation and skipped the record.

The migration introduced a first-party module dependency and a guard-schema
change into sources that other environments materialize by bytes. The previous
review could not see any of it, because the control's stale-source check fired
before the guest ever ran. A passing source-identity gate masked a functional
break in the primitive it was gating.

Two of the four are repaired. The two guard fixtures are not, and they must not
be repaired separately: fitting each one until the observer accepts it would
write the same synthetic receipt twice, which is the failure mode this unit
already refused once. The correct repair is a single shared guard-arming fixture
that publishes a real raw capture under `RUN_DIR` and sets `output_sha256` to the
digest of those captured bytes. It is specified and reviewed as its own unit.

## Unresolved observation outside this unit

A 354-test batch also surfaced four `test_s22plus_fyg8_p300_contract` errors.
They are not caused by this unit, on the following evidence rather than on a
reproduction: that test module and both implementations it exercises contain
zero references to this unit's auditor or to the campaign ledger, and both
implementations were rewritten by `c41fd1ddf7`. A reverted-file reproduction was
attempted and is not available, because the module cannot be imported on its own
(below), so the attribution rests on the absence of any dependency path.

- `reused S22 policy receipt changed: AGENTS.md` — `AGENTS.md` is unmodified in
  the working tree and was last changed by commit `52149ec34d`
  (`feat(s20plus): activate native canary R1`). The current 17,014-byte
  `6cd7e242` bytes are what the A90 hardening records carry, so the S22+ P3.00
  pre-LTO qualification is holding an older private policy receipt. This is a
  cross-target coupling: an S20+ commit stops an S22+ qualification gate.
- `sidecar result safety fields differ` at
  `s22plus_fyg8_p300_usb_trace_binding.py:349`, plus the sidecar rollback case —
  both files were rewritten by `c41fd1ddf7`, and unlike the consumed P3.18
  machinery these are common forward primitives.

This is reported rather than fixed. `test_s22plus_fyg8_p300_contract` cannot be
imported standalone (`ModuleNotFoundError: No module named
'device_action_f1_evidence_v2'`), so its result depends on batch composition and
needs confirming in a properly ordered full run before anyone acts on it. It is
deliberately not entered in the expected-failure manifest, because that manifest
must contain only designed rejects and these are not yet classified.

## Machine evidence

Implementation:

- `workspace/public/src/scripts/revalidation/s22plus_fyg8_raw_first_observer_audit.py`
  — 43,742 bytes,
  `2929a5f9d908fdc334dcc30b829f3b3a99f2d48a69ee4c67053f1888a2cbc4ca`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_consumed_suite_expected_failures.py`
  — 10,174 bytes,
  `8f56b7e9eeebfb4f863f3e12c1bc84cc978d11da8fd5f1391760402b40104b97`

Focused regression:

- `tests/test_s22plus_fyg8_raw_first_observer_audit.py` — 16,526 bytes,
  `59f7fd0c689454cf7d721a4900860e2e9009d32dd5bd8be15dd9291395457d1f`, 14/14
- `tests/test_s22plus_fyg8_consumed_suite_expected_failures.py` — 5,852 bytes,
  `da8f71dd077d52d8b69ac1891382c1858093c046425a6db55914aead5e20b8d0`, 6/6

Private deterministic receipts, each mode 0400 with link count one:

- `workspace/private/outputs/s22plus_fyg8_p319/raw-first-observer-audit-20260818-03-stage-a-probe.json`
  — 10,330 bytes,
  `d807ffac3eec504b82773d1a6a0aa8aaed9afc36b3687a31f49a6b8da20deaff`
- `workspace/private/outputs/s22plus_fyg8_p319/consumed-suite-expected-failures-20260817-01.json`
  — 3,778 bytes,
  `410b3e8f3d2de81b05e01b074f0785223b6a2dcf50c0b35da482a9a37550f76c`

The predecessor receipts `raw-first-observer-audit-20260817-01.json` and
`raw-first-observer-audit-20260817-02-behavioral-device-detection.json` are
preserved unmodified as historical evidence and are not current review
authority. The second was superseded when registering the Stage A truncation
probe moved the scanned population from 1,717 to 1,718; that registration was
forced by this auditor, which stopped on `closed observer source inventory
differs: count=122` rather than letting a new device-touching source in
unannounced.

The auditor's self binding was recomputed over its own normalized source after
the last edit, and the audit reopens its own stable bytes before reporting.

## Authority boundary

This is host-only source and test-inventory analysis. It changes no candidate,
live result, transfer count, correction registry entry, journal, or health state.
It creates no D0, D1, F1, recovery, replay, device, or live authority. No device
command, ADB command, reboot, Download request, Odin invocation, partition
transfer, candidate replay, rollback replay, A90 action, or S20+ action occurred.
The uncommitted S20+ files present in the working tree were not touched.

P3.19 Stage A remains open: attribute names under the Max77705 client, exact
`regmap` entry presence, and any Stage B target are still unproved, and a fresh
direct D0 request is still required. This unit changes the host side only.

An independent review of this exact changed closure is required before the
boundary is treated as qualified.
