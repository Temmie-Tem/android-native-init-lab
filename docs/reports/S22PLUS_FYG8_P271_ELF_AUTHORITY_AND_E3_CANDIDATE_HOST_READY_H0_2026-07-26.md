# S22+ FYG8 P2.71 ELF authority correction and E3 candidate host readiness

Date: 2026-07-26 KST

Scope: H0 host-only. No D0, approval, transaction, Odin session, transfer,
reboot, device contact, or device write occurred.

## Result

The corrected P2.70 E3 candidate completed the host qualification line:

- a fresh source-bound intent and reproducible two-link userspace build;
- exact linked-userspace authority and entrypoint rehearsal before Full LTO;
- clean Full-LTO Build A in `39:30.23`;
- clean Full-LTO Build B in `38:20.13`;
- peak RSS near 24.26 GiB, no process swap, and peak temperature `69.5 C`;
- byte equality for `.config`, `Image`, `System.map`, `abi.xml`, `vmlinux`,
  and `vmlinux.symvers`;
- the P2.60 versioned GNU linked audit;
- two byte-identical boot-only packages containing only `boot.img.lz4`;
- independent effective-rootfs and artifact closure; and
- offline Process v2 promotion.

Offline promotion creates no ready manifest, D0 binding, approval, or live
authority. The candidate has not been tested on the S22+.

## Late-checker incident

The first P2.70 Full-LTO pair and deterministic packages were reproducible,
but independent closure rejected the exact `/init` because one expected
absolute-path string was absent.

The missing value was `"/8@"`. It was not a runtime path or authority. It was
an incidental printable sequence emitted by an earlier link layout. The
checker incorrectly required exact equality between:

- required runtime paths;
- optional compiler/link artifacts; and
- every observed slash-prefixed printable sequence.

P2.70 changed code layout without changing authority, so the incidental value
disappeared. The candidate introduced no unregistered absolute path.

A diagnostic-only in-memory correction let the already-built candidate
complete the entire independent closure. That localized the only blocker
before tracked code changed; the diagnostic result was not used for
qualification.

## Correction

The source contract now exposes separate required and allowed absolute-path
sets:

- every required runtime path must be present;
- optional ELF slash artifacts may be present or absent; and
- any observed absolute path outside the allowed set remains rejected.

Focused tests prove:

- the complete authority set passes;
- omitting all optional ELF artifacts passes;
- removing a required base path fails;
- removing each E3 authority string fails; and
- adding each tested sibling or forbidden authority fails.

The fresh linked `/init` was checked before Build A. It contains every required
path and E3 control string, contains no unregistered absolute path, and has
the expected current ELF entrypoints for both executables.

## Rebuild cost

This was a host-checker defect, not a payload-runtime defect. The present
P2.60 identity implementation nevertheless includes the stock-closure adapter
and contract spec in the payload run-ID preimage. Correcting either changes
the run ID and kernel config, so the first otherwise-reproducible pair could
not be promoted and a fresh pair was mechanically required.

The primary defect class is asserting identity over non-invariants. Broad
source-receipt coupling amplifies the cost. Future pre-LTO checker rehearsal
must test the current linked userspace plus semantic mutations before Full
LTO. A separate payload/qualification/live identity split remains the
structural cost fix; it is not implemented by this unit.

## Linked-audit tool incident

The first post-build audit attempt incorrectly substituted the pinned LLVM
tools on the build host and supplied their `libc++.so.1` path. This violated
the runbook, consumed more than 24 GiB RSS and about 32 minutes, then produced
a non-authoritative validator-load failure.

The immutable bundles were retained. They were copied to the controlled host
with GNU AArch64 binutils, where the same versioned audit completed in about
21 seconds and passed. The final fresh pair used only that prescribed path.

## Thermal lane

Both final builds used the documented default lane: `schedutil`, stock maximum
frequency, hardware/kernel throttling, and read-only temperature recording.
There was no automatic abort or quota controller. The observed peak is a host
thermal result, not a candidate failure and not a reason to change built-byte
acceptance.

## Next

The next H0 boundary is creation and independent validation of a data-only
ready manifest from the promoted boot-only AP and the exact rollback artifact.
Only after that boundary may connected D0 be considered. Any future
payload-changing candidate must run the current-linked-userspace checker
rehearsal and semantic mutation fixtures before Build A.
