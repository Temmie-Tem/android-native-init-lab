# A90 H40 Bad Apple Deterministic Lifecycle H0

- Cycle: `H40`
- Init: `A90 Linux init 0.12.006 (h40-badapple-deterministic-lifecycle-v3)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_h40_badapple_deterministic_lifecycle_v3.img`
- Boot SHA256: `68e12101e151f9515f2cf519f2749a8c1218e6c79a49aa4c9fcadd96b0728db0`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Device action: `none`
- Runtime result: `unproved`

## Change

- Replays the H37 firmware mount plus ADSP/CDSP/SLPI one-shot cold-boot sequence explicitly.
- Starts the tracked boot-chime worker before forking the interactive HUD.
- Shows a visible STARTING frame before menu work blocks.
- Releases HUD input ownership while the video player owns physical cancellation.
- Binds video sync to the exact spawned audio worker PID and limits readiness to 10 seconds.
- Treats worker completion-before-ready as failure and accepts physical cancel during sync.
- Stops audio on every demo return, reports failure visibly, reopens fresh HUD input, and restores the menu.

## Boundary

- Independent review rejected v2's HUD-before-chime fork order; v3 reverses that order.
- H37 playback and H39 timeout are evidence for their own runs only.
- H40 cold-boot subsystem readiness, boot chime, physical input lifecycle, audio/video playback, cleanup, and final health remain unproved.
- The 10-second budget is a user-facing failure bound, not proof that audio will become ready.

## Candidate hazard binding

- Hazard ID: `A90_H40_EXPLICIT_SIBLING_SSCTL_DETERMINISTIC_DEMO_TEMPORARY_CANDIDATE`
- Statement: `H40 preserves the exact V3402 non-init boot components and private Bad Apple engine, replays the H37 firmware-backed ADSP/CDSP/SLPI cold-boot prerequisite sequence without the consumed cache flag, starts the tracked boot chime before the interactive HUD fork, and adds a deterministic physical demo lifecycle with immediate acknowledgement, worker-bound audio sync, bounded fail-fast/cancel, single input ownership, and a single cleanup path with fresh input reopen before menu return; all H40 runtime behavior remains unproved until one attended run.`
- Statement SHA256: `6c88727473c0a00bc2b41481ccc08a643ffb678aa724d47eb623180c6f1a1f44`
- Acceptance qualifies only these exact temporary-candidate bytes; it grants no live authority.

## Metadata

- Helper flags: ``
- Required init flags: `-DA90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS=1, -DA90_BADAPPLE_BOOT_EXPLICIT_SIBLING_SSCTL=1`
- Init extra flag count: `61`
