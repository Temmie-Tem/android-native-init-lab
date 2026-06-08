# Native Init Transport Commonization Design

Date: `2026-06-09`

## Goal

Make active live runners share the same timing, bridge recovery, transport
selection, and manifest contracts instead of carrying local one-off logic.

This is a host-runner refactor only. It does not change the promoted V2178 boot
image, Wi-Fi behavior, bridge wire protocol, or safety scope.

## Local Findings

- `workspace/public/src/scripts/revalidation/a90_transport.py` is already the
  right import target for bridge lifecycle, serial command execution, host NCM
  detection, optional NCM repair, and selector manifests.
- `native_wifi_dhcp_ping_handoff_v2176.py` has a local `phase_timer()` context
  manager. That should move into `a90_transport.py` instead of being copied into
  each runner.
- `a90ctl.py` already enforces the serial transaction lock and safe-command
  retry policy for low-level cmdv1 exchanges.
- `a90_transport.run_serial_command_recovered()` currently handles busy/menu
  noise by sending `hide` and retrying once, but V2179 showed a second
  recoverable class: malformed cmdv1 output caused by serial `AT` noise. That
  should be explicit in shared evidence, not hidden in per-run scripts.
- `docs/operations/NATIVE_INIT_BOOT_TRANSPORT_CONTRACT.md` already says active
  runners must call `a90_transport.select_transport()`, save selector output,
  use shared serial helpers, record phase timers, and avoid unsafe retries.

## External References

- Python `time.monotonic()` / `time.perf_counter()`:
  https://docs.python.org/3/library/time.html
  - Use a monotonic clock for elapsed phase timing because only differences are
    meaningful and the clock cannot go backwards.
- Python `subprocess.run(timeout=...)`:
  https://docs.python.org/3/library/subprocess.html#subprocess.run
  - Keep host commands bounded and preserve timeout evidence in step records.
- Python `json.dump` / `json.dumps(sort_keys=True, indent=...)`:
  https://docs.python.org/3/library/json.html
  - Keep manifests deterministic and easy to diff.
- Python `socket.create_connection()` / `socket.settimeout()`:
  https://docs.python.org/3/library/socket.html
  - Keep bridge TCP exchanges bounded with connection/read timeouts.
- pySerial timeout/read framing reference:
  https://pyserial.readthedocs.io/en/latest/pyserial_api.html
  - Useful background for serial timeout/framing behavior, but the current
    runner path should not add a new pySerial dependency; it should keep using
    the existing localhost TCP bridge plus `a90ctl.py`.

## Design

### 1. Shared Phase Timer

Add a small helper to `a90_transport.py`:

```python
with transport.phase(manifest, "flash"):
    ...
```

Contract:

```json
{
  "phase_timer_contract": 1,
  "phase_timers": [
    {
      "name": "flash",
      "started": "2026-06-09T00:00:00+00:00",
      "ended": "2026-06-09T00:02:00+00:00",
      "elapsed_sec": 120.123,
      "ok": true
    }
  ]
}
```

Rules:

- Use `time.monotonic()` or `time.monotonic_ns()` for elapsed time.
- Use UTC ISO timestamps only for human anchoring.
- Record the phase even when the wrapped block raises.
- Do not include command output or secrets in phase records.
- Standard phase names for live boot/Wi-Fi runners:
  - `preflight`;
  - `flash`;
  - `boot_wait`;
  - `helper_stage`;
  - `connect_window`;
  - `artifact_upload`;
  - `rollback`;
  - `selftest`.

### 2. Shared Serial Recovery Evidence

Extend `run_serial_command_recovered()` so the returned result includes a
machine-readable recovery block:

```json
{
  "serial_recovery_contract": 1,
  "serial_recovery": {
    "attempts": 2,
    "recovered": true,
    "reason": "protocol-noise",
    "actions": ["bridge-restart", "retry-command"],
    "unsafe_retry": false
  }
}
```

Recoverable reasons:

- `busy`: bridge reports another active client or native menu busy state.
- `protocol-noise`: `A90P1 END marker not found`, command mismatch, or known
  serial garbage such as `cmdvATATAT`.
- `serial-missing`: bridge reports serial device missing before any device
  command can be trusted.

Actions:

- For `busy`, send `hide`; retry once only if the original command is safe or
  `retry_unsafe=True` was explicitly scoped.
- For `protocol-noise`, restart the managed bridge once, then retry once.
- For `serial-missing`, do not hide; run bridge ensure/status, then retry only
  if the original command is safe.

Safety:

- Never automatically replay unsafe commands after a possibly partial device
  write.
- Use `a90ctl.command_allows_retry()` as the default allow-list.
- Keep `retry_unsafe=False` as the default.
- If a runner explicitly sets `retry_unsafe=True`, the manifest must show it.

### 3. Shared Step Records

Keep `write_step()` as the single path for step artifacts and add these fields
when available:

```json
{
  "elapsed_sec": 1.234,
  "recovery": {
    "reason": "protocol-noise",
    "recovered": true
  }
}
```

Rules:

- stdout/stderr still go to private run files.
- Step metadata may be public only after redaction review.
- Timeouts must be explicit: `timeout=true`, `rc=null`, `ok=false`.

### 4. Runner Migration Order

1. Add shared helpers to `a90_transport.py`.
2. Replace V2176 local `phase_timer()` with `transport.phase()`.
3. Migrate `native_wifi_connect_carrier_handoff_v2174.py` phase boundaries.
4. Migrate `native_wifi_hold_reconnect_handoff_v2177.py`.
5. Migrate `a90_v725_fasttransport_baseline_validation.py`.
6. Refresh `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-08.md` after
   active runner changes.

### 5. Validation Plan

Host-only:

- `python3 -m py_compile` for changed runner modules.
- Unit-style dry check of phase context with a synthetic manifest.
- Verify `git diff --check`.
- Verify no added-line secret leakage.

Live, after implementation:

- One bridge status/version/selftest runner path using shared serial recovery.
- One Wi-Fi runner with phase timers in manifest.
- Confirm manifest contains:
  - `phase_timer_contract=1`;
  - standard phase names;
  - `transport_selection.selector_contract=1`;
  - serial recovery block only when recovery fires.

## Implementation Status

Implemented in the follow-up code change:

- `workspace/public/src/scripts/revalidation/a90_transport.py`
  - `phase()` shared context manager;
  - `PHASE_TIMER_CONTRACT=1`;
  - `SERIAL_RECOVERY_CONTRACT=1`;
  - elapsed time in host/serial step records;
  - structured `serial_recovery` evidence from
    `run_serial_command_recovered()`;
  - safe-command protocol-noise recovery using managed bridge restart plus
    one retry.
- Migrated active runners:
  - `native_wifi_connect_carrier_handoff_v2174.py`;
  - `native_wifi_dhcp_ping_handoff_v2176.py`;
  - `native_wifi_hold_reconnect_handoff_v2177.py`;
  - `a90_v725_fasttransport_baseline_validation.py`.

Validation status:

- Host-only py_compile and synthetic helper checks passed before implementation
  commit.
- V2180 live validation confirmed the new manifest fields on:
  - transport-only runner `a90_ncm_transport_smoke.py`;
  - current-baseline Wi-Fi runner
    `native_wifi_v2178_autoconnect_phase_validation.py`.
- Evidence report:
  `docs/reports/NATIVE_INIT_V2180_TRANSPORT_COMMONIZATION_LIVE_VALIDATION_2026-06-09.md`.
- Serial `AT` noise recovery is implemented but only observable when the
  transient condition naturally fires.

## Non-Goals

- No boot image change.
- No new device-side protocol.
- No new serial dependency.
- No Wi-Fi scan/connect/DHCP/ping in this design step.
- No automatic replay of unsafe commands.
