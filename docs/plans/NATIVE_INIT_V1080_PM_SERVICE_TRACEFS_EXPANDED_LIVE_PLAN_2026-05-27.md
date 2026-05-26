# Native Init V1080 PM Service Tracefs Expanded Live Plan

## Goal

Use the V1079 tracefs-only path with the full V1075 PM-service PLT candidate set
to determine which early `pm-service` calls are actually reached before
`per_mgr` exits with `255`.

## Background

V1079 proved tracefs dynamic uprobes work for `pm-service` without BPF and
captured entry/main plus `get_system_info` and Android log calls. The next
minimal step is to add the remaining V1075 candidates in the same bounded
observer window rather than adding new actors or changing Wi-Fi state.

## Gate

- Require V1079 PASS evidence.
- Reuse the same temporary tracefs, read-only vendor, SELinuxfs, and
  `/dev/block/sda29` cleanup pattern.
- Register and enable the expanded event set:
  - entry/main
  - Android log
  - Binder driver/service-manager
  - mdmdetect `get_system_info`
  - QMI server register/event loop
  - property set
  - pipe/access/open/select/write/close
- Keep the PM observer child output redirected to a private device file and emit
  only contract summary plus tracefs lines/counts over TCP.

## Forbidden

- No BPF attach.
- No Wi-Fi HAL start, scan/connect/link-up, credentials, DHCP, route changes, or
  external ping.
- No `mdm_helper`, CNSS daemon, `/dev/esoc*` open, `wlan.ko` load, boot image
  write, partition write, flash, or reboot.

## Success Criteria

- All expanded dynamic uprobe events register, enable, disable, and clean up.
- At least one expanded event fires.
- PM observer contract remains parseable and postflight safe.
- Postflight has no forbidden actors, no Wi-Fi link, no persistent tracefs or
  vendor mount, and native selftest remains `fail=0`.

## Expected Decision Use

If QMI/Binder/open/access remain at zero while pipe/log/close are hit, the next
cycle should shift from broad PLT probing to host-only basic-block/callsite
classification around the early `pm-service` main path.
