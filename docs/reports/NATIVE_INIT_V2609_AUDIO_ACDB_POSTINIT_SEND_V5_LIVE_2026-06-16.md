# NATIVE_INIT V2609 — ACDB post-init send_audio_cal_v5 live discriminator

Date: 2026-06-16

## Scope

Live Android-good own-process ACDB measurement using the V2608 helper/preload override. This unit did not run native replay SET, did not run speaker playback, did not issue a real `AUDIO_SET_CALIBRATION`, and kept raw payload/log artifacts private under `workspace/private`.

## Decision

- decision: `v2609-init-tail-sigsegv-before-postinit-send-rollback-pass`
- v2490_engine_decision: `v2490-ownprocess-helper-sigsegv-no-events-before-rollback-rollback-pass`
- runner_ok: `True`
- rolled_back_to_v2321: `True`
- out_dir: `workspace/private/runs/audio/v2609-acdb-postinit-send-v5-live-20260616-183824`
- public_result: no ACDB out-buffer capture; no per-device payload captured
- counts_toward_fails_twice: `true` for the V2608 post-init route

## Artifacts

- helper: `workspace/private/builds/audio/v2608-acdb-postinit-send-v5-combined-preload-build-only/bin/a90_acdb_postinit_send_v5_exec_linked_v2608`
- helper_sha256: `bbb01b60b94d9ca04f4a7ffcd5d36c81e564d502e4036e8d60107e570e10ed14`
- preload: `workspace/private/builds/audio/v2608-acdb-postinit-send-v5-combined-preload-build-only/bin/liba90_acdb_postinit_send_v5_combined_preload_v2608.so`
- preload_sha256: `b6ccc853fd7f8d62e355b123ac10cf0bc70e7977f56a6da24bed524f84a611c5`

## What Happened

- V2490 Android handoff, staging, helper execution, artifact pull, cleanup, Android recovery reboot, and checked V2321 rollback completed.
- `A90_ACDB_FAKE_ALLOCATE=1` was active: fake allocate count was `25`; real `AUDIO_SET_CALIBRATION` count was `0`.
- V2608 preinit no-send hook entered, skipped real common topology, patched the initialized flag, and returned to `acdb_loader_init_v3`.
- The helper only emitted `before_init_v3`; it did not emit `init_v3_return`, `before_arm_capture`, or `before_send_audio_cal_v5`.
- The process then SIGSEGVed before post-init arm/send, so `acdbtap` never armed and no `acdb_ioctl` out-buffer rows were recorded.

## Key Evidence

- classification: `ownprocess-helper-sigsegv-no-events`
- helper_rc: `139`
- helper_sigsegv: `True`
- acdbtap_row_count: `0`
- acdbtap_raw_file_count: `0`
- ioctl_trace_event_count: `53`
- audio_allocate_ioctl_fake_success_count: `25`
- audio_set_ioctl_count: `0`

### V2608 helper/control events

`acdb-v2608-postinit-send-v5-events.jsonl`:

```json
{"event":"v2608_postinit_send_v5","stage":"before_init_v3","code":0,"pid":4162,"tid":4162}
```

`acdb-v2608-preinit-no-send-events.jsonl`:

```json
{"event":"v2608_preinit_no_send","stage":"entered_common_topology_hook","code":0,"pid":4162,"tid":4162}
{"event":"v2608_preinit_no_send","stage":"skip_real_common_topology","code":0,"pid":4162,"tid":4162}
{"event":"v2608_preinit_no_send","stage":"patched_initialized_flag_addr","value":0xf4821a9c,"pid":4162,"tid":4162}
{"event":"v2608_preinit_no_send","stage":"patch_initialized_flag_return","code":0,"pid":4162,"tid":4162}
{"event":"v2608_preinit_no_send","stage":"return_to_init_v3_no_arm_no_send","code":0,"pid":4162,"tid":4162}
```

### Crash signature

```text
06-16 18:39:59.164  4162  4162 F libc    : Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0 in tid 4162 (a90_acdb_ownpro), pid 4162 (a90_acdb_ownpro)
06-16 18:39:59.247  4185  4185 F DEBUG   : Cmdline: /data/local/tmp/a90-acdb-ownget/a90_acdb_ownprocess_get_exec_linked_v2529
06-16 18:39:59.247  4185  4185 F DEBUG   : pid: 4162, tid: 4162, name: a90_acdb_ownpro  >>> /data/local/tmp/a90-acdb-ownget/a90_acdb_ownprocess_get_exec_linked_v2529 <<<
06-16 18:39:59.247  4185  4185 F DEBUG   :       #00 pc 00008b30  /data/local/tmp/a90-acdb-ownget/libacdbloader.so
06-16 18:39:59.247  4185  4185 F DEBUG   :       #01 pc 00003904  /data/local/tmp/a90-acdb-ownget/liba90_acdb_combined_preload_v2538.so
```

## Interpretation

V2608 cleanly answered the discriminator. Moving `send_audio_cal_v5` out of the preinit hook does not reach post-init capture because the stock loader still crashes in the init tail after `send_common_custom_topology` returns. The V2604 timeout is not solved by simply returning from the hook and calling send later; the later call is unreachable.

This preserves the earlier static RE: the loader tail after common-topology remains unsafe in the own-process context. The next useful route is not another V2608 rerun. A follow-up must either avoid returning into the crashing init tail while also avoiding the loader-mutex deadlock, or switch back to direct pure-read getter construction.

## Safety / Rollback

- cleanup removed `/data/local/tmp/a90-acdb-ownget` and `/data/local/tmp/a90-acdb-tap`.
- rollback used `native_init_flash.py` with V2321 SHA `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- final rollback evidence: V2321 `0.9.285` booted and `selftest fail=0`.

## Validation

- preflight: V2321 `version/status/selftest` over the serial bridge before live action.
- dry-run: V2490 engine with V2608 helper/preload override reported `live_ready=True` and command safety `ok=True`.
- live: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py --run-live --use-combined-preload --fake-audio-cal-allocate --helper-path <V2608 helper> --combined-preload-so <V2608 preload> --helper-timeout 150 --adb-pull-timeout 180 --out-dir <private run>`
- `git diff --check`
