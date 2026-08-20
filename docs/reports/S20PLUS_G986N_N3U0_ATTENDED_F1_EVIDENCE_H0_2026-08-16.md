# S20+ G986N N3-U0 attended F1 durable evidence owner H0

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **H0 PASS_GO - NOT ACTIVE**

## Scope

This bounded H0 unit implements a dormant durable owner for the future N3-U0
backend's private command stdout, stderr, and exact result receipts. It binds
the reviewed journal, concrete backend, and consumer-integration identities.
It neither changes those components nor exposes them as a connected runner.

`EVIDENCE_ACTIVE`, `active`, `live_authority`, `backend_exposed`, and
`integrated_live_consumer` are false. The only CLI is `--render-plan`; rendered
device-command and partition-transfer lists are empty. The binding S20+ target
contract still defines no N3-U0 F1 authority.

## Frozen candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_evidence_h0.py` | 23,153 | `57b1929f1769a4b53da7d69fb085e13253d2e19864d3fc5bc395c0e46f74d205` |
| `tests/test_s20plus_n3u0_attended_f1_evidence_h0.py` | 15,039 | `6f0112188d66fbf37bd23f532d42701ca90185c98dac1bbf810807b04786cd39` |

The normalized owner SHA-256 is
`2123482599650eaa54f75d9637a59c15df05199f5b7f7b6e2d343b29f154af71`.
The deterministic binding is
`dce408d5631aa23158f6213939149102f893ec561afe1a16cefeb50500c168c5`.
It pins journal binding
`4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945`,
concrete-backend binding
`d476cdc93b56296178def170fd80e8fe88d3eaf6b96693e577064ba77b02e15f`,
and consumer-integration binding
`2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6`.

## Evidence transaction

The owner revalidates its complete source/binding closure before every publish
or inspection. It accepts only a fixed journal run directly under the fixed private
N3-U0 runs root, one operation from a finite operation/predecessor map, and a
two-digit command ordinal. It revalidates the complete journal prefix and its
owning active guard, requires that operation's durable predecessor, and binds
the predecessor's canonical SHA-256 into the result.

Command arguments are not written in clear text; one canonical command hash is
stored. Private stdout and stderr remain only under the fixed private evidence
root. The owner atomically publishes:

1. `<operation>-<ordinal>.stdout`;
2. `<operation>-<ordinal>.stderr`; and
3. `<operation>-<ordinal>.result.json`.

Every direct evidence-directory, fsync, blob-write, blob-read, and namespace
helper repeats the dormant gate first and accepts only the fixed evidence root,
one direct lowercase run ID, and the finite filename grammar. Each final name
is created only after complete file bytes and file fsync via an
unnamed same-directory inode and no-replace `linkat`, followed by directory
fsync. Every file is a direct mode-0400 regular file with one link. The result
strictly binds run, distinct evidence-owner and journal bindings, operation,
ordinal, predecessor, command,
timeout, output limit, typed return code, and both raw size/SHA-256 receipts.

An intent with no evidence is `intent-consumed-evidence-absent`; stdout-only or
stdout-plus-stderr is `uncertain-consumed`. Neither permits replay. A result
without both earlier raw nodes, stderr without stdout, duplicate key,
bool/integer substitution, raw drift, indirect node, hardlink, unknown name,
or source drift stops as malformed.

## Hostile validation

The focused suite passes **18/18**. It covers dormant publication and
inspection before any write, unmocked exact render closure, complete raw/result
binding, duplicate publication/no replay, intent-only and both reachable raw
publication cuts, impossible publication orders, raw-byte drift, duplicate
JSON keys, bool/integer substitution, symlink/hardlink/unknown nodes,
atomic-link failure with no final name, wrong run root, missing predecessor,
and execution-source drift before publication and complete-evidence
certification, plus direct-helper dormant and `../`/foreign-root/arbitrary-name
rejection. Evidence directories and files must retain the fixed root's
owner/group identity; changing a run directory and every child together still
fails its root-to-run continuity check.

Independent review rejected three earlier candidates: publish/inspect did not
revalidate the evidence-owner binding, direct file helpers could bypass the
dormant gate and fixed root, and inspection checked file-to-run but not
root-to-run ownership continuity. The current exact candidate closes all three
with boundary-local validation and hostile fixtures. Fresh exact-byte review
returned `PASS_GO`; the status rotation changes no activation or live surface.

The 2026-08-20 raw-first transport rotation changed the exact backend binding,
so this owner now pins that reviewed candidate. Independent dependency-only
review returned `PASS_GO`; it remains inactive and non-integrated.

## Deliberate non-claims and next gates

`raw_evidence_durable=true` means only that this reviewed owner can durably publish and
strictly re-read a supplied command return while its H0 activation gate is
opened by tests. It does **not** mean the concrete backend currently calls it.
`integrated_live_consumer=false` is explicit. A host crash after a device
command but before the first raw publication remains represented only by the
pre-existing effect intent and must never cause replay.

A later unit must connect a fixed command-return hook to this owner, derive a
missing journal result from exact complete evidence without repeating the
command, preserve recovery reachability for absent/partial evidence, implement
the separately reviewed physical-entry bridge, run end-to-end cut fixtures,
obtain independent executable review, amend the binding target contract, and
perform a separate mechanical activation. Only after those gates may a fresh
connected prepare and approval be created.

No device, USB endpoint, ADB, `su`, Odin, network, private live run, reboot, or
partition transfer was contacted by this H0 unit.
