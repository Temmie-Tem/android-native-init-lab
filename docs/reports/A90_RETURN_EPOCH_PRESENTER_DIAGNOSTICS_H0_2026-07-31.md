# A90 return epoch and presenter diagnostics H0 closure

Date: 2026-07-31
Result: `A90_RETURN_EPOCH_PRESENTER_DIAGNOSTICS_H0_PASS`

Independent verdict: GO
Unresolved HIGH: 0
Unresolved MEDIUM: 0
Device actions: none
Review decision: `GO_A90_RETURN_EPOCH_PRESENTER_DIAGNOSTICS_H0`

## Result

The repeated 220-228 second attended results no longer support a supervisor or
global-sync delay claim. The old host observer accepted the USB serial bridge
that remained present through the Debian epoch and issued `hide` before it had
proved native-init had returned. That command could consume the observation
budget and end with a missing A90P1 END marker.

The return path now records the exact pre-handoff USB serial generation. It
issues no device command until the USB `(busnum, devnum)` generation changes,
the bound TTY identity remains stable across the settle interval, and every
deadline check still passes. It then requires one exact candidate
`version: <version> build=<build>` line before menu settlement and one exact
zero-failure selftest line afterward. A late generation cannot be promoted
after the return deadline.

The SSH observer now retains the exact presenter log plus read-only card0,
connector status/DPMS, and backlight state. These diagnostics remain
non-proof. Strict framing rejects marker injection, and malformed display
data cannot erase independently valid native-release, Debian PID1, or
Dropbear facts. Static mutation tests reject direct transport calls in the
entire epoch dependency corridor, output redirection, variable-based sysfs
writes, and write-capable diagnostic commands.

The Debian presenter now reports the exact KMS failure stage and errno for
card0 open, DRM master acquisition, dumb-buffer capability, connector
selection, buffer creation/registration/mapping, and SETCRTC. A cross-build
produced a static ARM64 ELF with no dynamic section or INTERP.

## Image and hash closure

The new Debian A/B images are byte-identical at
`394fc9e3db303ea41e48139a6f57b6559ddd868412d6b7b217d2765276e4d55c`.
The presenter is byte-identical at
`71ef72d67cc42f6c5ce9b295b1ad8f9be2104e4b2a0f267b21d4ba28c876e77d`.
The base image stayed unchanged and both read-only e2fsck checks passed.

Phase2C, the single-run keyer, absent-only staging, and the finalizer all pin
this same new clean image and receipt. The keyer additionally requires
`presenter.log` and `launcher.pid` to be absent before materialization. The
old ab-06 image is no longer selectable through this execution closure.

## Validation

- Integrated focused tests: `208/208` PASS.
- Independent focused tests: `171/171` PASS.
- A/B Debian image and presenter equality: PASS.
- Keyer audit: ready, no contract issue, new clean image selected.
- Phase2C packet construction: PASS, new clean image selected.
- Python `py_compile`: PASS.
- `git diff --check`: PASS.
- Device contact, staging, flash, reboot: none.

## Reviewed execution sources

- `workspace/public/src/scripts/revalidation/a90_observation_pipeline.py`: `4e43d16e3dc5b2ef7509fa0432e1bebc9629ab77099206d95138af54dcbd7e08`
- `workspace/public/src/scripts/revalidation/a90ctl.py`: `11c567c5ec4d7b95dfbe0409af1759a90087eb937e47ce627b21511316d5766d`
- `workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py`: `9cc66229526217b162cb4be112a13f708b7ffb6ea435d008c77c777f011de933`
- `workspace/public/src/scripts/server-distro/a90_phase2c_display_packet.py`: `bc688e68818396e7a204582b5a0236dff2baf6aa53194db73910e2862cf7c337`
- `workspace/public/src/scripts/server-distro/a90_phase2d_display_observer.py`: `6b9720ca2e53f0fbed6efe9208b54739fa7f57df84c7a72ab61940f104ff7744`
- `workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py`: `97429b35f24250f73e2801ecd916ce459d9c80ed4ea824b8cc8f449a07c66ae9`
- `workspace/public/src/scripts/server-distro/a90_phase2d_keyed_rootfs.py`: `7e1fa6ed7c44c9c0626ee6ceca7055a4846ec2b44d4bcc258d310aa5d066b8c8`
- `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`: `41d4a1cddb47ad0bdd63ddce81dfbc94e96329804c746a872f1e16e7b63cadb0`
- `workspace/public/src/scripts/server-distro/prepare_phase2_display_v1_rootfs.py`: `8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/a90_debian_display_v1.c`: `55672214fda501a96115edec222f830bb26921ca71cea5f86faa4beb65830950`
- `workspace/public/src/scripts/server-distro/phase2_display_v1/manifest.toml`: `84d5fe878d9102bf77afec612e7d06fef38fc7b729ecf2e45a93e22b44f32c95`
- `workspace/public/src/scripts/server-distro/phase2c_display_packet_v1/contract.toml`: `9fa65a66812bce302ecfe4860bc521d210e00075f772df9f9d00d1742ce0a59f`
- `workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py`: `895298b8be3c4fd5e004464d228c832fa8ca84099b80d0b5292adbba1436da95`

## Next bounded unit

This closure grants no live authority. The next unit is fresh single-run key
materialization followed by connected A90 D0 and final manifest preparation.
Only after those exact artifacts are closed should a new F1 approval token be
requested.
