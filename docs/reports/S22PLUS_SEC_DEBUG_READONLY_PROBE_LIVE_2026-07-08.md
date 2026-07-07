# S22+ Sec Debug Read-Only Probe Live Result (2026-07-08)

## Verdict

READ-ONLY LIVE PROBE PASS. No flash, reboot, partition write, sysrq trigger,
procfs/sysfs write, Odin transfer, or AGENTS policy promotion was performed.

The probe confirms the sec_debug control surface is visible from rooted Android
and that the current retail state is still LOW-class, not MID.

## Helper

`workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py`

New mode:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --read-only-probe
```

This mode deliberately does not require the panic AGENTS exception because it
only performs rooted ADB reads and host observation. The panic/default live
paths remain policy-gated.

## Live Read-Only Result

Run directory, private and not committed:

`workspace/private/runs/s22plus_sec_debug_mid_sysrq_20260707T202456Z`

Public metadata:

```text
mode                  read-only-probe
writes_performed      false
reboots_performed     false
flashes_performed     false
sysrq_triggered       false
current boot hash     matched known-booting Magisk baseline
/sys/module/sec_debug/parameters/debug_level     present
debug_level decimal   20300
debug_level hex       0x4f4c
debug_level ascii_le  LO
debug_level ascii_be  OL
likely_low_code       true
/sys/module/sec_debug/parameters/enable          present, value 0
/sys/module/sec_debug/parameters/enable_user     present, value 0
/sys/module/sec_debug/parameters/force_upload    present, value 0
/dev/pmsg0            present
/sys/fs/pstore        present, empty listing
/proc/reset_reason    NPON
/proc/store_lastkmsg  0
/proc/sys/kernel/sysrq 0
```

SysDump route metadata, from the same read-only helper path:

```text
package                         com.sec.android.app.servicemodeapp
sysdump_activity_found           true  (com.sec.android.app.servicemodeapp/.SysDump)
cp_debug_level_activity_found    true  (com.sec.android.app.servicemodeapp/.CPDebugLevel)
secret_code_receiver_found       true  (.ServiceModeAppBroadcastReceiver)
secret_code_9900_found           true  (android_secret_code authority "9900")
secret_code_action_found         true  (com.samsung.android.action.SECRET_CODE)
development_preference_category  true
```

The retained `/proc/last_kmsg` grep still showed bootloader/download/reset style
history and Samsung/QCOM ramdump/sec_debug module activity, not a new kernel
panic marker. Raw retained logs remain under `workspace/private/`.

## Interpretation

The host finding that retail `debug_level` is LOW is now live-confirmed:
`20300 == 0x4f4c`, little-endian ASCII `LO`. This explains why previous
captures retained only bootloader/LPM/download context even though Samsung
sec_debug-related modules and `/dev/pmsg0` are present.

The next useful operator action is to set Samsung SysDump DEBUG LEVEL to MID if
the menu exposes it, then rerun `--read-only-probe`. Do not trigger sysrq panic
while the probe still decodes as LOW. Once the decoded value moves away from
LOW and the operator confirms MID, the already prepared `--live-panic` gate can
be consumed under the active policy.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --read-only-probe
```

Results:

- `py_compile`: pass.
- `--offline-check`: pass, `rc=0`, no device action.
- default execution: fail-closed, `rc=1`, before Android/device access because
  `AGENTS.md` lacks the panic policy markers.
- `--read-only-probe`: pass, `rc=0`, read-only rooted Android collection only.

## Next

1. Operator opens SysDump through `*#9900#` or the identified
   `com.sec.android.app.servicemodeapp/.SysDump` screen and sets DEBUG LEVEL
   MID if available.
2. Rerun `--read-only-probe` and require the decoded value to no longer be LOW.
3. Only then consider promoting the inert AGENTS exception for the intentional
   sysrq panic gate.
