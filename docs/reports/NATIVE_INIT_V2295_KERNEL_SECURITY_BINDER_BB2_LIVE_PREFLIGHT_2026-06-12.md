# V2295 Kernel Security Recon: Binder BB2 live preflight

Date: 2026-06-12

Scope: safety preflight only. No live BB2 run, no devnode creation except a
read-only existence check, no helper transfer, no `mmap`, no ioctl, no Binder
protocol command, no Binder transaction, no context-manager registration, no
payload, no crash trigger, and no exploit execution.

## Purpose

Before running the V2294 Binder BB2 mmap reachability gate, verify that the
tracked helper, runner, bridge, and resident device state satisfy the BB2 safety
preconditions.

## Static guard review

Tracked BB2 files:

- `workspace/public/src/native-init/helpers/a90_binder_mmap_bb2.c`;
- `workspace/public/src/scripts/revalidation/native_kernel_binder_mmap_reachability_v2294.py`;
- `docs/reports/NATIVE_INIT_V2294_KERNEL_SECURITY_BINDER_BB2_MMAP_HELPER_IMPLEMENTATION_2026-06-12.md`.

Results:

- helper source forbidden-token scan for
  `ioctl(`, `BINDER_WRITE_READ`, `BC_TRANSACTION`, `BC_REPLY`,
  `BC_FREE_BUFFER`, `PROT_WRITE`, `SET_CONTEXT_MGR`, `read(`, and `write(`
  returned no matches;
- runner contains the exact BB2 confirmation gate:
  `Stage B-Binder BB2 go: one-shot Binder mmap reachability on v2237, no ioctl, no transaction, no retry`;
- runner preflight checks resident `0.9.268` and `v2237`;
- runner aborts if `/dev/binder` already exists;
- runner cleanup removes only its helper, output file, and the temporary
  `/dev/binder` node it created;
- runner records post-run `selftest verbose`;
- runner does not continue to BB3.

## Build-only validation

Command:

```bash
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_mmap_reachability_v2294.py \
  --out-dir workspace/private/runs/security/v2294-binder-bb2-safety-preflight-build-only
```

Result:

- decision: `v2294-binder-bb2-helper-built-not-run`;
- run_live: `false`;
- helper SHA256:
  `4d751a75b511ab75a0e4f149e7c18d5f13a19ccd41cfefe21940c824602bcec0`;
- `file`: AArch64, statically linked, stripped;
- `git diff --check`: pass.

## Bridge and device preflight

Bridge:

- bridge process: running;
- endpoint: `127.0.0.1:54321`;
- selected serial: redacted Samsung ACM device;
- realpath: `/dev/ttyACM0`;
- ambiguity: false.

Device:

- version: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`;
- kernel: `Linux 4.14.190-25818860-abA908NKSU5EWA3 aarch64`;
- status selftest summary: `pass=11 warn=1 fail=0`;
- explicit `selftest verbose`: `pass=11 warn=1 fail=0`;
- runtime storage: SD backend mounted read/write;
- transport: serial ready, NCM ready;
- `/dev/binder` pre-existing check: `bb2.devnode_preexisting=0`.

Warnings:

- `selftest` still has the known `helpers manifest=no` warning. This is not a
  BB2 blocker because `fail=0` and V2294 transfers a purpose-built helper.
- `transport.tcpctl=starting` appeared in status, but BB2 runner uses serial
  control plus NCM file transfer and validates transfer SHA before running.

## Go / no-go

Preflight classification:

> `binder-bb2-live-preflight-pass-not-run`

The system is ready for a BB2 live attempt if, and only if, the operator gives
the exact BB2 approval phrase:

`Stage B-Binder BB2 go: one-shot Binder mmap reachability on v2237, no ioctl, no transaction, no retry`

That approval authorizes only BB2. It does not authorize BB3 or any Binder
transaction-path trigger.

## Suggested live command

When explicitly approved:

```bash
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_mmap_reachability_v2294.py \
  --run-live \
  --confirm 'Stage B-Binder BB2 go: one-shot Binder mmap reachability on v2237, no ioctl, no transaction, no retry'
```

Stop after the command returns. Do not proceed to BB3 in the same iteration.
