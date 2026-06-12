# V2299 Kernel Security Recon: Binder BB-T helper implementation

Date: 2026-06-13

Scope: source implementation and build-only validation. No live device action,
no devnode creation, no live ioctl, no live `mmap`, no Binder protocol command
on device, no Binder transaction on device, no context-manager registration on
device, no payload, no crash trigger, and no exploit execution.

## Purpose

V2298 designed `BB-T`, the Binder target reachability gate after the V2296 BB2
allocator reachability pass. This iteration implements the minimal helper and
guarded runner needed to build that gate later, while keeping default behavior
build-only.

BB-T is still not BB3. It is a well-formed target-delivery check only.

## Added files

| Path | Purpose |
| --- | --- |
| `workspace/public/src/native-init/helpers/a90_binder_target_bbt.c` | Static AArch64 helper source for a two-process, one-way, zero-object Binder target reachability check. |
| `workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py` | Build-only by default runner; optional live runner gated by the exact BB-T approval phrase. |

## Helper behavior

The helper is intentionally two-process:

- parent process never opens `/dev/binder`;
- child A opens `/dev/binder`, performs mandatory read-only Binder `mmap`,
  registers as context manager with legacy `BINDER_SET_CONTEXT_MGR`, enters
  looper state, and reads for one `BR_TRANSACTION`;
- child B independently opens `/dev/binder`, omits Binder `mmap` by design,
  and sends one well-formed `TF_ONE_WAY` zero-object `BC_TRANSACTION` to
  handle `0`;
- both children close and exit; no explicit `BC_FREE_BUFFER` is used.

The B-side `mmap` is omitted because local source shows transaction buffers are
allocated from the target process allocator. The target-side A `mmap` is
mandatory; B only supplies normal userspace payload bytes for copy-in.

Expected live success, if separately approved later:

- A `BINDER_SET_CONTEXT_MGR` returns `0`;
- A `BC_ENTER_LOOPER` write succeeds;
- B `BC_TRANSACTION` write consumes exactly one command buffer;
- A observes `BR_TRANSACTION`;
- returned transaction metadata is safe and expected:
  `data_size=8`, `offsets_size=0`, `TF_ONE_WAY=1`, sender pid nonzero.

## Helper hard stops

The helper source does not contain these forbidden Binder tokens:

- `BINDER_SET_CONTEXT_MGR_EXT`;
- `BC_TRANSACTION_SG`;
- `BC_REPLY`;
- `BC_REPLY_SG`;
- `BC_FREE_BUFFER`;
- `BC_ACQUIRE`;
- `BC_RELEASE`;
- `BC_INCREFS`;
- `BC_DECREFS`;
- `BC_REQUEST_DEATH_NOTIFICATION`;
- `BC_CLEAR_DEATH_NOTIFICATION`;
- `BINDER_TYPE_`;
- `flat_binder_object`.

The helper also reports constant evidence fields:

- `bbt.no_malformed_objects=1`;
- `bbt.no_free_buffer=1`;
- `bbt.no_reply=1`;
- `bbt.no_sg=1`.

## Runner guardrails

The runner is build-only unless `--run-live` is supplied.

Live mode additionally requires this exact confirmation phrase:

`Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

Live mode hard stops embedded in the runner:

- refuses live mode without exact confirmation;
- verifies resident version contains `0.9.268` and `v2237`;
- requires preflight `selftest verbose` to report `fail=0`;
- aborts if `/dev/binder` already exists, so it cannot delete a pre-existing
  legitimate node;
- materializes only `/dev/binder` major `10`, minor `81`;
- transfers only the BB-T helper to `/cache/bin/a90_binder_target_bbt`;
- runs the helper once under a bounded shell watchdog;
- removes helper, output file, and the temporary devnode;
- captures bounded `dmesg` tail before and after;
- reruns post `selftest verbose`;
- does not continue to BB3.

The runner does not use `/dev/hwbinder` or `/dev/vndbinder`.

## Build-only validation

Commands:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py \
  --out-dir workspace/private/runs/security/v2299-binder-bbt-build-only-validation
```

Result:

- decision: `v2299-binder-bbt-helper-built-not-run`;
- run_live: `false`;
- helper SHA256:
  `adb23af13836633b13ab3c61ea8d71d2d567d6b95e996aa33105b5658ac4bbda`;
- private build output:
  `workspace/private/runs/security/v2299-binder-bbt-build-only-validation/a90_binder_target_bbt`;
- `file`: AArch64, statically linked, stripped;
- helper forbidden-token scan: no matches;
- `git diff --check`: pass.

The compiled helper remains private and is not tracked.

## Interpretation

V2299 makes BB-T implementable but does not run it.

This implementation is deliberately the last safe pre-trigger Binder gate:

- it can prove context-manager registration;
- it can prove two-process handle-0 target resolution;
- it can prove target-side Binder allocator reachability;
- it can prove normal transaction delivery;
- it does not enter malformed object/offset handling;
- it does not attempt failed-cleanup behavior.

If a future live BB-T run returns `bbt-target-ok`, BB3 still remains separately
blocked. The malformed transaction geometry and any crash-only UAF trigger are
not implemented here and must not be inferred from this helper.

## Decision

Classification:

> `binder-bbt-helper-implemented-build-only-not-run`

The BB-T helper and runner are ready for a separate live preflight. The next
safe unit is a V2300 preflight report that reviews the tracked helper, runner,
bridge, resident v2237 state, and exact approval boundary without running the
helper.
