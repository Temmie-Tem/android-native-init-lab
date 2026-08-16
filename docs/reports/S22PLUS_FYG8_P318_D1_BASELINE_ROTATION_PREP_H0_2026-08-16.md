# S22+ FYG8 P3.18 D1 Baseline-Rotation Preparation H0

Date: 2026-08-16 KST

## Status

`PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1`

This is an independently reviewed H0 capability record. It creates no D0, D1,
F1, recovery, replay, live, A90, or S20+ authority. The binding manifest is
`pass-go`, but the adapter still requires a fresh exact attended operator
approval before it can create an execution snapshot, run directory, durable
start, or device command.

## Need

The first P3.18 live-prerequisite D0 correctly stopped on three residual P3.17
Carrier records. The typed stop-receipt repair and downstream Process-v2
requalification are independently approved, and current ready remains 2,778
bytes at SHA-256 `082c046f9091`. A single normal Android reboot is still needed
to rotate the retained baseline before another connected D0.

The failed P3.18 D0 is not promoted into a reusable success receipt. It lacks
durable final continuity and final health. This adapter instead uses the latest
available durable healthy D0 only as a static exact-target and expected-health
reference, then rereads and validates all actionable state before any reboot.

## Exact Inputs

The independently reviewed binding manifest is
`workspace/public/src/device-action/manifests/s22plus_fyg8_p318_d1_baseline_rotation_v1.json`.
It is 3,129 bytes at SHA-256
`dc5d737146ec5974f195fcf749f114e6b592be21dae27ee7fca4a86e64701cdf`
and binds:

- adapter `workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_baseline_rotation_d1.py`;
- current P3.18 ready manifest, 2,778 bytes, SHA-256 `082c046f9091`;
- durable healthy D0 `p308-post-rotation-health-20260807-1/result.json`,
  2,934 bytes, SHA-256 `e75d62206d0a`;
- exact S22+ target profile, 2,285 bytes, SHA-256 `7afa7b690b71`;
- reviewed P2.96 one-reboot primitive, 18,578 bytes, SHA-256
  `bfec4bc9c947`; and
- exact D0 runtime source, 40,024 bytes, SHA-256 `fc4849381bfc`; and
- host ADB source `/usr/lib/android-sdk/platform-tools/adb`, 716,968 bytes,
  SHA-256 `05a1a4435e43`.

The adapter stable-reads those regular, single-link bytes once and executes the
primitive and D0 runtime from the bytes it hashed. It supplies only an
adapter-owned canonical-JSON SHA-256 stub for the D0 source's otherwise broad
F1 import, so no current unbound local Python module enters the reboot path.
The binding manifest pins the adapter's own size and SHA-256. The approval
suffix is the SHA-256 of the entire binding manifest, so changing the adapter
or any named input changes the required approval. The reviewed manifest digest
is not live authority. The only approval string eligible for a later attended
operator decision is
`DEVICE-ACTION-D1-P318-BASELINE-ROTATE-V1-APPROVE:dc5d737146ec5974f195fcf749f114e6b592be21dae27ee7fca4a86e64701cdf`.

## Target and Topology Rule

The historical D0 topology is explicitly not current authority. P3.17 proved
that a physical cable move can legitimately change the host path while leaving
the exact device identity unchanged. Requiring the old path would turn a
historical observation into a standing topology lease.

Live selection instead requires:

1. exactly one online ADB row with `model:SM_S906N` and `device:g0q`;
2. that row's serial SHA-256 equals the durable exact-target identity before
   any target-specific topology query;
3. live model, device, FYG8 incremental, rooted completed Android, stopped boot
   animation, verified-boot state, boot image, vendor_boot, DTBO, recovery, and
   no-Download state all equal the bound healthy reference before the effect;
4. the current topology and a privacy-preserving digest of each inventory
   row's serial, state, and stable metadata are recorded in the durable start;
   exactly one ASCII-decimal ADB `transport_id` is explicitly ephemeral;
   missing, malformed, Unicode-digit, or multiple tokens reject; and
5. exact serial, stable inventory digest, selection topology, and both
   initial and returned-health snapshot topologies remain identical.

Zero or multiple S22+ candidates, a serial mismatch, current-topology drift,
health drift, or any Download endpoint stops fail closed. A serial mismatch and
multi-candidate ambiguity reject before `adb get-devpath`, so no target-specific
command is sent to a lookalike S22+.

## One-Shot Action

The inherited reviewed primitive permits exactly:

`adb -s <private-bound-s22-serial> reboot`

It writes a no-replace durable `start.json` before that command, sends the
command once, requires reboot initiation within 60 seconds, and requires exact
healthy return within 240 seconds. The returned boot ID must differ. No second
reboot, Download request, Odin invocation, candidate or rollback transfer,
partition payload, persistent setting, or F1 action exists. The attended
contingency is `stop without retry`; an observer failure after the start is an
uncertain consumed D1, not permission to replay it.

Both start and result gain the complete P3.18 adapter binding. The historical
D0 contributes expected identity and health only. Every mutable live predicate
is reread before the effect, and final identity/health is independently read
after return.

The live run directory is not caller-selected. The manifest binds the single
fixed direct path `p318-baseline-rotation-1`; directory creation and
`start.json` publication are both no-replace. A prior or uncertain invocation
therefore consumes that path and the same approval cannot be redirected to a
second path. Lexical `..`, alternate absolute paths, and caller `--run-dir` or
`--adb` options reject before snapshot publication or device contact.
After review and exact approval validation, a separate fixed no-replace arm is
file-fsynced and directory-fsynced before the ADB snapshot or any connected
read. That arm consumes the approval even if a later host or pre-effect read
fails, so a second invocation cannot reuse it.

## ADB Execution Bytes

After both independent review and the exact approval compare succeed, but
before any device contact, the adapter publishes the verified ADB bytes to one
fixed private executable snapshot by file fsync, atomic no-replace link, and
directory fsync. The parent must be direct, owner-controlled mode 0700; the
snapshot must be a single-link mode-0500 regular file with the exact bound size
and SHA-256. Live execution accepts no caller-supplied ADB and uses only that
snapshot. It reopens the snapshot after the state machine returns.

The host ADB ELF's dynamically loaded libraries and host kernel are not
byte-frozen by this unit. This report claims exact executable bytes, not a
hermetic host userspace or signed package-provenance closure.

## Host-Only Validation

- The exact pinned P2.96 fixture executes one synthetic reboot, zero
  other-target commands, and zero device contacts.
- A current topology different from the historical topology is accepted, but
  a topology change within one D1 rejects.
- Wrong-serial and two-S22 inventories reject before the topology query.
- ASCII numeric `transport_id` rotation across reboot is accepted; its missing,
  malformed, Unicode-digit, and multiple-token forms reject. Same-count and
  same-model stable-identity replacement changes the retained inventory digest,
  and a snapshot topology different from selection rejects.
- A synthetic review-pending manifest rejects `--live` before run-directory
  creation or device contact.
- Duplicate keys, non-finite values, boolean-for-integer substitution, and
  extra binding keys reject.
- Ambient fake D0/F1 modules cannot replace the verified D0 runtime source.
- Caller ADB/run-directory options and lexical path escape reject.
- A mode-0400 hostile-umask arm is durable, single-link, and no-replace.
- A temporary ADB execution snapshot is exact, mode 0500, single-link,
  idempotently reusable at the same bytes, and rejects a mode mutation.
- Focused adapter tests pass 16/16; the independent review reproduced focused
  66/66, P3.18 164/164, and common Process-v2 120/120, plus Python compilation
  and scoped diff checks.

No canonical approval arm, run directory, or private ADB execution snapshot was
created by the fixture. No device, USB, ADB, reboot, Download, Odin, payload,
partition, candidate, rollback, A90, or S20+ action occurred.

## Independent Review Result

The independent reviewer attacked:

- adapter self-identity and binding-manifest/approval transitivity;
- verified-byte D0 runtime execution and exclusion of ambient local imports;
- all pinned-input hash, size, regular-file, link-count, duplicate-key, and
  stable-read gates;
- wrong serial, zero/two candidates, old-versus-current topology, and
  full-inventory or mid-run topology drift, including health snapshots;
- pre-effect health and no-Download gates;
- one durable start, one reboot command, changed boot ID, returned exact health,
  and no replay after uncertainty;
- ADB no-clobber snapshot publication and caller-path rejection; and
- fixed run-directory containment and approval no-reuse; and
- absence of D0/D1/F1/recovery/replay/live and cross-target authority.

Those attacks passed against adapter SHA-256 `2b798b4ab73e`, and the final
manifest records `PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1`. This
qualifies only the H0 capability. It does not authorize a run. A new exact
approval must bind the post-review manifest digest and be supplied while the
operator is attended.

## Subsequent D1 Result

The operator subsequently supplied the exact reviewed approval while attended.
The adapter published the fixed durable arm, selected only the exact S22+ from
the two-device inventory, and sent one normal Android reboot. The durable result
is `PASS_P318_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`: the boot ID changed, rooted
boot-completed Android and stopped boot animation returned, boot, vendor_boot,
DTBO, and recovery identities remained unchanged, and Download stayed absent.
No command was sent to S20+.

The private evidence is arm 700 bytes at SHA-256 `a19e710d6da2`, start 5,097
bytes at SHA-256 `82c75e33c14b`, and result 5,647 bytes at SHA-256
`ec20fb6b46e8`. All are direct, single-link mode-0400 files. A strict reopen
confirmed the reviewed manifest binding, one reboot, changed boot ID, unchanged
boot and supporting partitions, and false candidate, partition, Odin, Download,
F1, device-write, and other-target-command fields.

The arm and fixed run path are consumed and cannot be replayed. This successful
D1 creates no D0, F1, recovery, replay, or live authority. Any subsequent
connected read requires its own current authority.

## Subsequent Fresh D0

A separately requested bounded D0 then selected the exact S22+ from the
two-device inventory and sent no command to S20+. Rooted boot-completed FYG8
health, stopped boot animation, boot, vendor_boot, DTBO, recovery, and
no-Download state passed. The observer read `/proc/last_kmsg` to EOF at exactly
2,097,136 bytes with empty stderr, SHA-256 `31cd48ab631f`, and zero marker-family
and exact-marker matches. The baseline is clean.

The strict durable reopen validated `result.json`, 2,941 bytes at SHA-256
`d14074c29673`, against the current 2,778-byte P3.18 ready manifest and the raw
observer. Device writes, reboot, Download transition, Odin, partition transfer,
F1 authorization, and live authorization are all false. This D0 creates no
prepared Process-v2 binding; preparation and any later F1 approval remain
separate steps.

## Subsequent Process-v2 Preparation

A separately requested D0-only Process-v2 preparation first revalidated the
current ready manifest and execution closure without device contact. An initial
invocation named the F1 core run root instead of the live-adapter run root and
was rejected by the direct-child path grammar before directory creation or
device contact. The corrected invocation used the fresh fixed direct child
`s22plus-fyg8-p318-live-1`, selected only the exact S22+ from the two-device
inventory, and repeated the clean connected read without sending a command to
S20+.

The preparation binds bundle SHA-256 `a48572090de9`, execution-closure SHA-256
`fb4805c68285`, the current candidate and exact rollback, the clean 2,097,136-
byte `31cd48ab631f` baseline, and the exact private target into approval binding
SHA-256
`fd68d3b4713d13afceaabdc5f97240f76808a5be2d09fc59b8853bcfd6e39136`.
The private evidence is:

- `prepared.json`, 9,611 bytes, SHA-256 `c6f36504430c`, mode 0400, link count 1;
- preflight `result.json`, 2,945 bytes, SHA-256 `dc5460f9cfa1`, mode 0400,
  link count 1;
- P3.00 USB trace binding, 1,712 bytes, SHA-256 `f7e3624a0660`, mode 0400,
  link count 1; and
- private target, 107 bytes, SHA-256 `94a7c1e84513`, mode 0400, link count 1.

Production `load_prepared()` reopened those bytes against the current manifest,
current source closure, D0 result, private target, and P3.00 binding. The run has
no transaction directory, journal, observer guard arm, terminal result, candidate
transfer, or rollback transfer. Its recorded flags remain
`device_writes=false`, `reboot_requested=false`, `odin_invoked=false`,
`partition_transfer=false`, `f1_authorized=false`, and
`live_authorized=false`.

The exact approval string eligible for a later, separate attended operator
decision is
`DEVICE-ACTION-F1-V2-APPROVE:fd68d3b4713d13afceaabdc5f97240f76808a5be2d09fc59b8853bcfd6e39136`.
Preparation does not activate it. No F1 execution, reboot, Download transition,
Odin invocation, payload, partition transfer, candidate, rollback, recovery,
replay, A90, or S20+ action or authority follows from this record.
