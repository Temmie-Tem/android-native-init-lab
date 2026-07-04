# WSTA94 Packet Filter Live Gate

- Date: 2026-07-04
- Scope: bounded D-public packet-filter loopback live gate
- Private run: `workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/`
- Decision: `wsta94-packet-filter-loopback-live-pass`

## Summary

WSTA94 proved the D-public packet-filter helper on-device in a bounded
loopback-only live prototype.  The run mounted a fresh private Debian rootfs
image, started temporary Dropbear over USB/NCM, staged loopback smoke helpers
and the packet-filter helper, then executed:

```text
preflight
loopback smoke before policy
apply-loopback-default-drop
observe default-drop policy
loopback smoke after policy
restore
exact IPv4/IPv6 rule comparison
cleanup + postcheck
final selftest
```

The final live result passed:

```text
explicit_live_gate=true
packet_filter_preflight_pass=true
loopback_before_ok=true
packet_filter_apply_pass=true
packet_filter_default_drop_observed=true
loopback_after_ok=true
packet_filter_restore_pass=true
packet_filter_restore_exact=true
dpublic_cleanup_ok=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
```

The packet-filter probe returned `0` in `1.237s`.  It observed the intended
policy:

```text
IPv4 INPUT DROP
IPv4 FORWARD DROP
IPv4 OUTPUT ACCEPT
IPv4 INPUT loopback ACCEPT
IPv6 INPUT DROP
IPv6 INPUT loopback ACCEPT
```

The loopback smoke marker remained reachable before and after default-drop, and
the restore proof reported:

```text
packet_filter_decision=packet-filter-restored
A90WSTA94_RESTORE_EXACT_V4=1
A90WSTA94_RESTORE_EXACT_V6=1
A90WSTA94_PACKET_FILTER_PROBE_PASS
```

## Live Evidence

Final run:

```text
run_id=wsta94-packet-filter-live-20260704T143227Z
resident=A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)
local_image=workspace/private/runs/server-distro/wsta94-image-stage-20260704T152000Z/debian-wsta94-packet-filter.img
local_image_sha256=63bb69b47b888a7fdcce69607251c51c9b2c867314ad2ee0280b2ca33e610ba7
started_utc=20260704T143238Z
ended_utc=20260704T143341Z
```

The runner restored the remote work image from the clean cached image before
the probe:

```text
remote_clean_sha_before=63bb69b47b888a7fdcce69607251c51c9b2c867314ad2ee0280b2ca33e610ba7
remote_clean_sha_after=63bb69b47b888a7fdcce69607251c51c9b2c867314ad2ee0280b2ca33e610ba7
remote_sha_after=63bb69b47b888a7fdcce69607251c51c9b2c867314ad2ee0280b2ca33e610ba7
```

Debian chroot and temporary admin SSH were live:

```text
debian_version=12.14
stage_marker_present=true
dropbear_started=true
debian_ssh_marker=true
```

Cleanup and postcheck completed:

```text
dpublic_cleanup_ok=true
cleanup_rc=0
postcheck_rc=0
post_mount_absent=1
post_loop_node_absent=1
post_dropbear_absent=1
```

Final device health stayed clean:

```text
selftest: pass=12 warn=1 fail=0
```

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta94_packet_filter_live_gate.py`
- `tests/test_server_distro_wsta94_packet_filter_live_gate.py`

Updated:

- `workspace/public/src/scripts/server-distro/a90_dpublic_packet_filter.sh`
- `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py` test coverage via
  `tests/test_prepare_wsta3_sta_rootfs.py`

The live runner is fail-closed and requires all explicit gates:

```text
--execute-loopback-default-drop-live
--allow-packet-filter-live
--ack-packet-filter-mutation
--force-restore-proof
```

Without those flags, the runner is device-inert.

## Fixes From Live Gaps

The first WSTA94 live attempts exposed two real issues:

1. `iptables-legacy-save` returned success while writing empty files in this
   environment.  The helper and probe now snapshot with `iptables -S`, convert
   that output into `iptables-restore` input, reject empty snapshots, and compare
   restored `iptables -S` output exactly.
2. Cleanup had to tolerate transient loop detach timing.  The runner now treats
   postcheck as authoritative for mount, loop, and Dropbear absence while still
   requiring cleanup execution and shadow restoration.

The helper version is now `2` and no longer depends on `iptables-legacy-save` /
`ip6tables-legacy-save` for the restore proof.

## Safety

- No boot image was built or flashed.
- No native reboot ran.
- No Wi-Fi association, DHCP, public tunnel, public smoke, external ping,
  userdata action, switch-root, or non-boot partition write ran.
- Packet-filter mutation was loopback-only, explicit-live-gated, and required a
  restore proof.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private raw artifacts and SSH keys remain under `workspace/private/` only.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta94_packet_filter_live_gate.py \
  tests/test_server_distro_wsta94_packet_filter_live_gate.py \
  tests/test_prepare_wsta3_sta_rootfs.py
```

Result: pass.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta94_packet_filter_live_gate \
  tests.test_prepare_wsta3_sta_rootfs -v
```

Result: `Ran 39 tests ... OK`.

Live command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta94_packet_filter_live_gate.py \
  --run-id wsta94-packet-filter-live-20260704T143227Z \
  --local-image workspace/private/runs/server-distro/wsta94-image-stage-20260704T152000Z/debian-wsta94-packet-filter.img \
  --local-image-sha256 63bb69b47b888a7fdcce69607251c51c9b2c867314ad2ee0280b2ca33e610ba7 \
  --execute-loopback-default-drop-live \
  --allow-packet-filter-live \
  --ack-packet-filter-mutation \
  --force-restore-proof
```

Result: `wsta94-packet-filter-loopback-live-pass`.
