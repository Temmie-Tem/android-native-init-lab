# A90 H33 minimal F1 qualification handoff — H0

Target: operator-owned Samsung Galaxy A90 5G only
Authority: none; no D0, approval, F1, transfer, reboot, or live effect

## Review subject

Review `docs/reports/A90_H33_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json`
against the frozen owner closure
`48cb09e35b25f02e15fde091c93f2755b366fcb561210df49ffbafea3d333854`, the
frozen candidate-return continuation closure
`a62318c74c334509560f7c84fead011eb0a0c7fa6d8a80a45b4d72539a97a4df`, and the
frozen continuation review digest
`6bf984a2c5ff7ce3b7487b1af63073a88664c130f0137a9e2ab40104db47aac8`.

This is a historical H33 preparation. The public input was frozen while its
`independentReview` field was `PENDING_INDEPENDENT_REVIEW at input freeze`;
the current independent review is now `PASS_GO`, 1,181 bytes at SHA-256
`251235439de66b408397768201016c390bbf4d3d94bd73877117501b21294f77`.
It binds the candidate, rollback, owner closure, fresh state, hazard, and zero
contacts at the pre-repair closure. The later narrow TWRP-banner repair changed
the owner closure from
`48cb09e35b25f02e15fde091c93f2755b366fcb561210df49ffbafea3d333854` to
`1c31fb97e8f181e63bd71949b020f647aa8dab45c63d13bd089f6be2659da8a8`.
The current continuation closure is also
`d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1`, not the
frozen `a62318c7…`. The PASS and private manifest are therefore
historical/stale for execution; a fresh independent review is required. No
D0, approval, F1, or live authority is created by this repair.

## Candidate and artifacts

H33 is `0.11.200 / phase3-minimal-h33-stock-rebuild-1007-cfp`, with A/B boot
artifacts of 58,372,096 bytes and SHA-256
`bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12`.
The A/B bytes are identical. The flat manifest SHA is
`10c26569cfac1202b364e7693665a17e32f3367b26ea4dd805934b8cea22aa58`; its
effective manifest SHA is
`591967b80e3b67ce01e1592819912e164cba3e58f6bbbcc10ca35e5a900a45a2`.
The builder A/B receipt SHA is
`edb7f6fcf2e8431995e459a68cf2f5c8274794fee40da114dce780ca11b9fd0e`.

The exact kernel blob is 49,827,613 bytes at
`59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac`; its
embedded kernel Image is 48,830,480 bytes at
`6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557`.
Those kernel bytes match H32's recorded kernel bytes. The complete H33 boot
SHA is intentionally different from consumed H32
`e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d`, because
the H33 version/build and fresh enable/latch identities are different.

The exact rollback remains V2321
`0.9.285 / v2321-usb-clean-identity-rodata`, 60,882,944 bytes at
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
Its private recovery identity is intentionally unbound in this public handoff
and must be bound only by the reviewed D0/F1 process.

## Bound limits

- H33 is host-built and unbooted. No claim is made about boot, Android/vendor
  external modules, stock byte equivalence, or full reproducibility.
- H29–H32 are consumed and cannot be replayed or used as H33 evidence.
- The H33 enable/latch paths are fresh:
  `/cache/a90-auto-handoff-phase3-minimal-h33.enable` and
  `/cache/a90-auto-handoff-phase3-minimal-h33.done`.
- The hazard is `A90_SELF_BUILT_KERNEL_BOOT_ACCEPTANCE_WITH_NEW_BUILD_CERT`;
  the statement digest is
  `146ea7c9615e1845821cf2992806edae1c1f2447fe729b8f6f616a355628021b`.
- `candidate_authority`, `d0`, `f1`, `live`, and `liveAuthority` are all
  false. No approval token or review JSON is created by this unit.

The public report is
`docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H33_H0_2026-08-22.md`
with frozen input digest
`9f404ea0a0c599b54face948407fb82627a92bbdd1ad8859a4c6e7bda1b0d63d`.
The current workspace copy is `9a5bd7d853c07f41b793f264388ec38c57978357a6558c95f0c4a726e6db5630`;
the frozen input is not silently rebound to that later host-only edit.
The private manifest is
`workspace/private/manifests/a90-h33-f1-20260822-01.json`; it binds the
historical review path, size, and SHA-256 using the H32 runnable schema.
Owner validation and exact candidate/rollback/review bytes passed before the
banner repair. It is now retained as stale historical preparation data, not a
D0/F1 approval, intent, or live authority.
