# S22+ FYG8 R4W1-C Odin Enumeration-Diff Observer Exception Draft

Status: `DRAFT_INACTIVE`

Policy marker: `S22+ FYG8 R4W1-C Odin enumeration-diff observation gate`

Parser boundary identifiers only:

`BEGIN_S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_V1`

`S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_STATE=ACTIVE`

`END_S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_V1`

The future active block must be byte-for-byte equal to the helper's
`rendered_policy_clause()` output. That output contains the complete action,
one-shot, recovery, timeline, no-transfer, and prohibition contract plus a
normalized clause-template digest. The embedded digest is computed with the
literal `{{POLICY_CLAUSE_SHA256}}` placeholder still present; the authority
receipt separately hashes the final rendered block:

`S22PLUS_FYG8_R4W1C_ENUM_DIFF_POLICY_CLAUSE_SHA256={{POLICY_CLAUSE_SHA256}}`

A skeletal marker/hash list is not an active policy clause.

This draft is not an authorization and must not be copied directly into
`AGENTS.md`. A later binding step must replace the exact placeholders below,
independently review the rendered clause and source, and install only that
reviewed clause in a separate policy commit.

```text
helper
  workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py
  SHA256 {{HELPER_SHA256}}

focused test
  tests/test_s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py
  SHA256 {{TEST_SHA256}}

policy draft
  docs/operations/S22PLUS_FYG8_R4W1C_ODIN_ENUMERATION_DIFF_OBSERVER_EXCEPTION_DRAFT_2026-07-20.md
  SHA256 {{POLICY_DRAFT_SHA256}}
```

The exact Odin4 binary is `/usr/bin/odin4`, size `3746744`, SHA256
`6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.

After activation, one attended observation would require both fresh tokens:

`S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-OBSERVE`

`S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-NORMAL-DOWNLOAD-CONFIRMED`

Interrupted recovery would require the separate exact token:

`S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-RECOVER-CONSUMED-OBSERVER`

The first token would authorize one exact Android read-only baseline, one
`adb reboot download`, and the observation state. It would not authorize any
Odin transfer or partition operation. The second token would attest that the
same physically attended handset remained on the same cable, hub path, and
host port and is visibly in normal Samsung Download immediately before the
single enumeration.

## Exact Observation Surface

The helper may execute exactly one bounded `odin4 -l`. It has no boot artifact,
AP archive, transfer argument, candidate execution, rollback transfer, or stock
cleanup input. It must prove in its offline gate that its source contains no
transfer surface.

The exact Odin executable must be opened and SHA-verified before device contact,
kept open across the session, and executed through that sealed descriptor. The
pathname must still identify the same inode immediately before and after the
listing. `--odin` or another executable path is not permitted.

Before the Download request it must prove exact `SM-S906N/g0q`, FYG8, completed
Android boot, stopped boot animation, orange state, Magisk uid 0, exact known
boot, stock vendor_boot, stock DTBO, stock recovery, exact ADB serial, and USB
topology. Normal Download must appear only at that topology as Samsung
`04e8:685d`, product `SAMSUNG USB`, manufacturer `Samsung`, and absent sysfs
serial.

The helper must durably consume its own observation-only one-shot state before
requesting Download. This state is distinct from and cannot create or satisfy
the retired R4W1-C candidate-consumed state. Immediately after creation, the
helper must reopen it through a direct no-follow FD and keep that FD pinned
through every later action and final-result creation. Authority and consumed
state path/inode/SHA checks must bracket the Download request, every
stabilization sample persistence, physical confirmation, Odin observation,
Android-return polling, preclosure, and final result.

## Required Evidence

Before `odin4 -l`, the helper must persist:

- every collected stabilization sample immediately as its own exclusive,
  fsync-complete record, with SIGINT, SIGTERM, and SIGHUP masked from the sample
  read through that record's fsync, preserving every collected sample on
  timeout, identity change, or interruption;
- two complete bracketing inventories of every Samsung Download sysfs endpoint;
- the complete bounded usbfs character-node inventory;
- the exact expected node with `st_dev`, inode, `st_rdev`, major/minor, mode,
  uid, gid, link count, atime, mtime, ctime, and birth time when available.

The last stable sample is the immutable pre-Odin baseline. The first complete
pre-listing bundle must match its topology, full sysfs identity, path, and all
immutable node fields. A replacement or descriptor/device-number change during
the physical-confirmation interval stops before Odin execution; it may not
become a new accepted baseline.

Immediately after the exact listing returns, fails, times out, or reaches its
output bound, or is interrupted, the helper must defer the interruption. Its
first operation must capture the same complete evidence shape. It must then
independently attempt to durably persist the after bundle, command-outcome
record, raw stdout, and raw stderr. A failure writing any one record must not
skip attempts to seal the other three; every such failure is non-PASS. The
command-outcome record must contain return, timeout/truncation, exception,
raw-output size/hash accounting, and any after-bundle persistence error before
executable rehashing, parsing, or classification. Only after complete evidence
closure may the original interruption be re-raised.
SIGINT, SIGTERM, and SIGHUP must remain thread-masked from command entry through
that closure, and an internal command interruption must retain every stdout and
stderr byte already read even if bounded process-group cleanup itself fails.
The command-outcome record must separately identify that cleanup failure while
preserving the original interruption for delivery after closure.
The evidence includes all
disappearance/race/error records, raw bounded stdout and stderr, return code,
timeout/truncation state, parsed endpoint paths, and an exact per-field diff.
Strict validation may classify the captured state only after those records are
durable. Evidence
files must be exclusive-create and fsync-complete. The helper may classify the
captured shape but must always emit `acceptance_decision=false`; this observer
cannot decide that ctime or any other mutation is safe for a later transfer
gate.

Only UTF-8, literal path-only stdout with exactly one expected usbfs path, at
most one final LF, no blank lines, no leading or trailing whitespace, and
byte-empty stderr is a strict listing. Arbitrary text, duplicate paths,
malformed output, whitespace-only stderr, or any other stderr is unsafe
evidence even when Odin returns zero.

Topology, descriptors, device number, immutable node fields, inventory
membership, endpoint ambiguity, disappearance, and command failure remain
explicit unsafe observations. A metadata-only classification is evidence, not
permission to relax those checks.

After evidence closure the operator must physically exit Download. The helper
must require the same exact Android serial and topology plus the complete
pre-run FYG8/Magisk/partition identities. PASS is only
`PASS_R4W1C_ENUM_DIFF_OBSERVER_EVIDENCE_CAPTURED` and means evidence was
captured and exact Android returned; it does not authorize a candidate or a
second observer run.

The Download request is recovery-relevant from the instant its command is
attempted, even if ADB returns an error or times out. A caught failure must wait
for exact Android return. If the host process is interrupted after durable
one-shot consumption, only the recovery mode and recovery token above may
reopen that exact consumed run. Recovery performs no reboot, Odin command, or
transfer; it only waits for and verifies the bound Android identity and closes
the canonical evidence timeline. Before any recovery device contact, the helper
must exclusive-create an attempt-numbered durable intent. An interrupted intent
counts as an attempt, Android evidence paths are attempt-specific, and a failed
or interrupted bounded recovery may be attempted only once more. Two intents
stop further helper recovery attempts. The consumed state must remain open and
pinned by direct FD, path inode, and SHA across intent creation, Android contact,
and result closure. Recovery must revalidate that pin before and after every
Android-return polling attempt, after the non-PASS preclosure fsync, and
immediately before creating the final result. A whole-session single-writer
authority lease is mandatory for both observation and recovery; it must pin the
lock FD/path inode and all policy/source inputs. Validation must bracket the
initial Android baseline, bracket `adb reboot download`, bracket each
Android-return polling attempt, follow the non-PASS preclosure fsync, and occur
again immediately before final result creation.

No durable result may contain a PASS verdict before those preclosure checks
complete. The helper must first exclusive-create and fsync a non-PASS preclosure
record. Only after the required authority and consumed-state checks pass may it
exclusive-create a final result containing PASS.

Timeline output must contain only `events:[{name,timestamp_utc}]` using the
canonical eight ordered phase names. The result must label candidate and
rollback phase names as zero-flash observation semantics. On failure, canonical
slots that were never reached are closure placeholders only; the result must map
every slot to either `reached` or `not-reached-no-action-placeholder` so a
placeholder cannot be read as a physical milestone. Before filling canonical
placeholder slots, the non-PASS preclosure must durably preserve the actual event
prefix. Recovery must reopen that semantic record and must never relabel a prior
placeholder as an actual milestone. Recovery activity must be reported in a
separate noncanonical result field and cannot affect canonical event status or
reuse a placeholder timestamp as a reached event.

## Prohibitions

This draft and any later observation clause authorize no candidate AP, Odin
transfer, flash, partition write, raw host `dd`, fastboot, Magisk module, panic,
SysRq, RDX/S-Boot command, RAM dump, qdl/Sahara/Firehose, EUD/UART write,
format, cleanup, A90 action, or write to boot, recovery, vendor_boot, DTBO,
vbmeta, BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster,
modem, bootloader, or any other partition. There is no transfer authority.

This is a host-only source draft. Current policy state is inactive, and no
device contact is authorized.
