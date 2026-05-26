# V1012 after-fd CNSS Service-Manager Matrix Plan

## Goal

Run the existing CNSS/service-manager matrix mode with helper `v171`, preserving
the V1010 fd-positive lower state before adding service-manager and CNSS actors.

## Scope

1. Use helper `v171`.
2. Force `--android-selinux-context-mode service-defaults`.
3. Use `service_manager_order=after-mdm-helper-esoc-fd`.
4. Start reduced lower actors first:
   - property shim;
   - `per_mgr_light`;
   - `mdm_helper`.
5. Add service-manager/CNSS only after `mdm_helper` has opened `/dev/esoc-0`.
6. Open `/dev/subsys_esoc0` only if the existing WLFW precondition gate becomes
   true.

## Guardrails

Allowed:

- `mountsystem ro`;
- `selinuxfs` mount/umount;
- private property shim;
- `per_mgr_light`;
- `mdm_helper`;
- service-manager trio only in the selected after-fd matrix order;
- `cnss_diag`;
- `cnss-daemon -n -l`;
- WLFW-gated `/dev/subsys_esoc0` child open;
- cleanup reboot only if needed.

Forbidden:

- Wi-Fi HAL;
- `wificond`;
- `qcwlanstate`;
- `IWifi.start`;
- Wi-Fi scan/connect/link-up;
- credential use;
- DHCP/routes;
- external ping;
- controller eSoC notify or BOOT_DONE spoofing;
- boot image, partition, firmware, GPIO, sysfs, or debugfs mutation.

## Success Criteria

V1012 passes if it classifies one bounded outcome without forbidden actions:

- WLFW precondition appears and trigger evidence is captured;
- WLFW precondition remains absent but `mdm_helper` fd and CNSS/service-manager
  actor state are captured;
- setup failure is safely classified with cleanup evidence.

This is still below final Wi-Fi connect/ping. It is the next gate toward WLFW
publication without using credentials or enabling Wi-Fi networking.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_after_fd_cnss_matrix_v1012.py
python3 scripts/revalidation/native_wifi_after_fd_cnss_matrix_v1012.py \
  --out-dir tmp/wifi/v1012-after-fd-cnss-service-manager-matrix-plan \
  plan
```
