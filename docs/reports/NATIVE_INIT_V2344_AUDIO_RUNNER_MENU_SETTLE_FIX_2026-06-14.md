# NATIVE_INIT V2344 — AUD-3 runner menu-settle fix

Date: 2026-06-14  
Scope: host-only runner hardening after V2343  
Touched code: `workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`  
Tests: `tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`

## Background

V2343 ran the exact-gated AUD-3 preflight live attempt on V2334, but the run stopped before ADSP activation:

```text
[busy] auto menu active; send hide/q before command
A90P1 END seq=9 cmd=audio rc=-16 errno=16 duration_ms=0 flags=0x0 status=busy
```

The shared serial recovery layer correctly sent `hide`, but it also correctly refused to retry `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` because that command is token-gated and unsafe to retry after dispatch.

## Change

The runner now performs an explicit pre-settle before each token-gated one-shot audio command:

1. Send safe control command `cmdv1 hide`.
2. Wait a bounded host-side settle delay (`--menu-settle-sec`, default `1.0`).
3. Dispatch the token-gated command exactly once.

Applied sites:

- Before `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT`.
- Before `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY`.

The token-gated commands themselves remain non-retried. If a one-shot still returns `busy` or fails, the runner will stop and rollback rather than re-dispatching it.

## Safety boundary

This is host-only. It does not flash, boot, activate ADSP, materialize `/dev/snd`, open ALSA devices, issue mixer commands, invoke tinyalsa, or play PCM.

The fix is limited to runner sequencing and tests. It preserves the existing live gate phrase:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py \
  tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_snd_nodes_preflight_handoff_v2335 -v

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py --dry-run \
  | python3 -m json.tool >/tmp/v2344-dryrun.json

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_*.py'

git diff --check
```

Results:

- `py_compile`: pass.
- Focused V2335 runner tests: 9 tests pass.
- Dry-run: `ok=true`, with two explicit `settle auto menu` plan entries.
- Full suite: 1005 tests pass.
- `git diff --check`: pass.

## Next unit

A fresh exact-gated AUD-3 live retry can now re-run the V2335 runner against V2334. Expected difference from V2343: the runner should hide/settle before `adsp-boot-once`, avoiding the auto-menu busy block while still preserving one-shot/no-retry semantics.
