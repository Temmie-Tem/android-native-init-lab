# WSTA138 Operator Status HUD Presenter Live Source Pass

Date: 2026-07-05 09:00 KST

## Verdict

WSTA138 folds the WSTA137 native/root-owned HUD presenter live proof into the
WSTA108 operator server status bundle.  Operator-facing status now treats the
D-public HUD presenter as live-proven: V3398 was checked-flashed in WSTA137,
fresh bounded intents validated and presented through the native KMS presenter,
and forbidden/stale intent reject paths passed.

This WSTA138 unit is host-only.  It did not perform device action, boot flash,
native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
packet-filter mutation, userdata mutation, DRM open, KMS `SETCRTC`, or
switch-root.  It only re-read private WSTA137 transcripts and regenerated the
operator status model.

## Source Changes

- `workspace/public/src/scripts/server-distro/run_wsta137_dpublic_native_presenter_live_summary.py`
  - reads the private WSTA137 live transcripts;
  - emits `wsta137_dpublic_native_presenter_live.json`;
  - recomputes pass/fail checks for the V3398 candidate, checked flash SHA
    match, fresh validate, fresh present, reject paths, and final health;
  - keeps URLs/secrets out of the public proof surface.

- `workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py`
  - imports the WSTA137 proof validator;
  - accepts `--wsta137-hud-presenter-live-proof-json`;
  - fail-closes on non-private, non-pass, or recomputed-invalid WSTA137 input;
  - sets `hardening.hud_presenter_model.state` to
    `DPUBLIC_HUD_NATIVE_PRESENTER_LIVE_PROVEN`;
  - marks `hud_live_proven`, `native_presenter_live_proven`, checked flash,
    validate, present, and reject-path checks true when the proof is complete;
  - moves the next action from prototype proving to durable Debian-handoff
    service design.

- `tests/test_server_distro_wsta108_operator_server_status.py`
  - adds WSTA137 live proof fixtures;
  - covers positive proof ingestion;
  - covers non-pass and incomplete fail-closed branches;
  - updates template, markdown, and source assertions.

## Source Proof

WSTA137 summary proof:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta137_dpublic_native_presenter_live_summary.py \
  --run-id wsta137-dpublic-native-presenter-live-summary-20260705T0900KST \
  --run-dir workspace/private/runs/server-distro/wsta137-dpublic-native-presenter-live-summary-20260705T0900KST \
  --source-run-dir workspace/private/runs/server-distro/wsta137-dpublic-native-presenter-live-20260705T0835KST
```

Result:

- decision: `wsta137-dpublic-native-hud-presenter-live-pass`
- candidate: `0.11.154 (v3398-dpublic-hud-presenter)`
- boot SHA256:
  `b18be6a39eb41fb71a5256db3b23d5c648631fb164061b98b35a35ffba9f3a0c`
- checked flash helper used: `true`
- local/remote/readback SHA matched: `true`
- checked flash boot health clean: `true`
- fresh validate passed: `true` (`sequence=13701`, `age_ms=653`)
- fresh present passed: `true` (`sequence=13702`, `age_ms=556`,
  `1080x2400`, `crtc=133`)
- reject paths passed: `true`
- final health clean: `true`

WSTA108 operator status proof:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py \
  --run-id wsta138-operator-status-hud-presenter-live-20260705T0900KST \
  --run-dir workspace/private/runs/server-distro/wsta138-operator-status-hud-presenter-live-20260705T0900KST \
  --emit-server-status \
  --wsta88-operator-workflow-json workspace/private/runs/server-distro/wsta107-status-hud-preflight-20260705T0200KST/wsta88_operator_workflow.json \
  --wsta90-service-hardening-manifest-json workspace/private/runs/server-distro/wsta108-server-status-hardening-input-20260705T0205KST/wsta90_service_hardening_manifest.json \
  --wsta94-packet-filter-proof-json workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/wsta94_result.json \
  --packet-filter-control-summary-json workspace/private/runs/server-distro/packet-filter-control-ssh-live-20260704T160025Z/packet_filter_control_summary.json \
  --wsta110-service-launcher-proof-json workspace/private/runs/server-distro/wsta110-service-launcher-live-20260704T173234Z/wsta110_result.json \
  --wsta114-syscall-trace-proof-json workspace/private/runs/server-distro/wsta117-server-only-wsta114-live-v2-20260705T0407KST/wsta114_result.json \
  --wsta120-dropbear-admin-proof-json workspace/private/runs/server-distro/wsta120-dropbear-admin-live-v6-20260705T044147KST/wsta120_result.json \
  --wsta122-cloudflared-model-json workspace/private/runs/server-distro/wsta122-cloudflared-service-model-20260705T045720KST/wsta122_cloudflared_service_model.json \
  --wsta125-cloudflared-runtime-proof-json workspace/private/runs/server-distro/wsta125-native-upstream-cloudflared-runtime-live-v4-20260705T062106KST/wsta125_result.json \
  --wsta127-hud-model-json workspace/private/runs/server-distro/wsta127-dpublic-hud-service-model-20260705T0645KST/wsta127_dpublic_hud_service_model.json \
  --wsta130-hud-presenter-model-json workspace/private/runs/server-distro/wsta130-dpublic-hud-presenter-model-20260705T0735KST/wsta130_dpublic_hud_presenter_model.json \
  --wsta137-hud-presenter-live-proof-json workspace/private/runs/server-distro/wsta137-dpublic-native-presenter-live-summary-20260705T0900KST/wsta137_dpublic_native_presenter_live.json
```

Result:

- decision: `wsta108-operator-server-status-source-pass`
- state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- public state: `PUBLIC_OFF`
- `hud_model_defined=true`
- `hud_presenter_model_defined=true`
- `hud_live_proven=true`
- `hud_native_presenter_live_proven=true`
- `hud_presenter_checked_flash_proven=true`
- `hud_presenter_validate_live_proven=true`
- `hud_presenter_present_live_proven=true`
- `hud_presenter_reject_paths_live_proven=true`
- `public_url_value_logged=false`
- `secret_values_logged=0`

Markdown status now includes:

- `D-public HUD live proof: true`
- `D-public HUD native presenter live proof: true`
- `D-public HUD presenter checked flash: true`
- `D-public HUD presenter KMS present: true`
- `D-public HUD presenter reject paths: true`

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py \
  workspace/public/src/scripts/server-distro/run_wsta137_dpublic_native_presenter_live_summary.py
```

Pass.

```sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta108_operator_server_status
```

`37 tests OK`.

## Next

WSTA139 should design the durable native HUD presenter service across the Debian
handoff.  The target shape is native/root keeping sole DRM/KMS ownership while
Debian writes fresh bounded intent files only; the design should specify
lifetime, restart/cleanup, stale-intent behavior, and how to prove that the
presenter is the sole DRM fd holder during handoff.
