# Public Tree Sanitization Policy

Adopted: `2026-08-07`
Scope: repository-wide (all targets)

`AGENTS.md` already forbids committing device serials, PARTUUIDs, MAC/BSSID/IP
values, and similar private identifiers. This document does not change that
rule. It defines how the rule is applied to content already in the public tree,
and what a sanitized file is allowed to claim.

## 0. Why this exists

The repository boundary was documented on `2026-07-08` (`7cfe854e`, *AGENTS:
require stripping device serials from reports before commit*) but remained
unenforced by any automated check for approximately one month. In that period
the tree accumulated identifiers both predating and postdating the documented
boundary, which demonstrates that documentation alone was not sufficient to
prevent recurrence. Mechanical enforcement (§5) is the remedy.

The measurements behind that statement — occurrence counts, affected files, and
the method used to date them — belong to the remediation report for the event,
not to this policy. This document states the rule; the report states what was
found.

## 1. What sanitization does and does not assert

- Historical documentation and archived sources in the active public tree **may**
  have maintainer device identifiers replaced.
- A sanitized file **does not** assert byte-exact historical identity. Where a
  replaced identifier appears inside a larger string — a device path, a tool
  output line, a descriptor value — that string is a sanitized representation,
  not a byte-exact historical record.
- Original experiment provenance is preserved by immutable Git history together
  with the artifact hashes, run IDs, and evidence receipts recorded in each
  report. Those are the reproducibility anchors; the identifier string is not.

## 2. Boundary

> Sanitization must not alter technical behavior, control flow, artifact hashes,
> or substantive findings beyond replacing non-public device identifiers.

A sanitizing change that also edits logic, results, conclusions, or recorded
hashes is out of scope for this policy and must be raised as an ordinary change.

Historical commit identities referenced by run evidence must not be rewritten
for identifier hygiene. Sanitization applies to the current tree only.

## 3. Replacement classes

The replacement token is chosen by the **role of the file** — is it a document
someone executes, or a record of something that happened? — not by the shape of
the line.

| Path | Role | Token |
| --- | --- | --- |
| `docs/operations/**` | Executable instructions | Runtime variable: `$A90_SERIAL`, `$S22P_SERIAL`; for expected tool output, `<your-device-serial>` |
| `docs/reports/**`, `docs/archive/**` | Historical evidence | Public device alias: `DEVICE-A90-01`, `DEVICE-S22P-01` |
| `workspace/public/archive/**` | Frozen past source, published copy | Explicit redaction token: `REDACTED-DEVICE-SERIAL` |
| `docs/security/findings/**` (code quotes) | Evidence of past behavior | `REDACTED-DEVICE-SERIAL`, with an inline redaction note |
| `tests/**` | Fixtures | Obviously synthetic but format-valid value: `RFCM0000000`, `RFCT0000000` |

Rationale for the third and fourth rows: an alias in an archived
`wf(".../serialnumber", ...)` call would assert that the code once wrote
`DEVICE-A90-01` to the USB descriptor, which is false. An explicit redaction
token states that a value was removed without substituting a fabricated one.

Rationale for the first row: an alias is not a value `adb -s` accepts, so
substituting one would leave a runbook whose commands fail when copied. Moving
these to a runtime variable also makes the runbooks usable by anyone with the
same model, which is an improvement independent of sanitization.

## 4. Public device aliases

Aliases are stable, arbitrary, and **not derived from any real identifier**.
They exist so that "the same physical unit" remains traceable across runs and
reports in the public tree.

| Alias | Model |
| --- | --- |
| `DEVICE-A90-01` | `SM-A908N` |
| `DEVICE-S22P-01` | `SM-S906N` |

The alias-to-serial mapping is maintainer-private and lives only under
`workspace/private/`. It is never committed.

Public aliases are distinct from the synthetic USB gadget serial strings used by
native init (`A90NATIVE001`, `S22M34RUNTIME01`, and similar). Those are
per-build experiment identifiers written to a device descriptor; aliases
identify a physical unit in documentation. Both are public; neither is a real
serial.

## 5. Enforcement

A repository-boundary check runs over the tracked tree. Its required invariants:

1. **Known real identifiers fail the check outright.** They are matched exactly,
   not heuristically.
2. **Approved values are subtracted before any heuristic judgement**, so a
   sanctioned fixture is never reported as a finding.
3. **Unknown serial-shaped tokens are reported for review** rather than silently
   accepted.
4. **Detection must not rely on regex word boundaries.** An identifier may be
   embedded in a udev or `by-id` path containing underscores, and a word
   boundary treats `_` as a word character — a check built that way reports a
   clean tree while an identifier is still present. This case must have a
   regression test.
5. **Adding an entry to the approved-value list is a reviewable change.** That
   cost is intended.

6. **The check must not itself contain a private identifier.** The known-identifier
   list is stored as SHA-256 digests. This is self-consistency, not secrecy — the
   values remain in immutable Git history either way — but a checker carrying the
   plaintext would fail its own rule and would reintroduce the string into the
   tree it is meant to keep clean.

The concrete pattern, the approved-value list, and the tests live with the
checker, not in this policy. At adoption the approved list holds only the test
fixtures `RFCM0000000` and `RFCT0000000`; the synthetic USB gadget serial corpus
is deliberately absent because no member of it can reach the heuristic.

Implementation: `workspace/public/src/scripts/security/repository_boundary_check.py`,
tests in `tests/test_repository_boundary_check.py`.

> If detection is expanded beyond the current Samsung-style `R...` identifier
> family, the synthetic public identifier corpus must be reevaluated before
> enabling the broader heuristic.

## 6. Relationship to current code

The current native init sources under `workspace/public/src/` already use
synthetic gadget serials exclusively. This policy therefore governs **historical
evidence hygiene plus forward enforcement**, not a defect in current code.
