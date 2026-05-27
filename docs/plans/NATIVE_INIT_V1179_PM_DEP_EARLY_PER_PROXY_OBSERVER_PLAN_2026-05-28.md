# Native Init V1179 PM Dep Early Per-Proxy Observer Plan

Date: `2026-05-28`

## Goal

Capture when the PM state-0 dependency object (at `peripheral+0x40`) transitions
from `state=0` to `state=1` by arming uprobes from boot before PM actor startup,
and test whether starting `per_proxy` within ~2.16s of `per_proxy_helper` prevents
the dep from reaching `state=1` before the parent peripheral's `state-0` is
processed.

V1178 proved: native starts `per_proxy` too late (after `mdm_helper` esoc-0 fd),
by which point the dep is already `state=1`.  Android starts `per_proxy` 2.159s
after `per_proxy_helper`.

## Key Questions

1. When does the dep (address `peripheral+0x40`, dynamic per boot) go to `state=1`?
2. Is this triggered by per_proxy_helper's own ack sequence, or by per_proxy connecting?
3. Does an early per_proxy (within ~2.16s of per_proxy_helper) keep the dep in
   `state<1` when the parent peripheral's `state-0` arrives?

## Helper Change (v218)

Added `--pm-observer-per-proxy-pph-delta-ms N` flag to
`a90_android_execns_probe`.  When set, after per_proxy_helper is spawned, the
helper waits until `N ms` have elapsed from that spawn time before starting
per_proxy, instead of the default 1s post-start probe.  This replicates Android's
~2159ms per_proxy_helper → per_proxy delta.

SHA256: `12c98f2563a5fbea3e5cfdd5a1874b16e41e24b5ae47b975ccd02ffcef2a4d31`

## Uprobe Spec

Same as V1177, but the capture window starts from BOOT (not at t=993s):
- `pm_ack_state_set_call` at offset `8d14` fires for ALL peripherals including dep
- `pm_ack_state2_dependency_ptr` at offset `88e4` identifies parent peripheral per boot
- `pm_dep_state0_dependency_present` at offset `da74` identifies dep address per boot
- `pm_dep_state0_dependency_state_first/second` at offsets `da94/dab8` check dep state

Key addresses are dynamic per boot.  The script identifies parent from first
`pm_ack_state2_dependency_ptr` event, computes dep = parent + 0x40, and finds
when `pm_ack_state_set_call` fires with `peripheral=dep state=1`.

## Mode

`wifi-companion-post-pm-mdm-helper-esoc-observer` with:
- `--allow-post-pm-mdm-helper-esoc-observer`
- `--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd` REMOVED
- `--pm-observer-per-proxy-pph-delta-ms 2159`
- `--pm-observer-start-cnss-before-per-proxy` REMOVED (per_proxy runs in-line)
- `--allow-post-pm-mdm-helper-lower-trace` for CNSS/lower layer still

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- No `esoc0` raw open, no `ESOC_NOTIFY`, no `ESOC_BOOT_DONE`
- No boot image write, no partition write, no flash
- Cleanup reboot required (subsys_esoc0 open blocks in D-state)

## Next Gate

V1179 live result:
- If dep stays `state<1` when parent `state-0` arrives → early per_proxy is the fix
  → V1180 repeat with flag-set confirmed → V1181 repair
- If dep goes `state=1` before parent `state-0` regardless of per_proxy timing
  → deeper investigation of dep initialization path
