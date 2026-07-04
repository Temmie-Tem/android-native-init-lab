# WSTA130 D-public HUD Presenter Model Source Pass

Date: 2026-07-05 07:34 KST

## Verdict

WSTA130 defines the replacement display architecture for the WSTA129
`SETCRTC` boundary.  The old WSTA127 target, where non-root Debian `a90hud`
directly owns DRM/KMS presentation, is now treated as rejected for the live
path.

The new model is split:

- Debian `a90hud` is a non-root, no-network HUD intent producer.
- Debian does not open `/dev/dri/card0` and never attempts KMS `SETCRTC`.
- A root/native-owned presenter keeps DRM master and owns KMS presentation.
- The only boundary is a bounded atomic JSON intent file with strict schema
  parsing.

This is a host-only source/model unit.  It did not perform device action, boot
flash, native reboot, Wi-Fi association, DHCP, public tunnel, packet-filter
mutation, userdata mutation, DRM open, KMS `SETCRTC`, or switch-root.

## Added

- `workspace/public/src/scripts/server-distro/run_wsta130_dpublic_hud_presenter_model.py`
  - inert by default and requires `--emit-presenter-model`;
  - records WSTA129 as `setcrtc-permission-denied`;
  - rejects direct non-root KMS as `rejected-for-live-path`;
  - defines Debian `a90hud` as a no-network intent producer only;
  - defines a native-init/root-owned KMS presenter as the sole DRM master;
  - defines `/run/a90-dpublic/hud-intent.json` as the bounded atomic intent
    transport;
  - forbids command/path/shell/url/ssid/psk/token/secret fields in the intent
    schema;
  - keeps public exposure default-off and live-gated.

- `tests/test_server_distro_wsta130_dpublic_hud_presenter_model.py`
  - default inert behavior;
  - split presenter/intent architecture validation;
  - bounded atomic intent schema validation;
  - service-launcher command shape without DRM/network arguments;
  - marker-only contract plan;
  - private source artifact generation;
  - non-private run-dir fail-closed behavior;
  - host-only/redaction source checks.

## Source Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta130_dpublic_hud_presenter_model.py \
  --run-id wsta130-dpublic-hud-presenter-model-20260705T0735KST \
  --run-dir workspace/private/runs/server-distro/wsta130-dpublic-hud-presenter-model-20260705T0735KST \
  --emit-presenter-model
```

Private output:

`workspace/private/runs/server-distro/wsta130-dpublic-hud-presenter-model-20260705T0735KST/wsta130_dpublic_hud_presenter_model.json`

Result:

- decision: `wsta130-dpublic-hud-presenter-model-source-pass`
- model state: `DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED`
- WSTA129 boundary acknowledged: true
- direct non-root KMS rejected: true
- producer user: `a90hud`, UID/GID `3904/3904`
- producer DRM/KMS access: false
- producer network access: false
- presenter owner: `native-init`
- presenter privilege model: `root-owned-kms-presenter`
- presenter DRM node: `/dev/dri/card0`
- intent file: `/run/a90-dpublic/hud-intent.json`
- intent max bytes: `4096`
- intent stale limit: `2000ms`
- intent update: `write-fsync-rename`
- public URL value logged: false
- secret values logged: `0`

All model checks were true.

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta130_dpublic_hud_presenter_model.py \
  tests/test_server_distro_wsta130_dpublic_hud_presenter_model.py
```

Pass.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta130_dpublic_hud_presenter_model.py'
```

`8 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

`439 tests OK`.

The WSTA94 runner-error JSON printed during the full run is the expected
exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA131 should fold this replacement HUD display architecture into the WSTA108
operator status bundle, superseding the WSTA127 direct non-root KMS model in
operator-facing status.  After that, the next live-capable unit can implement a
minimal presenter/intent prototype without giving the Debian `a90hud` service
direct KMS ownership.
