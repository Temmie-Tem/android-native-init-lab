# S22+ FYG8 R4W1-E0 offline candidate

Date: 2026-07-22 KST
Scope: H0 host-only
Status: deterministic boot-only candidate and independent static check passed

## Verdict

`PASS_R4W1E0_OFFLINE_CANDIDATE_STATIC_CONTRACT`

The existing P2.9 packager and checker now accept the exact R4W1-E0 build and
runtime through three narrow extension points: image classification, fixed
run binding, and run-binding evidence. The common boot reconstruction,
ramdisk replacement, LZ4, AP construction, and independent reconstruction
remain unchanged. No candidate-specific runner was created.

## Exact binding

The adapter requires the clean Full-LTO `Image`, its complete result JSON, the
fixed runtime receipt, and a fresh byte-for-byte runtime recompilation. The
fixed probe ID is `64554e8469385878c5bf8d57c44edeea`; callers cannot select or
replace it. The run manifest requires a retained baseline family count of zero
and accepts only exactly one post-candidate USERSPACE identity.

Execution-critical private input identities are:

- `Image`: 41,490,944 bytes, SHA256
  `54d637f9ee018e9daac017847c1a233dfa8913c20830a357ea597baf3f9232f9`;
- kernel result JSON: 692,896 bytes, SHA256
  `3303a528229d2b6e79e8b4393e7b7d1fd80a9e8ba489991b214bd554e8035857`;
- `init`: 66,056 bytes, SHA256
  `c3fd6cc88d8de494421ff2bf0f082d278745fdf9c2a74a2b5edba9fb8ca93627`;
- child: 720 bytes, SHA256
  `9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`.

## Reproduction

Two independent output directories produced byte-identical artifacts:

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| `carrier.boot.img` | 100,663,296 | `0469cbc1305656c099ebe7d68c9bd88073ebaee110c44c5f116f83aea5444c17` |
| `boot.img` | 100,663,296 | `6b8b7f07cdb0fd5802171df44378e098364555c09311c527ef26cf34fa41edaa` |
| `boot.img.lz4` | 27,061,297 | `e8094adb706d3a4f216fb9d0a79471a2f9b63d33f9c6647f5df48197f5dad689` |
| `odin4/AP.tar.md5` | 27,064,361 | `9b5ed2295ef9217746ba5e422acd54d13cfbc2daddcf35804ebaa08b9303ac08` |
| `manifest.json` | 6,271 | `72fb68f14f59fd00d1b8b2fb87be43e3702282c67de7ab01790fddd4f522487f` |
| `run-manifest.json` | 6,714 | `f99d29ece128ae645e45ea4c92c80843eb800ab837d1fcdec6a7419bacb9b4c8` |

Each AP contains exactly one regular member named `boot.img.lz4`. Independent
reconstruction verifies the boot header, unchanged non-kernel regions, exact
ramdisk substitution, kernel interval, LZ4 round trip, AP member, manifests,
runtime, source/tool receipts, and fixed run binding.

## Review and validation

Independent high-reasoning review exercised an end-to-end temporary build and
checker. It found one P2 issue: proof-contract errors used a distinct exception
class and could escape inherited structured failure handling. The adapter now
translates those errors at its boundary; a focused regression test verifies
the inherited fail-closed type. Re-review found no remaining actionable issue.

The complete related R4W1-D, R4W1-E, and R4W1-E0 suite passes 144 tests.
Targeted Python bytecode compilation, a final independent checker run, and
`git diff --check` pass. The generated candidates, checker outputs, kernel,
runtime, and receipts remain under `workspace/private/` and are not tracked.

## Boundary and next unit

This result performed no device contact, Odin invocation, transfer, partition
write, D0 preparation, or F1 authorization. It does not prove runtime execution
or retained durability.

The next bounded unit is H0 only: bind this exact offline contract and its
clean-baseline two-state classifier into the unchanged Process v2 runner and
observer. Connected D0 preparation and fresh F1 approval remain separate.
