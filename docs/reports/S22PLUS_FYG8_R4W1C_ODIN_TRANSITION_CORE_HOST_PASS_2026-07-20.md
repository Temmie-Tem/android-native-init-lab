# S22+ FYG8 R4W1-C Odin Transition Core Host PASS

Date: 2026-07-20 KST

## Verdict

`PASS_R4W1C_ODIN_TRANSITION_CORE_HOST_ONLY`

The first R4W1-C host unit is complete. It preserves every retired R4W1-B file
and adds a target-neutral, enumeration-only Odin endpoint evidence core for
future reviewed helpers.

No device was contacted. No image was built or changed. No ADB, reboot,
Download transition, Odin transfer, flash, consumed state, policy activation,
or partition action occurred.

## Sources

```text
core
  workspace/public/src/scripts/revalidation/s22plus_odin_transition_core.py
  SHA256 05aae02901a7ec48be4f3a5d89762437738d490892f944dc4859f9c5dd6402f8

test
  tests/test_s22plus_odin_transition_core.py
  SHA256 b45744614c4840952286aeb026cb6c07e2c46c86caefb3268bdc0fd73b00d469

postmortem
  docs/reports/S22PLUS_FYG8_R4W1B_WEB_CLAUDE_REPOSITORY_POSTMORTEM_2026-07-20.md
  SHA256 03213bb471e6704b1fe103dd176e417d254e6c01b5f4e0ab5b53e4062963904e

design
  docs/plans/S22PLUS_FYG8_R4W1C_RESUMABLE_TRANSACTION_WATCHDOG_CARRIER_DESIGN_2026-07-20.md
  SHA256 2d998273b2af9053ca50ab90403a8b0ede74363c4bb2850579e69618759091df
```

## Implemented Contract

- `odin4 -l` is the only subprocess surface.
- Output is bounded and nonzero enumeration fails closed.
- Raw paths are split into live and stale sets through direct device-node
  identity inspection.
- Stale-only output is accepted as live-endpoint absence.
- Multiple live endpoints fail closed.
- One live endpoint receives a generation ticket bound to path plus
  `st_dev:st_ino:st_rdev:st_ctime_ns`.
- Fresh pre-transfer revalidation requires the same single path and node
  identity.
- Every snapshot is an exclusive, fsynced JSON receipt.
- The JSONL transaction index is append-only and fsynced, but immutable receipts
  remain the trust root if the index ends with a crash-partial record.
- Receipt recovery validates schema, filename/payload sequence, and SHA256.
- Transaction phase receipts allow only the exact forward-only phase prefix.
- The existing canonical eight-event timeline schema is untouched.

## Validation

Focused new tests:

```text
18 tests OK
```

Coverage includes stale disconnect, nonzero enumeration, ambiguity, generation
assignment and cross-call resumption, contiguous sequence enforcement, same-path
node replacement, changed endpoint, symlink rejection, immutable phase receipts,
forward-only order, path/payload mismatch, missing-index recovery, crash-partial
JSONL segment rollover, orphan resume rejection, enumeration timeout
normalization, output-surface restrictions, and regular-file rejection.

Retired R4W1-B regression suite:

```text
94 tests OK, 3 skipped for build-host-only inputs
```

Existing reusable live core regression:

```text
12 tests OK
```

Additional checks:

```text
py_compile     PASS
git diff --check PASS
line length >100 scan clean
ruff unavailable on this host
```

Total observed test result is 124 tests OK with 3 environment skips.

## Review Notes

The retired R4W1-B helper and `s22plus_boot_only_live_core.py` were deliberately
not modified. Their historical hashes, reports, consumed state, and retired
policy remain reproducible.

The new core does not contain confirmation prompting, candidate pins, rollback
pins, marker semantics, or any transfer primitive. A future target helper must
call endpoint wait first, then start a separate full confirmation deadline, then
revalidate the returned ticket immediately before a policy-authorized transfer.

## Next Gate

Run a separate host-only adversarial review of the exact new core, tests,
postmortem, and R4W1-C design. Only a clean review may advance to the
M31B-derived watchdog-managed carrier builder and independent static checker.
There is no live authorization at this checkpoint.
