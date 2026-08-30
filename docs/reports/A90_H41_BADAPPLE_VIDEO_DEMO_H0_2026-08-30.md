# A90 H41 Bad Apple Video Demo H0

- Cycle: `H41`
- Init: `A90 Linux init 0.12.008 (h41-badapple-video-demo-v2)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_h41_badapple_video_demo_v2.img`
- Boot SHA256: `5aa3ca852e1cd9d89a23cfd0223a64fe98e5e0e356d71dc6543da6afe6389574`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Device action: `none`
- Runtime result: `unproved`

## Scope

- Uses the current H40 v3 runtime source unchanged apart from the fresh version/build identity.
- Keeps the reviewed firmware, sibling-SSCTL, boot-chime ordering, worker sync, input ownership, and cleanup lifecycle.
- Exists only for one attended manual Bad Apple evidence attempt followed by the ordinary safety outcome.

## Boundary

- H37 audio/video observation, H39 timeouts, and H40's unproved runtime do not prove H41.
- Build equality and source reuse do not prove boot, audio, video, physical input, cleanup, or final health.
- H40 candidate and rollback attempts remain consumed and are never replayed.

## Candidate hazard binding

- Hazard ID: `A90_H41_DETERMINISTIC_BADAPPLE_VIDEO_EVIDENCE_TEMPORARY_CANDIDATE`
- Statement: `H41 gives the reviewed H40 v3 deterministic Bad Apple lifecycle a fresh candidate identity without changing its runtime source: exact V3402 non-init boot components, explicit firmware mounts and ADSP/CDSP/SLPI prerequisites, tracked PID1 boot chime before the interactive HUD fork, immediate STARTING acknowledgement, worker-bound 10-second audio sync, physical cancellation, single input ownership, and cleanup plus fresh input reopen remain required; H41 boot, playback, cleanup, and health are unproved until one attended run.`
- Statement SHA256: `99d44d6a65e90340658fda13fcbfe0ba6c28703c7d6d93fdc59f83ddfd1de787`
- Acceptance qualifies only the exact H41 bytes and grants no live authority.

## Metadata

- Helper flags: ``
- Required init flags: `-DA90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS=1, -DA90_BADAPPLE_BOOT_EXPLICIT_SIBLING_SSCTL=1`
- Init extra flag count: `61`
