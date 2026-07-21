# S22+ FYG8 R4W1-E E1 runtime host contract

Date: 2026-07-21 KST
Scope: HOST-ONLY
Verdict: `PASS_R4W1E_E1_RUNTIME_HOST_CONTRACT`

## Result

P2.8 implements the first bounded post-PID1 runtime over the P2.7 R4W1-E
checkpoint carrier. It provides one static PID1 program, one exact static child,
a small checkpoint client, and one independent build/static contract. This unit
did not build a kernel, create a ramdisk or boot image, package a candidate,
contact a device, activate a live policy, or flash.

The runtime is intentionally not a general init system. It has no shell,
configfs, USB gadget, NCM, storage, Debian handoff, hot reload, arbitrary command
surface, or block-device path.

## Exact sources

The full contract accepts only these source identities:

- runtime: `d0767ebd1b10a9631c4306fe9d02e21faa3e49afcdb82e66fa77aeb1872e48cf`;
- checkpoint client: `9012a764887e3e37436d1396bacf53e63a70a0143941b7f3b8b2bb6255884703`;
- checkpoint header: `1a720dca985c159266a8dc281131de3c916ea223efec831a132a6d7217b44712`;
- child: `2af86dda0f6c93ee90996d89c9803bd84bab16b909d25b732b69144fe8760e14`;
- module inventory: `35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b`.

The host checker SHA256 is
`7c5c00760f328be0a86102aec2ee200561f4a0894432315ed496bfb7bab9cafd`.
Its focused test source SHA256 is
`0860abd200d041b1041ab858ebb7d445b9da8a9940b4c3cbe9ce1d45e5d9dbe1`.

## Runtime sequence

PID 1 initializes the checkpoint client with a generated 16-byte run ID, then
performs exactly these E1 operations. A progress checkpoint follows a successful
operation and readback; it never precedes the operation.

1. mount and `statfs`-verify procfs, sysfs, `/dev` tmpfs, and `/run` tmpfs;
2. create `/dev/null`, verify write/read semantics, and map file descriptors
   0-2;
3. create nonblocking close-on-exec token and exec-status pipes;
4. execute `/s22-e1-child`, require exec-pipe EOF, the exact token
   `S22PLUS_R4W1E_E1_CHILD_OK:4c3e58c0785b\n`, token EOF, exit status 23,
   and reap;
5. load and prefix-verify, in order, `smem.ko`, `minidump.ko`, `qcom-scm.ko`,
   `qcom_wdt_core.ko`, and `gh_virt_wdt.ko` against `/proc/modules`;
6. require the final exact five-module prefix, publish terminal E1 success, and
   enter a ten-second quiet park that continues bounded orphan reaping.

Child exec, token, and reap waits use at most 50 attempts separated by 100 ms.
Every error path closes both parent pipe descriptors and performs bounded
kill/reap before the failure checkpoint and quiet park. `sec_log_buf.ko` is
excluded from the module plan.

## Checkpoint client

The client reopens `/proc/s22_checkpoint` for each publication and writes one
packed little-endian 32-byte request. It fixes profile E1, exact successor
stages, item indices, outcome/detail semantics, a nonzero run ID, and IEEE CRC32
with polynomial `0xedb88320`, seed `~0`, and xor-out `~0`.

The checker host-compiles an instrumented copy of the exact client, executes the
first E1 publication, and captures the request bytes. The 32-byte output SHA256
is `38791ef0a26777f033229391568877024d4e0f0e59bdba128399b0d8f51303e2`.
It is byte-identical to `carrier.encode_request()` and decodes through the P2.7
model as E1, stage `0x10`, progress, item 0, detail 0, and model run ID
`45808f9ecd8d83a14e26dd34e4687b96`. That run ID is host-model-only and is
never live evidence.

## Build and executable audit

The checker reads each source once, validates exact identity, and stages only
those verified bytes into fresh temporary build directories. Both AArch64
reproductions and the host request probe use the staged header. Ambient compiler
include, executable, library, preload, dependency, assembler, and linker
environment variables are removed. Every recorded tool is resolved once and
invoked by absolute path.

Two stripped static AArch64 builds are byte-identical:

- init: 66,056 bytes,
  `06bc8431d501e84b60f5209f2eb4408b29b9b91f6d0deee688b61dbd0411c27a`;
- child: 720 bytes,
  `9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`.

Both have `_start`, no interpreter, no dynamic program header, no undefined
symbols, and no executable stack. Objdump finds only the exact init syscall set
`24,33,34,40,43,56,57,59,63,64,93,101,129,172,220,221,260,273` and child set
`64,93`. The raw `x0`-`x5`/`x8` assignments and asm constraints are exact-source
gates. QEMU executes the child with exit 23, exact stdout token, and empty
stderr.

## Validation and review

The focused suite passes 20 adversarial tests. It covers stage/operation
substitution, direct and function-pointer early checkpoint publication,
failure/success reorder, module reorder and scope growth, symbolic and numeric
syscall growth, raw argument-register swaps, CRC seed/polynomial/xor and data
step changes, profile override, request path/flags swaps, ABI offsets, token and
exit changes, module inventory changes, arbitrary source mutation, symlink and
size guards, adjacent malicious header shadowing, poisoned ambient `CPATH`,
two-build identity, child execution, and absence of build-image/device/live
authority.

One independent reviewer examined the implementation over five adversarial
rounds. Early rounds found real false-PASS paths in checkpoint call-site
cardinality, CRC/profile token-only checks, numeric syscall parsing, raw AArch64
argument routing, adjacent header selection, read-to-compile identity, and
ambient compiler include injection. Each finding was reproduced, fixed, and
added as a regression. The final review reran the bypasses, reported no critical,
high, medium, or low findings, and returned `GO` for P2.8 documentation and a
scoped commit.

Integrated E1/P2.7/frontier/docs tests pass, the R4W1-D regression suite passes,
the legacy frontier selector suite passes, GCC `-fanalyzer -Werror` passes all
three C units, Python bytecode compilation passes, and `git diff --check`
passes.

## Limits and next unit

This is a host source and executable contract, not a kernel, ramdisk, candidate,
retained-record live proof, or device result. Installed compiler, binutils,
system headers, and QEMU remain explicit host trust roots. Full-LTO kernel API
compatibility, final Image cardinality, kernel/client integration, real module
loading, repeated retained updates, persistence across reset, and device
behavior remain unproved.

P2.9 is the next bounded host-only unit: adapt the existing clean R4W1 build,
source-restoration, FIPS, reproduction, candidate-builder, and independent
checker path to the exact R4W1-E carrier and E1 sources. Produce one clean
Full-LTO kernel build plus an offline E1 ramdisk/candidate contract with a fresh
manifest-bound run ID. Do not contact or flash a device in that unit.
