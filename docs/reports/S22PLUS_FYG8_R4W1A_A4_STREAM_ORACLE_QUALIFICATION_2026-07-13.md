# S22+ FYG8 R4W1-A A4 Stream-Oracle Qualification

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R4W1A_STREAM_ORACLE_EVIDENCE_QUALIFIED_HOST_ONLY`

## Decision

The exact retained oracle run contains the complete evidence required by the
corrected stream-only baseline contract. A second device-side baseline capture
is not required.

This does not rewrite the consumed run. Its historical verdict remains
`FAIL_R4W1A_ORACLE_DRY_RUN_CLEANUP_OR_SHAPE`, the v1 exception remains RETIRED,
and no v1 oracle PASS record was created. A4 establishes a new host-only
qualification whose only promotion is that a separately reviewed candidate
clause may depend on this exact result.

Candidate policy remains inactive. No candidate transfer, rollback, device
contact, reboot, Download transition, Odin operation, or flash occurred.

## Implementation

New validator:
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_stream_oracle_qualification.py`

- source SHA256:
  `fa940a5ff225d0d42c7d31214458ebc4625b33be7eb0f5b32ec543342b5bcf3c`;
- test SHA256:
  `592e982d70a808e3f6f68429d4b8fb8891e78b2dd476b656c958d208b0e9cbb3`;
- result:
  `workspace/private/work/s22plus_fyg8_r4w1a_a4/stream_oracle_qualification.json`;
- result SHA256:
  `077885c4f785760720463763905e4db3453c6e262021524e6fff97700bf6b12a`.

The validator imports only the existing host-only marker parser. It has no
subprocess, ADB/PyUSB/Odin invocation, device-I/O primitive, transport, policy
activation, or promotion-record writer. ADB, Odin, and sysfs strings are only
compared as retained evidence. Its optional output is an exclusive-create host
JSON.

## Pinned Evidence

The validator reopens and pins every retained file from
`workspace/private/runs/s22plus_fyg8_r4w1a_oracle_dry_run_20260713T095754Z`:

- `result.json`, `oracle_capture.json`, and canonical `timeline.json`;
- consumed-state JSON and historical helper/test source identities;
- exact parser source SHA256
  `bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462`;
- `bugreport.zip` and empty `bugreport.stderr`;
- before/after `/bugreports` inventory JSON;
- connected preflight and both raw 2,097,136-byte observer snapshots;
- preflight/final no-Odin logs;
- retained post-run forensic parser JSON.

All regular-file identities, sizes, and SHA256 values are checked. JSON and
small binary evidence are interpreted from the same bytes that were hashed.
The parser independently opens the ZIP, performs a same-file pre/post hash,
checks all ZIP CRCs, and must reproduce the retained parser result exactly.

## Contract Result

The independently revalidated facts are:

- one-shot consumption occurred strictly between `live_session_start` and
  `candidate_flash_start`;
- timeline contains only the eight canonical ordered events;
- timeline semantics name one zero-flash bugreport capture and no rollback;
- baseline and final Android identities are exact and equal;
- Magisk root, known boot, stock DTBO, stock recovery, and orange state match;
- `sec_log_buf` is live and bound to the expected platform device;
- raw `ap_klog` and `last_kmsg` are EOF-complete and contain no R4W1 marker
  family, marker ID, phase, or PID/path token;
- both pstore console paths were absent;
- before and after direct `/bugreports` inventories are both empty;
- the stream returned rc=0, EOF, 14,461,892 bytes, exact SHA256
  `0935e3215ea39c5c9113f71a1de71e7a63de60f947878527a9926ba86aa071b1`,
  and zero stderr bytes;
- no remote file remained, so no remote cleanup was required;
- fresh parsing checks all 315 ZIP entries and recovers one complete
  2,097,136-byte `LAST KMSG (/proc/last_kmsg)` section;
- marker-family counts are zero across both archive and section;
- no Odin endpoint appears in either preflight or final evidence.

The generated result records:

```text
baseline_observer_qualified=true
second_live_baseline_required=false
candidate_clause_design_ready=true
candidate_live_authorized=false
old_oracle_pass_record_created=false
qualification_is_not_retroactive_old_policy_pass=true
device_contact=false
device_write=false
flash=false
policy_activation=false
promotion_record_created=false
```

## Validation

- Python bytecode compilation passed;
- ten focused tests passed, including the exact retained-evidence integration
  path;
- negative tests reject changed inventory, cleanup/success fabrication,
  altered timeline shape/order/time, marker fragments, and Android identity
  drift;
- `git diff --check` passed;
- `ruff` is unavailable on this host and was not installed in this unit.

## Boundary And Next Gate

A4 proves the marker-absent baseline observer. It does not prove the
marker-positive candidate path, direct-PID1 execution, candidate boot viability,
or rollback.

The next unit is host-only successor candidate-clause/helper design. It must:

1. preserve the consumed v1 helper, FAIL result, and RETIRED policy unchanged;
2. pin this validator source/test and exact A4 result;
3. accept the A4 schema/verdict only after independently reopening the result
   and every load-bearing source artifact;
4. retain stream-as-canonical behavior for the future marker-positive capture;
5. require unchanged `/bugreports` inventory and no deletion when no file is
   added;
6. keep boot-only candidate transfer, one-shot consumption, mandatory exact
   Magisk rollback, final Android health, and fail-closed marker cardinality;
7. remain inactive until separate review, binding policy activation, and fresh
   attended approval.

This report authorizes no live action.
