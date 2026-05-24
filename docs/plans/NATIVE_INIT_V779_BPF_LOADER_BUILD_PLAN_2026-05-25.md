# Native Init V779 BPF Loader Build Plan

## Goal

Build, but do not deploy or run, a minimal static aarch64 helper for the
`msm_pil_event:pil_notif` BPF tracepoint attach proof path selected by V778.

## Rules

- Host build only.
- No device command, deploy, BPF attach, ftrace control write, Wi-Fi action,
  scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or
  partition write.
- Helper must default to `--check-only`; attach requires explicit
  `--allow-attach`.
- Helper must target only `msm_pil_event:pil_notif` unless a later plan changes
  the target.

## Success Criteria

- `aarch64-linux-gnu-gcc -static` builds the helper.
- `readelf -l` shows no `INTERP` program header.
- The binary contains version marker `a90_bpf_trace_probe v779`.
- The binary contains both `--check-only` and `--allow-attach` gates.
- Evidence is private under `tmp/wifi/v779-bpf-loader-build/`.
