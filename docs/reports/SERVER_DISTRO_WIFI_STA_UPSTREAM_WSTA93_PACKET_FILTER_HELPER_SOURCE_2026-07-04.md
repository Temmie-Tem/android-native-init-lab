# WSTA93 Packet Filter Helper Source

- Date: 2026-07-04
- Scope: host-only bounded packet-filter helper staging for D-public
- Private run: `workspace/private/runs/server-distro/wsta93-packet-filter-helper-20260704T134500Z/`
- Decision: `wsta3-private-rootfs-prepared` with WSTA93 helper staged

## Summary

WSTA93 adds the bounded helper needed before any live default-drop prototype.
The helper is staged into the D-public Debian rootfs, but it is not invoked by
firstboot and no firewall policy is applied during this unit.

Helper target:

```text
/usr/local/bin/a90-dpublic-packet-filter
```

Supported operations:

```text
preflight
apply-loopback-default-drop
restore
status
```

The apply operation is intentionally narrow:

```text
backend=legacy-iptables
INPUT default=DROP
FORWARD default=DROP
OUTPUT default=ACCEPT
loopback INPUT=ACCEPT
established/related INPUT=ACCEPT
```

Before applying, the helper saves the current IPv4 and IPv6 filter tables under
`/run/a90-dpublic/packet-filter/`.  The `restore` operation reloads those saved
tables.  If apply fails after saving, the helper attempts restore before
returning failure.

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/a90_dpublic_packet_filter.sh`

Updated:

- `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`
- `workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py`
- `tests/test_prepare_wsta3_sta_rootfs.py`
- `tests/test_server_distro_debian_rootfs_builder.py`

The WSTA rootfs preparer now:

- stages `a90-dpublic-packet-filter` with mode `0755`;
- verifies the helper has preflight, apply, restore, and status surfaces;
- verifies save-before-apply and failure-restore logic is present;
- verifies loopback accept plus default-drop rules are present;
- verifies auto-apply is absent;
- records `packet-filter-helper=/usr/local/bin/a90-dpublic-packet-filter`;
- still records `packet-filter-policy=not-enforced`.

The base Debian rootfs builder stages the same helper for future clean rootfs
builds.

## Host Proof

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  --run-id wsta93-packet-filter-helper-20260704T134500Z \
  --immediate-snapshot-only \
  --no-tarball
```

Key result:

```text
packet_filter_helper.latest_helper_staged=true
packet_filter_helper.preflight_op_present=true
packet_filter_helper.apply_op_present=true
packet_filter_helper.restore_op_present=true
packet_filter_helper.save_before_apply_present=true
packet_filter_helper.failure_restore_present=true
packet_filter_helper.loopback_accept_present=true
packet_filter_helper.default_drop_present=true
packet_filter_helper.output_accept_present=true
packet_filter_helper.auto_apply_absent=true
packet_filter_helper.secret_hygiene_marker=true
packet_filter_stage_marker.helper_marker_present=true
secret_values_logged=0
no_public_tunnel=true
no_wifi_association=true
no_dhcp=true
no_ping=true
```

The staged helper also passed `sh -n` syntax validation.

## Safety

- Host-only rootfs preparation; no device command ran for WSTA93.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
  userdata action, switch-root, or non-boot partition write ran.
- No packet-filter rule mutation command ran in this unit.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private rootfs copies and raw summaries remain under `workspace/private/`
  only.

## Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_packet_filter.sh
```

Result: pass.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_prepare_wsta3_sta_rootfs \
  tests.test_server_distro_debian_rootfs_builder -v
```

Result: `Ran 28 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_server_distro_debian_rootfs_builder.py
```

Result: pass.

```text
git diff --check
```

Result: pass.

## Next

The next unit can be a live, bounded WSTA94 prototype: boot or hand off into a
fresh private rootfs containing the helper, run `preflight`, apply the
loopback-only default-drop policy, verify local loopback smoke still works and
unexpected inbound is blocked, then run `restore` and verify the original policy
was restored before cleanup.
