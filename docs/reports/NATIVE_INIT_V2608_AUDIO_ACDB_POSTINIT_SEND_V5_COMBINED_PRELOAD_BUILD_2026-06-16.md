# NATIVE_INIT V2608 — ACDB post-init send_audio_cal_v5 combined preload build

Date: 2026-06-16

## Scope

Host-only build-only unit after V2607. No Android handoff, device flash, native replay SET,
speaker write, ACDB command execution, or raw ACDB payload publication was performed.

## Decision

- decision: `v2608-acdb-postinit-send-v5-combined-preload-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2608-acdb-postinit-send-v5-combined-preload-build-only`
- helper: `workspace/private/builds/audio/v2608-acdb-postinit-send-v5-combined-preload-build-only/bin/a90_acdb_postinit_send_v5_exec_linked_v2608`
- helper_sha256: `bbb01b60b94d9ca04f4a7ffcd5d36c81e564d502e4036e8d60107e570e10ed14`
- preload: `workspace/private/builds/audio/v2608-acdb-postinit-send-v5-combined-preload-build-only/bin/liba90_acdb_postinit_send_v5_combined_preload_v2608.so`
- preload_sha256: `b6ccc853fd7f8d62e355b123ac10cf0bc70e7977f56a6da24bed524f84a611c5`

## Why This Unit

V2604 reached `before_send_audio_cal_v5` from the V2603 preinit hook and then timed out
without any armed `acdb_ioctl` rows. V2607 static RE showed `send_audio_cal_v5` begins with
the loader mutex before the initialized gate, making a self-deadlock plausible when called
from inside the init-time common-topology hook. V2605 global imported-call tracing regressed
with a linker-recursion SIGSEGV, so V2608 removes that unsafe tracing path and instead moves
`send_audio_cal_v5` into the helper after `acdb_loader_init_v3` returns.

## Contract

- preload keeps V2600 acdbtap and V2531 fake allocate/deallocate/SET behavior.
- preinit hook skips real common-topology by default, patches the initialized flag, and returns to init.
- preinit hook does not call `a90_arm_capture`, does not call `send_audio_cal_v5`, and does not exit.
- helper calls `a90_arm_capture()` only after `acdb_loader_init_v3` returns `0`.
- helper then calls `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`.
- future live success remains `ret==0` plus non-all-zero ACDB buffers; requested length alone is failure.

## Build Evidence

- helper_compile_ok: `True`
- preinit_compile_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'soname_v2608': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True}`

## Next Unit

Use the existing Android-good own-process runner with the V2608 helper/preload override.
If `init_v3_return` appears and `send_audio_cal_v5` emits acdbtap rows, V2604 was the
init-time call-site problem. If init never returns or still crashes before the helper can arm,
stop this route and continue the direct pure-read getter fallback rather than reintroducing
global pthread/log interposition.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_postinit_send_v5_combined_preload_v2608.py tests/test_build_android_acdb_postinit_send_v5_combined_preload_v2608.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_postinit_send_v5_combined_preload_v2608 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_postinit_send_v5_combined_preload_v2608.py --build --write-report`
- `git diff --check`
