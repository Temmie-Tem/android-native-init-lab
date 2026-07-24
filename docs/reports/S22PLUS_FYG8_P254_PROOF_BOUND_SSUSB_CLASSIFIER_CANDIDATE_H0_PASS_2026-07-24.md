# S22+ FYG8 P2.54 proof-bound SSUSB classifier candidate H0 pass

Date: 2026-07-24 KST
Tier: H0 host-only
Status: `PASS_P254_PROOF_BOUND_SSUSB_CLASSIFIER_CANDIDATE_HOST_ONLY`
Device contact: none
Live authority: none

## Result

P2.54 binds the unchanged P2.52 classifier/runtime semantics to proof adapters
that close the final linked writer and effective-rootfs claims. It supersedes
the incomplete P2.53 candidate-qualification attempt.

P2.53 found two host-proof defects before promotion:

1. its linked audit recognized the validator and tables but did not directly
   prove that validator success dominated the retained head, flushes, and
   stores or that the failure edge could not rejoin a retained write; and
2. its stock-rootfs adapter managed historical imported module state in place,
   so selecting a new contract could affect historical closure behavior.

P2.54 adds one source-bound linked adapter, one isolated stock-closure adapter,
their dispatch and candidate-enforcement receipts, and a new decoder/source
contract identity. P2.52 is explicitly refused by the new closure because it
is not proof-bound.

The exact candidate identity is:

```text
source contract = s22plus-fyg8-p254-e2-proof-bound-v1
run ID = 50538ff200eae6d168250f9abc426e24
userspace /init SHA256 = d73be5c84154d079f36b77cf5048763ff773fc7245eca74f288d66846617b31d
```

## Reproducible Full-LTO builds

Both builds used the same canonical absolute source path, clean output, pinned
toolchain, frozen intent, and frozen patch.

| Build | Wall time | Peak RSS | Swap |
|---|---:|---:|---:|
| A | `38:11.82` | `24,245,952 KiB` | `0` |
| B | `38:27.73` | `24,248,636 KiB` | `0` |

All six reproducibility artifacts are byte-identical:

| Artifact | Size | SHA256 |
|---|---:|---|
| `Image` | `41,490,944` | `4b154ffad3f5af822fc6af4a177261e07f4372a3fdd0a539b649666aace228e7` |
| `vmlinux` | `476,975,656` | `20e9f6f35904c478b5de6b70d5efa8fbba396b14686f3e62e87949c444e1fb3e` |
| `.config` | `185,508` | `25987115ff1411dc25e53ac19a86e8dc29fa305f0a4d5e910f78761d44ed2921` |
| `System.map` | `5,073,222` | `88cde2488e8b7f2a07b26b3ad4a729d3b886d897c51a1930a01273573a34f8a9` |
| `vmlinux.symvers` | `439,646` | `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19` |
| `abi.xml` | `12,787,205` | `3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c` |

The `Image` remains below the fixed `41,492,480`-byte kernel slot capacity.
Both wrappers returned zero, `p234_build_pass=true`, stderr was empty, and the
source tree returned to its pre-build hashes.

## Linked proof

The selected adapter is
`s22plus-fyg8-p253-linked-audit-v2`. It verifies exact final Full-LTO table
bytes and accepted `ldrb`/`ldarb`/`ldarh` load forms. Its CFG proof establishes:

- `s22_fyg8_e1_write()` calls `s22_fyg8_e1_request_allowed()`;
- the request validator calls both item and detail validators;
- validator success guards the retained head lookup, every retained flush, and
  all retained stores;
- the validator-failure edge cannot rejoin a retained write; and
- that failure path returns a negative value.

The final writer proof found:

```text
validator call  = 0xffffffc0080214e4
validator guard = 0xffffffc0080214e8
failure target  = 0xffffffc008021594
retained stores = 0xffffffc008021730
                  0xffffffc008021754
                  0xffffffc008021758
                  0xffffffc008021824
```

These are linked image addresses, not a live KASLR slide.

## Rootfs and packaging closure

The isolated adapter preserves P2.45/P2.48 historical dispatch, refuses the
unbound P2.52 closure, and selects exact P2.54 entrypoints:

```text
/init entrypoint = 0x4014f0
child entrypoint = 0x4000cc
```

Two package runs are byte-identical:

```text
boot.img SHA256     = defe3b66a50fb0269b9d0a8a590c5e60a389dfe0a4743fde77d18ef547279359
boot.img.lz4 SHA256 = 990b0723631d5ab1df484f00db590c2cca71705e82bef78ffff5b0e3e362266e
AP.tar.md5 SHA256   = 9d71d158a914cf84269a42ae5ba8b265e53d7ababaa3b81b14d03cb1edfc266c
AP member           = boot.img.lz4 only
```

The independent checker returned
`PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`. Process v2 offline
promotion returned `PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION`.

## Host catches and runbook

Four concrete host defects were caught without device contact:

1. an interrupted older build left five reproducibility-control files changed;
   a fresh preflight rejected them before Full LTO, and only hash-verified
   archive bytes were restored;
2. the first detached completion hooks produced a literal or empty return-code
   file; wrapper results still proved both completed builds, and the launcher
   was replaced with one-time `shlex` encoding;
3. the remote builder lacked GNU AArch64 binutils, while an LLVM substitution
   exceeded `24 GiB` RSS and did not finish in 25 minutes; it was terminated
   as non-authoritative and the GNU audit completed on the verification host;
4. one offline-promotion call used the candidate-directory root instead of
   `odin4/AP.tar.md5`; it failed host-only before promotion and was rerun with
   the builder's exact output path.

The reusable sequence and recurrence controls are now fixed in
`docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`.

## Validation

- P2.54 implementation result:
  `PASS_P254_PROOF_BOUND_IMPLEMENTATION_HOST_ONLY`.
- P2.54 userspace result:
  `PASS_P254_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY`.
- Focused Python compilation and 31 tests pass.
- The broader P2 discovery ran 255 tests. It has two skips and only the two
  known old P2.22/P2.27 manifest/runner fixture errors; no P2.54 test failed.
- Both clean Full-LTO builds and all six artifact comparisons pass.
- GNU linked proof audit passes.
- Both deterministic packages and the independent closure pass.
- Process v2 offline promotion passes.
- Independent execution-critical review returned GO after the failure-edge
  rejoin proof was added.

## Proof limit

An eventual `0xaXX` live result is a bounded settled-snapshot coordinate, not a
permanent root-cause verdict. Run-to-run variation is timing evidence. The
five-second grace is a bounded settling assumption. A later `0xa30` means the
known dependency snapshot is ready while the parent remains absent and should
route the next analysis to probe-internal/deferred behavior; it does not prove
the permanent cause.

The source-contract registry remains a moving tracked selector. Adding P2.54
changes that file's bytes, so tests prove historical dispatch behavior rather
than immutable historical selector receipts. This is a known architecture
limit, not a P2.54 execution blocker.

## Safety

```text
host_only=true
kernel_built=true
image_built=true
candidate_created=true
device_contact=false
device_write=false
odin_invoked=false
live_authorized=false
```

No ready manifest, connected binding, approval, or F1 authority was created.

## Next unit

P2.55 may perform one separate connected read-only D0 qualification against
the explicitly identified S22+ target. It must verify current health, exact
rollback availability, clean retained baseline, Odin absence, and this exact
execution closure. D0 remains read-only and grants no F1 authority.
