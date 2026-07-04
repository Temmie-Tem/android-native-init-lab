# WSTA89 Hardening Readiness Audit

- Date: 2026-07-04
- Scope: host-only D-harden readiness audit after WSTA88
- Private run: `workspace/private/runs/server-distro/wsta89-hardening-readiness-audit-20260704T130000Z/`
- Decision: `wsta89-hardening-readiness-audit-pass`

## Summary

WSTA89 moves the WSTA/D-public track from repeated publish proofs into the
hardening phase.  It adds a host-only audit runner that consumes existing
redacted D0 and Debian-eye inventory summaries, then classifies the current
D-harden readiness surface:

```text
seccomp-bpf-per-service          ready-for-profile-source
capability-drop-nonroot-services needs-service-manifest
network-namespace-containment    partial-no-veth
tun-node-tunnel-support          partial-node-missing
apparmor-mac                     needs-proof
packet-filter-default-drop       needs-netfilter-inventory
overlay-free-persistence         blocked-overlay-missing-use-plain-ext4
minimal-vendor-userspace         ready-observed-absent
tier2-text-hard-disable          needs-target-selection
```

The audit pass means the redacted readiness artifact was produced; it does not
claim the server is hardened yet.

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta89_hardening_readiness_audit.py`
- `tests/test_server_distro_wsta89_hardening_readiness_audit.py`

The runner:

- requires `--audit-hardening-readiness`;
- consumes only existing JSON summaries;
- performs no device action;
- emits `wsta89_hardening_readiness.json` and a markdown summary under a private
  run directory;
- keeps public summaries redacted;
- reports concrete recommended next units.

## Live Current-State Audit

WSTA89 consumed:

```text
D0: workspace/private/runs/server-distro/d0-device-live-20260702T200338Z/inventory_public_summary.json
Debian-eye: workspace/private/runs/server-distro/debian-eye-hw-inventory-20260704T082032Z/debian_eye_public_summary.json
```

Key findings:

- `CONFIG_SECCOMP=y` and `CONFIG_SECCOMP_FILTER=y`; seccomp profile source work
  is unblocked.
- Root shadow is locked and ext4 is available, but service users/capability
  policy are not yet defined.
- `CONFIG_NET_NS=y`, but `CONFIG_VETH=n`; network namespace containment needs a
  no-veth design or a deliberate host-network fallback.
- `CONFIG_TUN=y`, but `/dev/net/tun` is absent in D0; quick HTTP tunnel does
  not necessarily need it, but TUN-based modes would need node materialization.
- AppArmor support was not proven by the existing D0 summary.
- netfilter/nftables/iptables readiness was not proven by the existing D0
  summary, so default-drop packet filtering needs a read-only inventory before
  design selection.
- OverlayFS is absent; persistence design should stay on plain ext4/userdata or
  SD image.
- Debian-eye inventory observed the vendor command stacks absent from the
  Debian view, consistent with keeping vendor Wi-Fi native-owned.

Blocking items before a persistent always-on public posture:

```text
capability-drop-nonroot-services
packet-filter-default-drop
```

Recommended next units:

```text
WSTA90 source: per-service seccomp/capability manifest skeleton
WSTA91 read-only live: netfilter/iptables/nftables inventory
WSTA92 source/live: enforce no-new-privs plus capability drop for one smoke service
WSTA93 design: Tier-2 hard-disable candidate selection after service needs are fixed
```

## Safety

- Host-only audit; no device command ran for WSTA89.
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
  tests.test_server_distro_wsta89_hardening_readiness_audit -v
```

Result: `Ran 7 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta89_hardening_readiness_audit.py \
  tests/test_server_distro_wsta89_hardening_readiness_audit.py
```

Result: pass.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta89_hardening_readiness_audit.py \
  --audit-hardening-readiness \
  --run-dir workspace/private/runs/server-distro/wsta89-hardening-readiness-audit-20260704T130000Z \
  --print-full-json
```

Result: `wsta89-hardening-readiness-audit-pass`.

```text
git diff --check
```

Result: pass.

## Next

Continue with WSTA90 source work: define the per-service seccomp/capability
manifest skeleton for the D-public smoke service and tunnel process.  Run the
netfilter inventory as a separate read-only live unit before choosing an
iptables/nftables default-drop implementation.
