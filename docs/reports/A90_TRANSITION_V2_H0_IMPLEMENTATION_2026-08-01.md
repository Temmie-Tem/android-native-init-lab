# A90 transition-v2 H0 implementation

Date: 2026-08-01

Status: `A90_TRANSITION_V2_H0_REVIEWED_HOST_PASS_NOT_LIVE`

Device action: none

## Decision

The reduced resident-install and switch-root experiment architecture is now
implemented as a host-only contract and simulation engine. It does not replace
the frozen F1 machinery, create a resident baseline, prepare an approval, or
provide a live effects backend.

The execution split is now explicit:

```text
rare RESIDENT_INSTALL_F1
  -> one candidate effect
  -> promoted second-boot health, or exact rollback after any started failure

ordinary SWITCHROOT_EXPERIMENT_D1
  -> one fresh TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL approval
  -> one handoff
  -> Debian proof -> native return -> exact cleanup -> final health
  -> no payload and no flash phase
```

The old chroot stage name is separately namespaced as
`STAGE_D1_CHROOT_MVP`; it cannot be confused with the D1 risk tier.

## Observation acceptance

The existing byte-preserving codec and strict A90P1 parser remain the single
framing implementation. The new layer adds an atomic decision and the exact
cross-run failure tuple:

```text
(workflow, phase, failure_class, effect_started, last_proven_boundary)
```

The redacted V3406 fixture is bound to its private source size and SHA256 and
now replays:

```text
native_release       PROVEN
debian_pid1          PROVEN
dropbear             PROVEN
display_acquisition  REFUTED
bounded_return       REFUTED
atomic               NO_PROOF
failure_class        DISPLAY_ACQUISITION_REFUTED
last_proven_boundary DROPBEAR_PROVEN
```

Its correction annotations preserve the reviewed CRLF, independent-subproof,
and D3-marker PID1-scope fixes. They do not use the historical false fact
classifications as expected results. The independent S22+ real-plus-dummy UDC
membership correction remains in its own P2.58A semantic-oracle suite; it was
not copied into the A90 codec.

The private A90P1 expectation manifest labels 20 raw transcripts. Nineteen
still match exact source SHA256, decision, failure signature, and frame/
transition geometry. One V3405 D0 path was appended after the v3 catalog was
created: its old SHA256-bound bytes are no longer replayable. That item is
explicitly classified
`UNAVAILABLE_SOURCE_MUTATED / SOURCE_BYTES_CHANGED` rather than silently
accepting the current appended bytes as the historical oracle. This is direct
evidence that future raw capture needs absent-only immutable publication.

## State-engine properties

- contract import is pure and every effect is injected;
- simulation and any future reviewed backend traverse `execute_workflow()` and
  the same phase tables;
- every effect call has an intent record first;
- a candidate effect exception is conservatively ambiguous and rolls back;
- candidate replay is absent;
- D1 has no candidate, rollback, payload, or resident-reboot phase;
- successor declaration requires predecessor release and successor acquisition;
- display acquisition is split into DRM master, connector, modeset, backlight,
  DPMS, and separately sourced visibility;
- one ambiguous signature, or two identical failure signatures, refuses fresh
  preparation; and
- importing the three modules in a read-only bubblewrap disposable tree with
  no canonical private tree succeeds without a write.

H0 scenario results include:

| Scenario | Terminal | Candidate | Rollback | Handoff |
| --- | --- | ---: | ---: | ---: |
| resident success | `PROMOTED_CLOSED` | 1 | 0 | 0 |
| post-candidate failure | `ROLLED_BACK_CLOSED` | 1 | 1 | 0 |
| ambiguous candidate effect | `ROLLED_BACK_CLOSED` | 1 | 1 | 0 |
| visible D1 | `PASS_SWITCHROOT_RETURN_VISIBLE` | 0 | 0 | 1 |
| unattended D1 | `PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY` | 0 | 0 | 1 |
| display proof failure | `STOPPED_NO_RETRY` | 0 | 0 | 1 |
| ambiguous return | `STOP_AMBIGUOUS` | 0 | 0 | 1 |

These are simulation terminals, not device results.

## Validation and boundaries

Focused observation/transition tests, the active A90 F1/staging regression,
and the independent S22+ P2.58A UDC oracle pass `245/245`. The reviewer's
latest execution-critical subset passes `38/38`; touched Python compiles and
`git diff --check` passes. The Phase2C host-packet test
still rejects an already-stale private packet whose staging-adapter hash does
not match current committed `HEAD`; current `HEAD` reproduces that mismatch
without this change. The packet was not rebound because it is outside this H0
unit and must not be made to look live-current.

No native-init C, Debian image, boot image, manifest, approval, device state,
or rollback artifact changed. A90 and the separately connected S22+ were not
contacted.

Independent review found and closed the following H0 defects before returning
PASS with no remaining Critical, High, Medium, or Low finding:

- contradictory candidate PASS could suppress rollback;
- noncanonical ambiguity could bypass the next-run stop;
- intent or effect exceptions could escape without a structured recovery
  result;
- malformed display evidence could escape the engine;
- an observation failure could skip native return, cleanup, and final health;
- a later recovery-tail failure could erase an earlier ambiguity signature;
  and
- the same approval could be reused across engine invocations.

The final effects port requires atomic one-shot approval consumption before any
phase intent. Once handoff may have started, observation no-proof or ambiguity
is preserved while the bounded native-return, cleanup, and final-health tail
continues. If native return itself is not proved, cleanup is not attempted.
An earlier ambiguity remains the primary next-preparation stop while later
recovery failures remain as secondary signatures.

## Next gate

The next unit is still host-only: define a real-effects adapter design and an
immutable live manifest schema without enabling either. The live adapter must
implement durable atomic approval consumption; the in-memory H0 adapter is not
a substitute. Resident installation itself remains a new F1 and requires a
fresh exact approval only after those gates pass.
