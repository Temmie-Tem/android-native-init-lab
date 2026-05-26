# V1039 PM Proxy Context Parity Support Plan

- date: `2026-05-26`
- type: source/build-only helper support
- selected after: V1038 PM fd gap after domain proof

## Objective

Repair the concrete Android/native PM actor parity gap identified by V1038
before any further live PM full-contract retry.

V1037 proved PM actor SELinux runtime-domain guard can pass, but the fd
contract still failed: neither `pm_proxy_helper` nor `pm-service` held
`/dev/subsys_modem`. V1038 then found one remaining source-level mismatch:
Android runs `/vendor/bin/pm-proxy` as `u:r:vendor_per_proxy:s0`, while helper
`v176` still mapped it to `u:r:vendor_per_mgr:s0`.

## Changes

1. Bump `a90_android_execns_probe` to helper `v177`.
2. Keep `/vendor/bin/pm-service` mapped to `u:r:vendor_per_mgr:s0`.
3. Map `/vendor/bin/pm-proxy` to `u:r:vendor_per_proxy:s0`.
4. Preserve the existing PM SELinux domain allowlist and PM full-contract order.
5. Add focused PM full-contract failure capture before cleanup:
   - `pm_proxy_helper` fd links and stall snapshot;
   - `pm-service` fd links and stall snapshot;
   - summary key `cnss_before_esoc.pm_full_contract_gap_snapshot_captured`.

## Hard Gates

- Source/build-only in this unit.
- No device command, deploy, actor start, daemon start, Wi-Fi HAL,
  scan/connect/link-up, credentials, DHCP/routes, external ping, boot image
  write, partition write, firmware mutation, GPIO/sysfs/debugfs write, eSoC
  ioctl, or live `/dev/subsys_esoc0` open.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_proxy_context_parity_support_v1039.py
python3 scripts/revalidation/native_wifi_pm_proxy_context_parity_support_v1039.py
git diff --check
```

Verifier requirements:

- helper source reports `a90_android_execns_probe v177`;
- `/vendor/bin/pm-service` maps to `u:r:vendor_per_mgr:s0`;
- `/vendor/bin/pm-proxy` maps to `u:r:vendor_per_proxy:s0`;
- PM contexts remain in source/strings;
- PM full-contract mode remains present;
- focused gap snapshot labels appear in source/strings;
- artifact builds as static AArch64.

## Success Criteria

- V1039 verifier passes.
- Static helper artifact is produced under
  `tmp/wifi/v1039-execns-helper-v177-build/a90_android_execns_probe`.
- No live/device action is executed.

## Next

If V1039 passes, V1040 should be deploy-only for helper `v177`. The next live
unit after deploy should rerun the bounded PM full-contract proof and inspect
whether the corrected `pm-proxy` domain plus focused fd/wchan capture moves the
blocker toward `/dev/subsys_modem` fd formation.
