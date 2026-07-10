# V3439 S22+ Corrected Ramoops Live No-Proof Result

## Verdict

`NO_PROOF_NO_CURRENT_RUN_FRAME`.

V3439 proved the corrected ramoops backend and binding, executed exactly one
run-bound marker sequence and one sysrq panic, recovered through the operator-
observed RDX kernel-panic screen, and found zero ramoops records. Stock DTBO was
restored successfully. This closes the mainline ramoops retention path for the
current S22+ reset flow.

## Run Identity

```text
run_id=aa96a1cfe07a6a57d9a54dc3d2c04b24
run_dir=workspace/private/runs/s22plus_v3439_ramoops_20260710T233555Z
helper_sha256=a070b7d826c4698032cc6a3eb903f9c0365db72cf75bc900f5b1482f38432a81
candidate_ap_sha256=622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264
candidate_dtbo_sha256=3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281
rollback_ap_sha256=6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
stock_dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
magisk_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Corrected Backend Proof

All mandatory V3439 checks passed before marker arm:

```text
pstore_mount=1
pmsg0=1
pstore_backend=ramoops
bound_count=1
bound_device=reserved-memory:ramoops_region
bound_compatible=ramoops
bound_status=okay
mem_size=2097152
pmsg_size=1048576
console_size=524288
record_size=262144
```

The early backend log was empty as V3438 predicted, but it was corroborative
only and did not block the valid sysfs/binding proof.

## Panic And Recovery

```text
markers_written=2026-07-10T23:36:52Z
panic_trigger_start=2026-07-10T23:36:52Z
panic_transport_lost=2026-07-10T23:37:06Z
operator_observation=RDX kernel panic screen
patched_recovery_boot_ready=2026-07-10T23:38:42Z
```

The trigger was attempted once. ADB disappeared. The operator used RDX exit and
Android returned while the candidate DTBO remained active, allowing evidence
collection before rollback.

## Evidence Result

Both pstore reads completed without deletion and agreed on the same empty file
set:

```text
evidence/attempt-1/summary.json = {}
valid_frames=[]
raw_token_files=[]
errors=[]
result=NO_PROOF_NO_CURRENT_RUN_FRAME
```

There was therefore no `console-ramoops`, `dmesg-ramoops`, or `pmsg-ramoops`
record containing the current run frame.

After stock rollback, the first boot `/proc/last_kmsg` was read twice and matched:

```text
size=2097136
sha256=4e706127ec6065c98b1ade492fa3bd6f62b8294209b8b9b737546386c78589a3
panic_text_present=true
run_id_present=false
```

It contains `PANIC:sysrq triggered crash`, confirming Samsung's retained panic
path, but it does not contain the V3439 run ID or a ramoops record.

## Rollback

```text
rollback_flash_start=2026-07-10T23:38:48Z
rollback_flash_done=2026-07-10T23:38:55Z
rollback_boot_ready=2026-07-10T23:39:45Z
live_session_end=2026-07-10T23:39:45Z
rollback_odin_rc=0
```

Final readback passed:

```text
Android ADB=rooted
boot_completed=1
bootanim=stopped
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
ramoops_status=disabled
```

## Evidence Pins

```text
session.json=b1ed9a36ec9d5ddeb6286c4bb3b16881da124a56f52a236745a431789b1d49b8
timeline.json=31b2ef2a88eb6d4e1b85c80d0abfa0b94ad0139b13437528896a013e981dd5f7
v3439_live_gate.log=89e84fd8814def3ff1185d39164ea1baeb9bb6aa64e1f93edc8b96618d6c7b44
classification.json=fa356686dc06b7209bdb563fe5e77a8861c558fe2de58ee0069489a7cac6ccc1
pstore_summary.json=ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356
first_stock_last_kmsg=4e706127ec6065c98b1ade492fa3bd6f62b8294209b8b9b737546386c78589a3
first_stock_last_kmsg_summary=762846e97d7869a03a80e54444fb98be4e2325cebf33b4e2ba3c2b025a826750
```

## Decision

Do not rebuild or repeat this ramoops DTBO. V3439 separated backend activation
from retention and proved that activation succeeds while retained records do
not survive the attended sysrq/RDX/reset flow. Mainline ramoops is retired as
the missing pre/PID1 witness.

Future work should use the already-proven Samsung retained path where stock
kernel services are available, or move to EUD/UART for pre-userspace visibility.
The stock-global-PID1 plus mount-namespace service-supervisor architecture
remains the practical no-flash bring-up route while direct PID1 is unobservable.

Both V3439 one-shot policies are retired. No repeat candidate flash or panic is
authorized.

## Validation

```text
V3439 focused tests                    18/18 PASS
V3426-V3439 regression tests          194/194 PASS (62.785 s)
offline policy status                 dtbo_active=false panic_active=false
git diff --check                      PASS
```
