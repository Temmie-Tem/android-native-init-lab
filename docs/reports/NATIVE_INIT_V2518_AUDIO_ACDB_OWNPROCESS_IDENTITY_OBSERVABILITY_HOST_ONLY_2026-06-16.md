# NATIVE_INIT_V2518_AUDIO_ACDB_OWNPROCESS_IDENTITY_OBSERVABILITY_HOST_ONLY_2026-06-16

## Scope

- Unit: V2518 host-only hardening of the V2490 own-process ACDB live runner.
- Trigger: V2517 proved `acdb_loader_init_v3` reaches ACDB file load and ACPH init, then fails opening `/dev/msm_audio_cal` with `errno=13` while the helper is audited as shell.
- Goal: make the next live run capture execution identity, SELinux domain, property label, and `/dev/msm_audio_cal` node metadata before helper execution, without adding any calibration write or playback action.

## Changes

- Added `ownget-probe-execution-context` before the helper run.
- Added `ownget-exec-context.txt` with:
  - `id`
  - `id -Z`
  - `getenforce`
  - selected `/proc/self/status` identity/capability fields
  - current shell process label
  - helper file label
  - read-only `ls -lZ /dev/msm_audio_cal`
  - read-only vendor audio property file label probe
  - `getprop persist.vendor.audio.calfile0`
- Added `ownget-run-context.txt` from the exact shell that executes the helper.
- Refined artifact parsing:
  - `init-v3-block-msm-audio-cal-open-denied`
  - `init-v3-block-vendor-audio-prop-denied`
  - diagnostic booleans for `/dev/msm_audio_cal` denial, vendor audio property denial, and shell-domain context.
- Narrowed command-safety matching from the literal `/dev/msm_audio_cal` path to the forbidden SET/ioctl pattern. Read-only metadata probes are now allowed; `0xc00461cb` and `/dev/msm_audio_cal 0xc00461cb` remain blocked.

## Safety Boundary

- No live device run in V2518.
- No HAL injection, Magisk module install, HAL restart, AudioTrack/playback, `tinymix`, `tinyplay`, native speaker write, or `/dev/msm_audio_cal` SET path.
- The new `/dev/msm_audio_cal` usage is metadata-only via `ls -lZ`/`ls -l`; it does not open the node.
- Raw/proprietary artifacts remain under `workspace/private/`.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
  - Result: `16` tests passed.
- V2490 dry-run with the V2512 helper:
  - `ok=true`
  - `live_ready=true`
  - command safety `ok=true`
  - `probe_execution_context` present

## Retrospective Parse

- Re-running the V2518 parser on the V2517 private artifact set reclassifies that run as:
  - `init-v3-block-msm-audio-cal-open-denied`
- The same parse reports:
  - `has_msm_audio_cal_open_denied=true`
  - `has_vendor_audio_prop_denied=true`
  - `has_shell_domain_context=true`
- The V2517 artifact set does not contain the new `ownget-exec-context.txt` or `ownget-run-context.txt` files because they are introduced by this unit.

## Next Unit

- V2519 can run the hardened V2490 live path once.
- Acceptance for V2519 is not ACDB payload capture alone; it must first answer whether the helper is truly executing as root/vendor-capable context or still as shell domain.
- If it still executes as shell, design a bounded domain/identity fix explicitly. Do not silently set SELinux permissive or re-enter in-HAL injection.

