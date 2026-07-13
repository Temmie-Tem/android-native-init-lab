# S22+ FYG8 R4W1-A A12 Stream-Candidate Live PASS

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Run directory:
`workspace/private/runs/s22plus_fyg8_r4w1a_stream_candidate_live_20260713T142016Z`

## Verdict

`PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK`

The exact reviewed helper consumed the one-shot exception, transferred the
exact boot-only candidate, proved the retained PID1 marker through the canonical
host stream, and restored the exact Magisk boot-only baseline. No physical
Download intervention was required because the mandatory rollback transition
completed automatically.

## Candidate Proof

- candidate transfer completed successfully;
- candidate Android reached the exact FYG8 milestone;
- three stable exact candidate samples were collected;
- both `/sys/fs/pstore/console-ramoops` and `console-ramoops-0` were absent;
- canonical `adb exec-out bugreportz -s` stream:
  - bytes: `11632546`;
  - SHA256:
    `b22cd16a40d89a70913ff614909e30dac1ae5cdc9b8d822ce1e71598a02875c0`;
  - rc `0`, EOF complete, stderr bytes `0`;
- direct `/bugreports` inventories were `{}` before and after with no added,
  missing, or changed path;
- remote cleanup was forbidden and not attempted;
- parser input size/SHA/same-fd identity matched the canonical stream;
- all `355` ZIP entries passed CRC validation;
- marker classification was `EXACT_MARKER_ONCE_IN_LAST_KMSG`;
- archive and complete last-kmsg marker family/exact counts were each exactly
  `1`.

This is the load-bearing proof that the rebuilt candidate kernel reached the
intended early PID1 path and that its marker survived into the stock Android
bugreport observer.

## Mandatory Rollback

The exact Magisk boot-only rollback completed successfully. Final verification
proved:

- model/device/build: `SM-S906N` / `g0q` / `S906NKSS7FYG8`;
- Android boot complete and boot animation stopped;
- Magisk `uid=0(root)`;
- verified-boot state `orange`;
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- stock DTBO SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- stock recovery SHA256:
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- no Odin endpoint remained.

At `2026-07-13 23:27 KST`, the attending operator also confirmed normal Android
boot on the physical display. This is corroborative sensory confirmation of the
already-complete automated rollback health gate.

Two post-rollback `/proc/last_kmsg` reads were byte-identical at `2097136`
bytes with SHA256
`8ebc7e993f5b68c30ea70567ba48f135625fe7a00be8f2e8656c5e4dc3040ff4`.
They are corroborative only and did not affect the load-bearing stream verdict.

## Timeline

All eight canonical events occurred exactly once and in order:

1. `live_session_start` at `2026-07-13T14:20:16.534410Z`;
2. `candidate_flash_start` at `2026-07-13T14:20:29.899807Z`;
3. `candidate_flash_done` at `2026-07-13T14:20:31.360359Z`;
4. `candidate_boot_ready` at `2026-07-13T14:21:51.498740Z`;
5. `rollback_flash_start` at `2026-07-13T14:22:01.318406Z`;
6. `rollback_flash_done` at `2026-07-13T14:22:02.888178Z`;
7. `rollback_boot_ready` at `2026-07-13T14:22:41.445405Z`;
8. `live_session_end` at `2026-07-13T14:22:42.275581Z`.

Total live session elapsed time was approximately `145.74` seconds.

## Durable Identities

- result SHA256:
  `35d015d04bdde36469bbb9ebcd2f355158a2cc475444d426f49a9d83d112ad3e`;
- timeline SHA256:
  `134efa893727945b0767246c9f1e7da4e0145911d39dd5511bb47ce5b95d10ae`;
- oracle capture SHA256:
  `275db9c8656af2b25a0ce2ab2e40c97fe836c53d91b6833d771b8b1be2b51512`;
- v2 consumed state SHA256:
  `eb8fb255abe204732523c4e80578cd24d94e5a90f0fc46d963f52fe6a5fcd681`.

The consumed state binds helper SHA256
`9f3055e3c782d058f11bc2482c6cc4270a400e1654fdfdc50be6e681b4e3d7d7`,
candidate AP SHA256
`cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895`,
A4 result SHA256
`077885c4f785760720463763905e4db3453c6e262021524e6fff97700bf6b12a`,
the target, run directory, and consumption time.

## Post-Live Validation

The pre-live combined bounded suite passed `115/115` before consumption. A
post-live replay ran all `115` tests and produced `113` passes plus exactly two
errors:

- `test_real_retained_evidence_qualifies_host_only`;
- `test_real_a4_qualification_reopens_every_pinned_input`.

Both errors are the expected fail-closed post-consumption result. The historical
A4 qualification calls `validate_policy_state()`, which requires the candidate
consumed state to be absent and raises `QualificationError` when
`workspace/private/state/s22plus_fyg8_r4w1a_live_exception_consumed.json`
exists. That pre-candidate requirement was load-bearing before the live run and
must not be weakened afterward. The consumed state was preserved, and neither
the pinned A4 validator nor its pinned test was modified.

## Policy Close

The ACTIVE sentinel was replaced with
`S22PLUS_FYG8_R4W1A_STREAM_CANDIDATE_POLICY_STATE=RETIRED`. The binding is
one-shot consumed and authorizes no further candidate or rollback invocation.
The retired `AGENTS.md` SHA256 is
`71d2fa18cf5803a4bbc75d90048a57c891397597d7c10dbf512cef0f9f42209f`.
