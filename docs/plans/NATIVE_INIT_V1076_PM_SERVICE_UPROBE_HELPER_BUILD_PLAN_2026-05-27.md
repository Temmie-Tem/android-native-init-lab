# Native Init V1076 PM Service Uprobe Helper Build Plan

## Goal

Build a static AArch64 helper that can count selected `pm-service` userspace
uprobe hits with BPF counters, without continuous ptrace syscall stops.

## Background

V1075 proved the `pm-service` binary has aligned entry/main/PLT offsets and that
stock v724 has `CONFIG_UPROBES`, `CONFIG_UPROBE_EVENTS`, `CONFIG_BPF_EVENTS`,
and `CONFIG_BPF_SYSCALL`.  Direct kernel kprobes remain unavailable.

The practical implementation route is tracefs dynamic uprobe events plus the
existing BPF tracepoint counter pattern:

```text
tracefs uprobe_events -> events/<group>/<label>/id
-> perf_event_open(PERF_TYPE_TRACEPOINT)
-> BPF array counter per selected callsite
```

## Gate

- Add `stage3/linux_init/helpers/a90_pm_service_uprobe_counter.c`.
- Add build-only wrapper
  `scripts/revalidation/native_wifi_pm_service_uprobe_helper_build_v1076.py`.
- Compile a static stripped AArch64 helper under
  `tmp/wifi/v1076-pm-service-uprobe-helper-build/`.
- Preserve explicit safety gates:
  - default `--check-only`
  - `--allow-tracefs-write`
  - `--allow-attach`
  - `--allow-child-command`
- Reuse V1075 candidate offsets as future event specs.

## Forbidden

- No deploy.
- No live uprobe attach.
- No tracefs write during V1076 build gate.
- No PM actor, service-manager, CNSS, Wi-Fi HAL, `mdm_helper`, or child command
  execution.
- No scan/connect/DHCP/route/external ping.
- No `/dev/esoc*`, `wlan.ko`, boot image, partition write, or reboot.

## Success Criteria

- Static helper builds with `aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra
  -Werror`.
- Stripped binary has no `INTERP` program header.
- Binary contains marker `a90_pm_service_uprobe_counter v1076`.
- Binary contains all explicit safety gate strings.
- Build manifest records `device_commands_executed=false`,
  `tracefs_write_executed=false`, and `bpf_attach_executed=false`.

## Expected Decision Use

If V1076 passes, V1077 should only deploy the reviewed helper and run
check-only/default-no-attach modes.  Actual tracefs uprobe registration and BPF
attach must remain a separate bounded live gate after deploy parity is proven.
