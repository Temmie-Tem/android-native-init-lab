# S22+ FYG8 P2.82 Implementation and Pre-LTO Qualification H0

Date: 2026-07-28 KST

Verdict:

`PASS_P282_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY`

## Scope

This unit implemented the frozen P2.82 pre-bind child-reinit decision
contract and validated it before Full LTO. It did not build a kernel image,
package an AP, create a live manifest, authorize F1, invoke Odin, reboot a
device, or flash anything.

The selected mechanism remains one bounded parent role cycle before UDC bind:

```text
peripheral -> none -> peripheral
```

It observes the ordered parent, child runtime-PM, femto-HS initialization,
bind, and final UDC state/speed outcomes. It does not add host role, direct
power/clock/reset/MMIO writes, retry loops, or a larger retained carrier.

## Implementation

One P2.82 descriptor is the source of truth for:

- seven progress/terminal stages through generation 92;
- 46 exact C-band diagnostic details;
- 567 final state/speed tuples;
- generated runtime tables and the production C classifier;
- host decoder semantics;
- trace event ownership and source contracts;
- userspace write authority and timing bounds.

The runtime performs one stop/suspend/restart/reinit cycle, one UDC bind, one
banner attempt, then quiet-parks. The observer budget is 300 seconds and its
ModemManager guard is 360 seconds. An exact run-bound banner remains positive
evidence if the guard later expires; banner absence under guard loss is
indeterminate.

## Pre-LTO Evidence

The immutable v4 qualification receipt binds one fresh intent, patch,
userspace pair, generated implementation, pinned QEMU results, linked-audit
metadata, safety dictionary, and timing geometry.

Validated results:

- production AArch64 classifier details: `46/46`;
- generated tuple round trips: `567/567`;
- shared trace lifecycle cold samples: `5/5`, with zero missed probes;
- same-path userspace links: byte-identical;
- retained record geometry: fixed 45-byte carrier, valid through generation
  92;
- focused and Process v2 regression tests: pass;
- pre-LTO gate matrix: `19/19`;
- actual qualification producer to actual repro consumer: pass with six exact
  result receipts.

## Fail-Closed Corrections

The first qualification attempt exposed two incidental-ELF classifier bugs.
Short slash-prefixed byte fragments were being treated as absolute paths, and
read-only canonical speed labels were being treated as new write authority.
The fix does not add artifact strings to an allowlist:

- only slash strings of at least four bytes are path candidates;
- required paths remain mandatory and an unowned path such as `/tmp` fails;
- `high-speed` remains required;
- additional observed speed labels must belong to the P2.82 canonical speed
  source of truth.

An independent changed-closure review then found two integration blockers:

1. the qualification producer omitted `gate_result_receipts` although the
   repro consumer required them;
2. the central linked auditor and P2.80 wrapper both transformed logical
   linked-table bytes into physical storage.

The fixes make the producer derive six result receipts from its own evidence,
and make the central auditor the sole physical-storage transformer. A shared
regression now executes the P2.80 5-byte logical to 6-byte physical detail
layout and the P2.82 4-byte to 4-byte layout. P2.80/P2.82 wrappers no longer
monkeypatch the central audit entrypoint. A tracked integration assertion now
feeds the real qualification verifier result to the real repro consumer.
The same independent reviewer rechecked this changed closure and returned GO
with no remaining blocker.

## Interpretation

The design, implementation, and pre-LTO qualification are complete. This is
not a device result and does not prove that the controlled reinit repairs
electrical USB attach. It proves that the next kernel pair may be built
without reopening mechanism analysis.

The remaining order is:

1. independent review closure;
2. Full-LTO A/B;
3. GNU AArch64 linked audit;
4. boot-only packaging and offline promotion;
5. connected D0 and immutable ready manifest;
6. stop for one fresh F1 approval.
