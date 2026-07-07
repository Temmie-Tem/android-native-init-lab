# S22+ EUD OpenOCD Init Probe AGENTS Exception Draft (2026-07-08)

This document is inert until copied into `AGENTS.md`. It is a policy draft for
one bounded attended OpenOCD init probe after the host already has a visible EUD
USB/SWD endpoint.

Required live helper:

```text
workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py
```

Live ack token:

```text
S22PLUS-EUD-OPENOCD-INIT-PROBE-LIVE-GATE
```

Pinned host tool/config paths:

```text
workspace/private/tools/linux-msm-openocd-eud/install/bin/openocd
workspace/private/tools/linux-msm-openocd-eud/install/share/openocd/scripts
workspace/public/src/openocd
interface/eud.cfg
target/qualcomm/sm8450_s22plus_romtable.cfg
```

Preconditions:

- The same helper must report `host_openocd_eud_ready_to_probe` before live.
- The public SM8450 cfg audit must pass.
- The host EUD USB/SWD endpoint must be current, not inferred from stale logs.
- The operator must be present because OpenOCD may have a debug attach/halt side
  effect.

Authorized action:

- One bounded OpenOCD init probe only: a bounded OpenOCD init command using
  `interface/eud.cfg` and `target/qualcomm/sm8450_s22plus_romtable.cfg`,
  followed by `targets` and `shutdown`.

Forbidden:

- no flash
- no reboot
- no partition write
- no EUD sysfs write
- no memory write commands
- no reset command
- no native-init boot candidate
- no Magisk module
- no vendor_boot, DTBO, vbmeta, recovery, BL, CP, CSC, super, userdata, EFS,
  RPMB, keymaster, modem, or bootloader action

If the preflight is not `host_openocd_eud_ready_to_probe`, the helper must stop
before OpenOCD init. If OpenOCD init fails or times out, record the redacted log
and stop; do not retry-loop or widen the probe in the same exception.
