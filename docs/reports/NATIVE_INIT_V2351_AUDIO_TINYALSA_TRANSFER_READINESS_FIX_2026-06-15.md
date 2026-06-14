# NATIVE_INIT V2351 — audio tinyalsa transfer readiness fix

Date: 2026-06-15

## Scope

Host-only follow-up to V2350. No flash, no ADSP command, no `/dev/snd` command, no tinyalsa execution.

Goal: repair the V2349 AUD-3C runner so the next exact-gated read-only tinyalsa inventory attempt does not blindly assume `tcpctl` TCP reachability after V2334 ADSP + `/dev/snd` materialization.

## Problem From V2350

V2350 reached the post-materialization audio state twice, then stopped before tinyalsa inventory:

- attempt 1: install target was outside `tcpctl_host.py`'s allowlist;
- attempt 2: corrected target still timed out at `tcpctl_host.py install` while connecting to `192.168.7.2:2325`.

The audio side was not the blocker: `/dev/snd` materialized to 61 nodes in both attempts. The blocker was transfer/control readiness after the V2334 flash/materialization window.

## Changes

Updated `workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py`:

1. **Staging path moved to a simple allowed root.**
   - Before: `/cache/a90-runtime/bin/v2349-tinyalsa-inventory/{tinymix,tinypcminfo}`.
   - Now: `/cache/bin/{tinymix,tinypcminfo}`.
   - Reason: `/cache/bin` is already a `tcpctl_host.py`-allowed install root and avoids nested-directory assumptions when using the serial/bridge install fallback.

2. **Explicit transfer readiness probe added before tool install.**
   - Host NCM probe: `ping -c 1 -W 2 192.168.7.2`.
   - TCP control probe: `tcpctl_host.py ... ping` expecting `pong` + `OK`.

3. **Auto transport selection added.**
   - `tcpctl` mode when TCP control ping works.
   - `serial` fallback when TCP control ping fails but host NCM ping works.
   - hard block if neither transport is ready.
   - manual override: `--inventory-transport {auto,tcpctl,serial}`.

4. **Serial fallback covers both staging and read-only inventory.**
   - tool install uses `tcpctl_host.py install --install-control-channel bridge`;
   - read-only inventory uses native serial `run /cache/bin/tinymix ...` / `run /cache/bin/tinypcminfo ...`;
   - no retries are added around tinyalsa `run` execution.

## Safety Boundary

Unchanged:

- no `tinyplay`;
- no PCM playback/write;
- no mixer set operands;
- no audio HAL;
- no adsprpc path;
- live execution still requires the existing exact AUD-3C approval phrase and must roll back to V2321.

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py \
  tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 -m unittest discover -s tests -p 'test_native_audio_tinyalsa_inventory_live_handoff_v2349.py' -v
# 7 tests OK

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py --dry-run
# decision=v2349-audio-tinyalsa-inventory-live-dry-run ok=True
# transfer_readiness_plan emitted
# auto_select commands emitted for tcpctl and serial

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 -m unittest discover -s tests -p 'test_*.py'
# 1023 tests OK

git diff --check
# OK
```

## Next Safe Unit

The next device unit is a fresh exact-gated AUD-3C live attempt using the updated runner. It should be treated as a new live iteration because it will flash V2334, materialize `/dev/snd`, stage tinyalsa tools, and run read-only tinyalsa queries.

Expected behavior for the next live run:

1. if `tcpctl` is reachable, inventory uses the fast `tcpctl` path;
2. if `tcpctl` is not reachable but NCM is reachable, inventory falls back to serial/bridge;
3. if both are unavailable, stop before tool staging and roll back to V2321.
