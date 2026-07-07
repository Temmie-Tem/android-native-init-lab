# S22+ Sec Debug MID Sysrq Panic Gate Source (2026-07-08)

## Verdict

HOST-ONLY GATE SOURCE PASS. No flash, reboot, Odin transfer, partition write,
sysfs/procfs write, sysrq trigger, or Android device action was performed.

This is the zero-flash validation gate for the current frontier: verify whether
Samsung `sec_debug` with operator-set `debug_level=MID` can retain a real kernel
panic log before spending another native-init boot candidate.

## Added

Helper:

`workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py`

Inert policy draft:

`docs/operations/S22PLUS_SEC_DEBUG_MID_SYSRQ_PANIC_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`

The draft is not live authorization while it remains in `docs/operations/`.
The helper's default path fails closed before Android/device access until the
draft is explicitly promoted into `AGENTS.md`.

## Intended Future Flow

Once separately authorized:

1. operator sets Samsung SysDump DEBUG LEVEL to MID if available;
2. promote the SHA/marker-pinned AGENTS exception;
3. run the default helper dry-run to collect read-only sec_debug state;
4. run one attended `--live-panic` with the ack token and the
   `DEBUG_LEVEL_MID_SET_BY_OPERATOR` confirmation token;
5. operator recovers the phone;
6. run `--collect-after-recovery` to inspect `/sys/fs/pstore`,
   `/proc/last_kmsg`, pmsg-derived retained state, reset reason, and sec_debug
   state.

The live panic mode writes marker `S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL` to
`/dev/kmsg` and `/dev/pmsg0` if present, enables `/proc/sys/kernel/sysrq`, and
writes `c` to `/proc/sysrq-trigger`. It never flashes Odin packages and never
writes a block partition.

## Safety Gates

The active policy must contain:

```text
S22+ sec_debug debug_level MID sysrq-panic zero-flash
workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py
SM-S906N/g0q/S906NKSS7FYG8
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL
S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE
DEBUG_LEVEL_MID_SET_BY_OPERATOR
debug_level=MID
operator-set SysDump DEBUG LEVEL MID
sysrq-trigger-c
intentional kernel crash
collect /proc/last_kmsg
no Odin flash
no partition write
manual recovery
```

The dry-run and live modes also require the current `boot` partition to match
the known-booting Magisk baseline:

```text
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Host Validation

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
```

Results:

- `py_compile`: pass.
- `--offline-check`: pass, `rc=0`; inert policy draft marker coverage verified,
  no device action.
- `--print-plan`: pass, `rc=0`; operator plan printed, no device action.
- default execution: fail-closed, `rc=1`, before Android/root or device access
  because `AGENTS.md` lacks the sec_debug MID sysrq policy markers.

The missing-marker list included the helper path, target tuple, marker,
`S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE`,
`DEBUG_LEVEL_MID_SET_BY_OPERATOR`, `debug_level=MID`,
`sysrq-trigger-c`, `intentional kernel crash`, `collect /proc/last_kmsg`,
`no Odin flash`, `no partition write`, and `manual recovery`.

## Current Gate State

Live panic is not authorized by this report. The next live-capable sequence
requires:

1. operator confirms whether Samsung SysDump can set DEBUG LEVEL to MID;
2. explicit operator approval to promote the inert exception into `AGENTS.md`;
3. default dry-run pass after active policy;
4. attended `--live-panic` with:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --live-panic \
  --ack S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE \
  --confirm-debug-level-mid DEBUG_LEVEL_MID_SET_BY_OPERATOR
```

After recovery:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --collect-after-recovery
```

If this retained evidence works, use Samsung `sec_debug` for the native-init/QMP
fault capture. If it fails, decide whether the already prepared M22+DTBO gate is
still worth one attended mainline-ramoops negative control before moving to
EUD/UART.
