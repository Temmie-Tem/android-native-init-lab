# WSTA140 D-public HUD Presenter Service Source Build Pass

Date: 2026-07-05 09:25 KST

## Verdict

WSTA140 implements and source-builds the durable native D-public HUD presenter
service contract from WSTA139.  The service is native/root owned, starts before
the Debian handoff, watches the bounded HUD intent file, and preserves the
armed presenter through the native handoff cleanup path.

This is a source/build-only unit.  It did not flash, reboot, switch root, open a
live DRM node on the device, run Wi-Fi association, DHCP, public tunnel/smoke,
packet-filter mutation, or userdata mutation.

## Implemented

- Native command:
  `dpublic-hud-presenter-service [start|status|stop] [options]`.
- `start`:
  - prepares `/run/a90-dpublic` as numeric `root:a90hud` (`gid 3904`) with mode
    `1770`;
  - stops legacy auto-HUD;
  - forks a native/root presenter child;
  - records `/run/a90-dpublic/hud-presenter.pid`;
  - reports `forked-native-child-survives-switch-root`.
- Presenter child:
  - polls `/run/a90-dpublic/hud-intent.json` every `100ms`;
  - reuses the WSTA136 bounded/fail-closed intent parser;
  - presents only fresh sequence changes;
  - writes `/run/a90-dpublic/hud-presenter.status`.
- `status` reports process state, pid, pid/status/intent paths, DRM fd ownership,
  and `status.debian_direct_kms=0`.
- `stop` terminates the presenter, removes the pidfile, and releases DRM by
  process exit.
- Debian handoff cleanup now preserves the default armed durable presenter while
  still killing legacy unexpected native DRM owners.

## Build

- Cycle: `V3399`
- Init: `A90 Linux init 0.11.155 (v3399-dpublic-hud-presenter-service)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3399_dpublic_hud_presenter_service.img`
- Boot SHA256:
  `cd59b7a5eecc7dda464374c7fb412a60eeda7e2579ef7e2abe26d856277ff9dd`
- Candidate manifest:
  `workspace/private/builds/native-init/v3399-dpublic-hud-presenter-service/dpublic-hud-presenter-service.json`
- Native-init report:
  `docs/reports/NATIVE_INIT_V3399_DPUBLIC_HUD_PRESENTER_SERVICE_SOURCE_BUILD_2026-07-05.md`

The private candidate manifest records Debian direct KMS as false, the durable
service process model, runtime dir owner/mode, intent file mode, and handoff
preserve policy.

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3399_dpublic_hud_presenter_service.py \
  tests/test_build_native_init_boot_v3399_dpublic_hud_presenter_service.py
```

Pass.

```sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_build_native_init_boot_v3399_dpublic_hud_presenter_service
```

Pass, `5 tests`.

```sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta139_dpublic_hud_presenter_service_model
```

Pass, `8 tests`.

```sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  discover -s tests -p 'test_server_distro_wsta*.py'
```

Pass, `458 tests`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3399_dpublic_hud_presenter_service.py
```

Pass.  The build completed helper/native-init compile, required-string audit,
preserved ramdisk overlay, boot image pack, candidate manifest write, and report
write.

## Next

WSTA141 should live-gate V3399 through `native_init_flash.py`, run serial health
checks, then prove `dpublic-hud-presenter-service start|status|stop` on-device
without switch-root.  The later handoff survival proof should remain a separate
bounded unit after native service start/status/stop is device-proven.
