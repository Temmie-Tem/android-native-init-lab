# v232 Plan: Private Linkerconfig Materialization Probe

## Summary

v232 follows v231 `android-namespace-manual-review-required`.

v231 proved that a private Android-like namespace can be created and cleaned up,
but Android `linker64 --list /vendor/bin/cnss-daemon` terminated with
`SIGSEGV(11)` after `helper_status=namespace-ready`. The strongest current
explanation is incomplete Android linker namespace configuration:

- `/mnt/system/linkerconfig` exists but is empty in native init.
- `/mnt/system/system/etc/ld.config.txt`, `ld.config.arm64.txt`, and
  `ld.config.vndk_lite.txt` are absent.
- `/system/bin/linker64` points to `/apex/com.android.runtime/bin/linker64`.
- The linker binary contains `--list`, `/linkerconfig/ld.config.txt`,
  `/system/etc/ld.config.arm64.txt`, and namespace diagnostics.

v232 goal is to test linker namespace configuration inside the temporary private
root only. It must not start `cnss-daemon`, must not create global mounts, and
must not write Android partitions.

## Reference Notes

- Android linker config has two core parts: directory-to-section mappings and
  section namespace properties. Mappings use `dir.<section>=<directory>`, then
  sections define namespace search paths, permitted paths, and links.
- Android 11+ devices generally generate linker configuration at runtime under
  `/linkerconfig` instead of relying on static `ld.config.*.txt` files in the
  system image.
- Android bionic supports `linker64 --list` as ldd-like behavior. v232 still
  uses that mode only; it does not transfer control to `cnss-daemon`.

Reference URLs:

- https://android.googlesource.com/platform/bionic/+/master/linker/ld.config.format.md
- https://android.googlesource.com/platform/system/linkerconfig/
- https://source.android.com/docs/core/architecture/vndk/linker-namespace?hl=en
- https://android.googlesource.com/platform/bionic/+/90f96b9f483b8effefd6a6fe8a8f0562f616837e

## Goal

Answer this question:

> If `/linkerconfig/ld.config.txt` is provided only inside the helper's private
> temporary root, can `linker64 --list /vendor/bin/cnss-daemon` produce a normal
> dependency-resolution result instead of `SIGSEGV(11)`?

Expected v232 decision labels:

- `android-linkerconfig-source-ready`: a real Android `/linkerconfig` source was
  captured and can be materialized privately in the next probe.
- `android-linker-list-pass`: private linkerconfig materialization lets
  `linker64 --list` resolve the daemon.
- `android-linker-list-runtime-gap`: linker runs and reports a concrete missing
  library/path/dependency gap.
- `android-linkerconfig-required`: linker runs and reports namespace/config
  policy problems.
- `android-linkerconfig-crash-persists`: linker still crashes with a signal even
  after private linkerconfig materialization.
- `android-linkerconfig-materialization-blocked`: helper/source/preflight guard
  blocks the probe before linker execution.
- `android-linkerconfig-manual-review-required`: evidence is inconsistent or
  classification is not deterministic.

## Non-Goals

v232 must not perform:

- direct `cnss-daemon` execution;
- `cnss_diag` execution;
- Wi-Fi interface link-up, scan, connect, credential access, DHCP, routing, NAT,
  or DNS changes;
- ICNSS unbind/bind, `driver_override`, debugfs/sysfs recovery writes;
- global `/system`, `/vendor`, `/apex`, or `/linkerconfig` bind mounts;
- persistent writes under `/system`, `/vendor`, `/data`, `/efs`, firmware paths.

## Proposed Work

Add or extend host tooling:

```text
scripts/revalidation/wifi_linkerconfig_materialization_probe.py
```

Extend the device helper:

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
```

The v232 helper should keep the v231 allowlisted command shape, but add one
reviewed mode flag:

```text
--linkerconfig-mode none|copy-real|minimal-vendor
```

Initial implementation should support:

- `none`: v231 behavior, useful as regression baseline.
- `copy-real`: copy an already-provided private source file into
  `<root>/linkerconfig/ld.config.txt`.
- `minimal-vendor`: generate a small reviewed text config under
  `<root>/linkerconfig/ld.config.txt`.

The default remains `none`. `minimal-vendor` and `copy-real` must require host
flags and must be impossible to trigger from arbitrary shell strings.

## Preferred Path: Real Android Linkerconfig Source

Preferred evidence path:

1. Boot stock Android, using root access if needed.
2. Capture read-only:
   - `/linkerconfig/ld.config.txt`
   - `/linkerconfig/apex.libraries.config.txt`
   - `find /linkerconfig -maxdepth 2 -type f -o -type l -o -type d`
   - `getprop ro.vndk.version ro.product.first_api_level ro.board.platform`
   - `ls -l /apex /vendor/lib64 /system/lib64`
3. Store under:

```text
tmp/wifi/v232-android-linkerconfig-source/
```

4. Validate private/no-follow host evidence output.
5. Feed the captured `ld.config.txt` to the v232 helper only as private temp
   root material, never to global `/linkerconfig`.

If real Android linkerconfig is available, it is more defensible than guessing
namespace rules from AOSP templates.

## Fallback Path: Minimal Vendor Config

If real Android linkerconfig cannot be captured yet, v232 may run one
`minimal-vendor` probe, but the report must label it as synthetic.

The minimal config must be generated inside `<root>/linkerconfig/ld.config.txt`
only. Candidate shape:

```text
dir.vendor=/vendor/bin

[vendor]
additional.namespaces = system

namespace.default.isolated = true
namespace.default.visible = true
namespace.default.search.paths = /vendor/${LIB}:/odm/${LIB}
namespace.default.permitted.paths = /vendor/${LIB}:/odm/${LIB}
namespace.default.links = system
namespace.default.link.system.shared_libs = <LLNDK/Bionic allowlist>

namespace.system.isolated = true
namespace.system.search.paths = /system/${LIB}:/apex/com.android.runtime/${LIB}
namespace.system.permitted.paths = /system/${LIB}:/apex/com.android.runtime/${LIB}
```

The `<LLNDK/Bionic allowlist>` must be generated from existing v221/v227
evidence and kept explicit in `helper-result.json`. Do not use `allow_all_shared_libs`
unless a separate plan explicitly accepts that weakening.

## Helper Contract Updates

The helper should:

1. Keep exact allowlists for system root, vendor block, vendor fstype, linker,
   and target.
2. Keep `unshare(CLONE_NEWNS)` and `MS_REC|MS_PRIVATE`.
3. Keep private temp root under `/tmp/a90-v232-<pid>/root`.
4. Continue to mount:
   - `/mnt/system/system` -> `<root>/system` read-only;
   - vendor `sda29` -> `<root>/vendor` read-only with `noload`;
   - `<root>/proc` before `chroot`;
   - `/mnt/system/system/apex` -> `<root>/apex` if present.
5. Create `<root>/linkerconfig/ld.config.txt` only for explicit v232 modes.
6. Record SHA256 or FNV/hash of generated linkerconfig text in helper output.
7. Print:
   - `linkerconfig_mode`
   - `linkerconfig_source`
   - `linkerconfig_bytes`
   - `linkerconfig_hash`
   - `classification_hint`
8. Execute only:

```text
/system/bin/linker64 --list /vendor/bin/cnss-daemon
```

9. Capture stdout/stderr/exit/signal/timeout.
10. Reverse-unmount and remove temp paths.

## Host Tool Contract

The host wrapper should expose:

```bash
python3 scripts/revalidation/wifi_linkerconfig_materialization_probe.py plan
python3 scripts/revalidation/wifi_linkerconfig_materialization_probe.py inventory
python3 scripts/revalidation/wifi_linkerconfig_materialization_probe.py probe \
  --allow-temp-namespace \
  --allow-linker-list \
  --allow-private-linkerconfig \
  --linkerconfig-mode minimal-vendor \
  --assume-yes
```

Required guardrails:

- `--allow-private-linkerconfig` is mandatory for `copy-real` and
  `minimal-vendor`.
- Host validates that no path escapes the private evidence directory.
- Host validates helper command exact argv.
- Host writes:
  - `linkerconfig-candidate.txt`
  - `linkerconfig-candidate.sha256`
  - `helper-output.txt`
  - `linker-list.txt`
  - `helper-result.json`
  - `postflight.json`
  - `manifest.json`

## Classification Rules

Priority:

```text
timeout/helper setup > linker crash > linkerconfig/namespace > missing dependency/path > pass
```

Rules:

| Condition | Decision |
| --- | --- |
| helper setup/mount/chroot/write fails | `android-linkerconfig-materialization-blocked` |
| child timeout | `android-linkerconfig-materialization-blocked` |
| child signal with v231 `none` mode | `android-linkerconfig-crash-persists` |
| child signal with `copy-real` or `minimal-vendor` mode | `android-linkerconfig-crash-persists` |
| stderr contains namespace/config/permitted path errors | `android-linkerconfig-required` |
| stderr contains missing library/path/dependency errors | `android-linker-list-runtime-gap` |
| exit code 0 and no bad patterns | `android-linker-list-pass` |
| output cannot be classified | `android-linkerconfig-manual-review-required` |

## Test Plan

Static checks:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
python3 -m py_compile \
  scripts/revalidation/wifi_android_exec_namespace_probe.py \
  scripts/revalidation/wifi_linkerconfig_materialization_probe.py \
  scripts/revalidation/helper_deploy.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Device checks:

```bash
python3 scripts/revalidation/a90ctl.py version
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox sha256sum /cache/bin/a90_android_execns_probe
python3 scripts/revalidation/wifi_linkerconfig_materialization_probe.py probe \
  --allow-temp-namespace \
  --allow-linker-list \
  --allow-private-linkerconfig \
  --linkerconfig-mode minimal-vendor \
  --assume-yes
```

Postflight:

- `version` PASS.
- `status` PASS.
- `netservice status` PASS.
- `selftest verbose` PASS with `fail=0`.
- `/proc/mounts` has no leaked `/tmp/a90-v232-*` mounts.
- No new Wi-Fi interface activation, scan, connect, credential, DHCP, route, or
  DNS state is introduced.

## Acceptance

v232 is successful if it reaches one of these narrowed states:

- `android-linker-list-pass`;
- `android-linker-list-runtime-gap`;
- `android-linkerconfig-required`;
- `android-linkerconfig-crash-persists` with enough evidence to decide whether
  the next step is real Android linkerconfig capture, extra private mounts, or a
  different dry-run strategy.

v232 is not allowed to continue toward daemon start unless `linker64 --list`
passes or produces a concrete non-crash dependency result that is understood.

## Next-Step Candidates After v232

- If `android-linker-list-pass`: v233 controlled `cnss-daemon --help` or
  `start-only` preflight may be considered, still no scan/connect.
- If `android-linker-list-runtime-gap`: v233 missing library/materialization
  probe.
- If `android-linkerconfig-required`: v233 real Android linkerconfig capture
  from stock Android boot becomes mandatory.
- If `android-linkerconfig-crash-persists`: v233 should test whether additional
  private mounts such as `/dev/null`, `/dev/zero`, `/sys`, or property files are
  needed before any daemon work.
