# WSTA124 Cloudflared Runtime Live Gate

Date: 2026-07-05 05:46 KST

## Scope

WSTA124 adds a bounded live gate for the WSTA122 `cloudflared-quick-tunnel`
runtime model.  The runner is inert by default and requires explicit
acknowledgements before any cloudflared/public-exposure attempt:

- `--execute-cloudflared-runtime-live`
- `--allow-cloudflared-runtime-live`
- `--ack-public-exposure`
- `--ack-private-url-artifact`
- `--ack-runtime-cleanup`

This unit did not build or flash a boot image, reboot native init, associate
Wi-Fi, run DHCP, touch userdata, or switch root.  It uses the SD-backed Debian
work image as a temporary chroot service surface, then cleans Dropbear, runtime
sidecars, packet-filter state, mounts, and loop state.

## Changes

- Added `run_wsta124_cloudflared_runtime_live_gate.py`.
- Added a focused WSTA124 test module.
- Reused WSTA94/WSTA110/WSTA114/WSTA122 primitives for chroot lifecycle,
  service identities, launcher hardening, packet-filter gating, and syscall
  trace artifacts.
- Stage the runtime probe as a short-lived remote script instead of a large
  inline SSH command.
- Use the background launch PID for the smoke service instead of `pidof`, whose
  process-name matching is fragile for the launched helper.
- Pre-create the trace file as writable before launching `strace` through the
  non-root `a90tunnel` service identity.
- Fail closed before packet-filter apply when packet-filter preflight fails.
- Add resolver sync with loopback/link-local resolver rejection and host
  resolver fallback with redacted resolver content.
- Add a redacted egress-route preflight so public tunnel runtime does not start
  when the resolver target is unreachable.

## Live Results

Private result paths:

```text
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-surface-20260705T051528KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v1-20260705T051619KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v2-20260705T052003KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v3-20260705T052748KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v4-20260705T053132KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v5-20260705T053418KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v6-20260705T053845KST/wsta124_result.json
workspace/private/runs/server-distro/wsta124-cloudflared-runtime-live-v7-20260705T054259KST/wsta124_result.json
```

Key observations:

- Default invocation blocked as intended:
  `wsta124-blocked-cloudflared-runtime-live-required`.
- The default D1 rootfs image blocked at packet-filter preflight because it lacks
  the legacy iptables tools required for the live gate.
- The WSTA115 strace/packet-filter rootfs image passed packet-filter preflight
  and apply.
- Initial runtime attempts exposed runner issues and were fixed in-tree:
  smoke PID detection, long inline SSH runtime command, and trace-file
  permissions for non-root `strace`.
- After those fixes, cloudflared launched far enough to request a quick Tunnel,
  but no public URL was observed or saved.  The failure was upstream network
  reachability, not the local service model.
- Final WSTA124 v7 result stopped before packet-filter apply and before
  cloudflared runtime:
  `decision=wsta124-blocked-egress-route`.

Final v7 proof:

- Explicit live gate: true
- Local WSTA115 image present and restored from clean cache: true
- Debian chroot SSH marker: true
- Service hardening assets staged: true
- D-public binaries staged: true
- Native default route present: true (`ncm0`)
- Resolver sync ready: true, source `host-resolver`, values redacted
- Egress route ready: false
- Egress preflight marker: `target_present=1 route_ok=0 target_redacted=1`
- Packet filter preflight/apply: not run in v7
- Runtime probe/cloudflared: not run in v7
- Public URL value logged: false
- Secret values logged: `0`
- Postcheck: mount absent, loop absent, Dropbear absent
- Final selftest: `pass=12 warn=1 fail=0`

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta124_cloudflared_runtime_live_gate.py \
  tests/test_server_distro_wsta124_cloudflared_runtime_live_gate.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_server_distro_wsta124_cloudflared_runtime_live_gate.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  discover -s tests -p 'test_server_distro_wsta*.py'

git diff --check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90ctl.py selftest
```

Result:

- WSTA124 focused tests: `9 tests OK`
- Full server-distro WSTA regression: `403 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.
- `git diff --check`: OK
- Final resident health: `selftest pass=12 warn=1 fail=0`

## Next

WSTA124 provides the bounded runtime gate and now fail-closes before public
runtime when upstream egress is absent.  To complete a cloudflared runtime pass,
the next unit should first establish a known-good upstream route, preferably by
reusing the proven WSTA43/WSTA45 native-owned STA publish precondition or by
adding an explicitly gated NCM-egress/NAT preflight.  After egress is proven,
rerun WSTA124 and then fold the resulting private runtime proof into WSTA108
operator status.
