# S22+ EUD Phase-B Live Result (2026-07-08)

## Verdict

LIVE CONSUMED / CONTROLLED NEGATIVE / ENABLE RESTORED.

The attended EUD Phase-B run executed the one-shot reversible enable gate and
returned a safe negative. The EUD sysfs parameter accepted the write, but no
host EUD USB device or new serial/TTY path appeared.

## Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_eud_phase_b_enable_live_gate.py \
  --live --ack <redacted one-shot EUD Phase-B ack>
```

Result:

```text
rc=10
enabled=1
restored_enable_0=1
host_eud_usb_hint=0
host_new_serial_tty_hint=0
```

Private log:

```text
workspace/private/runs/s22plus_eud_phase_b_enable_20260707T220944Z/
```

## Evidence

| Check | Result |
| --- | --- |
| Android preflight | pass, Android boot completed with Magisk root |
| Pinned Magisk boot hash | pass |
| EUD before | `enable=0`, `/dev/ttyEUD0=present`, `eud.ko=loaded`, platform bound |
| Enable write | `requested=1`, `rc=0`, `after_value=1` |
| Disable restore | `requested=0`, `rc=0`, `after_value=0` |
| Host EUD USB hint | false |
| Host new serial/TTY hint | false |
| TTY delta after enable | no added paths |
| TTY delta after disable | no added paths |
| Post-run read-only check | pass, `enable=0`, `ttyEUD0=1` |
| Post-run host USB | Samsung MTP/ADB only; no EUD-looking device |

Device-side EUD state files under the private run directory captured:

```text
runtime_status=unsupported
msm-eud 88e0000.qcom,msm-eud: qcom_scm_io_writel failed with rc:-22
msm-eud 88e0000.qcom,msm-eud: qcom_scm_io_write failed with rc:-22
```

The host TTY baseline remained the existing Android CDC ACM path throughout
before, after-enable, and after-disable snapshots. The classifier therefore
correctly rejected the run as non-positive despite the pre-existing Android
serial path.

## Safety

No flash, reboot, partition write, native-init boot candidate, module insertion,
Magisk module, format-data action, raw `dd`, fastboot, or additional sysfs write
was performed.

The only live write was:

```text
/sys/module/eud/parameters/enable = 1
/sys/module/eud/parameters/enable = 0
```

The second write restored the original disabled state before exit. A later
read-only check confirmed `enable=0`.

## Interpretation

The EUD driver and node exist, and the runtime parameter does execute far
enough to attempt the secure EUD path. On this retail S22+ state, that path does
not cause host-visible EUD enumeration. The `qcom_scm_io_* rc:-22` lines and
`runtime_status=unsupported` make the current no-jig EUD path a controlled
negative, not an instrumentation success.

Do not rerun the same Phase-B enable. Future EUD writes need a new
operator-approved exception and a materially different hypothesis. For the
native-init control-channel problem, the current practical branches remain:

- continue using the Samsung `sec_debug` MID retained panic path for bounded
  crash evidence;
- add host-only source/property analysis for EUD mode-manager requirements;
- use physical UART/EUD hardware if a real live console is required.

## Follow-Up Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_eud_phase_b_enable_live_gate.py \
  --read-only-check
```

Result:

```text
read-only check ok: enable=0 ttyEUD0=1
```

After documenting the result, `AGENTS.md` was changed to mark the EUD Phase-B
exception consumed/retired so default helper execution is fail-closed again.
