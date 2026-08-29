# S22+ FYG8 P3.19 D0 fresh-baseline V3 repin

Date: 2026-08-29

Status: **IMPLEMENTED / INDEPENDENT PASS_GO / D0 COMPLETE / NOT F1 ACTIVE**

## Result

The exact `d1-fresh-baseline-3` run is now a valid consumed predecessor. It
performed one normal Android reboot and retained a 39,594-byte result with
SHA-256 `8dc828d3`. The result proves a changed boot identity, healthy rooted
FYG8 before and after, stable selected serial and topology, complete raw
evidence, and zero other-target commands. Candidate transfer, device writes,
Download, Odin, partition payload, F1, live authority, and replay are false.
The outer pre-F1 journal is `CLOSED` with one D1 effect; its 1,287-byte close
record has SHA-256 `ea7de807`.

The first prepare invocation stopped before device contact because the exact
private campaign parent did not yet exist. Creating only that fixed directory
as current-owner mode 0700 was the single bounded host preparation repair. No
source or binding changed, and the corrected prepare was the only re-entry.

## Minimal V3 successor

The prior D0 V2 source and reducer are permanently bound to the consumed
`d1-fresh-baseline-2` namespace and cannot consume the V3 result. They remain
byte-preserved. The successor therefore adds two versioned files rather than
rewriting reviewed history. The initial implementation is preserved by commit
`d669b84b45`; independent review then required a bounded repair. The current
artifacts are:

- D0 producer: 77,915 bytes / `adc3e979`;
- normalized reducer: 75,232 bytes / `848e20d8`;
- reviewed execution binding: 14,545 bytes / `fd595a25`.

The D0 namespace is separate from the D1 parent because D1 V3 permits only its
fixed arm and run children. The D0 behavior itself is unchanged: one exact
2,097,136-byte `/proc/last_kmsg` read, immutable raw-first parsing, fixed exact
target/current-boot continuity, zero other-target commands, typed consumed
stop on uncertainty, and no write, reboot, Download, Odin, payload, or F1.

The reducer does not reproduce the D1 result grammar. It compiles the exact
reviewed D1 V3 source and requires `_validated_static_inputs()`,
`_validated_execution_inputs()`, and `_post_validate()`. The caller-provided
result must be canonical-equal to that reopened result, after which the exact
result, D1 source, and D1 binding are read once more. V1/V2 paths, substituted
health, and forged raw inventory fail closed.

## Independent-review repair

The first hostile review returned `CHANGES_REQUIRED`, not `PASS_GO`. It found
five local D0-consumer gaps. The repair now:

- uses typed structural equality for nested execution bindings and results;
- refuses any stale arm, stop, or run directory before loading D1 evidence and
  reopens the exact arm-only parent before transport construction;
- rereads the consumed D1 V2 source, binding, arm, and stop after D1 V3
  `_post_validate()` without changing the reviewed D1 V3 source;
- records the exact consumed D1 V3 result receipt in the durable D0 arm; and
- requires every reconstructed raw-ADB handle to have return code zero, no
  timeout, no overflow, no producer error, and empty stderr.

These checks do not add a device action or widen the D0 command set. They close
pre-intent, provenance, and retained-result seams in the already bounded
consumer.

The first repair re-review still returned `CHANGES_REQUIRED` because several
scalar integer comparisons in the reducer retained Python numeric coercion.
The final repair requires exact integer types for candidate plan counts, arm
link count and attempt, observer byte counts, raw-receipt size, and normalized
raw cardinality. Its hostile test drives the real `_validate_d0()` path with
float and bool substitutions rather than testing the equality helper alone.
Final independent re-review found no remaining blocker and returned
`PASS_GO_P319_D0_FRESH_BASELINE_V3_H0_CAPABILITY_V1` for these exact bytes.

## Raw-first boundary

The new producer remains the twentieth active observer source. The current
76,349-byte auditor has SHA-256 `b86b0a67` and normalized self-hash `072a31b8`.
Its `-14` 15,075-byte `5dae3014` receipt is mode 0400/link-count one and preserves the
128-member pre-boundary and 126-member closed-observer inventories. The source
census changes only from 1,744 to 1,746 for the two new Python files;
subprocess-module census remains 412. The `-13` 15,075-byte `b70ac022` receipt,
`-12`, and all earlier predecessors remain unchanged.

## Validation and boundary

Focused V3 tests pass 18/18, including exact post-run D0 and normalized-result
reopening. They reopen the actual D1 V3 result, reject V2
paths and forged health/raw data, keep review and approval checks before
acquisition, exercise one exact raw-first read, reject short/stderr/nonzero
captures and target/topology/boot drift, reject stale namespaces and malformed
raw-handle outcomes, bind the D1 result receipt in the arm, reread consumed V2
evidence, and preserve consumed no-replay state. Raw active-source seams and
deterministic documentation pass 22/22. The combined D0 V2/V3, D1 V3,
taxonomy, and current-state guard passes 117/117; the unchanged common
Process-v2 four-module selection passes 142/142.

## Executed D0 result

The operator supplied the exact reviewed approval for binding `fd595a25`. The
runner consumed it once and published an 874-byte `84383f92` arm, a
57,888-byte `360a3849` result, and one 2,097,136-byte `ec4fe9fb` raw observer.
The raw capture receipt is 571 bytes / `b1298b6f`. All nodes are mode 0400 with
link count one, and no stop exists.

The result is `PASS_P319_D0_FRESH_BASELINE_RAW_V3`: exactly one FYG8 target,
stable D1-returned boot and topology, nine successful raw-ADB handles covering
27 owned children, zero stderr, no candidate marker, and no write, reboot,
Download, Odin, partition, F1, other-target command, or replay. The host-only
reducer then published the canonical 56,204-byte `fba4dc9f` normalized V3
baseline at mode 0400/link count one; it validates as fresh and clean while all
ready, live, candidate-success, causal-result, D0/D1/F1-authority, and replay
flags remain false.

The approval is consumed and grants no remaining D0 authority. The existing
Process-v2 integration code still names the V2 baseline and therefore remains
unchanged until its separately reviewed V3 successor. F1 remains separately
attended.
