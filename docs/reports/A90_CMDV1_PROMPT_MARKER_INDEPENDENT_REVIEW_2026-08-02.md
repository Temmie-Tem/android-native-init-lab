# A90 cmdv1 prompt-marker independent review

Independent verdict: GO

Unresolved HIGH: 0

Unresolved MEDIUM: 0

Device actions: none

Review decision: `GO_A90_RETURN_EPOCH_PRESENTER_DIAGNOSTICS_H0`

## Current execution closure

- `workspace/public/src/scripts/revalidation/a90_observation_pipeline.py`: `6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb`
- `workspace/public/src/scripts/revalidation/a90ctl.py`: `4d72b87b42ef49c5997ddcd24d0c6bb4fe94766c2c7fddaa21b07ff218009f8c`
- `workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py`: `9cc66229526217b162cb4be112a13f708b7ffb6ea435d008c77c777f011de933`
- `workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py`: `903e50cfbdd1255716cdcd482dd70ad67e4e141df9e0b1938ad06bfb745f8f4e`
- `workspace/public/src/scripts/server-distro/a90_phase2c_display_packet.py`: `bc688e68818396e7a204582b5a0236dff2baf6aa53194db73910e2862cf7c337`
- `workspace/public/src/scripts/server-distro/a90_phase2d_display_observer.py`: `6b9720ca2e53f0fbed6efe9208b54739fa7f57df84c7a72ab61940f104ff7744`
- `workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py`: `d822b09110ca8aa2c73bf95e983b05d5a1511d54f44c297f2ff8fbd0ebc61221`
- `workspace/public/src/scripts/server-distro/a90_phase2d_keyed_rootfs.py`: `499ca3a892edea3dfa959b1c13416857091caf279d23ef95b04ee14101cf6c82`
- `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`: `7c7dbda2f817228e7a044179fe545282388ce11a446abf44b85d66ea6b020451`
- `workspace/public/src/scripts/server-distro/prepare_phase2_display_v1_rootfs.py`: `8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/a90_debian_display_v1.c`: `98c65eceadaa8a35b35eabdedaa9edca2c37587bd344e021b1dd6be8d4b2e871`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/manifest.toml`: `fead4c45c42add75331cc93738177902f21aa18ea0f7e0e53098bec7b0d46d09`
- `workspace/public/src/scripts/server-distro/phase2c_display_packet_v1/contract.toml`: `38bf85a2abb38c199d73cc448d68f7cfcf4155d8fa3cec14c6126cab15adcf5b`
- `workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py`: `1404458dc5c8e318bc36393df37d05d6a30b4be9d3bd1c588f3a0595dfb6e759`

## Review result

The changed transport marker returns a safe `slow` or `double` command's
prompt-only transcript without waiting for the full read deadline.  It does
not accept that transcript as proof.  The existing prompt-only classifier and
strict A90P1 parser still require the exact safe-command echo and a subsequent
complete, command-matching frame before success.

Unsafe commands do not receive the prompt marker and remain single-dispatch by
default.  Arbitrary partial text, an END without BEGIN, or prompt plus partial
body cannot trigger the safe retry path.  Retry count, deadline, allowlist,
flash, rollback, target, and device authority are unchanged.

Focused regression passed `22/22`; independent adversarial prompt, partial,
and unsafe probes passed.  Python compilation and scoped `git diff --check`
passed.  The reviewer made no file or device change.
