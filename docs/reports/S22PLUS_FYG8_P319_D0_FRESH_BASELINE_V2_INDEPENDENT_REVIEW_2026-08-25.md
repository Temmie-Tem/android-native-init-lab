# S22+ FYG8 P3.19 D0 fresh-baseline V2 independent review

Date: 2026-08-25
Tier: H0 only
Verdict: `PASS_GO_P319_D0_FRESH_BASELINE_V2_H0_CAPABILITY_V1`

## Reviewed closure

The independent review covers implementation commit `cac3fdfad9` and the
append-only repair sequence `1be2532d5d`, `4ac628f3a4`, `380a7792db`,
`81cc6e8b6e`, `0e7c996e23`, `1cafc32a9e`, and `c89ca04069`. No predecessor
commit or ledger row is amended or deleted.

The final execution-critical identities are:

- active raw-first D0 V2 producer: `72288B/e1190b66a31ee674d9f0bf64726fbf8a5edb55d81e7910b07b6f4b0f46009d0d`;
- fresh-baseline reducer: `68400B/241c216e85d5644899d54702a318b5bc3b6db9b39f12d9cc79f8d8796fc0a9cb`;
- narrow H0 `linkat(AT_EMPTY_PATH)` helper: `1271B/0387869a286a925669ef0125ffec0619495acac01782fd60b38eef8e1c1bc886`;
- reviewed D1 V2 source: `66357B/9443c81cd51e23a24f48a0f43573e1449cfa188b3cd1c69e6f6f11644d15d478`;
- reviewed D1 V2 binding: `5351B/65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9`;
- promoted D0 V2 binding: `14292B/440d96727c17729f4845ccec6fd31ee25966b2a4075a1f12ca50e7cd5db85a98`.

The promoted binding differs from the review-pending
`14251B/f4ccb03ad38a44e0417f3150797ed9d4af9129dd67b2da33341d1589de4830cb`
predecessor only in `independent_review`: status is `pass-go` and verdict is
the source-declared value above. Reconstructing the pending tuple from the
promoted canonical object reproduces that predecessor byte-for-byte.

## Findings closed before PASS_GO

1. `1be2532d5d` applies the exact D1 V2 arm/start semantic predicates to the
   actual fixed journals; matching receipts cannot authorize foreign objects.
2. `4ac628f3a4` retains the parsed start payload and typed-cross-binds its
   `before` and `selection` to the D1 result.
3. `380a7792db` fixes D1, D0, normalized-result validation, and output
   publication to their absolute exact namespaces.
4. `81cc6e8b6e` traverses the final output parent through nofollow directory
   fds, closing parent-symlink escape and incomplete write handling.
5. `0e7c996e23` prevents partial final names and adds post-normalize final
   reopen, complete-write and replacement checks.
6. `1cafc32a9e` binds stage, final, and final-parent inode continuity across
   publication and validation.
7. `c89ca04069` removes named staging entirely. An unnamed `O_TMPFILE` inode
   is verified on its descriptor and atomically linked no-replace through the
   exact pinned helper; unsupported filesystems fail closed with no fallback.

The reviewer found no remaining blocker in this exact closure. The
proposal-label bookkeeping correction is explicit: the original proposal used
a `...V2_REPIN...` verdict label, but the sources declare
`...V2...`; the reviewer corrected the proposal to the source-declared exact
label. This is bookkeeping only and does not change the reviewed bytes or
closure decision.

The predecessor implementation report has its `17:31:41Z` nameless section
displayed before the `17:15:49Z` inode-continuity section. That is a
presentation-only append ordering blemish. This review does not reorder
historical text; commit order, ledger rows, identities, and the closure above
remain authoritative.

## Retained evidence and validation

- raw-first auditor `68231B/0cfd391b2ca26ddd8f51cac9fe2b7fcb14daaeba5985d4541e8b08354e9c0487`,
  receipt `12916B/66658f6739b8e0116209a13de3fbb2255b040fa68b0ee7bb34c7cb51876207ec`;
- prerequisite auditor `45258B/8ba7a3312f2a978941d578a2dd06d489a6242d232e0aa7cd33d7b3c26b9b3223`,
  receipt `12528B/7a5a824893dc40d2f284d6e719bad0d7e56ff92c358ddc921711fa46ef6955d0`;
- integration source `51990B/e35e2e8109e77766c5f03ee2efce13198be8fd76f1ed9602c7ef5b8ca459f1cd`,
  blocked receipt `61379B/49745fc2af81a74b9604ebe8404e84ccb7cabb47f29eca556d0b1d515a12b6ae`.

All three retained receipts regenerate byte-identically. Focused
producer/reducer/integration tests pass `57/57`; taxonomy plus integration/raw
documentation pass `66/66`; prerequisite tests pass `9/9`. The broad selector
remains 731, but broad was not rerun and no predecessor broad result is used as
review evidence.

## Boundary

This PASS_GO qualifies only the exact host-side capability. No D1 V2 result
exists, and no D0 approval, arm, run, stop, result, normalized fresh baseline,
ready/run/public candidate manifest, or approval string was requested or
issued. Integration remains exactly `FRESH_BASELINE_MISSING`. No device, ADB,
USB, Odin, network, D0, D1, F1, replay, recovery, causal-result,
candidate-success, or live authority is created. A90 and S20+ remain untouched.
