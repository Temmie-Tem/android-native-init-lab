# V2306 Kernel Security Recon: Binder BB-T-uid live result

Date: 2026-06-13

Scope: one-shot live execution of the V2304 Binder BB-T-uid helper on the
resident V2237 native-init checkpoint. This remained a well-formed Binder target
reachability gate. It did **not** use malformed Binder objects, did **not**
enter the failed-cleanup/UAF path, did **not** use `BC_FREE_BUFFER`, did **not**
use `BC_REPLY`, did **not** use SG/EXT Binder commands, did **not** heap spray,
did **not** attempt privilege escalation, and did **not** retry.

## Approval used

The live runner was executed only after the operator supplied the exact BB-T-uid
approval phrase:

`Stage B-Binder BB-T-uid go: one-shot child-A uid/euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

Command:

```bash
OUT=workspace/private/runs/security/v2306-binder-bbt-uid-live-20260613-014356
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py \
  --out-dir "$OUT" \
  --run-live \
  --confirm 'Stage B-Binder BB-T-uid go: one-shot child-A uid/euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry'
```

Private evidence directory:

`workspace/private/runs/security/v2306-binder-bbt-uid-live-20260613-014356/`

Tracked helper source:

`workspace/public/src/native-init/helpers/a90_binder_target_bbt_uid.c`

Helper SHA256:

`79f05df42bab4d9ad59a41ef5b5002eb45c18a274c1c3619993e0698b47ba392`

## Runner result

The runner returned non-zero with:

```json
{
  "decision": "bbt-protocol-unexpected",
  "run_live": true,
  "helper_sha256": "79f05df42bab4d9ad59a41ef5b5002eb45c18a274c1c3619993e0698b47ba392"
}
```

This runner decision is too strict for the selected one-way transaction shape.
The live Binder target-reachability evidence itself is positive.

## Live observations

| Field | Value | Interpretation |
| --- | --- | --- |
| `bbt.have_a` / `bbt.have_b` | `1` / `1` | both child processes ran |
| `bbt.a.open_rc` | `0` | child A opened `/dev/binder` |
| `bbt.a.mmap_rc` | `0` | child A established Binder allocator VMA |
| `bbt.a.ruid_before/euid_before/suid_before` | `0/0/0` | child A started as root |
| `bbt.a.setresuid1000_rc` | `0` | child A dropped UID state |
| `bbt.a.ruid_after/euid_after/suid_after` | `1000/1000/1000` | full UID drop succeeded |
| `bbt.a.set_context_mgr_rc` | `0` | child A registered as Binder context manager |
| `bbt.a.enter_looper_rc` | `0` | child A entered Binder looper |
| `bbt.b.open_rc` | `0` | child B opened `/dev/binder` |
| `bbt.b.transaction_write_rc` | `0` | child B wrote the Binder transaction command stream |
| `bbt.b.write_consumed` / `bbt.b.write_expected` | `68/68` | kernel consumed the full write buffer |
| `bbt.a.saw_br_noop` | `1` | child A read Binder protocol output |
| `bbt.a.saw_br_transaction` | `1` | child A received `BR_TRANSACTION` |
| `bbt.a.tr_data_size` | `8` | delivered payload size matched the helper's zero-object payload |
| `bbt.a.tr_offsets_size` | `0` | no object-translation offsets were delivered |
| `bbt.a.tr_flags_oneway` | `1` | delivered transaction was one-way |
| `bbt.a.tr_sender_pid_nonzero` | `0` | expected for `TF_ONE_WAY`; see source check below |
| `bbt.no_malformed_objects` | `1` | malformed-object path not used |
| `bbt.no_free_buffer` | `1` | `BC_FREE_BUFFER` not used |
| `bbt.no_reply` | `1` | `BC_REPLY` not used |
| `bbt.no_sg` | `1` | SG/EXT command path not used |
| `bbt.runner_timeout` / `bbt.parent_timeout` | `0/0` | no hang |

Effective classification:

> `binder-bbt-uid-target-delivered-sender-pid-zero-expected`

The helper reached the BB-T-uid target: A registered as uid-1000 context manager,
B sent a well-formed zero-object one-way transaction to handle 0, the kernel
resolved the target to A, allocated/delivered a Binder transaction, and A
observed `BR_TRANSACTION`.

## Source check: one-way sender PID is expected to be zero

The V2304 helper treated `sender_pid == 0` as unexpected. That is incorrect for
the selected `TF_ONE_WAY` transaction.

Source:

`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c`

During transaction creation:

```c
if (!reply && !(tr->flags & TF_ONE_WAY))
	t->from = thread;
else
	t->from = NULL;
```

During read-side delivery:

```c
t_from = binder_get_txn_from(t);
if (t_from) {
	struct task_struct *sender = t_from->proc->tsk;

	trd->sender_pid = task_tgid_nr_ns(sender,
					task_active_pid_ns(current));
} else {
	trd->sender_pid = 0;
}
```

Because BB-T-uid deliberately uses `TF_ONE_WAY`, `t->from` is `NULL`, so
`sender_pid` is `0` by design. The predicate should validate
`tr_flags_oneway == 1`, `tr_offsets_size == 0`, and successful delivery instead
of requiring `sender_pid_nonzero == 1`.

## Dmesg and cleanup

Bounded post-run dmesg showed no kernel panic, no Oops, and no crash. It did
show Binder cleanup noise consistent with a short-lived test process:

```text
binder: 2662:2662 ioctl c0306201 7fc2fe19a8 returned -11
binder: undelivered TRANSACTION_COMPLETE
```

The runner cleanup removed:

- `/dev/binder`
- `/cache/bin/a90_binder_target_bbt_uid`
- `/cache/a90-binder-bbt-uid.out`

Post-run health:

```text
selftest: pass=11 warn=1 fail=0
```

No retry was attempted.

## Decision

V2306 is a live BB-T-uid reachability success with a helper classification bug.

Accepted facts:

- `/dev/binder` can be materialized and used from V2237 native-init.
- Child A can open and `mmap` Binder, then drop to `ruid/euid/suid=1000`.
- Child A can register as Binder context manager under the existing uid-1000
  context-manager gate.
- Child B can send a well-formed zero-object one-way transaction to handle 0.
- Child A receives `BR_TRANSACTION`.
- No malformed object, failed cleanup, UAF trigger, or exploit path was used.

Blocked facts:

- BB3 remains unapproved and unrun.
- This result does not prove exploitability and does not touch the CVE cleanup
  path.

## Next safe unit

Build-only helper correction:

- accept `sender_pid == 0` when `tr_flags_oneway == 1`,
- record the raw `sender_pid` value instead of only `sender_pid_nonzero`,
- keep all V2304/V2306 hard stops unchanged,
- do not rerun live without a new explicit approval.

BB3 remains a separate gate requiring a new design review and a separate exact
approval phrase.
