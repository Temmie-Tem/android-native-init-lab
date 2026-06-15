# NATIVE_INIT_V2431_AUDIO_ACDB_MAGISK_STAGING_REDESIGN_2026-06-15

## Summary

V2431 is the host-only redesign after V2430 failed to directly stage a temporary
Magisk module under `/data/adb/modules`:

```text
mkdir: '/data/adb/modules': Permission denied
cp: /data/adb/modules/a90_audio_acdb_m1_v2429/module.prop: Permission denied
...
```

The direct `su -c` module placement path is not safe to retry blindly. The next
live unit should be a **read-only Android/Magisk access probe** that identifies
the real Magisk namespace/context and checks whether `su --mount-master` can see
and access `/data/adb/modules` before any new write is attempted.

Do **not** jump directly to `magisk --install-module`: it is the official module
installer interface, but installing a module is only safe in this project if
targeted cleanup/removal of the temporary module is proven first.

## Inputs

- V2430 live evidence:
  `docs/reports/NATIVE_INIT_V2430_AUDIO_ACDB_M1_MAGISK_MODULE_LIVE_2026-06-15.md`
- Private run dir:
  `workspace/private/runs/audio/v2430-acdb-m1-magisk-module-capture-20260615-124447`
- V2429 private module template:
  `workspace/private/builds/audio/v2429-acdb-m1-magisk-module/`

## Web / Source Basis

Official Magisk docs establish these facts:

- Magisk's secure directory is `/data/adb`, with module directories under
  `/data/adb/modules` and pending installs under `/data/adb/modules_update`.
  Source: <https://topjohnwu.github.io/Magisk/details.html>
- Module `service.sh` runs in Magisk late_start service mode; it is non-blocking
  and is the recommended mode for most scripts. General scripts can also live in
  `/data/adb/service.d`, but modules should not add general scripts during
  install. Source: <https://github.com/topjohnwu/Magisk/blob/master/docs/guides.md>
- Magisk modules are folders under `/data/adb/modules/$MODID`; module scripts are
  enabled only when the module is enabled. Source:
  <https://topjohnwu.github.io/Magisk/guides.html>
- The `magisk` tool has `--install-module ZIP`, and `su` has
  `-mm` / `--mount-master` to force the global mount namespace. Source:
  <https://topjohnwu.github.io/Magisk/tools.html>
- The Magisk installer implementation uses `/data/adb/modules_update` while
  installing in boot mode and later merges into `/data/adb/modules`; it also
  applies permissions and contexts. Source:
  <https://github.com/topjohnwu/Magisk/blob/master/scripts/util_functions.sh>

## Interpretation

V2430 proved:

1. Android ADB and Magisk root are reachable after checked Android handoff.
2. `/data/local/tmp` staging is writable.
3. APK install/uninstall works.
4. Direct `su -c` access to `/data/adb/modules` is not currently sufficient.

This strongly suggests the failed path is not "root unavailable"; it is one of:

- Magisk mount namespace mismatch: plain `su -c` is not in the namespace that can
  see or mutate Magisk secure module paths.
- SELinux/context mismatch: uid 0 alone is not enough for this path.
- Magisk-managed directory semantics: module writes are expected to go through
  Magisk's installer path so `modules_update`, labels, and generated state are
  consistent.

## Safety Constraint

The M1 module is still measurement-only, but `/data/adb/modules` is persistent
Android userdata state. A live path must therefore prove cleanup before it can be
accepted:

- no stale module directory after run;
- no stale `modules_update` directory after run;
- no `remove`/`disable` marker left behind;
- V2321 rollback and native `selftest fail=0` after cleanup.

Using `magisk --remove-modules` is **not** acceptable as a normal cleanup path
because the official tool removes all modules, not just the A90 temporary module.
It is an emergency recovery option only.

## Staged Redesign

### V2432 — read-only Magisk access probe

Purpose: classify why `/data/adb/modules` denied direct staging, without writing
anything under `/data/adb`.

Planned checked Android handoff:

1. Flash pinned Android boot through `native_init_flash.py`.
2. Verify Android boot-complete and `su -c id`.
3. Run read-only probes:

```sh
id
id -Z
command -v magisk
magisk -c
magisk -v
magisk --path
magisk --list
ls -ldZ /data /data/adb /data/adb/modules /data/adb/modules_update /data/adb/service.d 2>&1 || true
mount | grep -E ' /data|/data/adb|magisk' || true
su -mm -c 'id; id -Z; ls -ldZ /data/adb /data/adb/modules /data/adb/modules_update /data/adb/service.d 2>&1 || true; mount | grep -E " /data|/data/adb|magisk" || true'
```

4. Pull private text artifacts.
5. Roll back to V2321.

No writes, no module install, no playback, no calibration ioctl.

### V2433 — bounded namespace write probe only if V2432 shows a candidate path

Purpose: prove targeted create/remove cleanup before any module install.

Candidate command shape, only if V2432 supports it:

```sh
su -mm -c 'mkdir -p /data/adb/modules/a90_probe_v2433 && rmdir /data/adb/modules/a90_probe_v2433'
```

Abort if create or remove fails. Do not stage the real module in this unit.

### V2434 — direct-staging M1 retry only if V2433 passes

If `su -mm` targeted create/remove works, retry V2430's direct staging with
`su -mm -c` for `/data/adb/modules` operations, then:

1. reboot Android once;
2. launch the bounded AudioTrack stimulus;
3. pull artifacts;
4. remove the module and staging tree with the same proven namespace path;
5. rollback to V2321.

### Deferred — official installer path

Use `magisk --install-module` only if:

- direct `su -mm` create/remove cannot work;
- the install command exists on this Android image;
- targeted cleanup of the module installed through `modules_update` is proven;
- the live runner can verify no stale A90 module state before rollback.

This path needs a new exact gate because V2429/V2430 intentionally classified
`magisk --install-module` as forbidden for direct live use.

## Decision

The immediate next meaningful unit is V2432 read-only Magisk access probing. It
is cheaper and safer than another M1 live rerun, and it directly tests the likely
root cause exposed by V2430.

