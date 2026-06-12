# V2296 Kernel Security Recon: Binder BB2 mmap live result

Date: 2026-06-12

Scope: one approved Binder BB2 live reachability run. No reboot, no flash, no
Binder ioctl, no Binder protocol command, no Binder transaction, no
context-manager registration, no payload, no crash trigger, and no exploit
execution.

Approval phrase used:

`Stage B-Binder BB2 go: one-shot Binder mmap reachability on v2237, no ioctl, no transaction, no retry`

## Command

```bash
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_mmap_reachability_v2294.py \
  --run-live \
  --confirm 'Stage B-Binder BB2 go: one-shot Binder mmap reachability on v2237, no ioctl, no transaction, no retry'
```

Runner result:

- runner rc: `0`;
- decision: `bb2-mmap-ok`;
- private run directory:
  `workspace/private/runs/security/v2294-binder-bb2-mmap-20260612-235740`;
- helper SHA256:
  `4d751a75b511ab75a0e4f149e7c18d5f13a19ccd41cfefe21940c824602bcec0`.

## Preflight

The runner rechecked the live preconditions before touching Binder:

- resident version contained `0.9.268` and `v2237`;
- preflight `selftest verbose`: `fail=0`;
- `/dev/binder` was not pre-existing;
- helper transfer completed by NCM and SHA verification succeeded.

## Helper output

The helper reported:

| Field | Value |
| --- | --- |
| `bb2.open_rc` | `0` |
| `bb2.open_errno` | `0` |
| `bb2.mmap_rc` | `0` |
| `bb2.mmap_errno` | `0` |
| `bb2.map_length` | `1048576` |
| `bb2.prot` | `PROT_READ` |
| `bb2.flags` | `MAP_PRIVATE|MAP_NORESERVE` |
| `bb2.no_ioctl` | `1` |
| `bb2.no_transaction` | `1` |
| `bb2.no_deref` | `1` |
| `bb2.munmap_rc` | `0` |
| `bb2.munmap_errno` | `0` |
| `bb2.close_rc` | `0` |
| `bb2.close_errno` | `0` |
| `bb2.runner_timeout` | `0` |
| `bb2.runner_rc` | `0` |
| `bb2.decision` | `bb2-mmap-ok` |

The helper printed a linker configuration warning from the Android dynamic
linker environment. It did not affect execution: the helper is static,
completed, unmapped, closed, and returned `0`.

## Cleanup and health

Cleanup results:

- temporary `/cache/bin/a90_binder_mmap_bb2`: removed;
- temporary `/cache/a90-binder-bb2.out`: removed;
- temporary `/dev/binder`: removed;
- post-run `/dev/binder` check: `bb2.devnode_after=0`;
- post-run `selftest verbose`: `pass=11 warn=1 fail=0`;
- current explicit `selftest verbose` after the run: `pass=11 warn=1 fail=0`.

Kernel log tail:

- no Binder-specific error, BUG, OOPS, or panic was found in the bounded
  before/after tails;
- the dmesg tail contained a modem fatal line before the BB2 helper run and the
  same line remained in the after tail. This is not attributed to BB2.

## Interpretation

BB2 is now passed:

> `binder-bb2-mmap-ok`

This establishes that the resident native-init environment can:

- materialize and open `/dev/binder`;
- install Binder allocator VMA state through `binder_mmap()`;
- cleanly `munmap()` and close;
- remove the temporary devnode;
- return to `selftest fail=0`.

This does **not** establish:

- a valid transaction target;
- context-manager registration safety;
- Binder transaction reachability;
- CVE triggerability;
- any crash/no-crash signal for the CVE-adjacent path.

## Next gate

Do not proceed directly to a UAF trigger.

The next bounded design unit should be Binder target reachability under the
same Stage B-Binder branch:

1. source-review the minimum target setup path for a clean native-init Binder
   context with no Android `servicemanager`;
2. define a `BB3-target` or equivalent pre-trigger target gate that separates
   context-manager registration / handle-0 target setup from the actual
   transaction failure-cleanup trigger;
3. keep the transaction-path trigger behind the existing V2292 explicit
   approval phrase.

Any future BB3 transaction-path work still requires:

`Stage B-Binder go: one-shot crash-only Binder transaction-path trigger on v2237, no heap spray, no privilege escalation, no retry`
