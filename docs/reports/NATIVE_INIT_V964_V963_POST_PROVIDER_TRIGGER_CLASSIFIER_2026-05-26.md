# V964 V963 Post-Provider Trigger Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v964-v963-post-provider-trigger-classifier/manifest.json` | `v964-post-provider-trigger-stalls-in-sdx50m-reset` |

V964 classifies V963 evidence as a lower SDX50M reset/powerup blocker.

## Checks

All classifier checks passed:

- V963 helper was `a90_android_execns_probe v160`.
- `post-provider-no-wlfw` gate was selected.
- `pm-proxy` matrix order was selected.
- Provider stack was started.
- The new gate became ready at least once.
- WLFW remained absent at trigger time.
- `/dev/subsys_esoc0` open was attempted.
- Trigger child stalled and captured wchan/stack evidence.
- wchan was `sdx50m_toggle_soft_reset`.
- stack contained `mdm_subsys_powerup`, `__subsystem_get`, and
  `subsys_device_open`.
- kernel dmesg logged `__subsystem_get: esoc0 count:0`.
- cleanup reboot was healthy.
- no forbidden action or Wi-Fi bring-up occurred.

## Conclusion

Provider lifecycle, service-manager availability, `pm-service`, `pm-proxy`,
`mdm_helper` visibility, CNSS diag/daemon startup, and `cld80211` netlink are no
longer the primary blocker for this path.

The active blocker is the SDX50M bring-up handshake reached through
`/dev/subsys_esoc0`. The child blocks in `sdx50m_toggle_soft_reset`, then the
cleanup reboot restores the device. Another blind trigger retry is not useful
until Android-vs-native GPIO/IRQ/PMIC timing is compared.

## Next

V965 should capture or classify Android reference timing for:

- AP2MDM status GPIO high timing
- PMIC reset deassert timing
- MDM2AP status IRQ transition
- `mdm_helper`/eSoC dmesg sequence
- PCIe/MHI readiness markers near SDX50M powerup
