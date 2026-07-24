# S22+ FYG8 P2.49 derived-validator candidate D0 ready

Date: 2026-07-24 KST
Tiers: H0 build and connected read-only D0
Status: `PASS_P249_E2_CANDIDATE_D0_PREPARED`
F1 authority: none

## Result

P2.49 built and independently closed one P2.48 E2 candidate. Two clean
Full-LTO builds and two package runs are byte-identical. The new linked audit
proves that the final kernel writer calls the descriptor-derived validator,
that the validator reads the exact linked item table, and that the stale
compare against eight is absent.

| Build | Wall time | Peak RSS | Image SHA256 |
|---|---:|---:|---|
| A | `34:48.21` | `24,247,708 KiB` | `09db9ba152b2eff7ae7ee1b29faf7ca1d1fe122a25d8fd4c57771d1548cf0c71` |
| B | `34:55.98` | `24,250,704 KiB` | `09db9ba152b2eff7ae7ee1b29faf7ca1d1fe122a25d8fd4c57771d1548cf0c71` |

Both Images are `41,490,944` bytes and preserve `1,536` bytes of fixed
kernel-slot slack. `Image`, `vmlinux`, `.config`, `System.map`,
`vmlinux.symvers`, and `abi.xml` match across both builds.

Two package runs produced one deterministic boot-only AP:

```text
boot.img SHA256 = 2f59ff74d6afc2a8044562311c6f30cab26c661c9542f8d84795b454026fd47d
boot.img.lz4 SHA256 = e3ddbc4b31d15a109cd645debfc6651bd535da46eb50e37c77574f7843a9f60c
AP.tar.md5 SHA256 = d642905b3a645aef094e0a31bbe7d5c7c4895361deef17a451dd6617ea6cf873
AP member = boot.img.lz4 only
```

The independent artifact checker and Process v2 offline promotion passed.
Private build products and execution receipts remain under
`workspace/private/outputs/s22plus_fyg8_p249/`.

## Host Catch

The first clean build attempt stopped during C compilation. The P2.48 patch
transform preserved two stop markers and also appended duplicate copies,
creating invalid `function+static` source boundaries. No Image, package,
candidate transfer, or device action resulted from that attempt.

The transform now preserves each stop marker once. Focused tests assert one
definition of each affected helper and reject both observed malformed splice
strings. The corrected patch applies cleanly and has SHA256:

```text
5ab7ac478a290f3387e8100b447feb8da54c86591128710451b61f201e14cb9b
```

## Validation

- The post-boundary-fix selected regression closure passed `126/126`.
- Python compilation and `git diff --check` passed.
- Both clean Full-LTO builds completed without swap.
- All six reproducibility artifacts are byte-identical.
- The linked validator audit passed against both final kernels.
- Two boot-only package constructions are byte-identical.
- The independent artifact closure and Process v2 offline promotion passed.

## Connected D0

The first connected read-only preparation stopped because the retained
baseline still contained a historical E1 marker family. It invoked no Odin
session, Download transition, or partition transfer. One previously approved
normal Android reboot rotated that history out.

A fresh run directory then passed connected D0. It verified one exact healthy
FYG8 target, root and boot health, exact supporting partitions, no Odin
endpoint, a clean retained baseline, the exact candidate and rollback APs, and
the current reusable execution closure. It produced one private approval
binding. No device write, Odin invocation, Download transition, candidate
attempt, or F1 authority occurred.

## Evidence Limit

P2.49 proves construction, linked semantics, package identity, rollback
availability, and connected readiness. It does not prove any live gate after
`apps-rpmh-mxlvl`, terminal E2 success, UDC publication, or USB enumeration.

The only next action is one fresh exact F1 approval for the prepared private
binding. Process v2 then permits one boot-only candidate attempt and its
mandatory already-pinned Magisk rollback.
