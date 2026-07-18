# S22+ FYG8 R4W1-B Live Binding Clause Template

Date: 2026-07-19 KST

State: `TEMPLATE_INACTIVE`

This host-only template is inert. It grants no device contact, live execution,
rollback, or flash. After an exact connected PASS, the deterministic binding
packet generator replaces every `{{...}}` placeholder exactly once and emits a
private proposed clause. The rendered clause still requires independent
review and a separate `AGENTS.md` commit before it can activate live.

## Exact Proposed Clause Template

```text
**Pending exception (2026-07-19, S22+ FYG8 R4W1-B direct-PID1 retained
witness boot-only live gate):** after the separately bound connected-only
policy produced one exact `PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY`, and after
the rendered clause and evidence packet pass an independent host-only review,
Codex may perform one bounded attended candidate run on Samsung S22+
`SM-S906N` / `g0q` / `S906NKSS7FYG8` only after the attending operator supplies
the exact fresh live acknowledgement below. Policy marker:
`S22+ FYG8 R4W1-B direct-PID1 retained witness boot-only live gate`.

`S22PLUS_FYG8_R4W1B_POLICY_STATE=ACTIVE`

The previously bound connected-only clause remains binding in full, including
all source, candidate, firmware, rollback, baseline, observer, and prohibition
pins. This clause adds only the one-shot live and consumed-state recovery
authority below; it removes or relaxes no connected-stage requirement.

The executable helper remains
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1b_live_gate.py`
SHA256
`734693c456d482e6a09360129ba74e9123017b5c42829518a23870d07465a95d`.
Its focused test SHA256 remains
`87de80150d1962c5804471a8037657144a4c394cd8cba5c596947c0723be42c1`.
The reusable core SHA256 remains
`9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725`;
its focused test SHA256 remains
`b55db8579115ec437e7fe63b6a3b6ecef0d8cbcac54110599e85f310f3b2fd9d`.

The load-bearing connected PASS record is
`workspace/private/state/s22plus_fyg8_r4w1b_connected_read_only_pass.json`,
created at `{{CONNECTED_PASS_CREATED_AT_UTC}}`, size
`{{CONNECTED_PASS_RECORD_SIZE}}`, SHA256
`{{CONNECTED_PASS_RECORD_SHA256}}`. It binds connected result
`{{CONNECTED_RESULT_PATH}}`, size `{{CONNECTED_RESULT_SIZE}}`, SHA256
`{{CONNECTED_RESULT_SHA256}}`. Before candidate consumption, the helper must
reopen and validate that exact PASS and result, including target,
helper/test/core/core-test identities, complete observer receipts, byte-
identical double `/proc/last_kmsg` reads, pstore absence, no Odin endpoint,
and `device_writes=false`, `reboot=false`, `download_transition=false`,
`odin_transfer=false`, and `flash=false`.

Before any device contact, the helper must rerun its complete offline artifact
gate and fresh deterministic static checker. Candidate raw boot SHA256 is
`69690e6832bab2a422979054b51ad279222c14cbc369517433b55a785ed3d44d`,
size `100663296`; candidate boot-only AP SHA256 is
`ae26340d69f7208ae3a8c0d135e3f65317b4d16b539d4e19c1613b7f15f0f2c5`,
size `27064361`; static result SHA256 is
`969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47`,
schema `s22plus_fyg8_r4w1b_candidate_static_checker_v1`, verdict
`PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT`, with no blockers. It must
also reopen full FYG8 firmware SHA256
`f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`,
Magisk boot-only rollback AP SHA256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
stock boot-only cleanup AP SHA256
`2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`,
and Odin4 size `3746744`, SHA256
`6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.
Every AP must contain exactly one regular `boot.img.lz4` member and no other
member.

Fresh live acknowledgement:
`S22PLUS-FYG8-R4W1B-DIRECT-PID1-LIVE`.
Interrupted recovery after consumption requires fresh acknowledgement
`S22PLUS-FYG8-R4W1B-MAGISK-ROLLBACK-FROM-DOWNLOAD`.

Live preflight must repeat the exact connected baseline on one normal rooted
FYG8 Android target: completed boot, stopped boot animation, orange state,
Magisk `uid=0(root)`, known Magisk boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
stock `vendor_boot` SHA256
`096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`,
stock DTBO SHA256
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
stock recovery SHA256
`93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`,
live `sec_log_buf`, exact platform bind, both pstore console paths absent,
`/proc/ap_klog` read once and `/proc/last_kmsg` read twice through true EOF
within `64 MiB`, byte-identical repeated reads, clean R4W1-B marker namespace,
and no Odin endpoint.

Immediately before candidate transfer, the helper must durably and exclusively
create
`workspace/private/state/s22plus_fyg8_r4w1b_live_exception_consumed.json`
with schema `s22plus_fyg8_r4w1b_consumed_v1`. Creation at
`candidate_flash_start` consumes this exception regardless of transfer result
and binds target, helper, candidate AP, static result, and private run path. A
preexisting or malformed consumed state stops the run.

The helper may request normal Android Download and transfer the exact candidate
AP once to boot only. After Odin disconnect, it may passively observe raw park
for at most `90` seconds. Candidate ADB is neither required nor proof. The host
sends no RDX command. The operator must physically exit any RDX screen and
enter normal Samsung Download within the bounded transition window. Before any
rollback transfer, the helper must receive exact temporal confirmation
`S22PLUS-FYG8-R4W1B-NORMAL-DOWNLOAD-CONFIRMED`. Multiple, ambiguous, absent,
or changed endpoints stop before transfer.

Rollback is mandatory. The helper transfers the exact Magisk boot-only AP.
Only a failed Magisk transfer while the same single endpoint remains may use
the exact stock boot-only AP as cleanup; stock cleanup is never PASS. The first
Magisk rollback boot must pass exact Android, root, orange, boot,
`vendor_boot`, DTBO, recovery, and no-Odin health before observer capture. No
further reboot may occur. `/proc/last_kmsg` must then be streamed twice through
true EOF within `64 MiB`; both reads require rc=0, empty stderr, nonempty bytes,
and byte identity.

The exact 99-byte marker is
`\n[[S22R4W1B|id=36dc5462adedcf136176f2ddcfee08a8|phase=DIRECT_INIT_EXEC_ACCEPTED|pid=1|path=/init]]\n`.
The only family prefix is `[[S22R4W1B|`. Historical `[[S22R4W1|` is disjoint
and neither contaminates nor satisfies R4W1-B. One or more exact records with
no foreign, malformed, unterminated, delimiter-mismatched, or boundary-partial
record are positive. Exact marker plus exact Magisk health yields only
`PASS_R4W1B_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK`. Family absence yields
only `NO_PROOF_R4W1B_EXEC_OR_TRANSITION_UNRESOLVED`. Transfer, observer,
marker-integrity, and rollback failures retain the exact fail-closed verdicts
defined by the pinned helper.

Every live or recovery result must contain only
`events:[{name,timestamp_utc}]` with exactly one ordered occurrence of
`live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, and `live_session_end`. Recovery-only and failed-action
phases remain present with explicit no-action semantics.

Recovery mode is valid only after a correct consumed state exists. It verifies
the consumed state, exact rollback APs, Odin, one endpoint, and temporal normal-
Download confirmation; it never retransfers the candidate. Recovery does not
depend on the live ACTIVE sentinel or equality to a later helper hash after
consumption, so policy retirement or later source edits cannot strand an
already-consumed device.

This exception authorizes no second candidate run, raw host `dd`, fastboot,
Magisk module, panic, SysRq, RDX/S-Boot command, RAM dump, qdl, Sahara,
Firehose, EUD/UART write, format, wildcard cleanup, security-state change, or
A90 action. It authorizes no write to recovery, vendor_boot, DTBO, vbmeta, BL,
CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
bootloader, or any partition other than boot. Candidate execution without
verified exact Magisk rollback is never PASS.
```
