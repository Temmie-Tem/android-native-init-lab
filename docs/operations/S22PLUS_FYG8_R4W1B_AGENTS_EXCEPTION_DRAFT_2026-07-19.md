# S22+ FYG8 R4W1-B AGENTS Exception Draft

State: `DRAFT_INACTIVE`

Policy marker:
`S22+ FYG8 R4W1-B direct-PID1 retained witness boot-only live gate`

This draft grants no device contact, reboot, Download transition, Odin
transfer, flash, or rollback. It becomes executable only when the exact
relevant clause is copied into `AGENTS.md`, independently reviewed, committed,
and its sentinel is changed to an exact standalone `ACTIVE` line.

## Staged Sentinels

Connected read-only stage, initially inactive:

`S22PLUS_FYG8_R4W1B_CONNECTED_POLICY_STATE=ACTIVE`

One-shot live and recovery stage, initially inactive:

`S22PLUS_FYG8_R4W1B_POLICY_STATE=ACTIVE`

The connected stage does not authorize the live stage. The live stage requires
an exact connected PASS bound to the final helper and tests.

## Exact Program Pins

Helper:

`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1b_live_gate.py`

SHA256:
`3b42a52b406b7c0073fc13b1df957b165193f20a75a9b6010c96131013baec61`

Focused helper test:

`tests/test_s22plus_fyg8_r4w1b_live_gate.py`

SHA256:
`0016da20c765583e1adf15af105078ebefaf49ebf792fda328e25e4ba310680a`

Reusable mechanical core:

`workspace/public/src/scripts/revalidation/s22plus_boot_only_live_core.py`

SHA256:
`9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725`

Core focused test:

`tests/test_s22plus_boot_only_live_core.py`

SHA256:
`b55db8579115ec437e7fe63b6a3b6ecef0d8cbcac54110599e85f310f3b2fd9d`

## Candidate And Evidence Pins

- raw boot: size `100663296`, SHA256
  `69690e6832bab2a422979054b51ad279222c14cbc369517433b55a785ed3d44d`;
- LZ4: size `27055052`, SHA256
  `be2265ae72c584553945a82cdabc1ce36cc59cf6ee065c9675b97df9fc209c9a`;
- boot-only AP: size `27064361`, SHA256
  `ae26340d69f7208ae3a8c0d135e3f65317b4d16b539d4e19c1613b7f15f0f2c5`;
- manifest: size `4150`, SHA256
  `46c29171bfe640fb81b4dc36b8f342364c73055274145f413f29e0c8e36c65b0`;
- static result: size `30004`, SHA256
  `969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47`,
  schema `s22plus_fyg8_r4w1b_candidate_static_checker_v1`, verdict
  `PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT`;
- static checker SHA256
  `922b05eaffd1b17d33f69376564cbeab008c0e84b8cb2a34464aad8f5896d0b4`;
- static checker test SHA256
  `d0eb08ddb90c8569f858367f04d601eb4db59cc879bed8ceb157e7bc3b06105f`;
- builder SHA256
  `3d7b0cdcf5584c034589b713a85e15eb302932093b3721e8e65ee42242edf388`;
- builder primitive SHA256
  `dd2bdcb42d12a4453eaeb8f81208c801c990536e7516d8bdeacc0b8a92e663e1`;
- checker primitive SHA256
  `ebf2f0941324cf4e6204ab4526125e7b3b66356672bb10ad40f6625ab4563f17`;
- R3C0 transport source SHA256
  `f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4`;
- full FYG8 firmware ZIP SHA256
  `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`;
- Odin4 size `3746744`, SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.

The candidate, Magisk rollback, and stock cleanup APs must each contain exactly
one regular `boot.img.lz4` member and no other member.

## Baseline And Rollback Pins

- known Magisk boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- stock `vendor_boot` SHA256
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`;
- stock DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- stock recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- Magisk boot-only rollback AP SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- stock boot-only cleanup AP SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`.

## Connected Read-Only Stage

Fresh acknowledgement:

`S22PLUS-FYG8-R4W1B-CONNECTED-READ-ONLY-DRY-RUN`

This stage may contact exactly one normal rooted FYG8 Android target and perform
read-only ADB and Odin-listing operations. It must require completed Android,
stopped boot animation, orange state, Magisk `uid=0(root)`, exact boot,
`vendor_boot`, DTBO, and recovery hashes, no Odin endpoint, live `sec_log_buf`,
the exact platform bind, `/proc/ap_klog` read once and `/proc/last_kmsg` read
twice through true EOF within `64 MiB`, empty stderr, nonempty bytes, and byte
identity for the two `last_kmsg` reads. Every read must prove complete R4W1-B
family and boundary-partial absence. Both pstore console paths must be absent.

It may write only host-side private run evidence and one exclusive host PASS
record. It authorizes no device write, reboot, Download, candidate transfer,
rollback transfer, cleanup, or flash.

PASS is only `PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY` and must bind the exact
helper, focused test, core, core test, result path, and result SHA256. Before a
live candidate can consume the exception, the helper must stably reopen the
exact PASS, result, and direct observer files; require every raw file to be a
canonical private-run regular file no larger than `64 MiB`; verify its exact
size and SHA256; recompute marker semantics from the raw bytes; require those
semantics to equal the result; and recheck every PASS, result, and raw identity
after validation. Result metadata alone is not evidence.

## One-Shot Live Stage

Fresh live acknowledgement:

`S22PLUS-FYG8-R4W1B-DIRECT-PID1-LIVE`

The live helper must rerun the complete artifact gate and fresh static checker,
validate the exact connected PASS, then repeat the exact read-only baseline
preflight. Immediately before candidate transfer it must durably and
exclusively create
`workspace/private/state/s22plus_fyg8_r4w1b_live_exception_consumed.json`
with schema `s22plus_fyg8_r4w1b_consumed_v1`. Creation consumes the exception
regardless of transfer result and binds target, helper, AP, static result, and
run directory.

The helper may request baseline Android Download and transfer the exact
candidate AP once to boot only. It may passively observe raw park for at most
`90` seconds only after the Odin endpoint is proven absent; a disconnect
timeout or error skips raw park and proceeds to mandatory rollback. Candidate
ADB is not required and is not proof. The host sends no RDX command. The
operator physically exits any RDX screen and enters normal Samsung Download.
Before any rollback transfer, the helper must receive the temporal operator
input:

`S22PLUS-FYG8-R4W1B-NORMAL-DOWNLOAD-CONFIRMED`

After bounded disconnect and raw-park phases close, the physical transition to
confirmed normal Download is separately bounded to `120` seconds. Confirmation
must be fresh input received entirely within the remaining window; prebuffered,
partial, trailing, oversized, non-ASCII, or late input is rejected. For a TTY,
the helper clears the input queue before displaying the confirmation prompt so
no pre-prompt partial line can contribute to acceptance. Immediately afterward
the helper must run `odin4 -l`, require rc=0, reject stale endpoint paths, and
require the same single endpoint. Multiple, absent, ambiguous, or changed
endpoints stop before transfer. No durable write may occur between that
successful revalidation and the rollback transfer call.

The helper transfers the exact Magisk rollback AP. Only a failed Magisk
transfer while the same single endpoint remains may use the exact stock cleanup
AP. Stock cleanup is never PASS.

The first exact Magisk rollback boot must pass Android, root, orange, boot,
`vendor_boot`, DTBO, recovery, and no-Odin health before observer capture. No
further reboot may occur. `/proc/last_kmsg` is then streamed twice through true
EOF with a `64 MiB` bound; both reads require rc=0, empty stderr, nonempty
bytes, and byte identity.

The exact 99-byte marker is:

```text

[[S22R4W1B|id=36dc5462adedcf136176f2ddcfee08a8|phase=DIRECT_INIT_EXEC_ACCEPTED|pid=1|path=/init]]
```

The only family prefix is `[[S22R4W1B|`; loose `S22R4W1B` or `S22R4W1`
matching is forbidden. The historical `[[S22R4W1|` family is a deliberately
distinct namespace. Its count is recorded, but it neither contaminates the
R4W1-B baseline nor satisfies R4W1-B acceptance.
One or more exact records with no foreign, malformed, unterminated, delimiter,
or boundary-partial issue are positive. Repeated exact records are counted and
do not negate acceptance.

Verdicts:

- exact marker plus exact Magisk health:
  `PASS_R4W1B_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK`;
- absent family plus exact Magisk health:
  `NO_PROOF_R4W1B_EXEC_OR_TRANSITION_UNRESOLVED`;
- failed candidate transfer followed by exact Magisk rollback:
  `FAIL_R4W1B_CANDIDATE_TRANSFER_AND_ROLLED_BACK`;
- observer capture, EOF, emptiness, or byte-identity failure:
  `FAIL_R4W1B_OBSERVER_CAPTURE`;
- foreign, malformed, unterminated, delimiter-mismatched, or boundary-partial
  marker: `FAIL_R4W1B_MARKER_INTEGRITY`;
- rollback not exact: `FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED`.

The FYG8 Linux banner is not candidate-unique. Exact marker presence binds a
positive ring to R4W1-B. Marker absence cannot distinguish exec rejection,
retention loss, or an intervening kernel boot and must remain `NO_PROOF`.

## Recovery-Only Stage

Fresh acknowledgement:

`S22PLUS-FYG8-R4W1B-MAGISK-ROLLBACK-FROM-DOWNLOAD`

Recovery is valid only after a correct consumed state exists. It verifies only
the consumed state, Magisk AP, stock cleanup AP, Odin, one endpoint, and the
temporal normal-Download confirmation. The consumed state's helper identity
must be a well-formed SHA256 but need not equal the current helper source.
Recovery does not require an ACTIVE sentinel: policy retirement or a later
helper edit must not strand an already-consumed device. It must not hash full
firmware or rerun candidate qualification before emergency rollback. It never
retransfers the candidate and does not permit a second live run.

The fresh static checker is a deterministic hard gate. Any output size/SHA
change, nonempty stderr, nonzero return, schema mismatch, verdict mismatch, or
blocker fails offline before device contact; the pinned result and fresh replay
must remain byte-identical.

## Timeline

Every live or recovery result contains only
`events:[{name,timestamp_utc}]`, with exactly one ordered occurrence of:

`live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, `live_session_end`.

`candidate_boot_ready` means bounded raw-park observation close. Recovery-only
or failed-action phases remain in the timeline and are explicitly labeled as
no-action in the result.

## Absolute Prohibitions

This draft authorizes no write to recovery, vendor_boot, DTBO, vbmeta, BL, CP,
CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
bootloader, or any partition other than boot. It authorizes no raw host `dd`,
fastboot, Magisk module, panic, SysRq, RDX command, RAM dump, qdl, Sahara,
Firehose, EUD/UART write, format, wildcard cleanup, security-state change, or
A90 action.
