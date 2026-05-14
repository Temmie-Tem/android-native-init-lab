# Native Init v233 Real Linkerconfig Copy-Real Probe

## Summary

- Goal: boot stock Android, capture real generated `/linkerconfig`, restore
  native init, then rerun the private namespace helper with
  `--linkerconfig-mode copy-real`.
- Result: EXECUTED / CRASH PERSISTS.
- Device baseline restored after capture: `A90 Linux init 0.9.59 (v159)`.
- No Wi-Fi scan/connect/link-up, `cnss-daemon` entrypoint execution, `cnss_diag`
  execution, credential access, global Android bind mount, or persistent Android
  partition write was performed.

## Stock Android Capture

Temporary stock boot image:

- source: `backups/baseline_a_20260423_025322/boot.img`
- SHA256:
  `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`

Capture tool:

```bash
python3 scripts/revalidation/android_linkerconfig_capture.py \
  --serial RFCM90CFWXA \
  --out-dir tmp/wifi/v233-android-linkerconfig-source-live
```

Result:

- decision: `android-linkerconfig-source-ready`
- pass: `True`
- evidence: `tmp/wifi/v233-android-linkerconfig-source-live`

Captured files:

| source | size | sha256 |
| --- | ---: | --- |
| `/linkerconfig/ld.config.txt` | 134256 | `1ab340f0ee1e5f6d7c43e372dfe3bc9164d34b348dd9c716ded1b4e56e079f1a` |
| `/linkerconfig/apex.libraries.config.txt` | 366 | `5419adf6ed8f74c480d79096681a19a8570470ab8359c6e8c0be110da434f16e` |

## Native Restore

Native boot image restored after capture:

```bash
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v159.img \
  --expect-version "A90 Linux init 0.9.59 (v159)" \
  --recovery-timeout 180 \
  --bridge-timeout 180 \
  --verify-protocol auto
```

Result:

- boot prefix SHA256 matched:
  `7e7e81a6af774b3b523c993851d64b86484be4c471dbee02edf062b3903c536f`
- post-boot `cmdv1 version/status`: PASS.
- native init status after restore showed `selftest fail=0`.

## Copy-Real Probe

The captured `ld.config.txt` was transferred over NCM to:

```text
/cache/bin/a90_real_ld.config.txt
```

Transfer SHA256:

```text
1ab340f0ee1e5f6d7c43e372dfe3bc9164d34b348dd9c716ded1b4e56e079f1a
```

Probe command:

```bash
python3 scripts/revalidation/wifi_linkerconfig_materialization_probe.py \
  --out-dir tmp/wifi/v233-linkerconfig-copy-real-live \
  probe \
  --allow-temp-namespace \
  --allow-linker-list \
  --allow-private-linkerconfig \
  --linkerconfig-mode copy-real \
  --linkerconfig-source /cache/bin/a90_real_ld.config.txt \
  --assume-yes
```

Result:

- decision: `android-linkerconfig-crash-persists`
- pass: `False`
- reason: `linker process terminated by signal 11`
- evidence: `tmp/wifi/v233-linkerconfig-copy-real-live`

Helper fields:

- `helper_status=namespace-ready`
- `linkerconfig_mode=copy-real`
- `linkerconfig_source=/cache/bin/a90_real_ld.config.txt`
- `linkerconfig_mount_source=<private-materialized>`
- `linkerconfig_bytes=134256`
- `linkerconfig_hash=0x8ebe7e89aea854b5`
- `child_exit_code=-1`
- `child_signal=11`
- `timed_out=0`
- stdout/stderr: empty
- `cleanup_status=attempted`

No `/tmp/a90-v231-*`, `/tmp/a90-v232-*`, or `/tmp/a90-v233-*` mount leak was
observed in postflight captured mounts.

The temporary device copy `/cache/bin/a90_real_ld.config.txt` was removed after
the probe and verified absent.

## Interpretation

v233 closes the main v232 uncertainty: the crash is not explained by using a
synthetic linkerconfig. Even with the stock Android generated
`/linkerconfig/ld.config.txt`, `linker64 --list /vendor/bin/cnss-daemon`
terminates by `SIGSEGV(11)` without diagnostic output.

The next step should not be Wi-Fi daemon start. The next defensible step is a
linker crash-context pass:

1. confirm whether `linker64 --list` crashes for a trivial Android system
   binary inside the same private namespace;
2. compare linker environment variables, `/proc/self/exe`, and namespace paths;
3. optionally run a bounded `strace`/ptrace-style helper only if available and
   non-invasive enough for this target.

Until that boundary is understood, Wi-Fi scan/connect/link-up remains blocked.
