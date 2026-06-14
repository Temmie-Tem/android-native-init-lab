# NATIVE_INIT V2350 — audio tinyalsa inventory live blocked

Date: 2026-06-15

## Scope

Exact-gated AUD-3C live attempt:

`AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321`

Goal: reproduce the proven V2334 ADSP + `/dev/snd` materialization window, stage the pinned V2345 static `tinymix`/`tinypcminfo` query tools, run read-only tinyalsa inventory only, then roll back to V2321.

Hard boundary held: no `tinyplay`, no PCM playback/write, no mixer set operands, no audio HAL, no adsprpc path.

## Result

**Blocked before tinyalsa inventory.** The live path successfully reached the post-materialization `/dev/snd` state twice, but failed before any tinyalsa query command ran.

| Run dir | Outcome | Notes |
| --- | --- | --- |
| `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-003400` | blocked at `install-tinymix` | Host-side install policy rejected `/cache/a90-audio/v2349-tinyalsa-inventory/tinymix`; rollback to V2321 succeeded. |
| `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-004124` | blocked at `install-tinymix` | After moving the target under `/cache/a90-runtime/bin/`, `tcpctl_host.py install` timed out connecting to `192.168.7.2:2325`; rollback to V2321 succeeded. |

Because the same live sub-goal stopped twice before inventory, no further live retry was attempted in this iteration.

## Device Evidence

Second run, before `/dev/snd` materialization:

```text
audio.dev_snd.count=0
audio.dev_snd.control_like=0
audio.dev_snd.pcm_like=0
audio.sound_class.count=128
audio.sound_class.card_like=1
audio.sound_class.control_like=1
```

Second run, after token-gated `/dev/snd` materialization:

```text
audio.dev_snd.count=61
audio.dev_snd.control_like=1
audio.dev_snd.pcm_like=59
audio.sound_class.count=128
audio.sound_class.card_like=1
audio.sound_class.control_like=1
```

No tinyalsa command reached execution. `tinyalsa_inventory` remained unset in both result files.

Final post-rollback health:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: pass=11 warn=1 fail=0
```

## Runner Fix Landed

During the iteration, the runner was corrected to use a `tcpctl_host.py install`-allowed runtime root:

```text
/cache/a90-runtime/bin/v2349-tinyalsa-inventory/{tinymix,tinypcminfo}
```

A regression test now asserts that every planned install target is under `/cache/a90-runtime/bin/`. The runner also now records blocked live exceptions into `result.json` before rollback-finalization.

## Validation

Host-side validation after the runner fix:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py \
  tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 -m unittest discover -s tests -p 'test_native_audio_tinyalsa_inventory_live_handoff_v2349.py' -v
# 5 tests OK

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 -m unittest discover -s tests -p 'test_*.py'
# 1021 tests OK

git diff --check
# OK
```

## Interpretation

The ADSP and `/dev/snd` materialization result remains strong and repeatable. The new blocker is not audio-path readiness; it is the host-to-device tool staging path after the V2334 flash/materialization window.

The second failure points at missing or non-ready host/device TCP control reachability at the point where `tcpctl_host.py install` probes `ping` over `192.168.7.2:2325`. Candidate status earlier in the run still reported `transport.tcpctl=ready`, so the next unit should instrument and repair the transfer precondition instead of touching audio routing.

## Next Safe Unit

Host-only runner fix before any new live attempt:

1. Add an explicit post-flash/post-materialization NCM + tcpctl readiness step before tool install.
2. If TCP install is not reachable, either recover NCM deterministically or fall back to an approved serial-control install path that stays under the same read-only tinyalsa inventory boundary.
3. Keep tinyalsa execution exact-gated; no `tinyplay`, no mixer writes, no PCM playback.

