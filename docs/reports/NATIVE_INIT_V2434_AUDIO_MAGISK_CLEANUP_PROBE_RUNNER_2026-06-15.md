# NATIVE_INIT V2434 — Magisk Cleanup-Probe Runner Source/Test

Date: 2026-06-15

## Purpose

Implement the V2433 cleanup-probe design as a source/test-only runner. This unit does not
boot Android and does not write `/data/adb`; it prepares the exact-gated future live probe
that will create and remove one inert unique directory under the Magisk module namespace.

## Artifacts

Added:

- `workspace/public/src/scripts/revalidation/native_audio_magisk_cleanup_probe_live_handoff_v2434.py`
- `tests/test_native_audio_magisk_cleanup_probe_live_handoff_v2434.py`

Future live exact gate:

```text
AUD-5I-magisk-cleanup-probe go: rollbackable Android Magisk module namespace create-remove probe, inert unique directory only, no module.prop, no service.sh, no reboot before cleanup, rollback to V2321
```

## Runner Scope

The runner reuses the checked Android handoff and V2321 rollback helpers. In dry-run it emits the
full future live plan and command-safety metadata. In live mode, only after the exact gate, it will:

1. boot the pinned Android image through `native_init_flash.py`,
2. verify Magisk root settle,
3. verify `su -c` and `su -mm -c` can run read-only identity/path probes,
4. abort on pre-existing `.a90_v2433_cleanup_probe_*` residue,
5. create exactly one directory:
   `/data/adb/modules/.a90_v2433_cleanup_probe_<safe_tag>`,
6. write exactly one marker file `.probe`,
7. read back `ls -ldZ`, `stat`, and marker contents,
8. remove the marker with `rm -f "$MARKER"`,
9. remove the directory with `rmdir "$PROBE_DIR"`,
10. verify no candidate path and no residue remain,
11. reboot Android to recovery and roll back to V2321,
12. verify final native health.

The cleanup script includes an exact-path shell trap to remove the marker and directory if the
script fails after creation. It never uses broad module cleanup.

## Hard Stops Encoded

Command-safety checks reject:

- `magisk --install-module`
- `magisk --remove-modules`
- `module.prop`
- `service.sh`
- `post-fs-data.sh`
- `system.prop`
- `sepolicy.rule`
- `chmod +x`
- broad `/data/adb/modules` recursive removal
- playback/activity launch, `tinymix`, `tinyplay`
- `/dev/msm_audio_cal` or calibration ioctl tokens
- `fastboot` or raw partition-write tokens

Required command evidence includes:

- fixed probe prefix `.a90_v2433_cleanup_probe_`,
- `mkdir` against `$PROBE_DIR`,
- `rm -f` against `$MARKER`,
- `rmdir` against `$PROBE_DIR`,
- `A90_MAGISK_CLEANUP_OK`,
- `su -mm -c`,
- checked V2321 rollback command.

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_magisk_cleanup_probe_live_handoff_v2434.py tests/test_native_audio_magisk_cleanup_probe_live_handoff_v2434.py
PYTHONPATH=tests python3 -m unittest tests/test_native_audio_magisk_cleanup_probe_live_handoff_v2434.py
PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_magisk_cleanup_probe_live_handoff_v2434.py --dry-run --probe-tag unit_test
PYTHONPATH=tests python3 -m unittest discover -s tests
git diff --check
```

Focused tests cover:

- wrong live approval refuses before device action,
- unsafe probe tags are rejected,
- dry-run path is `/data/adb/modules/.a90_v2433_cleanup_probe_unit_test`,
- command plan contains exact create/remove operations,
- command plan omits activation files and install/remove module commands,
- cleanup summarizer classifies success and residue outcomes,
- checked V2321 rollback remains in the plan.

Dry-run result:

```text
decision=v2434-magisk-cleanup-probe-live-dry-run
ok=true
future_live_ready=true
probe_path=/data/adb/modules/.a90_v2433_cleanup_probe_unit_test
command_safety.ok=true
```

Full test result:

```text
Ran 1180 tests in 24.127s
OK
```

No live Android boot or `/data/adb` write was performed in V2434.

## Conclusion

V2434 is ready for the next bounded live unit. The next action should be the exact-gated
V2435 cleanup-probe live run, not M1 activation. If V2435 proves targeted cleanup/no-residue,
then the M1 temporary Magisk module can be retried with the corrected `adb shell "su -c '<script>'"`
quoting style. Keep `magisk --install-module` deferred unless direct targeted staging/cleanup fails.
