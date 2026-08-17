# S22+ FYG8 P3.10/P3.14/P3.17 Carrier-version cross-check H0

Date: 2026-08-17 KST
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only
Status: **PASS_GO_P318_CARRIER_VERSION_CROSSCHECK_H0_CAPABILITY_V2; H0 ONLY; NO LIVE AUTHORITY**

## Result first

The requested three campaigns pass the exact criterion that P3.11 previously
violated:

| Campaign | Frozen selection | Retained Carrier | Selected count | Opposite count | Match |
|---|---:|---:|---:|---:|---|
| P3.10 | v2 | v2 | 1 | v1 = 0 | yes |
| P3.14 | v2 | v2 | 1 | v1 = 0 | yes |
| P3.17 | v2 | v2 | 3 | v1 = 0 | yes |

P3.11 is the positive control: its immutable prepared binding selects
Carrier-v1, while the retained bytes contain one Carrier-v2 record and zero
Carrier-v1 records. The same audit reports `selected count = 0`,
`opposite count = 1`, and mismatch. It therefore reproduces the silent failure
that made absence of `[valid, bad-body]` an invalid exemption criterion.

P3.10, P3.14, and P3.17 are now exempt only from that specific hidden
Carrier-version-mismatch concern. Their prior semantic conclusions remain
owned by their reviewed campaign analyses. This H0 unit adds no proof-class or
campaign correction.

## Frozen selection authority

For each campaign the audit reopens the exact immutable `prepared.json`, its
exact CLOSED `live-result.json`, and a mode-`0400`/link-count-one snapshot of
the historical `device_action_f1_evidence_v2.py` bytes named by the prepared
execution closure. The four source snapshots are the exact Git-era bytes:

- P3.10: 167,696 bytes / `3d3aa1b3...`;
- P3.11: 174,404 bytes / `6231255b...`;
- P3.14: 201,932 bytes / `fc074db2...`; and
- P3.17: 230,280 bytes / `16795546...`.

It requires:

- the exact campaign manifest and one approval-binding identity across both;
- the frozen decoder ID and exact selected long/UNSAT family bytes;
- the source-contract, profile, run ID, and overlay identity;
- the exact historical evidence-source size/SHA receipt from the execution
  closure;
- exact critical function bodies for source-contract selection, observation
  decoder selection, acceptance validation, and classification;
- one acceptance-to-`_latest_stage_observation_decoder()`-to-selected
  `classify_observation()` path, including the Carrier-authority validator used
  by P3.14/P3.17; and
- the frozen final classification's exact counts and strict
  policy/profile/run-ID equality with the prepared acceptance.

This distinction matters for P3.11: its current CLOSED result contains the
post-live recovered Carrier-v2 record, so that result alone is not proof of
the decoder originally selected by the frozen run. The exact historical
consumer source proves that its prepared Carrier-v1 acceptance selected
`p311_decoder`; the retained bytes independently give selected count zero and
opposite-v2 count one. The audit therefore does not substitute the current
adapter or the recovery-normalized result for historical execution semantics.

## Retained-byte authority

The parent is the independently reviewed historical sweep V2 receipt:

- 34,667 bytes;
- SHA-256 `0c8880ab4b3e28c2d4f287e158fc235972af6a8570004c006e247bfd44252a4e`;
- mode `0400`, link count one.

The cross-check reopens both exact final reads for every campaign, requires
them byte-identical, and requires the direct Carrier-v2 family offsets to equal
the parent's already CRC-reviewed structural records. It then runs a distinct
Carrier-v1 record parser over the same bytes. Its positive control is not made
by that parser: the audit bound-executes the exact 25,340-byte P2.32 design
authority (`68d510ea...`) plus its exact 11,141-byte retained-snapshot
dependency (`cafab0df...`), asks that authority to encode and decode one
45-byte E2 record, and requires the local scanner to agree. Changing the local
CRC domain while retaining that external record rejects. A zero opposite count
is therefore not a parser-disabled or self-approved default.

Injecting that valid v1 record into an otherwise v2-only relation rejects the
semantic exemption. Mutations of decoder, manifest, historical evidence-source
identity, parent raw path, and parent record offset also reject.

## Consequence

The earlier historical sweep's deferred boundary is now closed:

- P3.10/P3.14/P3.17 frozen selection agrees with the retained Carrier version;
- their opposite Carrier-v1 record count is zero; and
- P3.11 remains the detected mismatch control rather than being normalized
  into the passing set.

The campaign accounting does not move: P3.10-P3.18 remains two `REFUTED`, two
`NO_PROOF_EXPERIMENT_PRECONDITION`, and five `NO_PROOF_OBSERVER`; conclusive
yield remains 2/9 and proof-class diagnostic-bearing yield remains 4/9.

The successor boundary also remains unchanged. A future EUD trigger must be
bound to module identity or derived from the exact effective plan. The
decision-bearing witness stays in the retained ring, while ACM remains
supplemental until a physical-device positive control qualifies that path.

## Machine evidence

Implementation:

- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_carrier_version_crosscheck.py`
- 43,498 bytes
- SHA-256 `08f127b3274f42cc28e4914dad0c2d5c3483420eedf1ed3dda5d2c428cbce60a`

Focused regression:

- `tests/test_s22plus_fyg8_p318_carrier_version_crosscheck.py`
- 12,761 bytes
- SHA-256 `b5e67a46ec1a2ac6e3ad466e717c542e1cdbd734465ee4f275340dd2522d9074`
- 12/12 passing

Superseded initial receipt, preserved as historical evidence:

- `workspace/private/outputs/s22plus_fyg8_p318/carrier-version-crosscheck-20260817-01.json`
- 6,381 bytes
- SHA-256 `23358117d38f02003e1388d6dda40d874114dddf18790a34469b6488a2dfd360`
- mode `0400`, link count one

That receipt is not current review authority. It bound the prepared source
identity but did not reopen the historical consumer bytes, prove the actual
selection/classification call path, or use an external Carrier-v1 ABI control.
The append-only pending ledger row remains a truthful record of that initial
state.

Current V2 successor receipt:

- `workspace/private/outputs/s22plus_fyg8_p318/carrier-version-crosscheck-20260817-02.json`
- 13,488 bytes
- SHA-256 `f3e152b484c3b5bf3000748bebab9814032248462e4f0ed312185c4e24c3f556`
- mode `0400`, link count one

Only this V2 successor and its exact current implementation/test identities
are independently approved for this H0 capability.

Python compilation and focused source mutations pass. The frozen closure also
passes focused/taxonomy/documentation 86/86, the complete P3.18 set 232/232,
and common Process-v2 120/120. Scoped whitespace checks pass.

## Authority boundary

This is retrospective H0 analysis over preserved host bytes. It changes no
candidate, live result, transfer count, correction registry, journal, or
health state. It creates no D0, D1, F1, recovery, replay, device, or live
authority. Independent read-only review regenerated the V2 receipt byte-for-byte,
reopened the historical consumer and P2.32 authority closure, reproduced all
four version relations, and found no blocker. The append-only
`h0-carrier-version-crosscheck-review-16` row resolves only this review topic;
it does not create any device or live authority.
