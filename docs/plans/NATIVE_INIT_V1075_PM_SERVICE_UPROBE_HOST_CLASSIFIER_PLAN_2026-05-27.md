# Native Init V1075 PM Service Uprobe Host Classifier Plan

## Goal

Classify whether `pm-service` can be observed with lower-overhead uprobes/BPF
instead of continuous ptrace, and select safe callsite offsets for the next live
PM blocker gate.

## Background

V1074 proved the PM observer can preserve final evidence while tracing selected
`per_mgr` syscalls, but the only decisive record was
`faccessat(/dev/urandom) = 0`.  Under ptrace-lite, `pm-service` did not
reproduce the natural exit-255 path before bounded cleanup.  The next gate needs
less intrusive userspace instrumentation.

The current PM chain remains:

```text
mss ONLINE -> mdm3 ONLINE missing -> per_mgr blocked
-> WLAN-PD missing -> WLFW service 69 missing -> wlan0 missing
```

## Gate

- Add a host-only classifier:
  `scripts/revalidation/native_wifi_pm_service_uprobe_host_classifier_v1075.py`.
- Analyze the extracted `/vendor/bin/pm-service` binary with `file`, `readelf`,
  `objdump`, and `strings`.
- Determine aligned ARM64 offsets for ELF entry, the libc-init main candidate,
  and important PLT callsites.
- Validate that the current stock kernel has enough support for uprobe/BPF event
  instrumentation while kernel kprobes remain unavailable.
- Emit private evidence under
  `tmp/wifi/v1075-pm-service-uprobe-host-classifier/`.

## Inputs

- `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`.
- `tmp/kernel-config/v202-kernel-config.json`.
- Raw kernel config text captures from V770/V281/V282 to recover options omitted
  or truncated in the JSON summary.
- V1074 report and live manifest for the ptrace limitation.

## Forbidden

- No device command execution.
- No live `pm-service`, PM, service-manager, CNSS, Wi-Fi HAL, or `mdm_helper`
  start.
- No `/dev/esoc*` or subsystem trigger.
- No scan/connect/DHCP/route/external ping.
- No tracefs write in this host-only step.
- No boot image or partition write.

## Success Criteria

- `pm-service` binary is present and classified as a stripped AArch64 PIE.
- ELF entry and inferred main candidate offsets are 4-byte aligned.
- Critical PLT callsites for log, binder, mdmdetect, QMI CSI, property, pipe,
  open/access/select/write/close are present and aligned.
- Kernel config confirms `CONFIG_UPROBES=y`, `CONFIG_UPROBE_EVENTS=y`,
  `CONFIG_BPF_EVENTS=y`, and `CONFIG_BPF_SYSCALL=y`.
- Kernel config confirms `CONFIG_KPROBES=n`, so userspace uprobes are the proper
  route over unavailable kernel probes.
- The next gate is narrowed to a bounded V1076 uprobe/BPF helper.

## Expected Decision Use

If V1075 passes, implement V1076 as a bounded helper that arms uprobes around
`pm-service` startup and records entry/callsite hits or return classifications
without continuous syscall-stop overhead.  If V1075 fails, repair binary/config
input collection before adding live instrumentation.
