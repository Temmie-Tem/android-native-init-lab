# NATIVE_INIT_V2387_AUD4_PCM_PROBE_LIVE_ADSP_MARKER_LOSS_2026-06-15

## Scope

Exact-gated AUD-4 live retry after V2386. Intended purpose: run the same V2377-observed speaker route and use `a90_pcm_write_probe_v2386` instead of stock `tinyplay` so a PCM write failure reports errno and `pcm_get_error()`.

Approval phrase used:

```text
AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, low-amplitude tinyplay, reverse reset, rollback to V2321
```

## Result

Decision: blocked before route apply/playback.

Private run evidence:

```text
workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-054101/
```

The runner completed:

- V2321 preflight verify and selftest: pass
- V2334 candidate flash: pass
- candidate `version`/`status`/`selftest`: pass
- pre-ADSP `audio adsp-status` / `audio snd-status`: card absent, `/dev/snd` absent as expected
- rollback to V2321: pass
- final rollback health: `rollback_version_ok=True`, `rollback_selftest_fail0=True`

The runner blocked at:

```text
candidate-adsp-boot-once
```

Step output tail:

```text
RuntimeError('A90P1 END marker not found\n\r\ncmdv1 audi doot-once AUD2_ONE_SHAaudio.adsp_boot_once.version=1\r\naudio.adsp_boot_once.retry=forbidden\r\n[done] audio (21ms)\r\nAT\r\na90:/# AT\r\na90:/# ATATAT\r\na90:/# ')
```

## Classification

This is not a V2386 PCM probe result. The run never installed tools, applied route controls, materialized `/dev/snd`, or attempted playback.

Source classification from `workspace/public/src/native-init/a90_audio.c`:

- `audio.adsp_boot_once.retry=forbidden` is printed at `a90_audio.c:826`.
- That line is reached only after:
  - token validation passes;
  - firmware preflight passes;
  - `/sys/kernel/boot_adsp/boot` opens;
  - `write_all_checked(fd, "1\n", 2)` succeeds;
  - `close(fd)` succeeds;
  - `audio.adsp_boot_once.write=accepted` is printed at `a90_audio.c:825`.

Therefore the best classification is:

```text
adsp-accepted-protocol-marker-lost
```

The command/output stream was corrupted enough that the harness did not see the `A90P1 END` marker. Because the ADSP activation command is one-shot and prints `retry=forbidden` after accepted write, blindly retrying the same command would be wrong.

## Safety outcome

- No `tinymix` set command ran.
- No route apply/reset command ran.
- No `a90_pcm_write_probe_v2386` command ran.
- No stock `tinyplay` command ran.
- No PCM write/playback occurred.
- Rollback to V2321 succeeded.
- Final device health: V2321 `0.9.285`, `selftest fail=0`.

## Next unit

Host-only V2388 should patch the AUD-4 runner around `candidate-adsp-boot-once`:

1. Run the one-shot ADSP boot command with `allow_error=True`.
2. If the command lacks `A90P1 END` but output contains `audio.adsp_boot_once.retry=forbidden` and contains no `refused=` / `write=failed` / `open_failed` / `close_failed`, classify it as accepted.
3. Immediately poll `audio adsp-status`, wait for card/materialization, and continue only if the normal post-ADSP evidence appears.
4. Preserve this classification in `result.json`.
5. Do not rerun the one-shot ADSP boot command after accepted-output marker loss.

Only after V2388 is implemented and statically validated should another exact-gated live attempt try to reach the V2386 PCM probe.
