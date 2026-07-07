# S22+ Sec Debug MID Sysrq Gate Hardening (2026-07-08)

## Verdict

HOST/READ-ONLY HARDENING PASS.

Codex hardened the zero-flash sec_debug sysrq-panic helper so active-policy
dry-run and `--live-panic` fail closed unless the live precheck confirms:

```text
debug_level is MID-class
sec_debug enable == 1
```

This closes the gap where the helper previously required the operator
confirmation token but did not independently reject a stale LOW kernel state
immediately before the intentional panic trigger.

No flash, reboot, partition write, procfs/sysfs write, sysrq trigger, Odin
transfer, Magisk module install, native-init candidate action, or intentional
crash was performed.

## Code Change

Touched helper:

```text
workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py
```

New behavior:

```text
collect_sec_debug_state()
  records numeric_values for read files with decimal payloads

assert_sec_debug_mid_state()
  accepts current MID-class state:
    debug_level decimal 18765 / 0x494d / ascii_le MI
    enable 1
  rejects LOW:
    debug_level decimal 20300 / 0x4f4c / ascii_le LO
  rejects disabled sec_debug:
    enable 0

default active-policy dry-run
  verifies AGENTS policy, Android/root stability, boot hash,
  collects sec_debug state, then asserts MID before returning dry-run OK

--live-panic
  uses the same pre-trigger assertion before writing marker/sysrq
```

`--read-only-probe` remains policy-free and read-only. It records the new
`numeric_values` metadata but does not require MID because it is also used to
diagnose LOW/stale states.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --print-plan

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --read-only-probe
```

Results:

```text
py_compile: pass
--offline-check: pass, inert draft markers verified, no device action
--print-plan: pass, no device action
default execution: rc=1 before Android/device access because AGENTS policy is inactive
--read-only-probe: pass, no writes/reboots/flashes/sysrq
```

Assertion unit check:

```text
MID state accepted:
  debug_level=18765 / 0x494d / MI
  enable=1

LOW state rejected:
  debug_level=20300 / 0x4f4c / LO

MID-with-enable-0 rejected:
  enable=0
```

Live read-only state after the hardening:

```text
debug_level decimal   18765
debug_level hex       0x494d
debug_level ascii_le  MI
likely_low_code       false
enable                1
enable_user           0
force_upload          5
/proc/sys/kernel/sysrq 0
writes_performed      false
reboots_performed     false
flashes_performed     false
sysrq_triggered       false
```

## Next Gate

The intentional panic gate is still inactive because `AGENTS.md` does not
contain the sec_debug MID sysrq exception. The next live-capable step requires
explicit operator approval to promote the inert exception, then:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --live-panic \
  --ack S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE \
  --confirm-debug-level-mid DEBUG_LEVEL_MID_SET_BY_OPERATOR
```

Manual recovery may be required after `--live-panic`.
