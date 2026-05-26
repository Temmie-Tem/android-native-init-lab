# V963 Post-Provider Trigger Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| bounded live proof | `tmp/wifi/v963-post-provider-trigger-live/manifest.json` | `v963-post-provider-trigger-stall-cleaned` |
| classifier | `tmp/wifi/v964-v963-post-provider-trigger-classifier/manifest.json` | `v964-post-provider-trigger-stalls-in-sdx50m-reset` |

V963 ran helper `v160` with:

- `service_manager_order=after-mdm-helper-esoc-fd-with-pm-proxy`
- `subsys_trigger_gate=post-provider-no-wlfw`
- `cnss_surface_mode=full`

The post-provider gate reached the `/dev/subsys_esoc0` child open path. The
child stalled in the SDX50M reset/powerup path and required cleanup reboot.
Cleanup recovered native health.

## Evidence

- Gate readiness was observed once:
  `cnss_before_esoc.post_provider_no_wlfw_gate_ready=1`.
- `/dev/subsys_esoc0` open was attempted:
  `cnss_before_esoc.subsys_esoc0_open_attempted=1`.
- Trigger child captured blocker evidence:
  `cnss_before_esoc.subsys_trigger.blocker_capture_attempted=1`.
- Trigger child wchan:
  `sdx50m_toggle_soft_reset`.
- Kernel stack included:
  `sdx50m_toggle_soft_reset`, `mdm4x_do_first_power_on`,
  `mdm_subsys_powerup`, `__subsystem_get`, and `subsys_device_open`.
- Cleanup reboot reached `BOOT OK` and `selftest fail=0`.

Note: a later plan-only check overwrote the live `manifest.json`; it was
reconstructed from the retained raw live evidence under
`tmp/wifi/v963-post-provider-trigger-live/native/`. The raw helper transcript
and reboot cleanup files are the authoritative V963 evidence.

## Guardrails

- `pm_proxy_helper` was not started.
- Wi-Fi HAL was not started.
- No scan/connect, credentials, DHCP/routes, or external ping was executed.
- No eSoC notify or boot-done was issued.
- No GPIO/sysfs/debugfs write, boot image write, partition write, or firmware
  mutation was executed.

## Interpretation

V963 removes the previous ambiguity around whether the existing WLFW gate was
circular. After provider stack repair and full CNSS surface collection, opening
`/dev/subsys_esoc0` does not publish WLFW; it blocks in the SDX50M reset path.

The remaining blocker is therefore below CNSS/userspace provider lifecycle:
the native path lacks whatever Android does around SDX50M GPIO/PMIC/IRQ timing
before or during `sdx50m_toggle_soft_reset`.

## Next

Compare Android boot evidence against native for the SDX50M soft-reset path:
GPIO135/AP2MDM status, PMIC GPIO9 deassert, GPIO142/MDM2AP status IRQ, and
related eSoC/MDM dmesg timing.
