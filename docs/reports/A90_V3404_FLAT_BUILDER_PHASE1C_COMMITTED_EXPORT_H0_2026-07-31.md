# A90 V3404 Flat Builder Phase 1C Committed Export H0

- Date: `2026-07-31`
- Decision: `A90_V3404_FLAT_BUILDER_PHASE1C_COMMITTED_EXPORT_PASS`
- Source commit: `79e5424da8be26b0bde77fb081f2725446d741f5`
- Schema: `a90-flat-builder-v1`
- Profile: `v3404-effective-portable-v1`
- Device authority: none
- Device, staging, reboot, flash, or network-to-device action: none

## Result

A wholly fresh disposable export of the committed Phase 1B source reproduced
the five portable hashes without any working-tree file injection. The export
was mounted only at `/work` in a bubblewrap namespace, the canonical repository
path was absent, and the clone preparation fault test passed.

Two builds from that committed export were byte-identical:

```text
init     beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   5b262978867bf98239e5d7e1b112f29b0217b59f057fc48c5b6e91d90eb5eaad
ramdisk  38e1edc8d9e8b0f396acaf366ef7d48311595a51df4ddf7849e183c8c505cbf2
boot     5839b260ef30d7ece9566a296155f571ad62b7f90ba3499b687f3db53eb956c2
```

Each identity and byte count also matched the Phase 1B portable A/B receipt.
The accepted historical V3404 boot remained
`0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3`.

## Commit binding

The disposable export receipt bound its tracked source to
`79e5424da8be26b0bde77fb081f2725446d741f5`. The two execution-critical entry
hashes matched the canonical committed files:

```text
build.py       a22696eca0b629401630ab8bcdaec6489a4af48c81c581f594c9435c8bc38124
manifest.toml  d6dedfccdc79a15eb31965c12a4db1b0f502c489539d8fad58facb8db32ee0f9
```

The clone receipt also revalidated the exact base and accepted boot inputs.
The A/B receipt declared `candidate_authority=false`,
`byte_identical=true`, and `accepted_boot_unchanged=true`.

## Path and packaging closure

All five artifacts from both build sides were scanned for the canonical
repository path and `/work/workspace`. No match was present. This closes the
packaging question left by Phase 1B: the portable result is reproducible from
committed state, not from uncommitted files or a hidden canonical-path
dependency.

## Disposition

The flattened V3404 effective snapshot is now the qualified baseline for
future host-side builder development. The 171-module legacy builder chain is
retained as historical evidence but need not be imported by a future version.

This result does not create V3406, a candidate artifact, a live manifest, or
device authority. The next bounded H0 unit may add a shallow data-only manifest
resolver with cycle, unknown-key, and no-op-child equality tests. A V3406
manifest should be created only after an actual candidate change is selected.
