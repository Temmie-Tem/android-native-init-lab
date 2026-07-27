# S22+ FYG8 P2.80 Full-LTO and linked ABI audit

Date: 2026-07-28 KST

## Verdict

`PASS_P280_FULL_LTO_AB_AND_LINKED_ABI_AUDIT_HOST_ONLY`

P2.80 has two clean Full-LTO builds with six byte-identical linked artifacts.
The versioned GNU linked audit passes after correcting a host-only target-ABI
layout error in the P2.80 adapter. No candidate package, ready manifest, D0,
approval, Odin session, device contact, transfer, reboot, or device write
occurred.

## Bound inputs

- source contract: `s22plus-fyg8-p280-parent-pullup-discriminator-v1`
- run ID: `568abdddae4a0320e14c95aad8bf1e9c`
- intent SHA256:
  `e0f6dacb0900cc61c910b135b1fa0f90cf489c13a74f857c12761c2504ecf65b`
- patch SHA256:
  `23e2febdd57388efbbca1aa0935f102e06dab165b1f855ca525c5b1a6f2d81b9`
- pre-LTO qualification SHA256:
  `00a7132b5fea8d8f4f0a3b7314d36ca92a272fcc9d96c0bb417b033b77bd9479`

Both builds reopened the same qualification, current sources, intent, patch,
run ID, userspace, safety dictionary, pinned QEMU substrates, and gate-result
receipts.

## Full-LTO result

| Build | Wall time | Peak RSS | Process swaps |
|---|---:|---:|---:|
| A | `37:47.60` | `24,249,732 KiB` | 0 |
| B | `38:14.53` | `24,257,024 KiB` | 0 |

The default `schedutil` lane and same canonical source path were used for both.
Fresh B preflight and the exact output-tree cleanup guard passed.

The following artifacts are byte-identical:

| Artifact | SHA256 |
|---|---|
| `.config` | `8c3cb7e637df26cc272e9628c13ee92bf3ff55060cb8102bc49b499601be9cba` |
| `Image` | `36054cdf754b52a3c158f57969fbf2c6742b58188628e42aa738272c45a237b5` |
| `System.map` | `01189e2ee1a4be06e3ccaf636bf7378fe4146df1b87745bd31ce3521dbd575d4` |
| `abi.xml` | `3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c` |
| `vmlinux` | `5ff636cc8a369e3d8fca937e5248c4fff3d20c5737376f6472a46787fc64042b` |
| `vmlinux.symvers` | `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19` |

## Initial audit failure

The first GNU linked audit stopped with:

```text
P2.80 linked descriptor tables differ
```

Five inherited tables matched exactly. Only `s22_fyg8_p280_details` differed.
The source contract intentionally represents each rule as five logical bytes:

```text
value:u16, outcome:u8, stage_first:u8, stage_last:u8
```

The linked kernel stores the corresponding C struct at six-byte stride. AArch64
aligns the `u16` field and adds one zero tail-padding byte to each entry. The
old adapter dumped only `21 * 5 = 105` bytes and compared interleaved physical
padding as if it were the next rule. This was a verifier defect; it did not
change or invalidate either build.

An attempted common-checker fix was rejected by the candidate identity gate:
the common P2.34 repro checker is itself in the P2.80 identity preimage.
Changing it would require a new run ID and rebuild. The final correction is
therefore confined to the already-selected P2.80 linked-audit adapter.

## Corrected audit

The adapter now:

1. derives exact physical storage from the unchanged logical table;
2. reads all `21 * 6 = 126` bytes from final `vmlinux`;
3. requires every field and every tail-padding byte to match;
4. rejects packed storage, nonzero padding, and changed field bytes;
5. normalizes only after physical verification;
6. runs the unchanged logical source-contract audit; and
7. restores the temporarily adapted source-contract functions on every exit.

Direct script execution also registers one canonical module identity, avoiding
double adaptation through `__main__` plus named import.

The final GNU audit completed in `17.12` seconds, used about `1,004,208 KiB`
peak RSS, used no swap, and returned:

```text
PASS_P234_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY
```

It proves:

- all six A/B artifacts are byte-identical;
- 21 physical P2.80 detail entries have six-byte stride;
- all 21 tail-padding bytes are zero and exact;
- normalization reproduces the 105-byte logical contract;
- `s22_fyg8_p280_detail_allowed` is called by the retained validator; and
- its final `ldarh` access resolves inside the exact 126-byte table range.

The private audit result SHA256 is
`09c7042cef26649bef566a34be5b4c19f1a7f3d1b14168fdf183443df8283ad9`.

## Validation

- focused common plus P2.80 tests: 29 passed;
- Python compilation: passed;
- Ruff `0.6.9`: passed;
- whitespace validation: passed;
- real GNU linked audit against both immutable bundles: passed.

## Residual work

The P2.80 adapter module name and adapter ID are selected by source-bound
machinery, but the adapter implementation bytes are downstream verifier state.
That is acceptable for this documented post-build verifier repair and matches
the runbook's no-rebuild recovery lane. P2.81 should make verifier implementation
receipts explicit without changing already-qualified P2.80 kernel identity.

Next: deterministic boot-only package A/B, independent effective-rootfs/static
closure, and offline Process v2 promotion. Connected D0 and F1 remain later,
separate steps; F1 has no authorization.
