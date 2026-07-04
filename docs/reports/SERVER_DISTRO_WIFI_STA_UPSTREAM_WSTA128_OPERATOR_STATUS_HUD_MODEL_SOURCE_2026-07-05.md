# WSTA128 Operator Status HUD Model Source Pass

Date: 2026-07-05 06:48 KST

## Scope

WSTA128 folds the private WSTA127 D-public HUD service model into the existing
WSTA108/WSTA90 operator server status bundle. This is a host-only status overlay.
It does not start the HUD, open DRM, perform KMS `SETCRTC`, switch root, or claim
HUD runtime proof.

This unit did not run a device action, build or flash a boot image, reboot
native init, associate Wi-Fi, run DHCP, open a public tunnel, run public smoke,
mutate packet filters, touch userdata, open DRM, perform KMS `SETCRTC`, or
switch root.

## Changes

- Updated `run_wsta108_operator_server_status.py` to accept
  `--wsta127-hud-model-json`.
- Added compact status field `hardening.hud_model`.
- WSTA108 now fail-closes unless the supplied WSTA127 result has the pass
  decision, non-empty all-true supplied checks, and a recomputed-valid HUD
  model via `run_wsta127_dpublic_hud_service_model.validate_model()`.
- Added status/check fields for:
  - HUD model supplied/defined;
  - no-network listener posture;
  - DRM node policy definition;
  - launcher no-new-privs/cap-zero requirement;
  - live proof remaining false.
- Added markdown lines for HUD model presence, target user, no-network posture,
  DRM node policy, and live proof state.
- Added operator next-action refinement:
  `prove-dpublic-hud-runtime-drm-boundary-before-always-on-profile`.

## Source Proof

Private regenerated status:

```text
workspace/private/runs/server-distro/wsta128-operator-status-hud-model-20260705T0648KST/wsta108_operator_server_status.json
```

Input proofs:

- WSTA88 workflow:
  `workspace/private/runs/server-distro/wsta107-status-hud-preflight-20260705T0200KST/wsta88_operator_workflow.json`
- WSTA90 manifest:
  `workspace/private/runs/server-distro/wsta108-server-status-hardening-input-20260705T0205KST/wsta90_service_hardening_manifest.json`
- WSTA94 packet filter:
  `workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/wsta94_result.json`
- Packet-filter control summary:
  `workspace/private/runs/server-distro/packet-filter-control-ssh-live-20260704T160025Z/packet_filter_control_summary.json`
- WSTA110 service launcher:
  `workspace/private/runs/server-distro/wsta110-service-launcher-live-20260704T173234Z/wsta110_result.json`
- WSTA117/WSTA114 syscall trace:
  `workspace/private/runs/server-distro/wsta117-server-only-wsta114-live-v2-20260705T0407KST/wsta114_result.json`
- WSTA120 Dropbear admin:
  `workspace/private/runs/server-distro/wsta120-dropbear-admin-live-v6-20260705T044147KST/wsta120_result.json`
- WSTA122 cloudflared model:
  `workspace/private/runs/server-distro/wsta122-cloudflared-service-model-20260705T045720KST/wsta122_cloudflared_service_model.json`
- WSTA125 native-upstream cloudflared runtime:
  `workspace/private/runs/server-distro/wsta125-native-upstream-cloudflared-runtime-live-v4-20260705T062106KST/wsta125_result.json`
- WSTA127 D-public HUD model:
  `workspace/private/runs/server-distro/wsta127-dpublic-hud-service-model-20260705T0645KST/wsta127_dpublic_hud_service_model.json`

Result:

- Decision: `wsta108-operator-server-status-source-pass`
- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- Public state: `PUBLIC_OFF`
- HUD model state: `DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED`
- HUD model supplied/defined: true/true
- HUD live proven: false
- HUD user: `a90hud`, UID/GID `3904/3904`
- HUD no-network listener posture: true
- HUD DRM node: `/dev/dri/card0`
- HUD DRM node policy defined: true
- HUD DRM master required: true
- HUD KMS surface: `dumb-framebuffer-xbgr8888`
- HUD launcher no-new-privs/cap-zero required: true/true
- HUD direct root always-on start rejected: true
- Operator next actions include
  `prove-dpublic-hud-runtime-drm-boundary-before-always-on-profile`
- Remaining launcher profiles still include `dpublic-hud`
- Remaining syscall profiles still include `dpublic-hud`
- Public URL value logged: false
- Secret values logged: `0`

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py \
  tests/test_server_distro_wsta108_operator_server_status.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  tests/test_server_distro_wsta108_operator_server_status.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

Result:

- WSTA108 focused tests: `31 tests OK`
- Full server-distro WSTA regression: `422 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.
- `git diff --check`: OK

## Next

WSTA128 makes the HUD model visible in operator status but does not retire the
HUD live proof gap. The next bounded unit should be the HUD live proof on the SD
work image: stage policy, launch through `a90-service-launch` as `a90hud`, prove
no-new-privs/CapEff-zero/no-network posture, prove `/dev/dri/card0` access
without broader root, capture DRM/KMS syscalls, and clean up HUD runtime
sidecars.
