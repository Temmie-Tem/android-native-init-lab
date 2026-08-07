# Public Tree Serial Remediation

```text
Date: 2026-08-07
Tier: H0 (host only; no device contacted)
Device flash: no
Policy: docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md
Host commit: c2c77700
```

Measurements for the one-time sanitization of maintainer device serials from the
active public tree. The policy states the rule; this report states what was
found and what was changed.

> This report ships with the remediation change it documents. The policy it
> applies was adopted in the preceding commit; between those two commits the
> tree carried the identifiers under a documented rule, which is a declared
> migration state rather than a policy violation.

## 1. Scope measured

| Quantity | Value |
| --- | --- |
| Tracked files carrying a real serial | 107 |
| Occurrences | 126 |
| Distinct real identifiers | 2 (one per target) |

Current native init sources under `workspace/public/src/` carry none of them;
they already use synthetic gadget serial strings exclusively. Every occurrence
is in documentation, archived source, or a test fixture.

## 2. Dating method

An occurrence's age is **not** the age of the file that contains it. A file
created before the boundary was documented can still have had an identifier
added afterward. Dating by file creation would misclassify that case.

Each occurrence was therefore dated by the commit that introduced the string
into that file:

```bash
git log --reverse --format='%ad %h' --date=short -S"<identifier>" -- <file> | head -1
```

Cross-checked with `git log --follow` on every post-boundary file, to confirm
none had pre-rename history that the path-scoped pickaxe would miss.

Result of the cross-check: introduction date and file creation date agreed for
**all 107 files** (0 divergent), and none of the post-boundary files had
pre-rename history. The simpler proxy would have produced the same answer here —
but that was not knowable without the measurement.

## 3. Result

Boundary documented `2026-07-08` (`7cfe854e`).

| Category | Occurrences | Target |
| --- | --- | --- |
| Introduced before the boundary was documented | 102 | A90 |
| Introduced after the boundary was documented | 5 | S22+ |

The five post-boundary files:

```
2026-07-20  fb05068b  docs/reports/S22PLUS_FYG8_R4W1C_DOWNLOAD_SERIAL_ABSENT_PRECONSUMPTION_2026-07-20.md
2026-07-20  32e1b283  docs/reports/S22PLUS_FYG8_R4W1C_NOSERIAL_PRECONSUMPTION_ENUMERATION_MUTATION_2026-07-20.md
2026-07-20  b63cc6f6  docs/reports/S22PLUS_FYG8_R4W1C_ODIN_ENUMERATION_DIFF_OBSERVER_LIVE_PASS_2026-07-20.md
2026-07-20  525d8037  docs/reports/S22PLUS_FYG8_R4W1C_PRECONSUMPTION_ENDPOINT_ARRIVAL_RACE_2026-07-20.md
2026-07-21  10d44120  docs/reports/S22PLUS_FYG8_R4W1C2_PRECONSUMPTION_USBFS_SETTLE_FAIL_2026-07-21.md
```

These five are the only carriers of the S22+ identifier. The split is clean by
target: every A90 occurrence predates the boundary, every S22+ occurrence
postdates it.

**Finding.** The recurrence tracks the introduction of a new target, not a lapse
on an existing one. A written rule was in place and did not survive contact with
a new workflow, because nothing checked it. This is the evidence for replacing a
documented boundary with an executable one.

## 4. Classification applied

Per policy §3, by file role:

| Class | Occurrences | Files | Token |
| --- | --- | --- | --- |
| A — historical evidence | 29 | 20 | `DEVICE-A90-01` / `DEVICE-S22P-01` |
| B — executable instructions | 12 | 2 | `$A90_SERIAL` (9), `<your-device-serial>` (3) |
| C — frozen source and code quotes | 84 | 84 | `REDACTED-DEVICE-SERIAL` |
| D — test fixture | 1 | 1 | `RFCM0000000` |

An initial pass classified by line content (`adb -s` present → executable) and
misfiled 3 occurrences in both directions: historical `adb devices` transcripts
in `PROGRESS_LOG.md` were treated as instructions, and runbook expected-output
lines were treated as records. The classification axis was corrected to the
role of the containing file, which is what policy §3 encodes.

Two occurrences were resolved by judgement and are recorded here:

- `docs/reports/ADB_FROM_LINUX_INIT_LOG_2026-04-23.md` — the identifier is inside
  a `/dev/serial/by-id/` path. Substituting the alias yields a path that never
  existed. Alias retained: the claim being recorded is that the ACM gadget
  enumerated under `by-id`, not the exact path bytes. Policy §1 covers this.
- `docs/archive/legacy/reports/NATIVE_INIT_V233_REAL_LINKERCONFIG_COPY_REAL_2026-05-15.md`
  — a `--serial` argument inside a historical record. Alias retained: the file
  documents what was run at the time, not a command a reader reproduces, and it
  already references private paths.

## 5. Verification

The outcome was simulated before any file was modified, then confirmed against
the real tree afterward.

```
before change, simulated  : 107 files known, 0 unrecognised
before change, checker    : 107 files known, 0 unrecognised
after change,  checker    :   0 files known, 0 unrecognised   -> clean
```

Substitution counts matched the classification table exactly:

```
A alias          29
B envvar          9
B placeholder     3
C redact         84
D mock            1
TOTAL           126        across 107 files
```

Regression tests: `tests/test_repository_boundary_check.py`, 12 tests, all
passing. They include the word-boundary case that motivated the tokenizer:

```
input                     usb-SAMSUNG_SAMSUNG_Android_<identifier>-if00
\bR[0-9A-Z]{10}\b      -> no match          (underscore is a word character)
whole-token match      -> match
```

and the non-flag cases `REDACTED-DEVICE-SERIAL`, `DEVICE-A90-01`,
`DEVICE-S22P-01`, `RFCM0000000`, `RFCT0000000`, the synthetic gadget serial
corpus, and the all-alphabetic near-misses `REASSOCIATE`, `RECOVERABLE`,
`REINTERPRET`.

Layer 1 is tested by pointing the digest table at a synthetic stand-in, so the
test file contains no real identifier either.

Tests touched by the substitution were re-run and pass:
`test_server_distro_d3_switchroot_handoff` (10), and
`test_s22plus_stock_usb_topology_readonly` (7), whose existing `RFCT0000000`
fixture is the convention the class-D replacement follows.

## 6. Not changed

- Git history. Historical commit identities are referenced by run evidence and
  by the `Host commit:` field required in report headers; rewriting them for
  identifier hygiene would destroy provenance to remove a value that the history
  would still contain in reflog and forks. Policy §2.
- Any logic, result, conclusion, or recorded hash. Policy §2 boundary.
