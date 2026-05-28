# V1190 PM Observer Policy Load Plan

- **cycle**: V1190
- **date**: 2026-05-29
- **type**: host-only (no device contact)
- **prior**: V1189 live FAIL — `per_mgr_domain_still_kernel` with helper v224 setcurrent fix

## V1189 Evidence

| metric | value |
|---|---|
| `per_mgr_domain_value` | `kernel` |
| `pre_drain_attr_captured` | `1` |
| `selinux_current.ok` | filtered (not visible) |
| `gate_result` | `timeout` |
| `gate_elapsed_ms` | `5185ms` |

## Root Cause Analysis

### V1188 fix was based on wrong assumption

V1188 assumed: "native init ensures permissive mode via V490 policy load" when the PM
trigger observer runs. This is false.

**Actual state**: No SELinux policy is loaded on native v724 boot. Confirmed:

```
$ a90ctl run /cache/bin/toybox cat /proc/self/attr/current
kernel
```

Every process is in `kernel` domain (initial context = no policy loaded).

### Why setcurrent (v224) failed

1. `apply_android_current_selinux_context_for_pm()` calls
   `write_selinux_attr("current", "u:r:vendor_per_mgr:s0")`
2. Internally: `security_context_to_sid("u:r:vendor_per_mgr:s0", ...)` → **EINVAL**
   because no policy is loaded, so the context string cannot be resolved to a SID
3. Write fails silently (non-fatal branch in the code)
4. exec proceeds from `kernel` domain
5. per_mgr runs in `kernel` domain

The same failure applies to `write_selinux_attr("exec", ...)` (V1187 finding) —
both fail because there is no policy loaded.

### Why no policy is loaded

The V1183/V1189 PM trigger observer chain (V1106 → V1113 → V1139 → V1143 →
V1165 → V1177 → V1180 → V1183 → V1189) only:
1. Mounts selinuxfs (Python script)
2. Mounts vendor/tracefs (Python script)
3. Runs the helper PM observer mode

It does NOT write to `/sys/fs/selinux/load`. The V490 policy load (`sepolicy-load-proof`
mode) is a separate standalone helper invocation that is NOT part of this chain.

## Correct Fix

Load the precompiled Android SELinux policy BEFORE spawning per_mgr. The
`/vendor/etc/selinux/precompiled_sepolicy` is already available in the helper's
vendor chroot (vendor is mounted from sda29).

Steps:
1. Open `<paths.root>/vendor/etc/selinux/precompiled_sepolicy`
2. Write its contents to `/sys/fs/selinux/load` (already computed as `paths.sys_fs_selinux_load`)
3. Write `0` to `/sys/fs/selinux/enforce` (permissive mode)
4. The existing `write_selinux_attr("exec", "u:r:vendor_per_mgr:s0")` in
   `apply_android_exec_selinux_context_if_requested()` now SUCCEEDS
5. exec from `kernel` domain with `attr/exec = vendor_per_mgr`:
   - Kernel checks `allow kernel vendor_per_mgr:process transition`
   - In permissive mode: AVC denial is logged but exec transition PROCEEDS
   - per_mgr lands in `vendor_per_mgr` domain

Note: `allow kernel vendor_per_mgr:process transition` may or may not exist in the
stock precompiled_sepolicy. In permissive mode, a DENIED transition still PROCEEDS
(the AVC is logged but `avc_has_perm()` returns 0). So the policy load + permissive
mode is sufficient regardless of whether this specific rule exists.

The setcurrent approach (v224) remains in the code as defense-in-depth — once a
policy is loaded and `vendor_per_mgr` SID is resolvable, the `attr/current` write
will also succeed.

## Change Plan for Helper v225

**Flag**: `--pm-observer-load-precompiled-policy`
**Config field**: `pm_observer_load_precompiled_policy`

**Function added**: `load_precompiled_policy_for_pm_observer()`
- Reads vendor's `precompiled_sepolicy` via `write_file_once_to_fd()`
- Writes to `/sys/fs/selinux/load`
- Writes `0` to `/sys/fs/selinux/enforce`
- Emits `pm_service_trigger_observer.policy_load.*` fields

**Call site**: In `run_wifi_companion_pm_service_trigger_observer_guarded()`,
immediately before `pm_service_trigger_observer.allowed=1` output (after the
`allow_pm_service_trigger_observer` check).

**SHA256**: `cfe70c8879ab956670d8502ffd0d51c7544c26dd2a641db12c29129613d40664`

## V1191 Next Live Gate

- Deploy helper v225
- Run V1191 live — same setup as V1189 with added `--pm-observer-load-precompiled-policy`
- Validate: `per_mgr_domain_value='u:r:vendor_per_mgr:s0'`
- If domain is now `vendor_per_mgr`: check whether vndservice gate opens

Scripts: `wifi_execns_helper_v225_deploy_preflight.py`, `native_wifi_pm_per_mgr_policy_load_v1191.py`
