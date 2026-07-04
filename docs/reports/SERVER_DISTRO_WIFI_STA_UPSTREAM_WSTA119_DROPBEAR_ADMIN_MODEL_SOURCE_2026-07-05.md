# WSTA119 Dropbear Admin Model Source Pass

Date: 2026-07-05 04:25 KST

## Scope

WSTA119 defines the source-level Dropbear admin user model that must replace the
current temporary D2 root-authorized-keys model before any always-on server
profile. This is a host-only source/model unit. It did not run a live device
action, build or flash a boot image, reboot native init, associate Wi-Fi, run
DHCP, open a public tunnel, run public smoke, mutate packet filters, touch
userdata, or switch root.

## Changes

- Added `run_wsta119_dropbear_admin_model.py`.
- The default invocation is inert and blocks until `--emit-admin-model` is
  supplied.
- The model keeps Dropbear as a root-boundary auth daemon, explicitly justified
  because SSH authentication/session setup requires that boundary.
- The login target is non-root `a90admin` instead of root:
  - UID/GID `3903/3903`;
  - home `/home/a90admin`;
  - shell `/bin/sh`;
  - authorized keys `/home/a90admin/.ssh/authorized_keys`;
  - home and `.ssh` mode `0700`, authorized keys mode `0600`.
- Root SSH login is disabled and `/root/.ssh/authorized_keys` is required to be
  absent.
- Dropbear command policy is key-only, root-denied, forwarding-denied, and bound
  to USB/NCM only:
  - `-s` password login disabled;
  - `-w` root login disabled;
  - `-j -k` local/remote forwarding disabled;
  - `-p 192.168.7.2:2222` admin USB/NCM bind.
- Added a stage-script generator for the later live gate. It may replace only
  the known WSTA109 placeholder line
  `a90admin:x:3903:3903:A90 service a90admin:/nonexistent:/usr/sbin/nologin`;
  any other existing `a90admin` entry is a fail-closed conflict.

## Source Proof

Private output:

```text
workspace/private/runs/server-distro/wsta119-dropbear-admin-model-20260705T0425KST/wsta119_dropbear_admin_model.json
```

Result:

- Decision: `wsta119-dropbear-admin-model-source-pass`
- Model state: `DROPBEAR_ADMIN_MODEL_SOURCE_DEFINED`
- Service: `dropbear-admin-usb`
- Daemon privilege model: `root-boundary-auth-daemon`
- Target identity: `a90admin`, UID/GID `3903/3903`
- Root login: disabled
- Password login: disabled
- Root authorized keys: absent-required
- Public tunnel: forbidden
- All model checks: true

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta119_dropbear_admin_model.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta119_dropbear_admin_model
```

Result:

- WSTA119 focused tests: `7 tests OK`
- Full server-distro WSTA regression: `403 tests OK`
- `git diff --check`: OK
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA119 is not a live proof. The next unit should run a bounded private
WSTA120 live gate on the SD work image: stage the admin model, start Dropbear
with `-s -w -j -k` on `192.168.7.2:2222`, prove SSH as `a90admin` returns
UID/GID `3903/3903`, prove root SSH is rejected, prove root authorized keys are
absent, then clean Dropbear/admin key material and postcheck the chroot/loop
state.
