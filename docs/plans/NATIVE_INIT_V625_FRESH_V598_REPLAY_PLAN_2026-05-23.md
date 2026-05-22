# Native Init V625 Fresh V598-Class Replay Plan

- date: `2026-05-23 KST`
- cycle: `v625`
- scope: bounded live replay from a fresh native boot
- target: reproduce the V598 warning-free partial `service-notifier` positive
  under current evidence, without advancing to Wi-Fi HAL, scan, connect, DHCP,
  routes, credentials, or external ping

## Background

V624 classified V598 as the only safe partial native positive:

```text
subsys_modem holder
  -> qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss-daemon
  -> service-notifier 180
  -> no direct DSP boot-node writes
  -> no kernel warning
```

V606/V608 did not reproduce that positive, while V619's broader DSP boot-node
path produced `pm_qos_add_request` warnings. V625 therefore replays the V598
class from a fresh native boot and captures the exact lower-QMI boundary.

## Preconditions

1. Boot native init `0.9.61 (v319)` and hide the auto menu before scripted
   commands.
2. Mount Android system read-only with `mountsystem ro`.
3. Ensure `/cache/bin/a90_android_execns_probe` is helper v100 with sha256
   `916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29`.
4. Mount SELinuxfs through the bounded V401 executor.
5. Load Android SELinux policy with V490 after the current boot.
6. Confirm V598 preflight passes with the current V490 manifest.

## Guardrails

V625 must not:

- write ADSP/CDSP/SLPI DSP boot nodes;
- open `esoc0`;
- start service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd, or scan
  tooling;
- send QMI payloads;
- scan/connect/link-up, use credentials, run DHCP, alter routes, or ping
  externally.

The only live daemon window is the V598-class companion replay behind the
`subsys_modem` holder. Cleanup is reboot-based.

## Success Criteria

V625 passes if it:

- runs from a fresh native boot with fresh V401/V490 preconditions;
- executes V598-class holder/readback and reboot cleanup;
- records QRTR RX/TX, modem `sysmon-qmi`, service-notifier, WLFW readback, BDF,
  WLAN-PD, `wlan0`, and kernel-warning counts;
- leaves post-reboot native health at `fail=0`;
- keeps Wi-Fi bring-up and external ping unexecuted.

If `service-notifier 180` returns, the next gate should focus on why
`service-notifier 74`/WLAN-PD/WLFW service `69` do not publish. If it does not
return, classify the missing current-boot precondition before any HAL or connect
attempt.
