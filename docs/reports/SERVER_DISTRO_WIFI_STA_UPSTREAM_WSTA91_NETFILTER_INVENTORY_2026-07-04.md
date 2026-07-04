# WSTA91 Netfilter Inventory Live

- Date: 2026-07-04
- Scope: read-only live netfilter/iptables/nftables inventory
- Private run: `workspace/private/runs/server-distro/wsta91-netfilter-inventory-20260704T132000Z/`
- Decision: `wsta91-netfilter-inventory-readonly-live-pass`

## Summary

WSTA91 ran a bounded live inventory to choose the packet-filter direction for
the D-public hardening track.  It did not run `iptables`, `ip6tables`, or `nft`
as rule-management commands; it only observed kernel config, procfs surfaces,
and userspace tool presence.

Result:

```text
backend_recommendation=not-proven
default_drop_ready_for_source=false
```

The kernel side is promising for legacy iptables, but the current native
userspace does not expose a rule-management tool:

```text
CONFIG_NETFILTER=y
CONFIG_NF_CONNTRACK=y
CONFIG_IP_NF_IPTABLES=y
CONFIG_IP6_NF_IPTABLES=y
CONFIG_NETFILTER_XTABLES=y
CONFIG_NF_TABLES=n

iptables=false
ip6tables=false
nft=false
lsmod=true
modprobe=true
```

Observed procfs surfaces:

```text
/proc/net/ip_tables_names      present
/proc/net/ip6_tables_names     present
/proc/net/nf_conntrack         present
/proc/sys/net/netfilter        present
```

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta91_netfilter_inventory.py`
- `tests/test_server_distro_wsta91_netfilter_inventory.py`

The runner:

- requires `--live-readonly-netfilter-inventory`;
- preflights and postflights with `selftest fail=0`;
- writes private raw command output under `workspace/private/`;
- writes a redacted public summary with booleans and config keys only;
- classifies `nftables`, `legacy-iptables`, or `not-proven`;
- keeps packet-filter mutation out of scope.

## Interpretation

WSTA91 does not unblock default-drop enforcement yet.  The in-kernel legacy
iptables path appears configured, but there is no observed native `iptables` or
`ip6tables` command and nftables is disabled by config.  The next packet-filter
unit should therefore stage or select a rule-management backend before any
always-on public posture claims packet filtering.

Practical next direction:

```text
WSTA92 source: stage/prove a legacy iptables userspace backend for the D-public rootfs or native boundary
WSTA93 live: bounded loopback-only default-drop prototype after the backend exists
```

## Safety

- No boot image was built or flashed.
- No native reboot ran.
- No Wi-Fi association, DHCP, public tunnel, public smoke, userdata action, or
  switch-root ran.
- No `iptables`, `ip6tables`, or `nft` mutation command ran.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private raw artifacts remain under `workspace/private/` only.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta91_netfilter_inventory -v
```

Result: `Ran 6 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta89_hardening_readiness_audit \
  tests.test_server_distro_wsta90_service_hardening_manifest \
  tests.test_server_distro_wsta91_netfilter_inventory -v
```

Result: `Ran 20 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta91_netfilter_inventory.py \
  tests/test_server_distro_wsta91_netfilter_inventory.py
```

Result: pass.

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
```

Result: resident `v3397-wsta-execute-gate-screen`, health OK, `selftest fail=0`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta91_netfilter_inventory.py \
  --live-readonly-netfilter-inventory \
  --run-dir workspace/private/runs/server-distro/wsta91-netfilter-inventory-20260704T132000Z \
  --print-full-json
```

Result: `wsta91-netfilter-inventory-readonly-live-pass`.

```text
git diff --check
```

Result: pass.

## Next

Do not implement packet-filter policy yet.  First stage or select the concrete
legacy iptables userspace backend for the D-public environment, then prototype
default-drop in a bounded loopback-only run.
