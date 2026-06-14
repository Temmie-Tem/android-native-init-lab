# NATIVE_INIT_V2346_AUDIO_TINYALSA_INVENTORY_GATE_2026-06-14

## Summary

- Run ID: `V2346`
- Type: host-only source/test update; no flash, no bridge command, no device action.
- Scope: prepare the future post-materialization **read-only tinyalsa inventory** gate.
- Decision: `v2346-audio-tinyalsa-inventory-gate-dry-run`

V2346 adds `native_audio_tinyalsa_inventory_gate_v2346.py`, a host-only planner that
verifies the private V2345 tinyalsa tool bundle and emits the bounded command plan for a
future read-only mixer/PCM inventory run after `/dev/snd` materialization succeeds.

This does **not** replace the pending AUD-3 materialization live gate. The current live
frontier remains the exact-gated V2335/V2344 runner:

`AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321`

## Why This Unit

The previous host-only V2345 step staged static AArch64 `tinymix`, `tinypcminfo`, and
`tinyplay` under `workspace/private`. Before any future ALSA/tinyalsa live work, the next
safe host-only step is to define the **read-only inventory boundary**:

- allowed: `tinymix -D 0` and `tinymix -D 0 --all-values` for mixer inventory;
- allowed: `tinypcminfo -D 0 -d <n>` for PCM capability query;
- forbidden: `tinyplay`, PCM playback/write, mixer set operands, audio HAL, adsprpc invoke/ioctl.

This avoids improvising tinyalsa commands during a later live gate.

## Source Grounding

The V2345 pinned tinyalsa source is AOSP `platform/external/tinyalsa` commit
`e14bf1479ebaaabf60bc4472ce8d304f72f03c32`.

Relevant source behavior, verified from the private pinned source copy:

- `tinymix` with no control/value operands opens the mixer and lists controls.
- `tinymix --all-values` expands enum/range reporting without setting controls.
- `tinypcminfo -D <card> -d <device>` calls `pcm_params_get()` for `PCM_OUT` and `PCM_IN`
  capability queries; it does not play or write PCM data.
- `tinyplay` remains staged by V2345 but is explicitly excluded by V2346.

## Implemented Artifact

- Script: `workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_gate_v2346.py`
- Test: `tests/test_native_audio_tinyalsa_inventory_gate_v2346.py`

The script is deliberately `--dry-run` only. It has no `--run-live` mode and exits with an
argument error unless `--dry-run` is supplied.

## Dry-Run Result

`python3 workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_gate_v2346.py --dry-run`

Key dry-run fields:

```json
{
  "decision": "v2346-audio-tinyalsa-inventory-gate-dry-run",
  "ok": true,
  "host_only": true,
  "device_action": "none",
  "commands": [
    "tinymix-list-card0",
    "tinymix-list-card0-all-values",
    "tinypcminfo-card0-device0"
  ],
  "safety_ok": true,
  "excluded_tools": ["tinyplay"]
}
```

Verified V2345 tool hashes:

| Tool | SHA256 |
| --- | --- |
| `tinymix` | `747b19a5a263a3f2f02223ba2bad2aa0e34f9e8a3948093d612d57e3ada15411` |
| `tinypcminfo` | `f1c370e6088cf6acca129c1c1f4a77a1d11d51526c3ba25721991505cbf4929e` |

`tinyplay` is present in the V2345 private manifest but is not referenced by the V2346 plan.

## Future Live Gate

Future tinyalsa inventory is a **separate** live gate because it will open ALSA devices and
perform read-only ALSA ioctls. Required future exact phrase:

`AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321`

Preconditions for that future gate:

1. V2334 `/dev/snd` materialization has passed first.
2. `selftest fail=0` and serial bridge/control channel are healthy.
3. V2321 rollback image and deeper fallbacks are present.
4. Only the V2346 allowed inventory commands are executed.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_gate_v2346.py tests/test_native_audio_tinyalsa_inventory_gate_v2346.py`
- `python3 -m unittest discover -s tests -p 'test_native_audio_tinyalsa_inventory_gate_v2346.py'` → 5 tests pass.
- `python3 workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_gate_v2346.py --dry-run` → `ok=true`.

- `python3 -m unittest discover -s tests -p 'test_*.py'` → 1014 tests pass.
- `git diff --check` → pass.

## Safety Boundary

No device action occurred. No boot image was built or flashed. No ADSP activation, `/dev/snd`
materialization, ALSA open/ioctl, mixer set, tinyalsa run, PCM playback/write, audio HAL, or
adsprpc path was attempted.
