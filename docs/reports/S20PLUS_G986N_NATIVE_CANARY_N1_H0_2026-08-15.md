# S20+ G986N Native Canary N1 H0 Report

Date: 2026-08-15

Selected target: operator-owned Samsung Galaxy S20+ 5G only,
`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

Status: **HOST BUILD PASS; INDEPENDENT REVIEW PASS_GO; LIVE CAPABILITY NOT ACTIVE**

Verdict: `PASS_S20PLUS_G986N_NATIVE_CANARY_N1_HOST_BUILD`

## Outcome

The first N1 H0 unit is implemented and remediated after its initial
independent review. A deterministic host builder produces a
four-member data-only Magisk module containing one static AArch64 canary. The
canary owns a closed one-shot state transaction, and its host process model
rejects malformed bindings, stale boot identity, replay ambiguity, partial
journals, unexpected nodes, wrong modes, final-path symlinks, hardlinks, and
special files without changing state. A completed result is now parsed as one
closed ordered typed schema rather than accepted by substring presence.

This is not an installed module and not a live-ready policy. No target
contract, routine action, resident-root runner, F1 runner, shared guard,
approval, device state, or binding registry row changed. No ADB, USB, `su`,
Magisk install, reboot, Odin, or device command ran.

## Tracked implementation closure

| File | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/native-init/s20plus_native_canary.c` | 34,802 | `31a4413f5d1d320d81ddb8720ff2f0303fb5198cd14a746af4c6cbe47bed3f2e` |
| `workspace/public/src/scripts/revalidation/build_s20plus_g986n_native_canary_n1.py` | 21,773 | `bcbbc60052631d810ffa3f866e7077fdbc394f161c701d00f17d9c1a3166c0cc` |
| `tests/test_s20plus_g986n_native_canary_n1.py` | 27,813 | `2759bfbc5ead562af5d7d247afb57f8b50c254f9b485982d76fd3e41be8b7e6d` |
| `docs/plans/S20PLUS_G986N_NATIVE_CANARY_ROOT_DATA_TRANSACTION_DRAFT_2026-08-15.md` | 16,085 | `0586051b9f8700d572f2cd17f5899d07426aa8b7ff9dd7ff11f20f9e3caa740f` |

The policy draft is explicitly H0, non-binding, and inactive. The earlier
phased design and official Magisk/AOSP/Linux/Samsung source map remain in
`docs/plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md`.

## Private build result

Canonical H0 output directory:

`workspace/private/outputs/s20plus_g986n/native_canary_n1_v1/`

| Artifact | Size | SHA-256 |
|---|---:|---|
| stripped static canary | 597,720 | `38e14e6f54374fc98604bdd61e50922ce9bff1c96feae7572221be548902066c` |
| deterministic module ZIP | 598,551 | `e06c88c3a1c029658160b974bc5938acc1f89ab68ea9a7d7d7169d5bd51525a2` |
| private build result | 8,923 | `fbfd7d7acd8108fad8cd44041cfa473470ac2fc6c945a224d2bf807d0f7c0a5a` |

The builder recorded its compiler driver, cc1, collect2, assembler, linker,
startup objects, static libc/libgcc inputs, strip/readelf/nm/file/qemu tools,
Python interpreter, and `zipfile` source identities. Two native builds and two
ZIP builds were byte-identical. The binary is a stripped static ELF64 AArch64
executable for GNU/Linux 3.7.0 or later with entry point `0x401500`, no
`PT_INTERP`, no dynamic section or `DT_NEEDED`, no undefined symbol, and no
writable-executable load segment.

The private ZIP contains exactly:

| Member | Mode | Size | SHA-256 |
|---|---:|---:|---|
| `module.prop` | `0644` | 178 | `542c4502a9183ba37d8428f81c311a979ff2e642a7320d540342a717db1e78dc` |
| `skip_mount` | `0644` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `service.sh` | `0750` | 215 | `e343071024cc982e2860736bbedfb141b0149dfb5050ba74a47624023a8353df` |
| `bin/s20plus_native_canary` | `0750` | 597,720 | `38e14e6f54374fc98604bdd61e50922ce9bff1c96feae7572221be548902066c` |

The archive uses stored compression and one fixed 1980 timestamp for every
entry. Its whole byte stream is compared with the canonical deterministic
encoding. It has no explicit directory, duplicate, encryption, traversal,
symlink, hardlink, special node, extra member, extra field, comment, or trailing
byte. Neither private artifact is tracked by Git. Superseded outputs are
retained separately at `native_canary_n1_v1_pre_review_fbd2/` and
`native_canary_n1_v1_pre_strict_json_5c0f/`; neither is canonical or eligible
as a future binding input.

## Native transaction implemented

Production execution has no arguments and uses only the fixed state directory
`/data/adb/s20plus-native-init/n1`. The test-only build requires a compile-time
macro and accepts one temporary host state directory; those bytes are not in
the module ZIP.

The production canary requires a root-owned `0700` directory and one direct,
single-link `0600` `binding.txt`. The ordered binding fixes the target tuple,
ZIP/binary identities, nonce, and pre-reboot boot-ID hash. It verifies its own
bytes through `/proc/self/exe`, requires a changed boot-ID hash, and creates
`intent.json` with `O_CREAT|O_EXCL` before observation. Once that name exists,
write, fsync, or close failure preserves it and consumes the run; the canary
does not unlink it and permit another attempt.

The bounded result records only fixed process, UID/GID, SELinux, capability,
monotonic-clock, executable, boot-ID-hash, and namespace fields. It is written
to a fixed pending regular file, flushed, published by same-directory
no-clobber `linkat`, directory-flushed, and then has the pending name removed.
An exact completed run returns consumed on later invocation without modifying
intent or result. The complete result parser requires the ordered schema,
fixed target, exact binding/nonce/self identity, typed scalar bounds, changed
boot hash, namespace grammar, the writer's canonical string escapes, and false
replay bit with no NUL or extra byte.
Intent-only, result-only, or malformed completed state is never retried.

The source contains no generic exec, child/thread creation, socket, network,
mount, namespace creation, ioctl, device-node, property/service control,
reboot, ptrace, kernel-module, or block-path operation. `service.sh` performs
only a 120-second bounded boot-completion wait and fixed `exec` of the module
binary.

## Host validation

`python3 -m unittest -v tests.test_s20plus_g986n_native_canary_n1`

Result: **16/16 PASS**.

The hostile corpus covers:

- two-build and two-ZIP identity;
- exact ELF and whole-byte canonical ZIP grammar;
- extra ZIP member, symlink member, wrong mode, comments, extra field, and
  trailing bytes;
- exact binding grammar and invalid nonce/hash forms;
- one successful QEMU AArch64 execution and an immutable second invocation;
- wrong fixed target/schema/self/boot identity, duplicate/extra fields, wrong
  scalar types, malformed capability/namespace material, replay true, and
  trailing result bytes;
- injected intent write, fsync, and close failures, each preserving the intent
  name and refusing a second execution;
- wrong target, changed executable hash, unchanged boot ID, extra/blank/CR or
  oversized binding;
- binding and result symlink/hardlink states;
- FIFO, extra regular file, pending file, state-directory symlink, and wrong
  directory mode;
- intent-only, result-only, and malformed completed journal; and
- output no-clobber behavior.

Additional validation:

- the eight-module S20+ host aggregate, **171/171 PASS**;
- `python3 -m py_compile` on the builder and test;
- GCC `-Wall -Wextra -Werror` static AArch64 cross-compile;
- `file`, `readelf`, and `nm` closure checks;
- `git diff --check`; and
- private published-vs-reproduction binary and ZIP byte comparison.

## Independent review findings and remediation

The first independent public H0 review correctly withheld `PASS_GO` for five
issues. Two High findings were a substring-only completed-result validator and
intent removal after a post-create publish failure. Two Medium findings were a
ZIP auditor that admitted comments/trailing bytes and draft wording that
incorrectly inferred cleanup authority. One Low finding was missing fsync on
the final published binary and ZIP.

The remediated closure now has a strict ordered typed result parser, preserves
every created intent on failure, compares the entire ZIP with its canonical
byte stream, publishes binary/ZIP/manifest no-clobber with file and directory
fsync, and makes future cleanup an explicit transaction-owned capability.

The first re-review found three remaining issues: a backslash-plus-NUL parser
case, an incorrect assumption that a standalone stock-recovery runner already
exists, and a reported namespace hostile case missing from the corpus. The
current bytes reject the NUL and other noncanonical escapes, include explicit
target and namespace mutations, and state that a stock-recovery lane must be
separately defined, reviewed, and activated; bootstrap/resident authority does
not transfer. The same independent reviewer re-ran the focused suite, rebuilt
the artifact independently in `/tmp`, reproduced the hostile cases, verified
the policies, and returned `PASS_GO` for the exact public H0 closure.

## Limits and next gate

QEMU proves the closed process/state model, not Android, Magisk, or SELinux
behavior on the phone. No install/observation runner exists. The current common
and S20+ contracts still do not allow arbitrary root execution, `/data/adb`
writes, or Magisk module installation.

The H0 implementation/review unit is complete. The next optional unit, only if
the operator chooses it, is a binding target-policy and exact-runner proposal
that separately defines the missing cleanup and stock-recovery capabilities
and receives its own independent review. No staging, `su`, install, reboot,
Safe Mode, factory reset, or device action is the next automatic step.

Unrelated A90 and S22+ working-tree activity was not read as S20+ evidence,
modified, staged, tested, or included in this unit.
