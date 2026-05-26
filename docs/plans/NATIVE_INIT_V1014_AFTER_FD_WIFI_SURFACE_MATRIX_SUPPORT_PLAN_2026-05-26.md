# V1014 After-Fd Wi-Fi Surface Matrix Support Plan

- date: `2026-05-26`
- type: source/build-only helper support
- selected after: V1013 WLFW gap classifier
- helper target: `a90_android_execns_probe v172`

## Objective

Add helper support for a bounded matrix order that preserves the proven
`mdm_helper` `/dev/esoc-0` fd predicate before starting Android upper Wi-Fi
surface actors.

The new order is:

```text
after-mdm-helper-esoc-fd-with-wifi-surface
```

It extends the existing
`wifi-companion-mdm-helper-cnss-service-manager-matrix` mode rather than adding
a separate mode.

## Rationale

V1013 established the split:

- V1012: `mdm_helper` fd, service-manager, and CNSS were present, but WLFW was
  absent.
- V1008: Wi-Fi HAL, `wificond`, and CNSS were present, but the `mdm_helper` fd
  predicate was absent.

Therefore the smallest next change is a source/build-only helper order that
combines both halves:

1. start property shim, `per_mgr_light`, and `mdm_helper`
2. wait until `mdm_helper` opens `/dev/esoc-0`
3. start service-manager trio
4. start Wi-Fi HAL legacy, Wi-Fi HAL ext, and `wificond`
5. start CNSS actors
6. observe WLFW only

## Hard Gates

- source/build-only
- no deploy
- no bridge/device command
- no actor, daemon, service-manager, Wi-Fi HAL, or `wificond` start
- no `/dev/esoc-0`, `/dev/subsys_esoc0`, eSoC ioctl, notify, or BOOT_DONE live use
- no `IWifi.start`, `qcwlanstate`, scan/connect, credential use, DHCP/route, or external ping
- no boot image, partition, firmware, GPIO, sysfs, or debugfs mutation

## Implementation

Modify:

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
```

Add verifier:

```text
scripts/revalidation/native_wifi_after_fd_wifi_surface_matrix_support_v1014.py
```

The helper should:

- bump `EXECNS_VERSION` to `a90_android_execns_probe v172`
- accept `--service-manager-order after-mdm-helper-esoc-fd-with-wifi-surface`
- expand the matrix child set to include Wi-Fi HAL legacy/ext and `wificond`
- gate CNSS start on the upper Wi-Fi surface actors when this order is selected
- keep scan/connect and controller eSoC actions explicitly disabled

## Success Criteria

- Static helper build succeeds.
- Build artifact is statically linked.
- Strings confirm `v172`, the new order token, and no scan/connect expansion
  markers.
- Verifier decision is
  `v1014-after-fd-wifi-surface-matrix-support-pass`.

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_after_fd_wifi_surface_matrix_support_v1014.py
python3 scripts/revalidation/native_wifi_after_fd_wifi_surface_matrix_support_v1014.py
git diff --check
```

Then run a limited secret scan over staged files before commit.
