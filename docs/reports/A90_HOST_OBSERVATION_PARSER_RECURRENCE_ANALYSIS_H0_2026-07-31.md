# A90 Host Observation Parser Recurrence Analysis

Date: 2026-07-31

Status: `H0_ANALYSIS_COMPLETE_IMPLEMENTATION_NOT_STARTED`

Device action: none

## Decision

The V3406 CRLF rejection is not an isolated regular-expression mistake. The
repository has a recurring observation-integrity problem in which transport
decoding, protocol framing, semantic fact extraction, and atomic experiment
decisions are implemented and tested at different layers without one replayed
evidence contract.

This is currently more expensive than another display or return experiment.
It can turn real device progress into a false failure, erase valid subproofs,
or accept malformed/spoofed command results. Another live candidate should not
be prepared until the active A90 observation closure is migrated to a strict
shared pipeline and replayed against preserved evidence.

The unifying remedy is not one global parser for every protocol. The correct
boundary is:

```text
immutable raw capture
-> transport-specific byte/line codec
-> protocol-specific frame parser
-> independent semantic fact classifiers
-> atomic experiment decision
```

A90P1, A90 handoff/SSH text, and S22+ retained records need different codecs
or frame parsers. They should share the same corpus manifest, pure-classifier
interface, semantic-oracle rules, mutation strategy, and replay harness.

## Recurrence Classification

Three related but distinct defects establish the structural pattern.

### A90 V3406 CRLF false rejection

The Phase 2 native-release validator exists twice:

- `a90_phase2c_display_packet.py`;
- `a90_phase2d_display_observer.py`.

Both copies anchor the final field directly before newline. The H0 test
fixture is LF-only. The live ACM transcript contains CRLF, so the final `\r`
prevents the exact success-line match.

Replaying the preserved V3406 transcript gives:

```text
release_raw=REJECT:ContractError
release_lf_normalized=PASS
stored_ssh_pid1=True
stored_top_pid1_key=False
```

The last two lines expose a second defect: one display-validation exception
short-circuits fact promotion. The private observation retains Debian PID1 in
its SSH subrecord, but the top-level fact is absent and the closed result
records it as false. Fail-closed atomic status is correct; erasing independent
subproofs is not.

### A90P1 F016 mitigation remains non-authoritative

The current `a90ctl.py` improved the original F016 implementation by waiting
for a prompt and choosing the last observed END. It still accepts incomplete
or inconsistent frames.

Current-source synthetic replay produced:

| Case | Current result |
|---|---|
| exact LF frame | accept |
| exact CRLF frame | accept |
| END without BEGIN | accept |
| BEGIN seq 1 / END seq 2 | accept |
| duplicate `rc=7 rc=0` | accept as rc 0 |
| missing sequence on both records | accept |
| ignored non-key token in END | accept |
| forged END plus forged prompt | accept as rc 0 |

The forged-prompt case passed command-name validation while retaining
`begin_seq=41` and `end_seq=999`. `has_prompt_after_last_end()` also accepted
the forged prompt. Therefore prompt detection, last-END selection, and a short
post-marker drain mitigate accidental truncation but do not establish an
authoritative frame boundary.

This is not fully repairable in host parsing if arbitrary command output and
the real protocol trailer remain on the same unescaped channel. A strict host
parser can reject missing, duplicate, malformed, or mismatched fields and can
make accidental-noise handling much safer. Adversarial F016 closure ultimately
needs a protocol revision with an unguessable request binding and escaped or
length-delimited body, or a separate trusted control channel. Until then,
A90P1 v1 must not be the sole proof for an unsafe transition.

### S22+ UDC singleton false failure

The P2.57 UDC issue is not a line/framing parser defect. It is a semantic
predicate defect: global singleton cardinality was used where exact target
membership was required, so the known-good real-plus-dummy topology was
rejected.

It belongs in the same recurrence program because the missing control is the
same: no executable positive oracle represented the known-good external
state. It does not belong in the same A90P1 codec. The P2.58A semantic oracle
matrix is the right general pattern for classifier tests:

```text
known-good target state              -> PASS
target absent                        -> NOT_READY or FAIL
target plus unrelated valid peer     -> PASS unless exclusivity is proved
wrong type or wrong identity         -> FAIL_CLOSED
malformed observation or read error  -> FAIL_CLOSED
```

## Current Implementation Inventory

The active tree contains:

- 36 Python scripts with direct A90P1 marker knowledge;
- at least 7 active scripts with their own BEGIN/END regex or framing-error
  classification;
- 66 scripts importing the shared A90 transport layer; and
- 2 copies of the Phase 2 native-release semantic regular expression.

The shared transport layer has broad adoption, but it does not own one strict
decoded-frame type. Consumers still reparse returned text or attach their own
semantic regular expressions.

The existing focused tests all pass:

```text
test_a90ctl.py: 18/18
test_a90_phase2c_display_packet.py: 6/6
```

Those suites contain no adversarial prompt-spoof case, exact field-schema
matrix, or CRLF native-release fixture. Green tests therefore did not exercise
the live failure shape or the remaining F016 boundary.

## Private Evidence Corpus

An H0 inventory of text-like files no larger than 20 MiB under
`workspace/private/runs/` found:

```text
eligible_text_files=4063
raw_log_files=27
raw_log_bytes=1495003
a90_framed_files=76
a90_lf_only=58
a90_mixed_endings=18
end_marker_missing_files=5
```

Eighteen raw logs contain A90P1 frames. The current whole-file parser accepts
all eighteen, but sixteen contain more than one END record. That is not a
successful replay result: it proves the current API selects one final frame
instead of segmenting and classifying every transaction in the transcript.

No preserved private evidence uses a receive-chunk plus monotonic-timestamp
schema. Final raw text is sufficient for CRLF, exact-field, semantic-marker,
and multi-frame regression. It cannot reproduce early read termination,
marker split across socket chunks, deadline expiry, or the forged-prompt timing
path. Those cases require synthetic chunk schedules now and chunk-aware raw
capture in future runs.

The corpus must remain private. Public tests should use minimal redacted
fixtures generated from a private catalog that binds the source size and
SHA256, extraction rule, redaction rule, expected facts, and expected atomic
decision. Raw device identifiers, credentials, addresses, and complete logs
must not be copied into tracked fixtures.

## Required Pipeline

### 1. Immutable capture

Store the received bytes before decoding, plus source/channel identity, byte
length, SHA256, and monotonic receive-chunk boundaries. Never overwrite raw
capture with normalized text.

### 2. Transport codec

Convert bytes to records while retaining byte offsets and the original line
ending. Accept LF and CRLF only where the protocol permits them. Reject bare
CR, NUL, invalid encoding, and mixed control syntax unless a versioned codec
explicitly classifies them. Do not use unrestricted `replace("\r", "")`.

### 3. Protocol frame parser

For authoritative A90P1 frames require:

- exact required keys and no unknown or duplicate keys;
- one matching BEGIN and END per returned transaction;
- exact sequence, command, and flags equality;
- canonical integer and status encodings;
- status/return-code coherence;
- complete consumption or explicit classification of prefix/suffix noise; and
- expected command identity.

The shell prompt is a readiness hint, not a security delimiter. The command
body is untrusted and cannot terminate the receive loop.

### 4. Independent fact classifiers

Classifiers return typed facts with `PROVEN`, `REFUTED`, or `UNKNOWN`, source
byte spans, and bounded errors. One fact failure must not erase unrelated
facts. For V3406 the correct fact set is:

```text
native_release       PROVEN
debian_pid1          PROVEN
dropbear             PROVEN
display_acquisition  REFUTED by terminal attempt-3 rc=1
bounded_return       REFUTED by deadline
atomic_f1            NO_PROOF
```

### 5. Atomic decision

The F1 evaluator consumes fact objects and the immutable manifest. It does not
search raw text. It may remain fail-closed while still preserving every valid
subproof and every explicit negative fact.

## Replay Acceptance Matrix

The first implementation must include at least:

- LF, CRLF, mixed host-wrapper text, bare CR, and invalid UTF-8;
- marker split at every byte boundary across receive chunks;
- truncated BEGIN, truncated END, missing BEGIN, missing END;
- duplicate and unknown fields;
- BEGIN/END sequence, command, and flags mismatch;
- multiple valid transactions in one log;
- stale prompt, forged END, forged prompt, and forged END plus prompt;
- known `AT`/missing-character command corruption;
- V3405/V3406 late-return and missing-END evidence;
- V3406 native-release success plus terminal display failure; and
- the S22+ known-good real-plus-dummy UDC semantic oracle in its own
  classifier suite.

Every corpus item needs an expected frame list, expected fact set, and expected
atomic outcome. “Parser did not throw” is not a sufficient expectation.

## Next Bounded Unit

The next unit should be `A90 observation pipeline Phase 0`, entirely H0:

1. create a private corpus catalog and redacted-fixture extractor;
2. implement the byte-preserving line codec and strict typed fact result;
3. move the duplicated native-release validator into one pure module;
4. add the V3406 CRLF and independent-subproof regression first;
5. add strict A90P1 field and forged-prompt fixtures without changing live
   retry policy yet;
6. replay the active V3406 closure and all labeled historical A90 transcripts;
7. require zero unexplained decision changes; and
8. independently review the execution-critical closure before any later F1.

Do not begin with a broad migration of all 66 transport consumers. First
migrate the active A90 F1 path and prove parity. Historical runners can remain
frozen until their behavior is explicitly selected for migration.

No parser change may retroactively promote a closed F1 result. No new live
authority is created by this analysis.
