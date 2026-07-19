# S22+ FYG8 R4W1-B Connected PASS / Live-Binding NO-GO Hardening Host PASS

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: record the consumed connected read-only qualification, the independent
live-binding `NO_GO`, and the host-only source corrections. No candidate,
rollback, reboot, Download transition, Odin transfer, flash, consumed-state
creation, or partition write occurred in this unit.

## Connected Result

The operator supplied the exact connected acknowledgement. The pinned helper
completed one connected read-only run:

```text
verdict      PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY
run          workspace/private/runs/s22plus-r4w1b-connected-20260719T064312Z
result       6919 bytes
result SHA   53db7c900f681310a5225e98a537988874c9f9e40df46e9cffd53d452c7ad920
PASS record  760 bytes
PASS SHA     dea447026c4aad259559c100698ee9463345026467b3cfccd90dfdcb466c067e
```

It proved exact FYG8 Android/Magisk boot, stock `vendor_boot`/DTBO/recovery,
orange state, no Odin endpoint, live `sec_log_buf`, exact platform bind, both
pstore console paths absent, one EOF-complete `/proc/ap_klog` read, and two
EOF-complete byte-identical `/proc/last_kmsg` reads. The latter are each
2,097,136 bytes with SHA256
`8ebc7e993f5b68c30ea70567ba48f135625fe7a00be8f2e8656c5e4dc3040ff4`.
The R4W1-B marker family was absent and every device-write/reboot/Download/
Odin/flash field was false.

## Independent Review

The deterministic packet was emitted under
`workspace/private/runs/s22plus-r4w1b-live-binding-20260719T064326Z` and was
internally coherent, but an independent read-only reviewer returned `NO_GO`
with three source-level MUST-FIX findings:

1. the live helper did not enforce the AGENTS-bound PASS/result file identities
   and did not fully reopen Android, artifact, and raw observer receipts;
2. the cached rollback Odin endpoint was not re-enumerated after temporal
   operator confirmation and immediately before transfer;
3. a failed candidate Odin-disconnect wait still permitted raw-park
   observation.

The prior packet and connected PASS are therefore not promotable to live. A
helper/test identity change invalidates the canonical PASS under the frozen
runbook. The exact private result remains retained as historical evidence; the
canonical PASS must be archived before a separately bound requalification.

A second hardening review then found two production-path blockers and one test
gap: the imported transport returns `stderr=None`, canonical TTY mode hides a
pre-prompt partial line from `select()`, and the intended final-reread mutation
test was unreachable. The helper now accepts the real `CompletedProcess` shape,
clears TTY input before showing the prompt, and has an actual mutation-during-
validation regression. That review also returned `NO_GO` before these fixes.

## Corrections

- live policy activation now requires one parseable exact connected-evidence
  binding in `AGENTS.md`;
- live entry stable-reads and directly checks the bound PASS/result sizes and
  SHA256 values, timestamp, canonical paths, and immutable source identities;
- the result validator now requires exact Android identity, fresh artifact
  equality, complete observer summaries and per-read receipts, canonical raw
  filenames, rc=0, EOF, empty stderr, a `64 MiB` bound, actual raw-file
  rehashes, and freshly recomputed marker semantics from the same run directory;
- PASS/result/raw bytes are reopened after validation to catch concurrent
  change;
- Download confirmation rejects prebuffered input and reads one bounded ASCII
  line incrementally within the remaining transition window; canonical TTY
  input is flushed before the prompt so a pre-prompt partial line cannot be
  completed into an accepted token;
- strict Odin enumeration requires `odin4 -l` rc=0 and no stale path; after
  confirmation it immediately requires the same one endpoint in both live and
  recovery modes, with no durable write between revalidation and transfer;
- strict enumeration handles the production transport's `stderr=None` result
  without bypassing rc or endpoint checks;
- raw park is entered only when candidate Odin disappearance returns true;
  timeout/error records no raw-park proof and continues to mandatory rollback;
- focused tests cover PASS and raw-receipt tampering, missing Android/artifact/
  receipt semantics, confirmation timeout, changed endpoint, and disconnect
  refusal.

## New Host Pins

```text
helper             3b42a52b406b7c0073fc13b1df957b165193f20a75a9b6010c96131013baec61
helper test        0016da20c765583e1adf15af105078ebefaf49ebf792fda328e25e4ba310680a
core               9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725
core test          b55db8579115ec437e7fe63b6a3b6ecef0d8cbcac54110599e85f310f3b2fd9d
packet generator   6fbe66768635e49da7b0d94387171de65bcef70607065b062ff06368507ca91b
packet test        0b833714b44920aa772f5080ac43be1db8a6a0e8a27a89e4052856ff43ca7d78
live template      fdad6dadcc43fc528b2e2b7390b4baad4115873b62182b74723613347bf956da
policy draft       deb55b14ac6c7d08ee2fd19f05b88d884740f1f1450d59c73f37093368d0b31d
```

## Validation

```text
focused helper tests       32 passed
helper + packet tests      39 passed
all R4W1-B tests           113 passed, 3 skipped
py_compile                 PASS
git diff --check           PASS
device contact after PASS  false
candidate consumed         false
live policy                inactive
```

## Verdict

`PASS_R4W1B_LIVE_BINDING_NO_GO_MUST_FIX_CLOSED_HOST_ONLY`

The final independent follow-up reproduced the production `stderr=None` path,
the PTY partial-input rejection, and the mutation-during-final-reread gate. It
reported no blocking finding and returned:

`GO_TO_HARDENED_SOURCE_COMMIT`

This verdict authorizes no device contact. Next is an independent review of the
exact hardened source commit delta, followed by retirement of the old connected
clause, a separately committed connected requalification clause with new pins,
and a new fresh exact operator acknowledgement.
