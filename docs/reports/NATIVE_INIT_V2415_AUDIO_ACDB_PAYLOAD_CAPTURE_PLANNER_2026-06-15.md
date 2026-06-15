# V2415 — ACDB payload capture planner

Scope: host-only N3-CAP0 planner/support after V2414 defined the native ACDB replay boundary. No flash, Android boot, Magisk module install, native `/dev/msm_audio_cal` ioctl, mixer write, PCM playback, or ACDB payload replay ran in this unit.

## Decision

`v2415-acdb-payload-capture-planner-ready`

V2415 turns the V2414 boundary into source-controlled support for the next safe measurement: a future rollbackable Android-good capture of `/dev/msm_audio_cal` ioctl command order and request payload facts from the stock audio path.

## Implemented artifacts

- Added `workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_v2415.c`.
  - Android-side observer only.
  - Attaches to an existing audio process with `PTRACE_ATTACH`.
  - Steps syscalls with `PTRACE_SYSCALL` and filters `__NR_ioctl`.
  - Accepts only ioctl entries whose fd symlink resolves to `/dev/msm_audio_cal`.
  - Copies up to 512 bytes from the target process ioctl request pointer with `process_vm_readv`, falling back to `PTRACE_PEEKDATA`.
  - Emits private JSONL with command, return code, fd target, request pointer, read length, read errno, and private raw hex.
- Added `workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_planner_v2415.py`.
  - Default mode is host-only dry-run.
  - Optional `--materialize-capture-helper` builds a private static AArch64 helper and controller script.
  - Future live plan uses checked Android handoff, Magisk root settle, helper/APK staging, bounded Android `AudioTrack` playback, artifact pull, cleanup, Android recovery reboot, and V2321 rollback.
  - `--run-live` remains a source-only placeholder in V2415; exact gate is accepted only to prove no device action occurs in this unit.
- Added `tests/test_native_audio_acdb_payload_capture_planner_v2415.py`.
  - Locks host-only behavior, checked Android handoff command shape, forbidden tokens, helper source properties, private helper build, and exact-gate placeholder behavior.

## Magisk direction

The Wi-Fi-style Magisk/module pattern is valid here only as an Android-good measurement capsule.

- **M0 default:** transient Magisk-root helper. Stage the ptrace ioctl observer under `/data/local/tmp`, run it with `adb shell su -c` after Android ADB/root settle, capture around bounded Android framework `AudioTrack` playback, then pull private artifacts and roll back to V2321.
- **M1 fallback:** temporary Magisk boot module only if M0 classifies `missed-early-payload`. This would start the same observer earlier from `post-fs-data.sh`/`service.sh`, under a separate exact gate and V-iteration, and must be removed by Android-to-V2321 rollback.
- **M2 deferred:** vendor wrapper/probe remains last resort if both M0 and M1 fail to expose one identified payload edge.

This keeps native init independent of Magisk. Android/Magisk observes the stock-good producer path; native init receives only reviewed facts: command sequence, decoded headers, lengths, payload hashes, and cleanup policy.

## Safety boundaries

- No native calibration ioctl is issued.
- The helper does not open `/dev/msm_audio_cal` itself.
- Raw payload bytes are private-only and must not be committed.
- Public reports may include command numbers, return codes, decoded headers, payload lengths, and payload SHA256 values.
- Persistent `magisk --install-module` remains forbidden.
- Native replay remains blocked until decoded headers, payload hashes, order, mem-handle policy, and cleanup behavior are pinned.

## Known caveat

The V2415 helper is an AArch64 syscall-register observer. If Android routes the relevant audio HAL process through a 32-bit compat syscall ABI, the future V2416 live run should classify `need-compat-helper-or-M1-wrapper` rather than forcing replay. This is a measurement caveat, not a native replay gate.

## Dry-run summary

Materialized dry-run with a temporary private output directory reported:

```json
{
  "ok": true,
  "decision": "v2415-acdb-payload-capture-planner-dry-run",
  "host_only": true,
  "future_live_ready": true,
  "future_live_blockers": [],
  "safety_ok": true,
  "helper_ok": true,
  "aarch64_static": true,
  "magisk_default": "M0-transient-helper",
  "m1_gate": "new exact approval and separate V-iteration only if M0 classifies missed-early-payload",
  "binary_mode": "0o700"
}
```

## Validation

Commands run:

```bash
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_planner_v2415.py tests/test_native_audio_acdb_payload_capture_planner_v2415.py
python3 -m unittest discover -s tests -p 'test_native_audio_acdb_payload_capture_planner_v2415.py' -v
python3 -m unittest discover -s tests
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_planner_v2415.py --dry-run --materialize-capture-helper --helper-out-dir "$(mktemp -d)"
git diff --check
```

Results:

- Focused V2415 tests: 10/10 pass.
- Full unittest suite: 1116/1116 pass.
- Private AArch64 static helper build: pass.
- Dry-run materialization: `future_live_ready=true`, `future_live_blockers=[]`, command safety pass.
- `git diff --check`: pass.

## Next step

V2416 should be the exact-gated Android-good M0 live capture using:

`AUD-5D-acdb-payload-capture go: rollbackable Android AudioTrack speaker msm_audio_cal ioctl payload capture, transient Magisk-root observer only, no native calibration ioctl, no native speaker write, rollback to V2321`

If V2416 returns `missed-early-payload`, insert a separate M1 temporary Magisk boot-module capture unit before parser/replay work.
