# Native Init V2813 Audio Late Manifest Wait Live Handoff

## Summary

- Cycle: `V2813`
- Track: audio core closure gate.
- Decision: `v2813-late-manifest-play-start-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2813-audio-late-manifest-wait-20260619-112639`
- Candidate tag/version: `v2812-audio-core-promotion-candidate` / `0.10.0`
- Candidate image SHA256: `9cf680ae7dce1dac53b58a72e98668f5f6347bc14d6a64428f06ce2af830cdd0`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Failure Detail

- Error type: `RuntimeError`
- Error: `native audio play did not start worker`
- First failing step stdout: `workspace/private/runs/audio/v2813-audio-late-manifest-wait-20260619-112639/09_candidate-audio-play-execute-listen-before-deploy.txt`
- Root cause class: serial protocol marker loss during play-start output, not a validated audio-path failure.
- Evidence: the transcript contains `A90P1 BEGIN`, the 0.10.0 candidate entered `audio play`, printed
  `audio.play.execute.foreground_prime_adsp.rc=0` and `audio.play.execute.async_worker=1`, then lost
  the `A90P1 END` marker before any `audio.play.worker.started=1` line could be parsed.
- Rollback evidence: `v2321` rollback completed, and follow-up `version` plus `selftest verbose`
  returned cleanly with `selftest fail=0`.
- Interpretation: the 0.10.0 image booted and reached the foreground ADSP-prime / async-worker
  handoff, but the runner aborted on a transport artifact. The next retry should treat
  `audio.play.execute.async_worker=1` without refusal markers as an accepted play-start and continue
  into card polling / late deploy / worker-status verification, where a real worker failure would be
  caught by `audio play-status`.

## Late-Manifest Evidence

- Native command started before ACDB deploy: `audio play --mode listen --execute`
- Play start rc: `None`
- Card ready after play start: `0` after `None` polls
- Card poll last summary: `{}`
- Card/control after late deploy before worker done: `0 / 0`
- Manifest wait started/ready/timeout: `0 / 0 / 0`

## Playback Evidence

- Worker status done/attempts: `0` / `None`
- Worker status stdout: `None`
- Worker log stdout: `None`
- Worker started/done: `0` / `0`
- Integrated done: `0`
- Sound-control ready/timeout: `0` / `0`
- SET-cal hold/all-set/dealloc: `0 / 0 / 0`
- Route apply/reset OK: `0 / 0`
- PCM write/done: `0 / 0`
- Safety amplitude/duration cap: `0 / 1`

## Runtime Artifacts

- Deploy plan: `workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json`
- Remapped remote root: `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe`
- Native manifest remote path: `/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest`
- Native manifest SHA256: `a4f52ce8e8e48a224bd1f5084bb1feebd898c2ce21ce93db605f3f49d3a785b8`
- No runtime artifact installs recorded.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; runtime ACDB files are staged under `/cache` after sound-card publication.
- No forbidden partitions are touched.
- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).
- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.
