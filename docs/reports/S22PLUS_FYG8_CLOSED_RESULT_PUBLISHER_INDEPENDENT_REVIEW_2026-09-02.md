# Shared closed-result publisher — independent review

Date: 2026-09-02
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Tier: H0 only
Verdict: `NO_GO_CLOSED_RESULT_PUBLISHER_INDEPENDENT_REVIEW_H0`
Device contact: none — zero ADB, USB, Odin, reboot, transfer, rollback or replay
Authority: none

Unit under review: commit `7d00c7c9be`
- `workspace/public/src/scripts/revalidation/closed_result_publisher.py`
- `tests/test_closed_result_publisher.py`
- `docs/reports/S22PLUS_FYG8_CLOSED_RESULT_PUBLISHER_H0_2026-09-02.md`

The unit was authored by the operator's Claude session. The review was performed
by a separate read-only Codex session (`gpt-5.6-luna`, reasoning effort max,
`codex exec -s read-only`), which made no repository edits. The read-only
sandbox enforced the no-write, no-device contract structurally rather than by
prompt text. Every finding below was then re-verified against the source, and
two were corrected in the process; those corrections are recorded here rather
than silently applied.

## Outcome

Fifteen findings: eleven major, four minor. The obligation opened by
`h0-closed-result-publisher-1` is **not** discharged and remains open.

Byte equivalence stands and was strengthened. The reviewer independently
reproduced 33,879 bytes / SHA-256
`a78a9c50c8242506e6f531cc3d48f5fcadbe19410b1da8a7fc5215847aef91b5`, and a
direct re-verification confirmed that reconstruction with **and** without the
test's `lane_shim` produces those identical bytes. The prior concern that the
shim might be what made the two agree is refuted.

## Verified by direct re-execution

An audit-hook probe counted `subprocess.Popen` events and reads under
`/sys/bus/usb` and `/sys/class/typec`:

| phase | subprocesses | sysfs reads | result |
|---|---:|---:|---|
| import only | 0 | 0 | — |
| `reconstruct`, no `lane_shim` | 358 | 22 | 33,879 B `a78a9c50` |
| `reconstruct`, with `lane_shim` | 266 | 0 | 33,879 B `a78a9c50` |

Executables on the default path: `aarch64-linux-gnu-nm` 135, `git` 90,
`magiskboot` 70, `aarch64-linux-gnu-objdump` 45, `lz4` 18.

## Corrections to the review

- **F2's mechanism is wrong.** It reports that *importing* the publisher
  executes transitive subprocesses. Import executes zero. The 358 processes
  occur inside `reconstruct()`. The observation is exact; the cause named in
  the title is not.
- **The taxonomy diff figure in the review prompt was wrong**, and the reviewer
  caught it. The single commit `7d00c7c9be` moves 453→454 rows; the 445→454
  figure supplied to the reviewer described two steps combined. The committed
  ledger and taxonomy are consistent at 454 rows and `(78, 60, 18)`.

## Findings

### The report claims more than the code enforces

**F7 (major) — the default path performs an undeclared USB/Type-C read.**
`closed_result_publisher.py:462`. With the allowed default `lane_shim=None`,
reconstruction reads `/sys/class/typec/port0/...` and
`/sys/bus/usb/devices/2-1/idVendor` twenty-two times, while the emitted report
declares `usb_revalidated: false`. The published bytes are unaffected, but the
side-effect declaration is untrue on the default path. This is the most
significant finding: a host-only publisher for an already-closed run has no
reason to read live USB state.

**F2 (major, retitled) — "no device path" understates what runs.**
`closed_result_publisher.py:204`. Reconstruction spawns 358 host processes
including `magiskboot` and `lz4`. No ADB, Odin, transfer, rollback or replay
occurs, so no device authority is created, but the report row reads as though
nothing is executed. The AST test enforces the claim only against the
publisher's own source and cannot see the transitive import graph.

**F5 (minor) — C5's wording is inaccurate.** The report says the result is
assembled from "the stored terminal classification; expectations are compared,
never computed" (`..._PUBLISHER_H0_2026-09-02.md:67`). The code computes the
projection and terminal classification from current state at
`closed_result_publisher.py:331,340` and then compares them. This is
deterministic revalidation, not stored-value consumption.

### Invariants held by convention rather than by code

**F3 (major) — `publish()` does not enforce the 64 KiB bound.**
`closed_result_publisher.py:387,428`. The bound is checked only in
`reconstruct()` and again during post-publication read-back. A direct call with
a self-consistent 65,537-byte spec writes the target, then raises, leaving an
invalid result in place.

**F4 (major) — the publication sink has no lifecycle authorization.**
`closed_result_publisher.py:384-391`. `publish(spec, payload)` is a public
entry point that performs no journal, run, source or transfer validation, so it
can be reached without `reconstruct()` or `finalize()`.

**F8 (major) — the CLOSED gate compares against a caller-supplied value.**
`closed_result_publisher.py:81,293`. `JournalShape.state` defaults to `CLOSED`
but is settable, and the gate tests `journal.state() != spec.journal.state`
rather than requiring the literal `CLOSED`.

**F13 (major) — mode 0400 is not enforced on read-back.**
`closed_result_publisher.py:144,173,438`. `stable_bytes` checks that `st_mode`
does not change during the read; it never checks `S_IMODE == 0o400`. A retained
0644 result with identical bytes passes audit.

**F9 (minor) — a pre-link failure leaves a temporary file.**
`closed_result_publisher.py:392-419`. The first `finally` closes the descriptor
but does not unlink; only the second `finally`, after `os.link`, removes the
temporary.

### Structural

**F14 (major) — C1 is asserted, not enforced.** `tests/test_closed_result_publisher.py:22-26,118-123`.
The one-way dependency is tested by grepping three hardcoded paths for a
literal string. It derives no transitive import closure and cannot see a
dynamic or computed import. This was named as the author's own weakest claim
before the review and is confirmed.

**F6 (major) — the verifier's own source is outside the pinned identity.**
`closed_result_publisher.py:195`. `exact_files` is caller-declared and the P3.26
map contains no publisher-source or verifier-commit entry, so a later edit to
the publisher could change publication semantics with every listed pin still
passing.

**F11 (major) — TOCTOU between final drift validation and publication.**
`closed_result_publisher.py:372,446`. Inputs are verified and the payload
returned; publication happens later without rechecking or holding immutable
descriptors.

**F12 (major) — pinned source is not pinned bytecode.**
`closed_result_publisher.py:204,208`. The module hashes source text, then uses
ordinary imports, which resolve through timestamp-based `.pyc` caches. Identity
validation checks module paths and `MAX_RECORD` only.

**F10 (minor) — `os.link` omits `follow_symlinks=False`** and the directory
open omits `O_NOFOLLOW` (`closed_result_publisher.py:377,421`).

**F15 (minor) — unrecognized transfer artifacts are ignored.**
`closed_result_publisher.py:305`. Only caller-selected attempt numbers and
`.start.json` files are examined.

## Claims as assessed

| claim | outcome |
|---|---|
| C1 one-way dependency | current references absent; enforcement inadequate (F14) |
| C2 nothing before CLOSED | false for the generic API (F8); normal P3.26 path safe |
| C3 cannot become the default | `reconstruct()` ordering correct; sink bypasses it (F3) |
| C4 journal never repaired | verified for the P3.26 path; descriptor restoration faithful |
| C5 no reinterpretation | bytes deterministic; wording inaccurate (F5) |
| C6 exact identity, drift stops | listed files checked; verifier and bytecode not (F6, F12) |
| C7 audit_only publishes nothing | result unchanged; transitive side effects not excluded |
| C8 atomic, exclusive, 0400 | new-file mechanics sound; bound, mode and race gaps (F3, F13, F11) |
| C9 no device path | no ADB/Odin/transfer/rollback/replay; host subprocesses and USB reads do occur (F2, F7) |
| C10 equivalence | **verified**, 33,879 B `a78a9c50`, with and without the shim |

Independently rerun during review: publisher tests 12/12, taxonomy 39/39,
repository boundary 12/12.

## Disposition

No remediation is applied in this commit. Recorded order for the next unit:

1. F7, then F2 and F5 — the report and the emitted result must not claim less
   host activity than occurs. F7 should be closed in code, by giving the
   publisher an explicit stored-lane strategy that reads no USB state, rather
   than by widening the declaration.
2. F3, F4, F8, F13 — move the four invariants from convention into the code.
3. The remainder recorded; F14 and F6 need a design answer, not a patch.

`h0-closed-result-publisher-1` stays open until remediation and an exact-byte
re-review.

## What this review grants

Nothing. No device, ADB, USB, Odin, transfer, rollback, replay, candidate,
approval or live authority is created, no consumed run is altered, and no
published result is republished.
