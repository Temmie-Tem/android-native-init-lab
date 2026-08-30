# A90 H39 Bad Apple Audio Prerequisite H0

- Cycle: `H39`
- Init: `A90 Linux init 0.12.003 (h39-badapple-audio-prereq-v1)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_h39_badapple_audio_prereq_v2.img`
- Boot SHA256: `5e74175c40d252cc9c38a2c918adad0d91d4b116eda8859142f2ea053064f796`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Device action: `none`
- Runtime result: `unproved`

## Change

- Preserves H38's PID1-tracked asynchronous boot-chime worker.
- Calls the existing read-only APNHLOS/modem firmware mount preparation before boot chime.
- Removes dependence on the consumed `/cache/native-init-sibling-fwssctl-v641` flag for audio prerequisites.
- Emits `audio.boot_prereq.firmware_mounts.*` receipts before the chime launch.

## Boundary

- The mount call is designed and host-built, not runtime-proved for H39.
- This build does not prove `/dev/snd`, ADSP readiness, boot chime, Bad Apple playback, rollback, or final health.
- H38's failed playback is evidence for its own run only and is not promoted into H39 success.

## Candidate hazard binding

- Hazard ID: `A90_H39_EXPLICIT_AUDIO_FIRMWARE_MOUNTS_TEMPORARY_EVIDENCE_CANDIDATE`
- Statement: `H39 preserves the H38 tracked-worker repair and exact V3402 non-init boot components, but explicitly prepares the reviewed read-only APNHLOS/modem firmware mounts before boot chime without relying on the consumed cache flag; cold-boot audio initialization, physical Bad Apple playback, rollback, and final health remain unproved until one attended boot-only F1 run.`
- Statement SHA256: `bf4d74b62aa484caf0f69f4e395ceb8505b03a6ecc6efbfb9b0b97b05fa52104`
- Acceptance at H0 would qualify only an explicit temporary-candidate risk; it grants no live authority.

## Metadata

- Helper flags: ``
- Init extra flags include: `-DA90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS=1`
- Init extra flag count: `60`
