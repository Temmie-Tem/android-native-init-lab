# A90 resident promotion guard corridor independent review

Independent verdict: GO

Unresolved HIGH: 0

Unresolved MEDIUM: 0

Device actions: none

Review decision: `GO_A90_RETURN_EPOCH_PRESENTER_DIAGNOSTICS_H0`

The review decision identifier is retained by the Phase 2 finalizer contract.
This report cumulatively binds the previously reviewed unchanged Phase 2
closure and the newly reviewed resident guard changes.

## Cumulative Phase 2 execution closure

- `workspace/public/src/scripts/revalidation/a90_observation_pipeline.py`: `6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb`
- `workspace/public/src/scripts/revalidation/a90ctl.py`: `11c567c5ec4d7b95dfbe0409af1759a90087eb937e47ce627b21511316d5766d`
- `workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py`: `9cc66229526217b162cb4be112a13f708b7ffb6ea435d008c77c777f011de933`
- `workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py`: `25440dac04b6010d8d33ea0e8053ff046945a011dd496c35b08e8ef4c7420cdd`
- `workspace/public/src/scripts/server-distro/a90_phase2c_display_packet.py`: `bc688e68818396e7a204582b5a0236dff2baf6aa53194db73910e2862cf7c337`
- `workspace/public/src/scripts/server-distro/a90_phase2d_display_observer.py`: `6b9720ca2e53f0fbed6efe9208b54739fa7f57df84c7a72ab61940f104ff7744`
- `workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py`: `6b2dd55dfb534e179a824370fed545147a4d48c9181aa5099e8b59f32b77a2f2`
- `workspace/public/src/scripts/server-distro/a90_phase2d_keyed_rootfs.py`: `499ca3a892edea3dfa959b1c13416857091caf279d23ef95b04ee14101cf6c82`
- `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`: `27326f21928776d1da4b38298497148c77a4193df8716824305eae0a6416ee17`
- `workspace/public/src/scripts/server-distro/prepare_phase2_display_v1_rootfs.py`: `8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/a90_debian_display_v1.c`: `98c65eceadaa8a35b35eabdedaa9edca2c37587bd344e021b1dd6be8d4b2e871`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/manifest.toml`: `fead4c45c42add75331cc93738177902f21aa18ea0f7e0e53098bec7b0d46d09`
- `workspace/public/src/scripts/server-distro/phase2c_display_packet_v1/contract.toml`: `2721a65246d92a52725ea8713444e94f103e824b90fdd94555fd3e945b9a102a`
- `workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py`: `1404458dc5c8e318bc36393df37d05d6a30b4be9d3bd1c588f3a0595dfb6e759`

## Reviewed snapshot

- orchestrator: `27326f21928776d1da4b38298497148c77a4193df8716824305eae0a6416ee17`
- resident promotion: `0e18d50ee059419b273f7af9d3735e8ac8c5ee49c825973f3c36f1adcc7a13c8`
- CDC ACM guard: `6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9`
- Phase 2C contract: `2721a65246d92a52725ea8713444e94f103e824b90fdd94555fd3e945b9a102a`

## Findings closed during review

The review required the recovery path to derive the exact guard identity from
durable evidence rather than a currently present ACM node, moved guard-property
proof ahead of every framed settle or health command, and made guard-arm
evidence journal-bound. It also required bounded recovery leases for arm-only
crashes, exact success and failure release receipts, and rejection of stale or
dangling runtime rules.

Rollback authority was separated from observer cleanup: exact adb-recovery can
still perform the pre-authorized rollback if the guard is unavailable, while
unguarded from-native commands and unguarded final health remain forbidden.
Terminal close now follows successful guard release, and a release failure is
left as bounded recoverable state rather than a false close.

The final lifetime audit counted every remote command, the fixed 30-second
bridge preflight floor, six success-path bridge preflights, two complete
155-second NCM slow-success paths, and rollback-source/final-health work. This
removed defaults that had only hidden smaller-timeout under-budgeting.

## Independent validation

- Independent related regression: `268/268` PASS.
- Phase 2C packet: `6/6` PASS.
- Python compilation: PASS.
- `git diff --check`: PASS.
- All four final SHA256 identities were rechecked after the tests with no
  drift.
- Device contact, transfer, flash, and reboot: none. No other device was
  touched.

The review authorizes host-side closure of this implementation unit only. It
does not grant F1 or other live-device authority.
