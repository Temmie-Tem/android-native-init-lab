# Native Init V2808 Audio Late Manifest Wait Live Handoff

## Summary

- Cycle: `V2808`
- Track: audio core closure gate.
- Decision: `v2808-late-manifest-live-blocked`
- Result directory: `workspace/private/runs/audio/v2808-audio-late-manifest-wait-20260619-105918`
- Candidate tag/version: `v2807-audio-late-manifest-wait` / `0.9.315`
- Candidate image SHA256: `6e2f710f106ab5e91ae6887518db7f2b50076bf5c7edda044281ba939eda5e1a`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Failure Detail

- Error type: `RuntimeError`
- Error: `step failed: install-acdb-00-set_arg`
- First failing step stdout: `workspace/private/runs/audio/v2808-audio-late-manifest-wait-20260619-105918/19_install-acdb-00-set_arg.txt`
- Root cause: the shared runtime installer refused the new default runtime data path
  `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/...` because its current allowlist
  only permits `/cache/bin`, `/cache/a90-acdb-setcal-replay-*`, `/cache/a90-runtime/bin`, or
  `/mnt/sdext/a90/bin`.
- Interpretation: V2808 validated that the late-manifest sequencing reaches ADSP/card publication
  before the late deploy, but the runtime artifact install policy must be updated before the full
  native `audio play` proof can complete.
- The `audio play ... --execute` command itself returned `rc=0`, started the async worker
  (`audio.play.worker.started=1`), and returned control before artifact deployment as intended.
- ADSP/rpmsg was present on the first post-play poll, and the sound card/control nodes appeared on
  the second poll before the failing artifact install (`audio.sound_class.count=128 card_like=1
  control_like=1`, `audio.dev_snd.count=61`).

## Late-Manifest Evidence

- Native command started before ACDB deploy: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --execute`
- Play start rc: `0`
- Card ready after play start: `1` after `2` polls
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
