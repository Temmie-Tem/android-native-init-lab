# S22+ FYG8 R4W1-A AGENTS Exception Draft

State: `DRAFT_INACTIVE`

This document is a review source only. It does not activate device contact,
`bugreportz`, Download mode, Odin, a candidate transfer, or rollback. Neither
active sentinel below is present in binding `AGENTS.md`.

The proposed helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_live_gate.py`
SHA256
`6dcf003c2c0ef186e4001af44da8cc526014d1704c8b25d7ba04788afd9ca577`.
Its focused test source currently has SHA256
`c6b650024db29ad97919e3896d19693efca365bb05f5da27031518e2e73e78dd`.
Any helper edit invalidates this draft pin and requires a complete re-review.

## Common Preconditions

Every mode must first verify the complete R4W1-A host artifact contract:

- candidate raw boot SHA256
  `a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133`,
  size `100663296`;
- candidate strict LZ4 SHA256
  `0bf83af2bb7167aae4a57be1686599aa99fe9e75ccd7aa89128da799a4c14a99`;
- candidate boot-only AP SHA256
  `cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895`,
  containing exactly `boot.img.lz4`;
- candidate manifest SHA256
  `3b9b5c0f0d3bac818a010cb7682e1146eaa50d5feec8a16324a039bbd5d2f85b`;
- exact R4W1 Image SHA256
  `9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c`;
- builder SHA256
  `081d608ef54ddd171aaa2013c5b06eb33b72aba760192e66ac023dc2f23e759f`;
- independent checker SHA256
  `cb2fb233370463135d6f8a26c2fbd93fb3404c973aa5b326a94c6ec149c2f711`
  and exact rerun result SHA256
  `fc528ba9c8acce18a636d398a13add42a7882e7bfd505e82d63ff861e0963a0b`
  with verdict `PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT`;
- marker oracle SHA256
  `bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462`
  and audit SHA256
  `f243191c985caf918a2a4504be349fdaa133c10b75caab973c71b1e31c1610dd`;
- reviewed R3 transport/identity primitive source SHA256
  `f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4`;
- reviewed Odin primitive source SHA256
  `1f093d78a110925440c98741399d8828201cce38265a5c941ac2f71b6c104305`;
- Odin SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`,
  size `3746744`;
- Magisk boot-only rollback AP SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- cleanup-only stock boot AP SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`.

Offline verification must contact no device, enumerate no USB endpoint, and
perform no transfer. A connected preflight must start from exactly one normal
Android `SM-S906N` / `g0q` / `S906NKSS7FYG8` target with completed boot,
stopped boot animation, orange verified-boot state, Magisk `uid=0(root)`, exact
known Magisk boot, stock DTBO and recovery hashes, no Odin endpoint, and absent
R4W1-A consumed state.

The connected preflight must also prove `sec_log_buf` is `Live`, exact platform
bind
`/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf`,
both `/proc/ap_klog` and `/proc/last_kmsg`, complete nonempty bounded root reads
to EOF, and zero exact, foreign, malformed, or boundary-partial R4W1 marker
evidence. Both raw snapshots and their SHA256 values are durably stored in the
private run directory. It must not clear, rotate, initialize, or write either
observer.

## Connected Identity Dry-Run Gate

The read-only connected mode requires fresh acknowledgement
`S22PLUS-FYG8-R4W1A-CONNECTED-IDENTITY-DRY-RUN`. It may only perform the common
connected preflight and create host-side private evidence. It authorizes no
device write, `bugreportz`, reboot, Download transition, Odin transfer, or
consumed-state creation. Passing this mode does not activate either exception
below. A PASS creates one immutable SHA-bound promotion record at
`workspace/private/state/s22plus_fyg8_r4w1a_connected_dry_run_pass.json`.
The future oracle ACTIVE clause must contain that exact record SHA, and the
helper independently reopens the named private result and verifies its SHA,
target, mode, verdict, helper identity, and `device_writes=false`. A missing,
stale, replaced, or mismatched record keeps the oracle policy inactive.

## Proposed Oracle Dry-Run Exception

Policy marker: `S22+ FYG8 R4W1-A bugreport oracle dry-run live gate`.

Future binding activation would require the exact whole-line sentinel
`S22PLUS_FYG8_R4W1A_ORACLE_DRY_POLICY_STATE=ACTIVE`, the exact helper SHA above,
the exact connected promotion-record SHA, independent review, and a fresh attended acknowledgement
`S22PLUS-FYG8-R4W1A-BUGREPORT-ORACLE-DRY-RUN` supplied after that review.

This is a zero-flash, zero-reboot rehearsal. After the complete common
preflight it must prove both `/sys/fs/pstore/console-ramoops` and
`console-ramoops-0` absent. It may then:

1. inventory every direct `/bugreports` entry through non-root shell;
2. run exactly one `adb exec-out bugreportz -s` with no other dumpstate command;
3. stream stdout to one new exclusive mode-0600 host file under a fixed size
   and time bound, while separately bounding stderr;
4. inventory `/bugreports` again and require every preexisting entry unchanged;
5. require exactly one strict direct regular file to have appeared;
6. require that remote file's size and SHA256 equal the complete host stream;
7. parse the complete CRC-valid ZIP with the pinned parser and require marker
   family absence in the exact `LAST KMSG (/proc/last_kmsg)` section; and
8. only after the host/remote identity match, remove that exact path through
   non-root shell while rechecking path, non-symlink regular-file identity,
   stat tuple, and SHA256, then require the final inventory to equal baseline.

Parser failure after an exact host/remote identity match still permits exact
cleanup. A missing, changed, duplicate, unsafe, multiple, or unmatched new
entry prohibits deletion and returns a non-PASS recovery state. The helper may
never wildcard-delete, recursively remove, clear the directory, delete a
preexisting entry, or use root to force cleanup. A dry-run PASS is
`PASS_R4W1A_ORACLE_DRY_RUN_EXACT_ZIP_AND_CLEANUP` and proves only the actual
FYG8 stream shape and exact cleanup path.

Immediately before the one capture, the helper must durably create
`workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_consumed.json`.
Capture start consumes the oracle exception regardless of result and cannot be
retried. A PASS additionally creates immutable promotion record
`workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_pass.json`, bound to
the exact helper and full result JSON. The future candidate ACTIVE clause must
name that exact record SHA. The helper reopens and verifies the result's exact
mode/verdict plus `capture.success=true`, `cleanup_verified=true`, and marker-
absent parser classification; absent or mismatched proof keeps candidate mode
inactive.

The standard eight timeline names remain the only event schema. Result-side
semantics explicitly label every candidate/rollback flash phase as zero-flash.

## Proposed One-Shot Candidate Exception

Policy marker: `S22+ FYG8 R4W1-A retained PID1 witness boot-only live gate`.

This exception cannot be activated until the connected identity dry-run and
oracle dry-run above both pass, an independent read-only review returns GO, and
the operator supplies fresh acknowledgement
`S22PLUS-FYG8-R4W1A-RETAINED-PID1-WITNESS-LIVE`. Future binding activation
would require the exact whole-line sentinel
`S22PLUS_FYG8_R4W1A_POLICY_STATE=ACTIVE`, the connected promotion-record SHA,
and the oracle promotion-record SHA.

After re-running every host and connected preflight, the helper may request
Download mode and transfer the exact candidate AP once to boot only. It must
durably create
`workspace/private/state/s22plus_fyg8_r4w1a_live_exception_consumed.json` at
`candidate_flash_start`; candidate flash start consumes the exception
regardless of result and cannot be retried.

Candidate observation is bounded to 300 seconds and requires three stable
samples of exact model, device, build, completed Android boot, stopped boot
animation, orange verified-boot state, exact FYG8 release, and exact
`/proc/version`. Root is not required. Both pstore console paths must be absent.
The helper then performs exactly the same one-capture, exact-inventory,
host/remote identity, parser, and non-root cleanup contract above, except the
parser must require the exact R4W1 marker once in the exact
`/proc/last_kmsg` section and once across the complete archive.

After observation, the helper requests Download. The operator physically
enters Download if candidate ADB is absent. Mandatory rollback transfers the
exact Magisk boot-only AP once. Only a failed Magisk transfer with one
unambiguous still-present Odin endpoint permits the exact stock boot-only AP as
cleanup, never PASS. Final PASS requires exact Magisk Android/root, boot, DTBO,
recovery, no Odin endpoint, completed exact bugreport cleanup, and verdict
`PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK`.

On the first Magisk rollback boot, the helper reads `/proc/last_kmsg` twice to
EOF and records both hashes and byte equality as non-load-bearing
corroboration. A mismatch is recorded but does not override the load-bearing
candidate streamed oracle.

Interrupted recovery from an already-started run requires acknowledgement
`S22PLUS-FYG8-R4W1A-MAGISK-ROLLBACK-FROM-DOWNLOAD` and the same active candidate
policy. It permits only the mandatory exact boot rollback chain.

## Absolute Exclusions

Neither proposed exception authorizes a second candidate run, R3 exception
reuse, R4W1-B, raw host `dd`, fastboot, repartitioning, a Magisk module, panic,
SysRq, RDX/S-Boot command, RAM dump, qdl/Sahara/Firehose, EUD/UART write,
format, userdata cleanup beyond the one exact run-created bugreport file,
partition-table action, or any recovery/vendor_boot/DTBO/vbmeta/BL/CP/CSC/
super/userdata/persist/EFS/sec_efs/RPMB/keymaster/modem/bootloader write. Only
the boot partition is in the future candidate/rollback envelope. No A90 action
is authorized.

Activation requires an exact helper SHA re-pin after every source fix, complete
offline and connected evidence, independent review of source/tests/artifacts/
this draft, and fresh attended approval. This draft remains inactive.
