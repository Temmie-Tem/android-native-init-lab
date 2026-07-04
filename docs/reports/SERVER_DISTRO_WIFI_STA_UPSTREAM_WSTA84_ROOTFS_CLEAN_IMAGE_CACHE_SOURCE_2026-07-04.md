# WSTA84 Rootfs Clean Image Cache Source

- Date: 2026-07-04
- Scope: source-only optimization for repeated WSTA42/WSTA55/WSTA58 live runs
- Decision: `wsta84-rootfs-clean-image-cache-source-pass`

## Summary

WSTA83 proved WSTA80 to WSTA58 live end-to-end, but both WSTA42 sub-runs had
to reinstall the Debian rootfs image because the read-write chroot changed the
work image SHA between legs.  WSTA84 changes WSTA42's image preparation from
"host re-upload the work image whenever it drifted" to a clean-image cache:

```text
remote clean image missing/drifted -> upload clean image once
remote work image missing/drifted  -> device-side copy clean image to work image
remote work image clean            -> skip restore
```

The default clean image is the normal remote image path with `.clean` appended.
Operators can still disable the cache by passing an empty `--remote-clean-image`,
which preserves the previous direct-upload behavior.

## Source Changes

Updated WSTA42:

- Added `--remote-clean-image`, defaulting to `DEFAULT_REMOTE_IMAGE + ".clean"`.
- Added `prepare_remote_work_image()` to verify the work image and clean image
  separately.
- Added `install_image_to_remote()` so the existing checked tcpctl install path
  can upload the clean image without changing the public WSTA42 API.
- Added `restore_work_image_from_clean()` which copies the clean image to the
  work image on-device before mounting, then verifies the work-image SHA.
- Added fail-closed decisions:
  - `wsta42-blocked-remote-clean-image-sha`
  - `wsta42-blocked-clean-image-restore`
- Preserved the old direct upload path when clean-image caching is disabled.

Updated WSTA43:

- Added `--remote-clean-image`.
- Propagates custom clean image paths into the nested WSTA42 run so custom
  `--remote-image` users do not accidentally restore from the default image.

## Safety

- Source-only change; no live device command ran for WSTA84.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
  userdata action, switch-root, or non-boot partition write ran.
- The future live behavior only writes SD/runtime image files under the existing
  WSTA rootfs image path family.
- Raw public URL values, credentials, network identifiers, routable addresses,
  confirm-token values, and device serials are not committed here.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py \
  workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py \
  tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py \
  tests/test_server_distro_wsta43_orchestrated_native_uplink_dpublic.py
```

Result: pass.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta42_native_uplink_dpublic_tunnel \
  tests.test_server_distro_wsta43_orchestrated_native_uplink_dpublic \
  tests.test_server_distro_wsta45_appliance_operator \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta80_persistent_operator_execute_gate -v
```

Result: `Ran 55 tests ... OK`.

Coverage added:

- drifted work image restores from a valid clean image without host re-upload;
- missing/drifted clean image uploads once, then restores work from clean;
- empty `--remote-clean-image` preserves the legacy direct upload path;
- restore script uses device-side copy and verifies the restored work SHA;
- WSTA43 propagates custom clean image paths to WSTA42.

```text
git diff --check
```

Result: pass.

## Next

Run the next explicit WSTA live proof or a bounded WSTA42 live micro-run to
measure whether the second leg now avoids host-side rootfs upload and uses
`remote_work_restore_from_clean` instead.
