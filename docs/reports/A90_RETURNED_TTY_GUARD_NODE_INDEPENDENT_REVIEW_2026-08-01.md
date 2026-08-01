# A90 returned tty guard node independent review

Independent verdict: GO

Unresolved HIGH: 0

Unresolved MEDIUM: 0

Device actions: none

Review decision: `GO_A90_RETURN_EPOCH_PRESENTER_DIAGNOSTICS_H0`

## Current execution closure

- `workspace/public/src/scripts/revalidation/a90_observation_pipeline.py`: `6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb`
- `workspace/public/src/scripts/revalidation/a90ctl.py`: `11c567c5ec4d7b95dfbe0409af1759a90087eb937e47ce627b21511316d5766d`
- `workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py`: `9cc66229526217b162cb4be112a13f708b7ffb6ea435d008c77c777f011de933`
- `workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py`: `25440dac04b6010d8d33ea0e8053ff046945a011dd496c35b08e8ef4c7420cdd`
- `workspace/public/src/scripts/server-distro/a90_phase2c_display_packet.py`: `bc688e68818396e7a204582b5a0236dff2baf6aa53194db73910e2862cf7c337`
- `workspace/public/src/scripts/server-distro/a90_phase2d_display_observer.py`: `6b9720ca2e53f0fbed6efe9208b54739fa7f57df84c7a72ab61940f104ff7744`
- `workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py`: `6b2dd55dfb534e179a824370fed545147a4d48c9181aa5099e8b59f32b77a2f2`
- `workspace/public/src/scripts/server-distro/a90_phase2d_keyed_rootfs.py`: `499ca3a892edea3dfa959b1c13416857091caf279d23ef95b04ee14101cf6c82`
- `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`: `a434ee2f26d4c2bd877f6a0eeb7102d39f1f94b100d01fea0117f10304bad8b1`
- `workspace/public/src/scripts/server-distro/prepare_phase2_display_v1_rootfs.py`: `8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/a90_debian_display_v1.c`: `98c65eceadaa8a35b35eabdedaa9edca2c37587bd344e021b1dd6be8d4b2e871`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/manifest.toml`: `fead4c45c42add75331cc93738177902f21aa18ea0f7e0e53098bec7b0d46d09`
- `workspace/public/src/scripts/server-distro/phase2c_display_packet_v1/contract.toml`: `38bf85a2abb38c199d73cc448d68f7cfcf4155d8fa3cec14c6126cab15adcf5b`
- `workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py`: `1404458dc5c8e318bc36393df37d05d6a30b4be9d3bd1c588f3a0595dfb6e759`

## Review result

The changed call now queries ModemManager ignore properties on
`endpoint.tty_class`, where the tty udev rule installs them. Exact bridge,
character-device, topology, vendor/product, serial, interface, and `cdc_acm`
identity checks still precede acceptance. Guard liveness, boot-only transfer,
rollback, and S22+ isolation paths are unchanged.

The existing regression distinguishes the tty and USB-interface paths and
requires the tty path. Related tests pass `179/179`; Python compilation,
source-contract validation, and scoped `git diff --check` pass. The review made
no file or device change and grants no live authority.
