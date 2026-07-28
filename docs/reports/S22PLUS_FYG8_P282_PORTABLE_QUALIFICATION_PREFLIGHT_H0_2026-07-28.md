# S22+ FYG8 P2.82 Portable Qualification Preflight H0

Date: 2026-07-28 KST

Verdict:

`PASS_P282_PORTABLE_QUALIFICATION_PREFLIGHT_HOST_ONLY`

## Scope

This H0 unit closed an integration defect between the P2.82 pre-LTO
qualification producer and the real Full-LTO build wrapper. It did not change
the P2.82 runtime, classifier, retained ABI, kernel patch, candidate intent, or
device policy. It did not build a kernel, package an AP, contact a device,
authorize F1, invoke Odin, reboot, or flash.

## Defect

The build wrapper materializes a private temporary repository before applying
the candidate patch. The qualification receipt originally bound repository
inputs by absolute host path. Byte-identical inputs in the temporary repository
therefore failed receipt verification even though their repository-relative
identity, size, and SHA256 were unchanged.

The first correction exposed the same defect in nested gate implementation and
QEMU evidence. In particular, old-root private substrate paths could not be
opened from the temporary repository. These failures happened before Full LTO
and did not consume a candidate build or any device authority.

## Correction

Repository-owned materials now bind as:

```text
repository-relative path + size + SHA256
```

External tools retain their absolute identity. Command arrays are not rewritten.
Qualification creation still opens and hash-verifies every pinned private QEMU
kernel, config, QEMU binary, initramfs, result, and tracked source. Reported
substrate paths and the QEMU command executable and `-kernel` argument must
resolve to those exact canonical materials.

Build-wrapper rehydration then verifies:

- the exact qualification receipt and payload digest;
- the exact stored result receipts;
- pinned kernel, config, QEMU, compiler, and contract semantics;
- current tracked implementation and test sources;
- repository-relative candidate intent, patch, and gate identities; and
- the complete evidence inventory.

It deliberately does not reopen origin-repository bulk private substrate paths.
Changing result JSON, a tracked source, candidate intent, candidate patch,
semantic pin, or required repository-relative suffix remains fail-closed.

## Validation

- focused and Process v2 regression suite: `204 tests`, `OK`;
- Python bytecode compilation: pass;
- pinned `ruff 0.6.9`: pass;
- `git diff --check`: pass;
- real build-wrapper temporary-repository preflight:
  `build_allowed=true`;
- missing tools: `0`;
- missing paths: `0`;
- source overlay reconstruction and audit: complete;
- independent changed-closure review: `GO`, no blocking finding.

The successful preflight used the unchanged P2.82 run ID
`5525fada87150ec7d94c208f7875b83f` and the unchanged candidate patch SHA256
`718dc39decb42ec4ea5c0b9fdae37fc8d0ad3dd98903b84738f085c311da785d`.

## Interpretation

The P2.82 device discriminator design was already complete. This unit proves
that its qualification can travel from the source repository to the build
wrapper's private temporary repository without weakening material identity.
The next work is Full-LTO A/B, local GNU linked audit, boot-only packaging,
offline promotion, connected D0, and an immutable ready manifest. F1 remains
unauthorized.
