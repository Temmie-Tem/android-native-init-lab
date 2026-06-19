# Native Init V2810 Audio Late Manifest Wait Live Handoff

## Summary

- Cycle: `V2810`
- Track: audio core closure gate.
- Decision: `v2810-late-manifest-play-start-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2810-audio-late-manifest-wait-20260619-110851`
- Candidate tag/version: `v2807-audio-late-manifest-wait` / `0.9.315`
- Candidate image SHA256: `6e2f710f106ab5e91ae6887518db7f2b50076bf5c7edda044281ba939eda5e1a`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Failure Detail

- Error type: `RuntimeError`
- Error: `native audio play did not start worker`
- First failing step stdout: `workspace/private/runs/audio/v2810-audio-late-manifest-wait-20260619-110851/09_candidate-audio-play-execute-listen-before-deploy.txt`
- Root cause class: host/serial command framing failure, not an audio-path failure.
- Evidence: the failed transcript contains a truncated command echo (`cmdv1 audio play ... --eut`) and
  no `A90P1 END` marker; the device rolled back to `v2321`, and a follow-up bridge health check
  returned clean `version` plus `selftest fail=0`.
- Interpretation: V2810 did not reach the intended late-manifest discriminator. The V2809 allowlist
  fix remains valid, but the retry must stabilize the play-start transport before repeating the
  full audio proof.

## Late-Manifest Evidence

- Native command started before ACDB deploy: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --execute`
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
- Safety amplitude/duration cap: `0 / 0`

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
