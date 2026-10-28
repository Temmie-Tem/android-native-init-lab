# S22+ mainline RAM/USB experiment ML002 — 2026-10-29

Status: **PREPARED; NO CANDIDATE TRANSFER YET**.

The operator requested continuation through a physical successor experiment.
The exact candidate and connector task are prepared, and the fixed preapproval
D0 health transcript passed fresh raw revalidation. The generated finite
approval and actual attendance statement have been requested; no grant or
candidate transfer has occurred at this stage.

## Candidate and retained scope

ML002 uses the [reviewed staging correction](S22PLUS_MAINLINE_ABL_PLACEMENT_SUCCESSOR_H0_2026-10-28.md)
with a fresh RAM-canary key, identity and derived USB/network identity.
Its seven init input pins equal the retained physical init's inputs. The
prepare-4 kernel and g0q DTB are reused; no production source changed.
`ML002` is the reporting ordinal. The existing
`ml001/mainline-ram-1/mainline-ram-v1` wire capability identifiers stay fixed;
the actual run ID, payload and AP are fresh. The consumed ML001 is preserved.

The selected scope remains one boot-only N transfer, at most 120 seconds of
authenticated RAM PID1/USB observation, physical Download and one original-A
return with rooted Android health. The finite grant is one operation within
1800 seconds. Linux storage access and installed-root execution are excluded;
automatic recovery remains unproved. Native_data consistency is unobserved.

## Preparation and validation

- Built and inspected the new static ARM64 init and loader.
- The actual new loader passed 20 cases and 1,051 linked copy cases.
- All 64 normal source placements passed the entry guard; three representative
  full copies matched exactly. Maximum-selector execution also passed from
  relocation through the kernel branch, including BSS, stack, register,
  kernel/initrd-byte and FDT checks.
- Actual-EL QEMU entered at EL1/EL2 and rejected EL3 without rewriting entry
  registers. Physical entry and cache behavior remain unproved.
- Two independently repacked boot-v4/AP outputs are byte-identical and contain
  only `boot.img.lz4`, preserving the checked original-A outer envelope.
- The narrow independent candidate addendum found no issues, reused the
  unchanged 15-source staging review and current 34-source execution review,
  and bound 64 fresh/retained evidence receipts. Old review records were not
  repinned. The current admission consumer and connector bundle accepted the
  exact new artifacts and predecessor's healthy Android closure.
- The reviewed ordinary-terminal bridge is connected. Named fixed preapproval
  D0 passed identity/root/partition-digest and host checks; its raw evidence
  rederived successfully, with no unresolved F1 owner, control or transfer.
  Current health must still meet the original freshness checks at grant/effect.

Relevant past-failure rows are ABI (actual ARM64 entry/copy), ARTIFACT (exact
new identity and package joins), ROUTE/HOST (actual consumer and ordinary worker),
SEMANTIC (H0 and physical proof separation), and RETURN (original-A physical
recovery and final health). Display changes are not selected. A90, S20+ and
unrelated paused boot-journal/ABL-report work were untouched.

Prepared task SHA-256:
`640ce3911aa8cf18c86f3b40fc2ca41dc3b5c40bee80f802a7da87cb2538ca76`.
Candidate AP SHA-256:
`997c6844b68e01a529f6d0b0364a7a62313c2a700921796d3a544c588051744b`.
Candidate addendum SHA-256:
`08fa8c53be34acdb517c1a8f72f5a913f44034d2c105429baab0cbd19ef92d83`.

Private artifacts, source snapshots, test results, exact task, review and
preapproval raw evidence are under
`workspace/private/outputs/s22plus-mainline-ml002-h0-20261029-1/`.
Preparation is not a consumed operation, device authority or mainline proof.
