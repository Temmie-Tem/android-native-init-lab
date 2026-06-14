# NATIVE_INIT_V2349_AUDIO_TINYALSA_INVENTORY_LIVE_RUNNER

Date: 2026-06-15
Scope: host-side exact-gated live runner for post-materialization tinyalsa inventory
Device action: none in this iteration
Flash: none in this iteration

## Reason

V2348 closed the `/dev/snd` materialization preflight: V2334 can boot ADSP/Q6,
materialize 61 allowed `/dev/snd` nodes, avoid ALSA open/ioctl/playback, and roll back to V2321.
The next safe audio unit is not playback. It is a read-only tinyalsa inventory gate that opens ALSA
for query-only inspection using pinned V2345 `tinymix` and `tinypcminfo` tools.

## Change

Added `native_audio_tinyalsa_inventory_live_handoff_v2349.py`.

The runner composes the proven pieces instead of widening the live scope:

1. exact approval phrase check,
2. V2321 preflight verify,
3. flash V2334 using the checked flash helper,
4. candidate health checks,
5. one ADSP boot token if needed,
6. one `/dev/snd` materialization token,
7. install pinned V2345 `tinymix` and `tinypcminfo` to `/cache/a90-audio/v2349-tinyalsa-inventory/` via tcpctl/NCM,
8. run read-only inventory only:
   - `tinymix -D 0`,
   - `tinymix -D 0 --all-values`,
   - `tinypcminfo -D 0 -d 0`,
9. candidate selftest,
10. rollback to V2321 and final health.

The live command remains exact-gated and was not run in this iteration.

Required phrase for the future live run:

```text
AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321
```

## Safety Boundaries

Hard exclusions in the runner and tests:

- no `tinyplay`,
- no PCM playback/write,
- no `tinymix` value/control set operands,
- no audio HAL,
- no adsprpc invoke/ioctl,
- rollback to V2321 after inventory.

`tinypcminfo` is allowed to fail without making the whole run unsafe because an invalid/closed PCM
query is still useful inventory data; `tinymix` list commands are not allow-error.

## Dry-Run Result

Dry-run command:

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py --dry-run
```

Result:

- decision: `v2349-audio-tinyalsa-inventory-live-dry-run`
- ok: `true`
- materialization preflight: ok
- V2345 tinyalsa manifest: ok
- command safety: ok
- install plan: `tinymix`, `tinypcminfo`
- inventory plan: `tinymix-list-card0`, `tinymix-list-card0-all-values`, `tinypcminfo-card0-device0`

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py \
  tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py

python3 -m unittest discover -s tests -p 'test_native_audio_tinyalsa_inventory_live_handoff_v2349.py'
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Results:

- focused V2349 tests: 4 passed
- full test suite: 1020 passed
- whitespace check: passed

## Outcome

V2349 is ready for a future exact-gated live read-only tinyalsa inventory run.
It does not prove playback and does not attempt playback. Playback remains a later, separately gated
step after mixer/PCM inventory identifies a safe route and candidate PCM device.
