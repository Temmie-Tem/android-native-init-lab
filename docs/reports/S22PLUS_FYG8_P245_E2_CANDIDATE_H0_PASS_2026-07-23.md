# S22+ FYG8 P2.45 E2 candidate H0 pass

Date: 2026-07-23 KST
Tier: H0 host-only
Status: `PASS_P245_E2_CANDIDATE_HOST_ONLY`
Device contact: none
Live authority: none

## Result

P2.45 produced one closed E2 host candidate from the P2.44 provider
implementation. The legacy P2.42 source and stock-closure behavior remain
unchanged. One explicit source-contract selector binds the P2.45 generated
plan, runtime, checkpoint client, kernel patch, decoder, run-ID domain,
userspace, stock-module closure, and Process v2 evidence.

Two clean Full-LTO builds completed successfully:

| Build | Wall time | Peak RSS | Image SHA256 |
|---|---:|---:|---|
| A | `34:16.27` | `24,246,820 KiB` | `2d6d2ce282601272b4091c01a908fae4576187b2b655b8f2e785a5252ae26ec3` |
| B | `34:57.92` | `24,255,728 KiB` | `2d6d2ce282601272b4091c01a908fae4576187b2b655b8f2e785a5252ae26ec3` |

Both Images are exactly `41,490,944` bytes and preserve `1,536` bytes of
fixed kernel-slot slack. `Image`, `vmlinux`, `.config`, `System.map`,
`vmlinux.symvers`, and `abi.xml` are byte-identical across both builds.

Two independent package runs produced the same boot-only AP:

```text
boot.img SHA256 = 33cb680c57d13492e25f97e0651f4dec65ad85027e7cf70460feade9f8239887
AP.tar.md5 SHA256 = 4638215bdb998874a4edbdfd79063a3cbeb1a96d40cb0915a030e46368619f5c
AP member = boot.img.lz4 only
```

The independent artifact checker and Process v2 offline promotion passed.
Detailed build products and execution evidence remain under
`workspace/private/outputs/s22plus_fyg8_p245/`.

## Contract Changes

P2.45 does not mutate the historical P2.42 implementation. The exact legacy
stock-closure source remains:

```text
sha256=f252aabf00b06bc6b919761778d588fbf1af88ce00ba8eb4d7e7db21d3bc2c87
```

The new selector `s22plus-fyg8-p245-e2-provider-v1` chooses:

- the four exact generated P2.44 outputs;
- a fresh run-ID domain and versioned intent/preimage/contract schemas;
- a P2.45-only decoder for the 80-stage E2 sequence;
- 323,585 exhaustively checked reachable records; and
- a stock-closure adapter that delegates unchanged validation to the exact
  P2.42 implementation through the P2.45 plan receipt.

The decoder preserves the 45-byte A/B record and CRC domains. It validates
generation ordinals, module and provider-gate item indexes, outcome/detail
pairs, adjacent slots, terminal ordering, added gates `0x83..0x86`, and
terminal success `0x8f`.

## Validation

- Focused P2.45 tests passed `10/10`.
- The selected build, Process v2, P2.33, and P2.41-P2.45 regression suite
  passed `146/146`.
- `py_compile` and `git diff --check` passed.
- Every one of the 323,585 reachable P2.45 records was encoded and decoded
  through the selected decoder.
- Adversarial CRC, ordinal, item-index, terminal, and A/B adjacency mutations
  were rejected fail-closed.
- The independent execution-critical review returned `GO` with no remaining
  finding.
- The linked audit verified the kernel-entry and proc-write call ordering,
  two kernel-entry flush calls, three proc-write flush calls, and the
  `dc civac` plus `dsb sy` cache-flush helper.
- The effective rootfs retained the exact 59-module closure and rejected
  forbidden writers.
- Candidate package A and B were byte-identical and contained only
  `boot.img.lz4`.
- Process v2 promotion returned
  `PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION`.

## Host-Only Deviations

The first remote preflight stopped because only `29.02 GiB` was free against
the `30 GiB` requirement. Removing an unused duplicate clean source copy
raised free space and the repeated preflight passed.

The first reproducibility audit attempts stopped before linked inspection
because the build host lacked the default GNU cross-binutils path and the
selected Android LLVM tool needed its pinned `lib64` search path. Supplying
that exact path passed. The canonical result was then regenerated locally so
its tool and artifact-path receipts matched the local independent static
checker. Neither event changed a kernel, boot image, AP, or device state.

## Evidence Limits

`VERIFIED`:

- the P2.44 provider implementation is bound into one reproducible kernel and
  deterministic boot-only P2.45 candidate;
- the complete P2.45 record decoder and Process v2 offline path select the
  same explicit source contract;
- the effective stock rootfs and exact 59-module plan are closed; and
- the candidate is ready for a separate connected read-only D0 qualification.

`NOT PROVEN`:

- direct-PID1 success of any corrected provider gate;
- apps RSC, RPMh children, GCC, SSUSB, DWC3, or UDC live bind;
- USB enumeration or transport;
- connected target health or baseline state for a future run; and
- F1 authority or any live candidate result.

## Next Unit

Run one connected read-only D0 qualification against the explicitly identified
S22+ target. If D0 passes, create one fresh immutable Process v2 binding and
request one exact F1 approval for this candidate and its already-pinned
Magisk rollback. No approval or device authority follows from this H0 report.
