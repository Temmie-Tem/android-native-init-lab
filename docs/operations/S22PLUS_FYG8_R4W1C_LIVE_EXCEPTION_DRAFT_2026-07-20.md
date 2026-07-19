# S22+ FYG8 R4W1-C Live Exception Draft

Date: 2026-07-20 KST

Status: `DRAFT_INACTIVE`

This file is an inert deterministic policy template. It grants no device
contact, reboot, Download transition, Odin transfer, flash, or recovery. The
placeholders are rendered only after the separately authorized R4W1-C
connected read-only PASS. The rendered clause must be independently reviewed
and committed to `AGENTS.md` before it can become active.

BEGIN_S22PLUS_FYG8_R4W1C_LIVE_POLICY_V1
**Pending one-shot exception (S22+ FYG8 R4W1-C watchdog-carrier direct-PID1
boot-only live gate):** this clause applies only to Samsung S22+
`SM-S906N` / `g0q` / `S906NKSS7FYG8`. The exact policy state is
`S22PLUS_FYG8_R4W1C_LIVE_POLICY_STATE=ACTIVE`.

The only executable helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_gate.py`
SHA256 `{{LIVE_HELPER_SHA256}}`; its focused test is
`tests/test_s22plus_fyg8_r4w1c_live_gate.py` SHA256
`{{LIVE_TEST_SHA256}}`. The reviewed inert policy template is
`docs/operations/S22PLUS_FYG8_R4W1C_LIVE_EXCEPTION_DRAFT_2026-07-20.md`
SHA256 `{{POLICY_TEMPLATE_SHA256}}`. The live acknowledgement is
`S22PLUS-FYG8-R4W1C-NOSERIAL-PHYSICAL-CONTINUITY-DIRECT-PID1-LIVE`. Supplying
that token is also the operator's load-bearing attestation that the same
physically attended handset remains on the same cable, hub, and host port from
the Android preflight through candidate observation, final rollback transfer,
and exact Android return, with no unplug, substitution, topology reassignment,
or custody gap. Interrupted recovery requires a renewed attestation through
`S22PLUS-FYG8-R4W1C-NOSERIAL-PHYSICAL-CONTINUITY-MAGISK-ROLLBACK-FROM-DOWNLOAD`;
every actual rollback transfer requires a fresh immediate attestation through
`S22PLUS-FYG8-R4W1C-NOSERIAL-PHYSICAL-CONTINUITY-NORMAL-DOWNLOAD-CONFIRMED`.
If that Magisk transfer returns a definite failure, the separate stock cleanup
transfer requires another fresh immediate attestation through
`S22PLUS-FYG8-R4W1C-NOSERIAL-PHYSICAL-CONTINUITY-STOCK-CLEANUP-CONFIRMED` and an
exclusive durable stock-cleanup intent receipt before launch.
A crash after rollback intent but before a completion receipt may retransmit
Magisk at most once, only after exact Magisk Android postcondition fails and the
operator renews the original-handset attestation through
`S22PLUS-FYG8-R4W1C-NOSERIAL-PHYSICAL-CONTINUITY-AMBIGUOUS-MAGISK-ROLLBACK-RETRY`.
If continuity cannot be attested at any one of these gates, no rollback or
cleanup transfer is authorized.

The frozen connected helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_connected_gate.py`
SHA256 `fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9`;
its focused test SHA256 is
`98938da61fc6a3f95389a31f019950fa00b3e6575687aab8d1edf5d070240251`
and its exact ACTIVE clause SHA256 is
`35f1d2cf8b9a4b25bac108832fb3f9ec9fd37e05c1b03f9fa34eeb5367c17ffa`.
The frozen live core SHA256 is
`9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725`
and frozen Odin transition core SHA256 is
`ab418aac5ce4c854f433e2132bd9536a610991384ec82c50dc0ba063f1888a9b`.

The load-bearing connected PASS record is
`workspace/private/state/s22plus_fyg8_r4w1c_connected_read_only_pass.json`,
created at `{{CONNECTED_PASS_CREATED_AT_UTC}}`, size
`{{CONNECTED_PASS_RECORD_SIZE}}`, SHA256
`{{CONNECTED_PASS_RECORD_SHA256}}`. It binds connected result
`{{CONNECTED_RESULT_PATH}}`, size `{{CONNECTED_RESULT_SIZE}}`, SHA256
`{{CONNECTED_RESULT_SHA256}}`.

Before device contact and again immediately before consumption, the helper must
reopen that exact PASS and result, validate all connected raw observers,
receipts, transaction-index segments, and exact artifact contract, and require
the full FYG8 stock firmware SHA256
`f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`.
The exact candidate raw boot SHA256 is
`1d394028714c48cfc0fd220acade9ead9a49ea21a81c59b2b87f88e61de704b0`;
candidate boot-only AP SHA256 is
`85514e79e3400de30b7146606a9e86c3655fc7a8766daba5f054ae1bd54fd42f`;
fresh static result SHA256 is
`14786803582b62b88db9a3791ac49364a580fe9c5c8459d0e11b66e0f8215c94`;
Magisk rollback AP SHA256 is
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
stock cleanup AP SHA256 is
`2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`;
and exact stock vendor_boot SHA256 is
`096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`.
Each AP must contain exactly one regular `boot.img.lz4` member.

Live entry requires one completed exact FYG8 Android target with stopped boot
animation, orange state, Magisk `uid=0(root)`, known Magisk boot, stock
vendor_boot/DTBO/recovery, live `sec_log_buf`, exact retained-log platform
bind, complete clean `/proc/ap_klog` and duplicate `/proc/last_kmsg` reads,
both pstore console paths absent, and clean-empty Odin evidence. Before reboot,
the helper must bind the Android ADB `get-devpath` USB topology and require the
selected ADB serial, `adb get-serialno`, and Android USB sysfs serial to agree.
Candidate and rollback Odin endpoints must be Samsung USB character devices at
only that topology. FYG8 normal Download is measured to expose no sysfs
`serial`; absence is mandatory, while any present serial is fatal. The host
cannot cryptographically or intrinsically distinguish a same-model substitute
handset placed on that port. The physical-continuity attestations are therefore
an explicit residual trust assumption, not a host-measured identity proof. They
cover initial candidate entry, interrupted recovery entry, every rollback
transfer immediately before launch, the separate stock-cleanup transfer, and any
ambiguous retransmission. If the operator cannot maintain or renew that custody,
the run is forbidden.

Before either ticketed endpoint wait, the helper must use the same finite wait
deadline to observe that exact sysfs topology as Samsung Download product
`685d`, exact strings `SAMSUNG USB` and `Samsung`, matching `busnum`/`devpath`,
and absent serial, derive its direct USB character-device node, and obtain three
consecutive identical node samples over at least 0.5 seconds. The node pathname
must equal the zero-padded sysfs `busnum`/`devnum`; its character-device identity
must have usbfs major 189 and minor `(busnum - 1) * 128 + (devnum - 1)`. Every
sample and final check must read the complete sysfs identity twice around two
complete node snapshots and recheck that relation. A ctime-only udev transition
resets the consecutive count. Node loss, wrong topology, present serial,
descriptor mismatch, malformed sysfs, timeout, or any pathname, `st_dev`, inode,
`st_rdev`, or ctime difference between the stabilized sample and hardened ticket
is fatal. Ticket acceptance and every pre-transfer USB revalidation must again
require that exact identity and product `685d`; the combined identity/binding
check is the final device check before sealed Odin launch. Stabilization grants
no endpoint authority by itself and does not weaken the hardened Odin core's
inventory, ambiguity, generation, receipt, or final revalidation gates.

Immediately before candidate transfer the helper must durably and exclusively
create
`workspace/private/state/s22plus_fyg8_r4w1c_live_exception_consumed.json`.
It binds the helper/test, exact active clause and policy template, connected
PASS/result, prepared transaction receipt, Android serial/boot ID and USB
topology/Android-serial-digest/Download-serial-absence binding, the operator's
physical-continuity acknowledgement through final rollback and Android return
through the active-clause hash, run directory, artifact contract, and rollback
APs. The Android serial digest must
be recomputed from the recorded serial at consumption and every recovery reopen;
it is an Android-return binding and does not create Download-side intrinsic
identity.
Consumption
occurs before candidate transfer and consumes the one-shot regardless of
result. Recovery must reopen all these identities under this exact ACTIVE
clause before any device contact.

The candidate, Magisk, stock, and Odin pathnames must be copied and hash-checked
into write-sealed memfds. AP membership is rechecked from the sealed bytes.
Endpoint generation and physical topology are revalidated only after sealing;
Download serial absence and exact Samsung descriptors are revalidated
immediately before invoking the sealed Odin binary. No durable write may occur
between final endpoint revalidation and Odin launch.

The helper may request normal Download and transfer the exact candidate AP once
to boot only. It must require endpoint disappearance and then hold the passive
observation for exactly 120 seconds. That interval is behavioral evidence only:
it does not directly prove watchdog ownership, watchdog survival, PID1 liveness,
or display state. After observation, the attending operator must physically
leave any RDX screen and enter normal Samsung Download for mandatory rollback.

`rollback_confirmed` is the durable Magisk transfer-intent receipt. If execution
stops after that intent without a completion receipt, recovery must first look
for exact known Magisk Android. Only if the postcondition is absent may one
separately acknowledged ambiguous Magisk retransmission occur; a second
ambiguous retry is forbidden. Recovery uses the original run directory,
append-only receipts, and at most two numbered recovery attempts. Candidate is
never retransferred. Partial observer files are never reused as proof; a later
attempt uses new names. A completed first observer is reopened byte-for-byte
and never recaptured. Original live and recovery result files are exclusive and
never overwrite each other. The same repeated recovery failure stops after two
attempts.

Magisk transfer is mandatory for PASS. Exact stock boot cleanup is permitted
only after a definite failed Magisk transfer, a new stock-specific physical-
continuity confirmation, an exclusive durable cleanup intent, and final same-
ticket endpoint/topology revalidation. A preexisting cleanup intent forbids a
second stock attempt and permanently taints the transaction as non-PASS. Any
later built-in recovery invocation must detect that intent before opening an
Odin session or waiting for an endpoint and stop without a transfer. A crash at
or after stock intent requires a separately designed and reviewed recovery
policy; it may not be reclassified as ambiguous Magisk by this helper. The
intent and any completed stock transfer log are reopened into transaction
evidence. Stock cleanup can never produce PASS. Final health
requires exact normal Android, root, known Magisk boot, stock vendor_boot/DTBO/
recovery, orange state, and no Odin endpoint. Before classification the first
complete rollback `/proc/last_kmsg` observer must be read twice to EOF under
64 MiB, have empty stderr, be byte-identical, and pass the exact R4W1 marker
family classifier.

PASS is only `PASS_R4W1C_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK`. Clean marker
absence after exact candidate transfer and exact rollback is
`NO_PROOF_R4W1C_EXEC_OR_RETENTION_UNRESOLVED`. Unknown transfer outcome,
foreign/partial/duplicate marker, observer failure, stock cleanup, or incomplete
rollback is non-PASS. The public timeline uses only
`events:[{name,timestamp_utc}]` and canonical names
`live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, `live_session_end`. Events are emitted only for actual
durable milestones; failure timelines may be partial and may not synthesize
action timestamps. A completed PASS timeline contains all eight exactly once.

This exception authorizes no second candidate, recovery without exact consumed
and connected evidence, cross-topology endpoint, R4W1-A/B reuse, raw host `dd`,
fastboot, Magisk module, panic, SysRq, RDX/S-Boot command, RAM dump,
qdl/Sahara/Firehose, EUD/UART write, format, cleanup wildcard, A90 action, or
partition-table action. It authorizes no recovery, vendor_boot, DTBO, vbmeta,
BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
bootloader, or any partition write other than boot through the exact one-member
APs above. The clause must be retired after final exact Magisk rollback and
classification; it must never be reused.
END_S22PLUS_FYG8_R4W1C_LIVE_POLICY_V1
