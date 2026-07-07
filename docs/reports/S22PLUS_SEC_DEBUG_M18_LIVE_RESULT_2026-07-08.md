# S22+ Sec Debug MID M18 Live Result (2026-07-08)

## Verdict

LIVE GATE CONSUMED. DEVICE CLEAN RESTORED. M18 STILL DID NOT PRODUCE RETAINED
NATIVE-INIT FAULT EVIDENCE.

The boot-only M18 candidate was flashed once under the sec_debug/MID capture
gate. The device did not expose ACM or ADB during the M18 observation window.
It later appeared as an Odin/Download endpoint, and the pinned Magisk boot
rollback AP flashed successfully. Final Android/root returned, current boot hash
matches the known Magisk baseline, and sec_debug DEBUG LEVEL remains MID.

## Live Run

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py \
  --live \
  --ack S22PLUS-SECDEBUG-M18-CAPTURE-LIVE-GATE \
  --confirm-debug-level-mid DEBUG_LEVEL_MID_SET_BY_OPERATOR
```

Private run, not committed:

```text
workspace/private/runs/s22plus_sec_debug_m18_capture_20260707T213507Z
```

Result:

```text
M18 candidate Odin flash: rc=0
M18 observation: no ACM, no ADB
M18 Odin/Download endpoint: observed at iteration 57
Magisk boot rollback Odin flash: rc=0
live helper process rc: 1 due helper NameError after rollback flash
```

The `rc=1` was a host helper bug after rollback had already flashed, not an Odin
or partition rollback failure. The bug was fixed by importing the missing
Android-wait helper and adding an explicit `--collect-after-rollback` mode.

The operator observed bootloop behavior and manually entered Odin/Download mode
during the recovery window. Host-side ADB later showed Android had returned.

## Post-Rollback Collection

Final collection command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py \
  --collect-after-rollback
```

Private run, not committed:

```text
workspace/private/runs/s22plus_sec_debug_m18_capture_20260707T213930Z
```

Result:

```text
Android/root stability: OK
current boot hash: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
sec_debug DEBUG LEVEL: 18765 / 0x494d / MI
/sys/fs/pstore files: []
/proc/last_kmsg bytes: 2097136
M18 marker: not found
S22_NATIVE_INIT/M18/S22M18FULL: not found
Kernel panic/Oops/SError/native fault signal: not found
native_signal_found: 0
```

The retained grep lines are dominated by the host-commanded Android
`reboot,download` path, ABL/XBL Download records, normal watchdog/regulator/dwc3
noise, and the Odin target reset. This is not a useful M18 fault localization.

## Final Health

Final active dry-run before retiring the policy:

```text
workspace/private/runs/s22plus_sec_debug_m18_capture_20260707T214000Z
```

Result:

```text
dry-run: pass
Android/root stability: OK
boot hash: known Magisk baseline
sec_debug DEBUG LEVEL: MID
```

After recording the result, `AGENTS.md` was changed to mark the one-shot
sec_debug M18 exception consumed/retired. A default helper run now fails closed
at the AGENTS marker gate before Android/device access.

## Interpretation

M18 remains a no-hit for retained native evidence:

- no ACM
- no ADB during M18
- bootloop/Odin return observed
- rollback successful
- no M18 marker or kernel panic retained in `/proc/last_kmsg`

Do not repeat the same M18 boot candidate under this gate. The remaining
native-init path needs a stronger live progress channel or a materially
different candidate/instrumentation design; the Samsung sec_debug retained
channel is proven for real panics, but this M18 failure did not leave a retained
kernel panic.
