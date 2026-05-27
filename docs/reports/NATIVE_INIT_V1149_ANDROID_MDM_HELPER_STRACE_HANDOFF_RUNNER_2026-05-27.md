# Native Init V1149 Android `mdm_helper` strace Handoff Runner Report

Date: `2026-05-27`

## Result

- Decision: `v1149-handoff-dryrun-ready`
- Pass: `true`
- Runner: `scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py`
- Dry-run manifest: `tmp/wifi/v1149-dryrun/manifest.json`
- Dry-run summary: `tmp/wifi/v1149-dryrun/summary.md`
- Module ZIP: `tmp/wifi/v1149-dryrun/a90_mdm_trace_v1149.zip`

## Summary

V1149 adds the bounded Android handoff runner for the V1147/V1148
`mdm_helper` strace module.

The live gate is intentionally two-boot Android:

```text
native v724
  -> recovery/TWRP
  -> flash known Android boot
  -> boot Android for Magisk module install
  -> install a90_mdm_trace module
  -> reboot Android so Magisk overlay wraps /vendor/bin/mdm_helper early
  -> collect /data/local/tmp/a90-wifi/
  -> remove module
  -> recovery/TWRP
  -> restore native v724
```

Dry-run verified:

- V1147 module root is install-ready.
- The generated ZIP contains `module.prop`, static AArch64 `strace`, wrapper,
  `post-fs-data.sh`, and `service.sh`.
- Android boot candidate and native v724 rollback candidate are locally
  classified.
- Step plan has unique boot-complete evidence names.
- Failure after Android boot write attempts cleanup/native rollback.

## Selected Images

Dry-run selected:

| role | path |
| --- | --- |
| Android boot | `backups/baseline_a_20260423_025322/boot.img` |
| Native rollback | `stage3/boot_linux_v724.img` |

## Live Success Criteria

The live V1149 pass condition is not Wi-Fi bring-up. It only proves the Android
syscall contract needed before the next native repair:

- native v724 preflight passes;
- Android boot image write/readback matches;
- Magisk module installs;
- second Android boot creates `/data/local/tmp/a90-wifi/`;
- `mdm_helper.wrapper.log` shows wrapper start and original binary selection;
- `mdm_helper.strace.txt` exists and captures `/dev/esoc-0`;
- module is removed;
- native v724 rollback is verified by bridge `bootstatus`/`version`.

## Guardrails

- No Wi-Fi credentials, scan/connect, DHCP/routes, or external ping.
- No native `/dev/subsys_esoc0` retry.
- No native eSoC ioctl.
- No direct `/vendor` partition mutation; use Magisk overlay only.
- Native rollback is part of the live plan.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py
python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1149-dryrun \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run
```

Result:

```text
decision: v1149-handoff-dryrun-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

## Next

Run the same V1149 runner in live mode with the approval flags. If it captures
the Android `mdm_helper` syscall contract and rolls back cleanly, V1150 should
classify the trace into the native image-link action sequence.
