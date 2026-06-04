# V1988 Lead-A Downrank and Modem-internal Re-anchor

## Summary

- Cycle: `V1988`
- Type: host-only re-anchor after user stop directive; no new device run.
- Decision: `v1988-lead-a-downrank-modem-internal-producer-gate`
- Label: `lead-a-downrank-modem-internal-producer-gate`
- Pass: `True`
- Scope: stop tuning Android `strace` attach timing and stop blind-retrying Android handoffs for a clean boot.

## Why Lead A Is Down-ranked

Lead A was "RIL DMS/NAS modem-init handshake triggers `wlan_pd`." Current evidence no longer supports keeping that as the primary blocker:

| run | result | RIL pre-UP send / attribution | clean-status impact |
| --- | --- | --- | --- |
| V1974 | normal Android, clean | explicit `rild` send events `0`; explicit `rild` DMS/NAS/WDS lookups `0`; pre-UP DMS lookup exists but anonymous | clean |
| V1978 | producer attribution retry | `rild-send=0`; pre-UP DMS lookup unresolved | rejected: pre-`wlan0` PCIe/MHI contamination |
| V1979 | strace+QRTR+attribution | `rild-send=0`; pre-UP DMS lookup attributed to `/system/vendor/bin/cnss-daemon -n -l` | rejected: pre-`wlan0` PCIe/MHI contamination |
| V1980 | V1979 retry | `rild-send=0`; same contaminated capture class | rejected |
| V1985 | fast-poll strace | post-UP RIL DMS/NAS decoded, but `rild_attached_before_wlanpd=False`; producer-window decoded RIL lead count `0` | rejected |
| V1986 | `pidof` fast attach | post-UP RIL DMS/NAS decoded, but `rild_attached_before_wlanpd=False`; producer-window decoded RIL lead count `0` | rejected |

The decisive pattern is not an attach-timing bug anymore:

- Four producer-side runs show explicit pre-UP `rild` send evidence remains `0`.
- The one attributed pre-UP DMS service-list edge points at `cnss-daemon`, not `rild` (V1979).
- Direct pre-`wlan_pd` ptrace/strace attempts perturb or select a non-clean Android path often enough that further tuning is low value.
- Post-UP RIL DMS/NAS traffic exists and decodes, but that does not prove RIL causes the earlier modem self-start of `msm/modem/wlan_pd`.

## Boot Non-determinism Finding

The clean baseline is still real but observer-sensitive:

| run | observer class | `wlan_pd` / `wlan0` | pre-`wlan0` external SDX50M/PCIe/MHI |
| --- | --- | --- | --- |
| V1982 | V1753 minimal Android-good firmware request observer | `wlan0` at `14.866239` | `0` |
| V1979/V1980 | tracefs uprobe + strace + QRTR matrix | `wlan0` ~`15s` | `30` |
| V1983 | V1753 + minimal `rild`/`pm-service` strace | `wlan0` `15.202059` | `17` |
| V1985 | fast-poll strace + QRTR | `wlan_pd` `44.676684`, `wlan0` `50.063131` | `10`; first PCIe/MHI `44.223907` |
| V1986 | `pidof` fast attach + QRTR | `wlan_pd` `44.619278`, `wlan0` `50.327863` | `10`; first PCIe/MHI `43.851645` |

Conclusion: the next loop must not rely on another Android producer handoff as the discriminator. Android-good is valid only when the gate explicitly proves the internal-modem-first baseline (`0` pre-`wlan0` PCIe/MHI/eSoC and normal ~15s `wlan0`). Otherwise the external SDX50M path contaminates the comparison.

## New Primary Gate

Re-anchor from "RIL sends the trigger" to:

> What internal-modem readiness state must be true before the modem ROOT-PD self-starts `msm/modem/wlan_pd` and requests `wlanmdsp.mbn`?

Known constraints:

- Native already starts pm-service enough to open `/dev/subsys_modem`.
- Native already reaches the CNSS WLFW worker wait path, but WLFW service 69 is absent.
- Native already has pd-mapper/service-locator visibility for `msm/modem/wlan_pd` instance 180.
- EFS/RFS/jsn, msg22, service74-only, pm-service/property/binder, and external SDX50M/eSoC/PCIe/GDSC have been refuted or marked off-path.
- Android pre-UP DMS lookup is not RIL-owned in the best-attributed run; it is `cnss-daemon`-owned.

## Next Unit

Run a native-side modem-internal readiness capture, not an Android producer retry:

1. Use the existing native test-boot companion route that brings up the internal modem, pm-service, pd-mapper, rmt_storage, tftp_server, cnss-daemon, and the clean-DSP/sibling sysmon companion.
2. Read-only observe the modem QRTR/service state after modem ONLINE and before any expected WLAN-PD state-up:
   - QRTR nameservice service set for core modem services: WDS `1`, DMS `2`, NAS `3`, service-registry/notifier, WLFW `69`.
   - service-notifier state for `msm/modem/wlan_pd` instance 180.
   - tqftpserv/rmt_storage requests for `wlanmdsp.mbn` and modem EFS access.
   - cnss-daemon local libqmi/service-list outcomes if available without pre-edge ptrace.
3. Label the native blocker:
   - `native-modem-core-services-missing`: DMS/NAS/WDS are not published/visible on the internal modem node, so the modem is not in the Android-equivalent ready state.
   - `native-core-services-present-wlfw-missing`: DMS/NAS/WDS are present but WLFW 69/`wlan_pd` never starts, so the blocker is deeper in modem ROOT-PD guest-PD policy/state.
   - `native-wlanmdsp-requested-but-no-wlan0`: modem self-starts WLAN-PD but downstream WLFW/BDF/HDD fails, allowing a downstream native Wi-Fi bring-up gate.

This directly targets the modem-internal producer wall and keeps the final goal path intact: only after native produces WLFW 69 and `wlan0` should Wi-Fi HAL/scan/connect/DHCP/ping be attempted.

## Safety

Host-only report. No new device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, sda29 remount-write, or partition write was performed for this V1988 re-anchor. Existing device state after the interrupted in-flight V1987 handoff was verified as native v724 with `selftest fail=0`, and V1987 script/report artifacts were removed uncommitted.
