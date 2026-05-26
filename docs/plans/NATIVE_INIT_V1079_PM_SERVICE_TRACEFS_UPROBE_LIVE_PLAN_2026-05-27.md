# Native Init V1079 PM Service Tracefs Uprobe Live Plan

## Goal

Bypass the V1078 BPF/perf attach blocker by using tracefs dynamic uprobes
directly: register `pm-service` uprobe events, enable them through tracefs, run
the existing PM trigger observer, collect trace lines and counts, then disable
and remove all dynamic events.

## Background

V1078 proved that native v724 can mount the read-only vendor surface and
register dynamic uprobes for `/mnt/vendor/bin/pm-service`, but the V1076 BPF
counter helper failed at the perf attach boundary with `EINVAL`. The next
minimal diagnostic step is to avoid BPF entirely while keeping the same PM
observer safety contract.

## Gate

- Verify V1078 exists and ended at the BPF/attach boundary.
- Mount tracefs only for the bounded observation window.
- Create a temporary `/dev/block/sda29` node if native devtmpfs omitted it, then
  mount `sda29` read-only with `noload`.
- Register all dynamic uprobe events before enabling any event.
- Use append writes to `uprobe_events`; truncating writes remove previous
  dynamic events.
- Redirect the verbose PM observer child output to a private device file and
  emit only contract summary lines plus tracefs counts over TCP.
- Cleanup temporary uprobe events, tracefs, vendor mount, SELinuxfs, child
  scripts, child output, and synthetic block node.

## Forbidden

- No BPF attach.
- No Wi-Fi HAL start, scan/connect/link-up, credentials, DHCP, route changes, or
  external ping.
- No `mdm_helper`, CNSS daemon, `/dev/esoc*` open, `wlan.ko` load, boot image
  write, partition write, flash, or reboot.

## Success Criteria

- Dynamic uprobe registration, enable, disable, and cleanup all succeed.
- The PM observer child reaches its contract summary without output truncating
  the collector result.
- At least one `pm-service` tracefs uprobe event fires.
- Postflight has no forbidden actors, no Wi-Fi link, no persistent vendor or
  tracefs mount, and native selftest remains `fail=0`.

## Expected Decision Use

If V1079 captures entry/main or PLT hits, the next cycle can select more precise
`pm-service` offsets or actor-specific observation around the `per_mgr` exit-255
path without relying on BPF.
