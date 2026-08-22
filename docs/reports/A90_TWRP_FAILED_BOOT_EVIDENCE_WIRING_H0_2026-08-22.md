# A90 TWRP failed-boot evidence wiring — H0

Date: 2026-08-22
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only implementation and static review
Device contact: none
Authority: none — no D0, D1, F1, candidate, approval, manifest, token, reboot,
rollback, or replay authority is created

Follow-up: `A90_UNCERTAIN_RETURN_FAILED_BOOT_EVIDENCE_CONTINUATION_H0_2026-08-22.md`
extends the same fixed observer to the evidence-only, explicitly uncertain
TWRP-after-physical-return continuation branch. It does not revise this
report's original eligibility or proof claims.

## Result

The existing A90 minimal F1 owner now has a first-opportunity failed-boot
evidence path. It remains inactive because changing the owner, adapter, and
postrollback consumer changes their execution-critical closures and makes all
earlier review leases stale.

The live behavior added by this unit is deliberately narrow:

1. it runs only after the candidate helper proved one exact boot write,
   readback, and confirmed TWRP System return, but candidate health did not
   pass;
2. it durably records `26-failed-boot-evidence-intent.json`;
3. it waits through bounded normal USB reboot churn until one exact A90
   Recovery endpoint and the qualified recovery ADB serial are present;
4. it reads `/proc/cmdline` and `/proc/last_kmsg` once each with fixed argv;
5. it durably stores exact private raw bytes and publishes
   `27-failed-boot-evidence-result.json`; and
6. it proceeds to the existing V2321 rollback only when every observer
   process is quiescent.

No new operator confirmation, manifest field, candidate action, transfer
primitive, mount, shell, or general ADB command was added.

## Exact eligibility and command surface

Evidence is ineligible for `PRE_WRITE_FAILURE`,
`WRITE_OR_READBACK_UNCLASSIFIED`, candidate-helper non-quiescence, healthy
candidate PASS, and exact uncertain System return. Those paths retain their
existing decisions and do not create records `26` or `27`.

The only source commands are equivalent to:

```text
/usr/bin/adb -s <qualified-recovery-serial> exec-out cat /proc/cmdline
/usr/bin/adb -s <qualified-recovery-serial> exec-out cat /proc/last_kmsg
```

The caller cannot select the executable, serial, command, source path, mount,
or output path. Native `04e8:6861` never opens ADB. The capture method is a
private backend method reached only through the existing reviewed owner CLI;
arbitrary same-UID module imports remain outside repository authority, as they
already are for the adapter's existing `flash()` method.

## Proportional reboot tolerance

The observer does not require USB inventory bytes or bus/device numbers to
remain identical across reboot. During a maximum 30-second settle window it
accepts these normal intermediate states:

- no Samsung endpoint;
- exactly one A90 Native `04e8:6861` endpoint;
- exactly one A90 Recovery `04e8:6860` endpoint whose qualified ADB row is
  temporarily absent or `offline`; and
- final transition to that same qualified serial in ADB state `recovery`.

A foreign or multiple Samsung endpoint, wrong serial, malformed producer, or
non-quiescent process stops the observer. The total device-command budget,
including settle and the two reads, is 60 seconds. Private file fsync remains
a durability requirement but is not falsely described as an interruptible
device-command timeout.

## Evidence and failure semantics

`/proc/cmdline` is bounded to 64 KiB and must be non-empty ASCII.
`/proc/last_kmsg` is bounded to 8 MiB and must be non-empty. Capture success
records exact byte counts and SHA-256 values, the final USB and ADB inventory
digests, quiescence, and raw durability. The raw files are direct private
mode-`0600`, link-count-one files created with `O_EXCL|O_NOFOLLOW`, followed
by file and directory fsync.

An empty `last_kmsg`, ordinary command failure, timeout, or unavailable final
Recovery becomes `NO_PROOF_OBSERVER`; it does not become a device refutation.
A malformed or surviving observer is different: it records non-quiescence,
publishes an exact recovery-required park, and never overlaps rollback.

The journal crash cuts are explicit:

- `26` without `27`: evidence intent consumed, no rollback;
- quiescent `27` without `30`: candidate consumed, same rollback remains the
  only continuation;
- invalid or non-quiescent `27`: no-rollback park;
- `26 -> 27 -> 40`: canonical observer-non-quiescent park; and
- quiescent `26 -> 27 -> 30 -> 31`: the existing one-shot rollback semantics.

The candidate-neutral postrollback consumer accepts both historical rollback
journals and the new evidence-bearing form. The new form additionally requires
the exact confirmed candidate effect and a quiescent evidence result. The
fixed H27 historical reconciler was not changed.

## Review and proportionality

The first independent adversarial pass returned `NO_GO` for possible observer
and rollback overlap, missing crash-cut distinctions, weak result typing, and
an incomplete postrollback consumer. Those findings were reproduced and
fixed. A second pass exposed swallowed lease loss and malformed-result
downgrade; those were also fixed. The final bounded delta review returned
`PASS_GO_H0_IMPLEMENTATION_REVIEW`.

The tracked production delta is larger than the two read commands because it
must preserve legacy journals, publish intent before contact, retain exact raw
bytes, distinguish observer failure from device failure, and keep rollback
one-shot. Runtime and operator surface did not grow proportionally: there is
still one owner, one candidate attempt, at most one rollback, and no new
approval step. Duplicate endpoint-epoch equality and hard fsync timing were
explicitly rejected as over-strict.

This review disposition is not the canonical owner or postrollback review
lease consumed by live code. Fresh execution-closure review artifacts and the
ordinary candidate qualification, D0, and attended F1 binding would still be
required before any future run.

Current host-only closure calculation makes that stop mechanical:

- minimal owner: `c22b5a8ae6b630a178c31db22b6a9167ac6ed969b1d894a29c3399275db44c5e`;
- postrollback recovery: `a6bf12eef5a5c9514a2c8613cbfdcd4c4e0c8f5800f393b6b728b3048827af2c`;
- existing postrollback review binding: `a0cc1b26a3c7f1c0f36801e8de990a4f5502cbaa11b60daa6b9853def305284d`.

The last two values differ, so the existing review file cannot activate the
changed consumer.

## Validation

- 129 focused owner/adapter/postrollback tests passed;
- 368 adjacent A90 owner, return, receipt, recovery, H30, and redaction tests
  passed;
- all six touched Python files passed `py_compile`; and
- `git diff --check` passed.

The new evidence tests used temporary host fixtures and did not invoke ADB,
enumerate USB, or contact a device or network endpoint. No private live-run
state was changed.

## Next unit

The evidence channel is now implemented at H0. The next independent host-only
kernel unit remains stock MPGen catalog closure: reproduce the stock
RO/WK/WU/AW `3/1/2/0` policy and deterministic measured bytes. Only after both
that kernel input and a fresh runtime closure review exist should a new
candidate/F1 question be posed.
