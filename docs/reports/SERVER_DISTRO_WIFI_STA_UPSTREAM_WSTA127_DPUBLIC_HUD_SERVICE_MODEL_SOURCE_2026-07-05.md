# WSTA127 D-public HUD Service Model Source Pass

Date: 2026-07-05 06:45 KST

## Scope

WSTA127 defines the hardening target for the Debian-side D-public HUD service.
This is a host-only source/model unit. It does not start the HUD, open DRM,
perform KMS `SETCRTC`, switch root, or claim a live device-node proof.

This unit did not run a device action, build or flash a boot image, reboot
native init, associate Wi-Fi, run DHCP, open a public tunnel, run public smoke,
mutate packet filters, touch userdata, open DRM, perform KMS `SETCRTC`, or
switch root.

## Added

- `workspace/public/src/scripts/server-distro/run_wsta127_dpublic_hud_service_model.py`
  - inert by default and requires `--emit-hud-model`;
  - defines the `dpublic-hud` target identity as non-root `a90hud`, UID/GID
    `3904/3904`;
  - defines no-network intent: no TCP listener, no UDP socket, no public inbound
    listener;
  - defines the display boundary: `/dev/dri/card0` materialized from
    `/sys/class/drm/card0/dev`, DRM master required, dumb framebuffer XBGR8888;
  - requires the service launcher, no-new-privs, and zero effective capabilities;
  - rejects direct root firstboot start for an always-on profile;
  - records runtime proof requirements for user/group, CapEff, DRM node policy,
    no-network posture, KMS syscall trace, and cleanup.

- `tests/test_server_distro_wsta127_dpublic_hud_service_model.py`
  - default inert safety;
  - model validation;
  - launcher command shape without URL/token/network arguments;
  - marker-only launch plan;
  - private source artifact generation;
  - non-private run-dir fail-closed behavior;
  - source/template redaction and host-only checks.

## Source Proof

Private output:

```text
workspace/private/runs/server-distro/wsta127-dpublic-hud-service-model-20260705T0645KST/wsta127_dpublic_hud_service_model.json
```

Result:

- Decision: `wsta127-dpublic-hud-service-model-source-pass`
- Model state: `DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED`
- Service: `dpublic-hud`
- User/group: `a90hud`, UID/GID `3904/3904`
- Daemon privilege model: `non-root-drm-client`
- Launcher command: `a90-service-launch dpublic-hud /usr/local/bin/a90-dpublic-hud`
- Default public off: true
- Network listener policy: none
- DRM node policy defined: true
- DRM master required: true
- KMS surface: `dumb-framebuffer-xbgr8888`
- no-new-privs required: true
- CapEff zero required: true
- Direct root always-on start rejected: true
- Public URL value logged: false
- Secret values logged: `0`

This source proof does not retire the HUD live gap yet. The remaining live work
is to prove the DRM node policy and runtime process posture on the SD-backed
Debian surface.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta127_dpublic_hud_service_model.py \
  tests/test_server_distro_wsta127_dpublic_hud_service_model.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  tests/test_server_distro_wsta127_dpublic_hud_service_model.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

Result:

- WSTA127 focused tests: `7 tests OK`
- Full server-distro WSTA regression: `419 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

Either fold this model into WSTA108 operator status as a HUD model overlay, or
move directly to a bounded HUD live proof: stage the WSTA127 policy into the SD
work image, run `a90-service-launch dpublic-hud /usr/local/bin/a90-dpublic-hud`
as `a90hud`, prove no-new-privs/CapEff-zero/no-network posture, prove
`/dev/dri/card0` can be opened without broader root, capture the DRM/KMS syscall
set, and cleanly remove HUD process/runtime sidecars.
