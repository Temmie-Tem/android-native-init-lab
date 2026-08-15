# S20+ G986N Native Canary N1 H0 Report

Date: 2026-08-15

Selected target: operator-owned Samsung Galaxy S20+ 5G only,
`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

Status: **HOST BUILD PASS; LIVE CAPABILITY NOT ACTIVE; INDEPENDENT REVIEW PENDING**

Verdict: `PASS_S20PLUS_G986N_NATIVE_CANARY_N1_HOST_BUILD`

## Outcome

The first N1 H0 unit is implemented. A deterministic host builder produces a
four-member data-only Magisk module containing one static AArch64 canary. The
canary owns a closed one-shot state transaction, and its host process model
rejects malformed bindings, stale boot identity, replay ambiguity, partial
journals, unexpected nodes, wrong modes, final-path symlinks, hardlinks, and
special files without changing state.

This is not an installed module and not a live-ready policy. No target
contract, routine action, resident-root runner, F1 runner, shared guard,
approval, device state, or binding registry row changed. No ADB, USB, `su`,
Magisk install, reboot, Odin, or device command ran.

## Tracked implementation closure

| File | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/native-init/s20plus_native_canary.c` | 26,898 | `e611310eadf992bb1050fd5e35f236d3523e5c04693fd9e2beede1173766791b` |
| `workspace/public/src/scripts/revalidation/build_s20plus_g986n_native_canary_n1.py` | 20,017 | `2046fc81a3cd71b2f9390cf29387e75b7ede9c0195eb2b30739b87a16c80175f` |
| `tests/test_s20plus_g986n_native_canary_n1.py` | 19,662 | `6420ec44a1b911ecfc1e93a281a765b0a2688906d638e8d8ba468c537e4658a9` |
| `docs/plans/S20PLUS_G986N_NATIVE_CANARY_ROOT_DATA_TRANSACTION_DRAFT_2026-08-15.md` | 14,076 | `5f842988af9fdf584433af5c2c9e32ef6a8bc6346cf0b0e8137de9f6b305a327` |

The policy draft is explicitly H0, non-binding, and inactive. The earlier
phased design and official Magisk/AOSP/Linux/Samsung source map remain in
`docs/plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md`.

## Private build result

Canonical H0 output directory:

`workspace/private/outputs/s20plus_g986n/native_canary_n1_v1/`

| Artifact | Size | SHA-256 |
|---|---:|---|
| stripped static canary | 597,720 | `f5ebd70951827f831b2b11bb6eb012e150ef5a198444cc335e15016627e9536c` |
| deterministic module ZIP | 598,551 | `207c91293714a22460441c10b9b126530328ce0f2e2f384e8584a85663218e79` |
| private build result | 8,923 | `b0862e67c3308ad3c1dc361a8b1b059aed41611337392811ed179b299ec8bd41` |

The builder recorded its compiler driver, cc1, collect2, assembler, linker,
startup objects, static libc/libgcc inputs, strip/readelf/nm/file/qemu tools,
Python interpreter, and `zipfile` source identities. Two native builds and two
ZIP builds were byte-identical. The binary is a stripped static ELF64 AArch64
executable for GNU/Linux 3.7.0 or later with entry point `0x401040`, no
`PT_INTERP`, no dynamic section or `DT_NEEDED`, no undefined symbol, and no
writable-executable load segment.

The private ZIP contains exactly:

| Member | Mode | Size | SHA-256 |
|---|---:|---:|---|
| `module.prop` | `0644` | 178 | `542c4502a9183ba37d8428f81c311a979ff2e642a7320d540342a717db1e78dc` |
| `skip_mount` | `0644` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `service.sh` | `0750` | 215 | `e343071024cc982e2860736bbedfb141b0149dfb5050ba74a47624023a8353df` |
| `bin/s20plus_native_canary` | `0750` | 597,720 | `f5ebd70951827f831b2b11bb6eb012e150ef5a198444cc335e15016627e9536c` |

The archive uses stored compression and one fixed 1980 timestamp for every
entry. It has no explicit directory, duplicate, encryption, traversal,
symlink, hardlink, special node, or extra member. Neither private artifact is
tracked by Git.

## Native transaction implemented

Production execution has no arguments and uses only the fixed state directory
`/data/adb/s20plus-native-init/n1`. The test-only build requires a compile-time
macro and accepts one temporary host state directory; those bytes are not in
the module ZIP.

The production canary requires a root-owned `0700` directory and one direct,
single-link `0600` `binding.txt`. The ordered binding fixes the target tuple,
ZIP/binary identities, nonce, and pre-reboot boot-ID hash. It verifies its own
bytes through `/proc/self/exe`, requires a changed boot-ID hash, and creates
`intent.json` with `O_CREAT|O_EXCL` before observation.

The bounded result records only fixed process, UID/GID, SELinux, capability,
monotonic-clock, executable, boot-ID-hash, and namespace fields. It is written
to a fixed pending regular file, flushed, published by same-directory
no-clobber `linkat`, directory-flushed, and then has the pending name removed.
An exact completed run returns consumed on later invocation without modifying
intent or result. Intent-only, result-only, or malformed completed state is
never retried.

The source contains no generic exec, child/thread creation, socket, network,
mount, namespace creation, ioctl, device-node, property/service control,
reboot, ptrace, kernel-module, or block-path operation. `service.sh` performs
only a 120-second bounded boot-completion wait and fixed `exec` of the module
binary.

## Host validation

`python3 -m unittest -v tests.test_s20plus_g986n_native_canary_n1`

Result: **13/13 PASS**.

The hostile corpus covers:

- two-build and two-ZIP identity;
- exact ELF and ZIP grammar;
- extra ZIP member, symlink member, and wrong mode;
- exact binding grammar and invalid nonce/hash forms;
- one successful QEMU AArch64 execution and an immutable second invocation;
- wrong target, changed executable hash, unchanged boot ID, extra/blank/CR or
  oversized binding;
- binding and result symlink/hardlink states;
- FIFO, extra regular file, pending file, state-directory symlink, and wrong
  directory mode;
- intent-only, result-only, and malformed completed journal; and
- output no-clobber behavior.

Additional validation:

- the eight-module S20+ host aggregate, **168/168 PASS**;
- `python3 -m py_compile` on the builder and test;
- GCC `-Wall -Wextra -Werror` static AArch64 cross-compile;
- `file`, `readelf`, and `nm` closure checks;
- `git diff --check`; and
- private final-vs-preclosure binary and ZIP byte comparison.

## Limits and next gate

QEMU proves the closed process/state model, not Android, Magisk, or SELinux
behavior on the phone. No install/observation runner exists. The current common
and S20+ contracts still do not allow arbitrary root execution, `/data/adb`
writes, or Magisk module installation.

The next unit is an independent H0 review of the C source, builder/toolchain
closure, ZIP, hostile tests, draft root-data state machine, higher-precedence
policy interaction, and recovery model. Only after `PASS_GO` should the
operator decide whether to propose and review a binding target-policy change
and exact runner. No staging, `su`, install, reboot, Safe Mode, factory reset,
or device action is the next automatic step.

Unrelated A90 and S22+ working-tree activity was not read as S20+ evidence,
modified, staged, tested, or included in this unit.
