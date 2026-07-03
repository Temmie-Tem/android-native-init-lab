# Native Init V3373 Server-Distro D4B Userdata Appliance Source Build

- Cycle: `V3373`
- Decision: `v3373-server-distro-d4b-userdata-appliance-source-build`
- Init: `A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3373_server_distro_userdata_appliance.img`
- Boot SHA256: `78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`

## Change

- Adds the D4B command surface: `userdata-appliance-preflight`, `userdata-appliance-format`, `userdata-appliance-populate`, and `switch-root-to-userdata`.
- All D4 commands require `SERVER-DISTRO-D4-USERDATA-APPLIANCE`; mutating commands re-derive sysfs `PARTNAME=userdata` and compare host-pinned `devname`, `dev`, and `sectors` before touching storage.
- The surface does not rely on `/dev/block/by-name/userdata`; it materializes `/dev/block/a90-userdata` from verified `MAJOR:MINOR` only after target identity passes.
- The format path is deliberately explicit as `busybox mke2fs -t ext4 -F -L A90D4ROOT`; D4C remains gated on proving that formatter path on-device.
- Populate accepts only SHA-pinned source tarballs under `/mnt/sdext/a90/runtime/`, mounts userdata at `/mnt/a90-userdata-root`, extracts the rootfs, verifies `/sbin/init`, and writes `userdata=appliance-root`.
- `switch-root-to-userdata` verifies the appliance marker, prepares/moves `/proc`, `/sys`, and `/dev`, then execs BusyBox `switch_root` so userdata Debian init becomes PID1.
- This is a D4B source-build/static gate. D4C format/populate still requires candidate boot health, device-side preflight agreement, proven formatter behavior, and rollback readiness.

## Static Validation Contract

- Boot image strings must contain the V3373 identity, all four D4 command names, `SERVER-DISTRO-D4-USERDATA-APPLIANCE`, `A90D4`, `/sys/class/block`, `PARTNAME=`, `userdata`, `/dev/block/a90-userdata`, `/mnt/a90-userdata-root`, and the formatter/populate/switch markers.
- Source contract must show command table registration with `CMD_DANGEROUS` on mutating D4 commands and `CMD_DANGEROUS | CMD_NO_DONE` on `switch-root-to-userdata`.
- Live contract before D4C: flash only through `native_init_flash.py`, prove candidate health, run only device-side `userdata-appliance-preflight`, and roll back to v2321 unless the next bounded D4C unit starts immediately under the same controlled plan.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-d4b-userdata-appliance`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3373_server_distro_userdata_appliance.py tests/test_build_native_init_boot_v3373_server_distro_userdata_appliance.py tests/test_build_native_init_boot_v3372_server_distro_switchroot_stdio.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_build_native_init_boot_v3373_server_distro_userdata_appliance tests.test_build_native_init_boot_v3372_server_distro_switchroot_stdio tests.test_server_distro_d4a_userdata_preflight`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3373_server_distro_userdata_appliance.py`
- `git diff --check`

The build compiled the touched native-init C and produced the boot artifact above. This source/build
unit performed no flash, no reboot, no mount, no format, and no device-side command execution.

## Next Gate

D4C remains disallowed. The next bounded step is D4B candidate-health validation: confirm rollback and
recovery preconditions, flash this exact `V3373` artifact through `native_init_flash.py`, verify
`version`/`status`/`selftest`, run only `userdata-appliance-preflight`, then roll back to v2321 unless
the destructive D4C unit starts immediately under its own runbook.
