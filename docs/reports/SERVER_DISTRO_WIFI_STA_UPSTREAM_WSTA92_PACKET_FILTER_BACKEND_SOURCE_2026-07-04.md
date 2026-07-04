# WSTA92 Packet Filter Backend Source

- Date: 2026-07-04
- Scope: host-only legacy iptables userspace backend staging for D-public
- Private run: `workspace/private/runs/server-distro/wsta92-packet-filter-backend-20260704T133000Z/`
- Decision: `wsta3-private-rootfs-prepared` with WSTA92 packet-filter backend staged

## Summary

WSTA92 follows the WSTA91 result: the kernel has legacy netfilter support, but
the native userspace did not expose `iptables`, `ip6tables`, or `nft`.

This unit stages the packet-filter backend in the Debian D-public rootfs path,
not in native init:

```text
backend=legacy-iptables
requested_package=iptables
policy_enforced=false
default_drop_ready_for_source=true
```

The private host run started from a rootfs without legacy iptables tools and
ended with these required backend commands present:

```text
iptables-legacy
ip6tables-legacy
iptables-legacy-save
ip6tables-legacy-save
iptables-legacy-restore
ip6tables-legacy-restore
```

The host run downloaded/extracted the Debian arm64 `iptables` package plus
dependencies into the private rootfs copy.  Some nftables userspace bits are
dependency payloads of the package set, but WSTA92 explicitly selects the
legacy backend because WSTA91 observed `CONFIG_NF_TABLES=n` on the running
kernel.

## Source Changes

Updated:

- `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`
- `workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py`
- `tests/test_prepare_wsta3_sta_rootfs.py`
- `tests/test_server_distro_debian_rootfs_builder.py`

The WSTA rootfs preparer now:

- checks for the legacy iptables backend command set;
- downloads/extracts the Debian `iptables` package into the private rootfs copy
  when the tools are absent;
- fails closed if installation is disabled and the backend is missing;
- records `packet-filter-backend=legacy-iptables`;
- records `packet-filter-policy=not-enforced`;
- records `packet-filter-default-drop=deferred-WSTA93`;
- does not run packet-filter mutation commands.

The base Debian rootfs builder now includes `iptables` in the default package
set so future clean rootfs builds do not rely on a later WSTA preparer install
for the backend.

## Host Proof

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  --run-id wsta92-packet-filter-backend-20260704T133000Z \
  --immediate-snapshot-only \
  --no-tarball
```

Key result:

```text
packet_filter_tools.ok=true
packet_filter_tools.backend=legacy-iptables
packet_filter_tools.installed=true
packet_filter_tools.deb_count=10
packet_filter_tools.policy_enforced=false
packet_filter_tools.after.default_drop_ready_for_source=true
secret_values_logged=0
no_public_tunnel=true
```

WSTA92 intentionally did not create a live firewall policy.  It only makes the
selected userspace backend available for the next bounded prototype.

## Safety

- Host-only rootfs preparation; no device command ran for WSTA92.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
  userdata action, switch-root, or non-boot partition write ran.
- No `iptables`, `ip6tables`, or `nft` rule mutation command ran.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private rootfs copies, package payloads, and raw summaries remain under
  `workspace/private/` only.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_prepare_wsta3_sta_rootfs \
  tests.test_server_distro_debian_rootfs_builder \
  tests.test_server_distro_wsta89_hardening_readiness_audit \
  tests.test_server_distro_wsta90_service_hardening_manifest \
  tests.test_server_distro_wsta91_netfilter_inventory -v
```

Result: `Ran 47 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py \
  workspace/public/src/scripts/server-distro/run_wsta89_hardening_readiness_audit.py \
  workspace/public/src/scripts/server-distro/run_wsta90_service_hardening_manifest.py \
  workspace/public/src/scripts/server-distro/run_wsta91_netfilter_inventory.py \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_server_distro_debian_rootfs_builder.py \
  tests/test_server_distro_wsta89_hardening_readiness_audit.py \
  tests/test_server_distro_wsta90_service_hardening_manifest.py \
  tests/test_server_distro_wsta91_netfilter_inventory.py
```

Result: pass.

```text
git diff --check
```

Result: pass.

## Next

WSTA93 should prototype a bounded loopback-only default-drop policy using the
legacy iptables backend.  That unit should apply rules only inside a disposable
D-public rootfs/session and must include a restore path before any broader or
persistent policy is considered.
