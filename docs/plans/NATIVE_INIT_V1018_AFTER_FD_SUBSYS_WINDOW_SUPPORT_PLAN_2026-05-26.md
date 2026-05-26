# V1018 After-Fd Subsystem Window Support Plan

- date: `2026-05-26`
- type: source/build-only helper support
- selected after: V1017 lower-gap classifier
- helper target: `a90_android_execns_probe v173`

## Objective

Add a helper order that keeps the V1016 fd-positive upper-surface stack, then
opens `/dev/subsys_esoc0` in a bounded child even if WLFW has not appeared yet.

New order:

```text
after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window
```

New gate:

```text
post-upper-surface-no-wlfw
```

## Rationale

V1017 selected this route because V1016 proved:

- `mdm_helper` `/dev/esoc-0` fd predicate
- service-manager trio
- Wi-Fi HAL legacy/ext
- `wificond`
- `cnss_diag`
- `cnss-daemon`

but WLFW remained absent and the helper never opened `/dev/subsys_esoc0`.

Android dmesg places `/dev/subsys_esoc0` get in the same narrow timing window
as `cnss-daemon wlfw_start`, so a WLFW-precondition gate can be circular.

## Implementation

Modify:

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
```

Add verifier:

```text
scripts/revalidation/native_wifi_after_fd_subsys_window_support_v1018.py
```

The helper should:

- bump `EXECNS_VERSION` to `a90_android_execns_probe v173`
- accept `--service-manager-order after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window`
- accept `--subsys-trigger-gate post-upper-surface-no-wlfw`
- require that gate to use the new order
- preserve service-manager, Wi-Fi HAL, `wificond`, and CNSS ordering
- start the `/dev/subsys_esoc0` child only after:
  - `mdm_helper` fd predicate
  - service-manager trio
  - Wi-Fi HAL legacy/ext
  - `wificond`
  - `cnss_diag`
  - `cnss-daemon`
  - at least one WLFW poll without WLFW
- keep scan/connect and credentials forbidden

## Hard Gates

- source/build-only
- no deploy
- no device command
- no daemon live start
- no live `/dev/esoc-0` or `/dev/subsys_esoc0` open
- no raw eSoC controller ioctl
- no GPIO/sysfs/debugfs write
- no `IWifi.start`
- no `qcwlanstate` write
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no boot image, partition, or firmware write

## Success Criteria

- static helper build succeeds
- build artifact is statically linked
- strings expose helper `v173`, the new order, and the new gate
- verifier decision is:

```text
v1018-after-fd-subsys-window-support-pass
```

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_after_fd_subsys_window_support_v1018.py
python3 scripts/revalidation/native_wifi_after_fd_subsys_window_support_v1018.py
git diff --check
```
