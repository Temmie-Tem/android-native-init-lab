# WSTA131 Operator Status HUD Presenter Source Pass

Date: 2026-07-05 07:40 KST

## Verdict

WSTA131 folds the WSTA130 HUD presenter architecture into the WSTA108 operator
server status bundle.  Operator-facing status now treats the WSTA127 direct
non-root KMS HUD model as superseded and shows the split intent/native-presenter
model as the active HUD display architecture.

This is a host-only source/status unit.  It did not perform device action, boot
flash, native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
packet-filter mutation, userdata mutation, DRM open, KMS `SETCRTC`, or
switch-root.

## Source Changes

- `workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py`
  - imports WSTA130 and accepts `--wsta130-hud-presenter-model-json`;
  - fail-closes on non-private, non-pass, or recomputed-invalid WSTA130 model
    input;
  - adds `hardening.hud_presenter_model`;
  - marks the legacy `hardening.hud_model` as
    `superseded_by_presenter_model=true` when WSTA130 is supplied;
  - updates operator next actions from the old direct-KMS live proof to
    `prototype-dpublic-hud-intent-presenter-boundary-before-live-hud-profile`;
  - renders the presenter model, split architecture, intent file, and native
    presenter owner in the markdown status.

- `tests/test_server_distro_wsta108_operator_server_status.py`
  - adds WSTA130 proof fixtures;
  - covers WSTA130 positive fold-in with WSTA127 superseded;
  - covers WSTA130 non-pass and incomplete fail-closed branches;
  - updates template/source assertions.

## Source Proof

Private run directory:

`workspace/private/runs/server-distro/wsta131-hud-presenter-status-20260705T0740KST`

Inputs generated inside that run:

- WSTA88 preflight: `wsta88-persistent-operator-workflow-preflight-pass`
- WSTA127 legacy HUD model: `wsta127-dpublic-hud-service-model-source-pass`
- WSTA130 presenter model: `wsta130-dpublic-hud-presenter-model-source-pass`

WSTA108 command consumed both WSTA127 and WSTA130:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py \
  --run-id wsta131-wsta108-hud-presenter-status-20260705T0740KST \
  --run-dir workspace/private/runs/server-distro/wsta131-hud-presenter-status-20260705T0740KST/wsta108 \
  --emit-server-status \
  --wsta88-operator-workflow-json workspace/private/runs/server-distro/wsta131-hud-presenter-status-20260705T0740KST/wsta88/wsta88_operator_workflow.json \
  --wsta127-hud-model-json workspace/private/runs/server-distro/wsta131-hud-presenter-status-20260705T0740KST/wsta127/wsta127_dpublic_hud_service_model.json \
  --wsta130-hud-presenter-model-json workspace/private/runs/server-distro/wsta131-hud-presenter-status-20260705T0740KST/wsta130/wsta130_dpublic_hud_presenter_model.json
```

Result:

- decision: `wsta108-operator-server-status-source-pass`
- state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- public state: `PUBLIC_OFF`
- `hud_model_defined=true`
- `hud_model.superseded_by_presenter_model=true`
- `hud_model.superseded_reason=wsta129-setcrtc-permission-denied`
- `hud_presenter_model_defined=true`
- `hud_direct_nonroot_kms_rejected=true`
- `hud_intent_producer_no_drm=true`
- `hud_intent_producer_no_network=true`
- `hud_native_presenter_owner=true`
- `hud_intent_schema_fail_closed=true`
- `public_url_value_logged=false`
- `secret_values_logged=0`

Markdown status now includes:

- `D-public HUD direct KMS superseded: true`
- `D-public HUD presenter model: true`
- `D-public HUD display architecture: split-intent-native-presenter`
- `D-public HUD intent producer no DRM: true`
- `D-public HUD presenter owner: native-init`
- `D-public HUD intent file: /run/a90-dpublic/hud-intent.json`

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py \
  tests/test_server_distro_wsta108_operator_server_status.py
```

Pass.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta108_operator_server_status.py'
```

`34 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

`442 tests OK`.

The WSTA94 runner-error JSON printed during the full run is the expected
exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA132 can now start the implementation ladder for the split display path:
stage a minimal intent producer and a root/native presenter prototype, still
default-off and no-public, then prove the live boundary without giving Debian
`a90hud` direct KMS ownership.
