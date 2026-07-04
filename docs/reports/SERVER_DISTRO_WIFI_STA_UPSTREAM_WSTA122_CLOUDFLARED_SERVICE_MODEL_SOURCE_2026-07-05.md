# WSTA122 Cloudflared Service Model Source Pass

Date: 2026-07-05 04:57 KST

## Scope

WSTA122 defines the hardening target model for the D-public
`cloudflared-quick-tunnel` service. This is a host-only source/model unit. It
does not start a tunnel and does not rebrand prior tunnel reachability as a
hardening proof.

This unit did not run a device action, build or flash a boot image, reboot
native init, associate Wi-Fi, run DHCP, open a public tunnel, run public smoke,
mutate packet filters, touch userdata, or switch root.

## Changes

- Added `run_wsta122_cloudflared_service_model.py`.
- Added `tests/test_server_distro_wsta122_cloudflared_service_model.py`.
- The default invocation is inert and blocks until
  `--emit-cloudflared-model` is supplied.
- The model defines the target service contract for
  `cloudflared-quick-tunnel`:
  - non-root user/group `a90tunnel`, UID/GID `3902/3902`;
  - daemon privilege model `non-root-outbound-client`;
  - default public state off;
  - start requires the private enable marker
    `/etc/a90-dpublic/cloudflared-quick-enable`;
  - start requires an explicit operator live gate;
  - no boot autostart without the enable marker;
  - command shape:
    `/usr/local/bin/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8080 --metrics 127.0.0.1:0 --loglevel info`;
  - launcher shape:
    `/usr/local/bin/a90-service-launch cloudflared-quick-tunnel ...`;
  - no-new-privs and zero effective capabilities required;
  - direct root firstboot start is marked unacceptable for an always-on
    profile;
  - packet-filter precondition is loopback-default-drop before public start;
  - public URL is private runtime state only and not committable.

## Source Proof

Private output:

```text
workspace/private/runs/server-distro/wsta122-cloudflared-service-model-20260705T045720KST/wsta122_cloudflared_service_model.json
```

Result:

- Decision: `wsta122-cloudflared-service-model-source-pass`
- Model state: `CLOUDFLARED_SERVICE_MODEL_SOURCE_DEFINED`
- Service: `cloudflared-quick-tunnel`
- Target identity: `a90tunnel`, UID/GID `3902/3902`
- Default public state: off
- Explicit enable marker required: true
- Operator live gate required: true
- No autoupdate: true
- Loopback origin: true
- Loopback ephemeral metrics: true
- Outbound-only tunnel client: true
- Launcher/no-new-privs/cap-zero required: true
- Direct root start rejected for always-on profile: true
- Public URL logged in committed output: false
- Secret values logged: `0`
- All model checks: true

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta122_cloudflared_service_model.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta122_cloudflared_service_model
```

Result:

- WSTA122 focused tests: `7 tests OK`
- Full server-distro WSTA regression: `391 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.
- `git diff --check`: OK

## Next

WSTA122 is a source model, not a live proof. The next bounded unit should either
wire this model into WSTA90/WSTA108 operator status as a cloudflared model
overlay, or implement a bounded private live gate that starts cloudflared via
`a90-service-launch` as `a90tunnel`, proves UID/GID/no-new-privs/cap-zero and
outbound-only behavior, then cleans the tunnel process and runtime files.
