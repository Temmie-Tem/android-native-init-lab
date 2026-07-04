# WSTA90 Service Hardening Manifest Source

- Date: 2026-07-04
- Scope: host-only D-public service hardening manifest skeleton
- Private run: `workspace/private/runs/server-distro/wsta90-service-hardening-manifest-20260704T131000Z/`
- Decision: `wsta90-service-hardening-manifest-source-pass`

## Summary

WSTA90 consumes the WSTA89 readiness audit and emits the first structured
D-public service hardening contract.  This is still source/planning only: no
seccomp filter, capability drop, user creation, packet filter, or service
launcher is enforced yet.

The generated manifest covers five service surfaces:

```text
dpublic-smoke-httpd         user=a90www               network=loopback 127.0.0.1:8080
cloudflared-quick-tunnel    user=a90tunnel            network=outbound + loopback origin
dropbear-admin-usb          user=a90admin             network=USB/NCM admin only
dpublic-hud                 user=a90hud               network=none, DRM output only
wsta-native-uplink-helper   user=root-native-boundary network=native-owned Wi-Fi boundary
```

All entries start with:

```text
no_new_privs=true
ambient_capabilities=[]
bounding_capabilities=[]
```

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta90_service_hardening_manifest.py`
- `tests/test_server_distro_wsta90_service_hardening_manifest.py`

The runner:

- requires `--emit-service-hardening-manifest`;
- requires a passing WSTA89 readiness audit;
- fails closed if seccomp is not ready for profile source work;
- writes `wsta90_service_hardening_manifest.json` and a markdown summary under
  a private run directory;
- keeps public summaries redacted;
- performs no device action.

## Current Manifest Result

The live host-side run consumed:

```text
workspace/private/runs/server-distro/wsta89-hardening-readiness-audit-20260704T130000Z/wsta89_hardening_readiness.json
```

Result:

```text
wsta90-service-hardening-manifest-source-pass
service_count=5
all_services_no_new_privs=true
all_services_drop_ambient_caps=true
seccomp_ready_for_profile_source=true
```

Blocking before enforcement:

```text
non-root users/groups not staged
syscall traces not captured
packet-filter backend not inventoried
dropbear admin user model not finalized
```

Recommended next units:

```text
WSTA91 read-only live: netfilter/iptables/nftables inventory
WSTA92 source: rootfs user/group and no-new-privs launcher plan
WSTA93 live/source: trace smoke-httpd syscall set under loopback-only load
```

## Safety

- Host-only source/manifest work; no device command ran for WSTA90.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
  userdata action, switch-root, or non-boot partition write ran.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private raw artifacts remain under `workspace/private/` only.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta90_service_hardening_manifest -v
```

Result: `Ran 7 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta90_service_hardening_manifest.py \
  tests/test_server_distro_wsta90_service_hardening_manifest.py
```

Result: pass.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta90_service_hardening_manifest.py \
  --emit-service-hardening-manifest \
  --run-dir workspace/private/runs/server-distro/wsta90-service-hardening-manifest-20260704T131000Z \
  --print-full-json
```

Result: `wsta90-service-hardening-manifest-source-pass`.

```text
git diff --check
```

Result: pass.

## Next

WSTA91 should be a read-only live netfilter/iptables/nftables inventory.  The
manifest deliberately keeps packet filtering as a blocker until that inventory
selects a viable backend.
