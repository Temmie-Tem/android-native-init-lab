# S22+ FYG8 P3.19 Process-v2 Integration Prerequisites H0

Status: `IMPLEMENTED_REVIEW_PENDING`

This unit is host-only. It creates no ready or run manifest, approval, fresh
baseline, device authority, recovery authority, or live authority. It does not
contact ADB, USB, Odin, the S22+, the A90, or the S20+.

The integration result is deliberately
`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`. Static experiment executability
passes, while four pre-live blockers remain:

1. `BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY`;
2. `CONSUMED_CANDIDATE_REGISTRY_MISSING`;
3. `FRESH_BASELINE_MISSING`; and
4. `REQUALIFICATION_REQUIRED`.

Runtime evaluability witnesses remain `PENDING_FRESH_CANDIDATE_RUN`. That is a
post-run causal-classification gate, not an extra pre-approval blocker: a
missing bind/probe/status witness must prevent causal interpretation of the
result, but it cannot be observed before the future candidate runs.

## Result-contract arming

The adapter now derives its admitted terminal set by executing the exact
P3.19 stock C encoder from the bound 435334-byte source
`0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9`,
placing each 128-byte envelope in the real Carrier record, and decoding it
through the real host adapter. The native harness is compiler-bound to
`/usr/bin/x86_64-linux-gnu-gcc-15`, 1305304 bytes,
`b5f1b773a7c733738352000c92a077dc5852a1a2fc6d836b1e411be1e9ec5f88`,
with version-output SHA-256
`60f7dc07ed00e918c903d995b6f86bfcd5452856f75f2816cc8ca379ce2b5344`.
Another `CC`, compiler-byte drift, or version drift fails closed.

The publisher-reachable decoded result contract is:

| detail | stock state | admitted proof class |
|---|---|---|
| `0x6724` | `COMPLETE` | `NONCAUSAL_SUCCESS_PATH` |
| `0x6725` | `INCOMPLETE` | `NO_PROOF_EXPERIMENT_PRECONDITION` |
| `0x6726` | `AMBIGUOUS` | `NO_PROOF_OBSERVER` |

`COMPLETE` is intentionally noncausal because this stock witness adapter keeps
`causal_result_allowed=false`. `INCOMPLETE` is admitted as experiment
precondition no-proof only with exact required-module results and gap-free
retained record accounting; missing or contradictory evidence falls back to
observer no-proof. Detail/state swaps, Carrier-state swaps, proof-class swaps,
an alternate compiler, and publisher-unreachable direct state combinations
are hostile controls. A state that the exact encoder and decoder cannot
round-trip is not admitted.

## Experiment executability closure

The P3.17 fixed-point extractor is rerun against its exact inputs and must
regenerate the retained 496664-byte `67042a70...` receipt byte-for-byte before
the unchanged QUP/I2C upstream projection can be reused. P3.19 replaces the
P3.17 diagnostic parent with the stock chain:

`QUPv3 wrapper -> 994000.i2c -> MAX77705 MFD client -> max77705-usbc child`.

The combined fixed point contains 22 nodes and 47 deduplicated edges: 25
`FW_DEVLINK_DT_SUPPLIER_CLOSURE`, 21 `DEVICE_INSTANTIATION_CLOSURE`, and one
`DRIVER_CONSUMED_DT_REFERENCE_CLOSURE`. All three relationship families are
offered every frontier node. The exact 73-row plan, derived EUD index 38, stock
module bytes, `MFD_DEV_NAME=max77705`, `max77705_i2c_probe`, and
`mfd_add_devices(max77705_devs)` child creation are bound. The P3.17 diagnostic
driver is forbidden from the roots, edges, and providers.

This is `PASS_SOURCE_CLOSURE_RUNTIME_GATES_PENDING`, not a causal or live PASS.
Future module results, MFD/PDIC bind, initial status/classification, VBUSDET,
probe, and retained Carrier evidence decide the post-run classification.

## Recovery usability versus an artifact pin

The rollback claim is not inferred from reopening an AP. The prerequisite
audit binds the exact 23367721-byte rollback AP `d2373bf8...`, verifies its
single regular `boot.img.lz4` member, and reopens the P3.18 completed rollback
attempt, same-path `rollback_bound_exact` topology record, journal records
0010 through 0018, 19-record `CLOSED` head, post-rollback health, and close
audit. The retained transfer is `odin_transfer_completed`, attempt 2 is absent,
and final health is closed and healthy. This proves historical usability of
that exact recovery path; it grants no new recovery invocation.

## No-replay boundary

The exact boot-only candidate AP is reopened and its one-member shape is
verified. Forty public manifests and 2268 selected durable manifest/run/journal
JSON files plus the append-only campaign ledger show that the proposed P3.19
live-run/candidate pair is absent. The 32-hex Carrier observation identifier is
also kept distinct from the Process-v2 live-run identifier namespace.

The generic runner's real journal and `_begin_transfer_attempt` functions are
then exercised in three fresh Python processes. Attempts 1 and 2 survive
reopen; attempt 3 is rejected; no backend function, transfer, ADB, USB, or Odin
call occurs. This proves the two-attempt cap within one prepared run directory.

It does **not** prove cross-run candidate consumption. The generic live runner
does not consume an authoritative global registry, and no such registry is
present. Therefore this unit does not claim no-replay closure and blocks
Process-v2 integration instead of treating per-run durability as global
durability.

## Raw-first pin granularity

The retained raw-first auditor is 62595 bytes, SHA-256 `58427607...`; its
retained `-05` receipt is 11012 bytes, SHA-256 `5f7b2b07...`, mode `0400`, link
count 1. An on-disk copied-population experiment establishes the exact drift
granularity:

- a neutral Python file changes only
  `all_revalidation_python_files_scanned`;
- a neutral host-only subprocess file also changes
  `subprocess_modules_scanned`;
- deleting those files restores the exact baseline; and
- changing a bound S22+ acquiring source fails closed.

The semantic pin therefore excludes exactly those two census counters and
keeps every observer count, inventory, source identity, function hash, and
behavioral field. The stored `-05` and current 1733-file/412-subprocess
populations project identically to SHA-256
`15beb53b5ca52676c95b24c2bea34f74a2cbf2bf0b8f234004d98560c9351a95`.
The earlier override-only experiment is not cited as authority; this test uses
actual files in a copied on-disk population.

## Current source-key drift

The reviewed `candidate-qualification-v1-20260821-08` intent pins 436 source
keys and the old 27318-byte adapter `62531ec3...`. The current closure has 437
keys and the 44401-byte adapter `9cfb20e5...`. Three source-key entries differ:

- `adapter`;
- `adapter_closure:s22plus_fyg8_p319_stock_process_v2_adapter.py`; and
- `adapter_closure:s22plus_fyg8_p319_result_contract_arming.py`.

The arming source is absent from the old intent and present in the current
closure. The integration audit compares the full candidate qualifier
`SOURCE_KEYS`, not only the top-level adapter file, so an arming-only mutation
also requires requalification. The current-source digest is
`a4492358e712aa5fea472b17cd35a84ea541471900565e202c050b3e914f8909`;
the pinned-intent digest under the integration auditor's canonical encoding is
`576d67a6e3114679f4179770b1e4d07e96ad409d0bdc9db5a7b74ad9d4dffb96`.

## Receipts and validation

- prerequisite receipt: 11155 bytes,
  `9fa0f994fe30419f10acc2965ed507cf6f1ebd8ac5f7267fef9ac6d8588d4ca0`,
  mode `0400`, link count 1;
- current integration receipt: 57123 bytes,
  `d0380d7d9dab635fb20aa365b8251023bf286b6ea5c3347b27e1d38330085307`,
  mode `0400`, link count 1; and
- the superseded pre-compiler/SOURCE_KEYS-strengthening `-01` integration
  receipt remains preserved at 14843 bytes, `70349b76...`.

The focused arming, executability, prerequisite, and integration suite passes
43 tests. Relevant docs and taxonomy pass 86/86, and the common Process-v2
selector passes 122/122 (`22 + 28 + 47 + 25`). The first independent full P3.19
selection actually ran 532 tests: 527 passed, four failed on the four stale
GOAL prose guards, and one errored while regenerating the materialization
because its configured `/mnt/android-lab-logical/vendor_dlkm/lib/modules`
source is absent on this host. After replacing those four duplicated prose
literals with one shared semantic assertion, a fresh full selection again ran
532 tests: 531 passed, zero failed, and only the same unavailable mount-path
regeneration errored. The materialization test passes separately when rebound
to the already identity-bound
`stock-witness-runtime-v1-20260821-32/module-bytes` copies; no test logic or
expected hash is changed. Thus 531/531 is a post-correction result after one
explicit unavailable-input exclusion, not a true description of the original
commit-time run. The integration receipt contains no ready, run, approval,
causal, candidate-success, D0, D1, F1, recovery, replay, or live authority.

## Required next order

1. implement and independently review a global consumed-candidate registry
   that the real live runner consumes at the candidate-attempt boundary;
2. rerun P3.19 candidate qualification after this changed adapter closure is
   frozen and reviewed;
3. obtain and execute a fresh exact S22+ baseline rotation only under its
   separate D1 authority; and
4. only then build and independently review a Process-v2 ready manifest.

No later step inherits authority from this report.
