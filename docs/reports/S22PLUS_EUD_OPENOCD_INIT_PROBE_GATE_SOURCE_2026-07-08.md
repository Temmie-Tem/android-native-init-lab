# S22+ EUD OpenOCD Init Probe Gate Source (2026-07-08)

## Verdict

Host-only source for the next EUD/OpenOCD live gate is ready, but the live policy
is intentionally inert. This unit does not run OpenOCD init and does not touch
the device.

The current preflight result remains `waiting_for_eud_enumeration_or_hardware`:
the toolchain and SM8450 cfg are present, but the host still has no current EUD
USB endpoint.

## Added

- `workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py`
- `tests/test_s22plus_eud_openocd_init_probe_gate.py`
- `docs/operations/S22PLUS_EUD_OPENOCD_INIT_PROBE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`

## Safety Shape

Default and offline-check modes are host-only:

- SM8450 cfg audit
- EUD OpenOCD host audit
- policy marker coverage check
- no OpenOCD init
- no ADB/sysfs/device write
- no flash/reboot/partition action

Live mode is fail-closed unless all are true:

- exact ack token `S22PLUS-EUD-OPENOCD-INIT-PROBE-LIVE-GATE`
- active `AGENTS.md` exception contains the required markers
- host audit reports `host_openocd_eud_ready_to_probe`
- SM8450 cfg audit passes

The live action, once separately authorized, is only a bounded OpenOCD
`init; targets; shutdown` probe. The draft explicitly calls out the possible
debug attach/halt side effect and forbids flash, reboot, partition write, EUD
sysfs write, memory write commands, and reset commands.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_eud_openocd_host_audit.py \
  tests/test_s22plus_sm8450_openocd_target_cfg_audit.py \
  tests/test_s22plus_eud_openocd_init_probe_gate.py

Ran 16 tests: OK

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py \
  --offline-check

S22+ EUD OpenOCD init probe gate: waiting_for_eud_enumeration_or_hardware; cfg=sm8450_cfg_draft_ready_romtable_dbgbase host=waiting_for_eud_enumeration_or_hardware host_eud_usb=0; draft_missing=0 active_missing=...

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py \
  --live --ack S22PLUS-EUD-OPENOCD-INIT-PROBE-LIVE-GATE

AGENTS.md missing S22+ EUD OpenOCD live authorization markers: [...]
```

## Next Gate

Do not run live OpenOCD now. The remaining external prerequisite is a real,
current host EUD USB/SWD endpoint. If that appears, promote the draft exception
into `AGENTS.md`, run `--offline-check`, then run the exact ack-gated live probe
once.
