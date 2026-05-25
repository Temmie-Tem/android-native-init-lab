# Native Init V840 Provider-first Prearmed Listener Plan

## Goal

V840 combines the two currently useful native lower-window signals:

- V700 provider-first CNSS retry after `vendor.qcom.PeripheralManager`
  registration is visible.
- V838 listener-only prearm that registers for `msm/modem/wlan_pd` before
  service `74` and holds through the post-`74` window.

The first success signal is WLAN-PD `UP`. WLFW/BDF/`wlan0` are recorded if they
appear, but scan/connect remains out of scope.

## Basis

- V833 Android positive-control proves the listener model can observe WLAN-PD
  `UP`.
- V838 proves lower-only listener timing is not the blocker: the listener was
  open before service `74` and stayed open after service `74` with no
  indication.
- V839 selects provider-first CNSS retry plus prearmed listener as the next
  narrow gate.
- Helper v130 already contains both the V700 provider-first mode and the
  listener-only mode, so no new device helper binary is required.

## Implementation

- Add `scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py`.
- Reuse helper v130 and deploy only if the remote helper hash is stale.
- Run the normal clean-DSP stock-v724 prerequisite and current V401/V490 prep.
- Monkeypatch the V700 companion command so a listener-only helper is started
  in the background before the provider-first helper runs.
- Collect the listener transcript from `/cache` after reboot cleanup.
- Parse listener timing against the provider-first dmesg delta.

## Allowed Live Actions

- Helper v130 deploy if stale.
- V641 clean-DSP one-shot arm and reboot.
- Read-only system mount and current SELinuxfs/policy prep.
- Firmware mounts and `subsys_modem` holder used by the lower proof.
- Bounded service-manager/vndservicemanager/PeripheralManager provider-first
  start-only path from V700.
- One fresh bounded `cnss-daemon` retry after provider registration.
- Listener-only QMI registration for `msm/modem/wlan_pd`.
- Runner-owned reboot cleanup.

## Hard Gates

- No Wi-Fi HAL, wificond, supplicant, hostapd, scan, connect, or link-up.
- No credentials, DHCP, route changes, or external ping.
- No `esoc0` open or hold.
- No sysfs subsystem state write.
- No `wlan.ko` load/unload.
- No boot image write, partition write, or custom kernel flash.

## Success Criteria

- V839 reference is present and selected V840.
- Local/remote helper v130 exposes provider-first and listener-only contracts.
- Clean-DSP and current V401/V490 prep pass.
- Provider-first order matches the V700 contract and CNSS retry starts after
  provider registration.
- Listener registration succeeds and service `74` is observed.
- Cleanup reboot returns to healthy v724.

## Decision Branches

| Result | Meaning | Next |
| --- | --- | --- |
| WLAN-PD `UP` | Provider-first path supplied the missing lower trigger | Observe WLFW/BDF/`wlan0` below HAL/connect |
| WLFW/BDF/`wlan0` without listener `UP` | Kernel/WLFW advanced but listener state disagrees | Classify listener state mismatch |
| Listener open through service `74` + `5s`, no indication | Provider-first still does not supply WLAN-PD state-up | Classify missing lower WLAN-PD trigger |
| Listener not open at service `74` | Prearm placement failed | Move listener earlier |

