# Native Init V3366 Hot-Reload Clean Storage Source Build

- Cycle: `V3366`
- Decision: `v3366-hot-reload-clean-storage-source-build`
- Init: `A90 Linux init 0.11.127 (v3366-hot-reload-clean-storage)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3366_hot_reload_clean_storage.img`
- Boot SHA256: `e966c47f134651357bc9dcd807dc5c48f0654f2967abc4a1bb33cb8493076067`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- H3 cleanup candidate after V3365 H2: keep the reload command and V3365 proof surface, but fix reload storage cleanliness.
- `/cache` mount setup now treats `EBUSY` plus an already-mounted rw `/cache` as ready.
- SD boot probing now adopts an already-mounted rw `/mnt/sdext` after UUID validation, then runs the same workspace, identity-marker, and rw probes before selecting SD storage.
- Normal boot behavior remains the same when those mounts are not already present.

## Validation Contract

- Static PASS requires the V3366 version strings, reload markers, and the storage adoption markers (`storage-adopt`, `sd already mounted rw`, `/cache already mounted rw`).
- Live H3 PASS, separately gated, requires: staged V3366 init SHA matches; `reload` returns through the new V3366 shell; `status` reports `BOOT OK`, `storage backend=sd`, runtime SD root, and `selftest fail=0`; then rollback to v2321 and health-check clean.
- No live H3 reload result is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `hot-reload-clean-storage`.
