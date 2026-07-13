# S22+ FYG8 R4W1-A Stream-Candidate AGENTS Exception Draft

State: `DRAFT_INACTIVE`

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

This document is a host-only source for a possible future binding clause. It is
not copied into `AGENTS.md`, the ACTIVE sentinel is absent from binding policy,
and it authorizes no device contact, reboot, Download transition, Odin transfer,
candidate flash, or rollback flash.

## Proposed Binding Clause

**Narrow operator-authorized exception (S22+ FYG8 R4W1-A stream-only retained
PID1 witness boot-only live gate):** after an independent source/artifact/policy
review and fresh attended approval, Codex may perform one bounded candidate run
on Samsung S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8` using only the helper and
pins below. Policy marker:
`S22+ FYG8 R4W1-A stream-only retained PID1 witness boot-only live gate`.

Future binding activation requires this exact whole-line sentinel:

`S22PLUS_FYG8_R4W1A_STREAM_CANDIDATE_POLICY_STATE=ACTIVE`

The only executable helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_stream_candidate_live_gate.py`
SHA256
`07d9133dd01c26e9188c582226d1c0f647b6fa72935affd1fcfc99824e0c5068`.
Its focused test source SHA256 is
`0539c8391701839034855a156227c8b6c08e2adfaa3a6f16aead682714297bde`.
The fresh live acknowledgement is
`S22PLUS-FYG8-R4W1A-STREAM-CANDIDATE-LIVE`. Interrupted recovery from an
already-consumed run requires
`S22PLUS-FYG8-R4W1A-STREAM-MAGISK-ROLLBACK-FROM-DOWNLOAD`.

## A4 Baseline Qualification Gate

The helper must pin and rerun host-only validator
`s22plus_fyg8_r4w1a_stream_oracle_qualification.py` SHA256
`fa940a5ff225d0d42c7d31214458ebc4625b33be7eb0f5b32ec543342b5bcf3c`,
focused test SHA256
`592e982d70a808e3f6f68429d4b8fb8891e78b2dd476b656c958d208b0e9cbb3`,
and exact result SHA256
`077885c4f785760720463763905e4db3453c6e262021524e6fff97700bf6b12a`.
The result must have schema
`s22plus_fyg8_r4w1a_stream_oracle_qualification_v1` and verdict
`PASS_R4W1A_STREAM_ORACLE_EVIDENCE_QUALIFIED_HOST_ONLY`.

Fresh validation must equal the pinned result and prove baseline observer
qualification, no need for a second baseline live capture, unchanged empty
direct `/bugreports` inventories, canonical host stream parsing, marker-family
absence, no old oracle PASS record, no policy activation, and no device action.
The consumed v1 live verdict remains FAIL and its policy remains RETIRED. This
clause must not synthesize or depend on the retired v1 oracle PASS record.

## Exact Artifacts

Before device contact, the helper must rerun its complete offline artifact gate
and require:

- candidate raw boot SHA256
  `a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133`,
  size `100663296`;
- candidate boot-only AP SHA256
  `cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895`,
  containing exactly `boot.img.lz4`;
- marker oracle SHA256
  `bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462`;
- exact Magisk boot-only rollback AP SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- cleanup-only stock boot AP SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`;
- full FYG8 stock evidence required by the repository policy;
- the builder, manifest, static checker, R3 transport, Odin binary, and all
  subordinate hashes already pinned by the reviewed historical helper.

The candidate AP and both rollback APs must each contain exactly one
`boot.img.lz4` member. No other Odin slot or partition payload is permitted.

## Connected Preflight And Consumption

The run must begin from exactly one completed normal Android target with stopped
boot animation, orange verified-boot state, Magisk `uid=0(root)`, exact known
Magisk boot, stock DTBO and recovery, and no Odin endpoint. It must prove live
`sec_log_buf`, the exact platform bind, complete bounded reads of `/proc/ap_klog`
and `/proc/last_kmsg`, marker-family absence in both raw observers, and absence
of both pstore console paths.

Immediately before candidate transfer, the helper must durably and exclusively
create
`workspace/private/state/s22plus_fyg8_r4w1a_live_exception_consumed.json`
with schema `s22plus_fyg8_r4w1a_stream_candidate_consumed_v2`. Creation occurs
at `candidate_flash_start`, consumes the one-shot exception regardless of the
transfer result, and binds the helper, candidate AP, A4 result, target, and run
directory. A preexisting or malformed state stops the run.

## Candidate Observation

The helper may request Download and transfer the exact candidate AP once to the
boot partition only. After the original Odin endpoint disconnects, observation
is bounded to 300 seconds and requires three stable exact FYG8 Android samples.
It then proves both pstore console paths absent and executes exactly one bounded
`adb exec-out bugreportz -s` capture.

The host stdout ZIP is the only canonical marker artifact. The helper must:

1. inventory direct `/bugreports` entries before capture;
2. stream stdout to one exclusive host file while separately bounding stderr;
3. require rc=0, EOF, nonzero bounded size, and empty stderr;
4. inventory direct `/bugreports` entries after capture and require exact
   byte-for-byte JSON equality with the before inventory;
5. perform no device-side deletion under any outcome;
6. parse the exact host stream with same-file pre/post size and SHA verification;
7. validate all ZIP CRCs, unique safe entry names, `main_entry.txt`, and the
   complete `LAST KMSG (/proc/last_kmsg)` section; and
8. require exactly one R4W1 marker-family occurrence and exactly one exact marker
   in both the complete archive and the last-kmsg section.

Any added, removed, or changed remote path is non-PASS and must not be cleaned
up by the helper. Timeout, nonzero return, stderr, partial ZIP, duplicate/unsafe
entry, CRC failure, parser/stream mismatch, marker absence, foreign marker,
duplicate marker, or boundary-partial marker is non-PASS.

## Mandatory Rollback And Verdict

After bounded observation, the helper must request Download when candidate ADB
is available; otherwise the attending operator physically enters Download. It
must require one unambiguous Odin endpoint and transfer the exact Magisk
boot-only rollback AP. Only a failed Magisk transfer with the same unambiguous
endpoint may use the exact stock boot-only AP as cleanup; stock return is never
PASS.

PASS is only
`PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK` and requires all
of the following:

- exact candidate transfer completed;
- stable candidate FYG8 Android samples were collected;
- the canonical host stream passed exact marker cardinality;
- direct `/bugreports` inventory remained unchanged;
- exact Magisk rollback returned normal Android and root;
- known boot, stock DTBO, stock recovery, orange state, and no Odin endpoint
  returned.

Two post-rollback `/proc/last_kmsg` reads may be recorded as non-load-bearing
corroboration only. Their absence or mismatch cannot create or negate the
load-bearing streamed proof. A rollback-from-download invocation is permitted
only while this binding clause is active, with the exact rollback
acknowledgement, and after a valid v2 consumed state exists.

Timeline output must contain only
`events:[{name,timestamp_utc}]` with the canonical ordered phases
`live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, and `live_session_end`. Result-side semantics may
explain recovery-only or no-transfer phases; the timeline schema may not
change.

## Absolute Exclusions

This proposed exception authorizes no second candidate run, second baseline
oracle run, retired v1 helper execution, R4W1-B, raw host `dd`, fastboot,
partition-table action, Magisk module, panic, SysRq, RDX/S-Boot command, RAM
dump, qdl/Sahara/Firehose, EUD/UART write, format, wildcard or recursive device
cleanup, or A90 action. It authorizes no recovery, vendor_boot, DTBO, vbmeta,
BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem, or
bootloader write. Only the boot partition is in the future candidate and
rollback envelope.

Activation requires a separate adversarial review of the final helper, tests,
artifacts, this exact draft, and binding text; a committed exact ACTIVE clause;
and a fresh attended operator approval. Until then this remains
`DRAFT_INACTIVE` and authorizes no live action.
