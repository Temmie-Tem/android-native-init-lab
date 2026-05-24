# Native Init V735 Current CNSS-only Observer Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py`
- evidence target: `tmp/wifi/v735-current-cnss-only-observer/`

## Goal

Replay the closest safe current-build gate after V734:

```text
firmware mounts
  -> subsys_modem holder
  -> lower companions
  -> cnss_diag + cnss-daemon only
  -> observe service publication, MHI/QCA6390, WLFW/service 69, BDF, wlan0
```

This incorporates the SM8250 CNSS2/PCIe correction from V726/V727:
service-notifier `180/74` is useful side evidence, but the actionable Wi-Fi
path still requires modem readiness, static `wlan` surface, MHI/QCA6390
progression, and WLFW service `69`.

## Scope

Allowed:

1. mount firmware partitions read-only in the bounded proof window;
2. open only `subsys_modem` through the established holder path;
3. start `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`, `cnss_diag`, and
   `cnss-daemon`;
4. perform QRTR nameservice readback for WLFW service `69` without QMI payloads;
5. reboot for cleanup and verify native health.

Forbidden:

1. `esoc0`, subsystem state writes, DSP boot-node writes, module load/unload;
2. service-manager, hwservicemanager, vndservicemanager;
3. Wi-Fi HAL, wificond, supplicant, hostapd;
4. scan/connect, credentials, DHCP, route changes, and external ping.

## Success Criteria

| condition | expected |
| --- | --- |
| current prerequisites | V401 and V490 pass on the same boot |
| modem holder | `mss` reaches `ONLINE`, QRTR RX is observed |
| helper contract | order is `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| guardrails | service-manager/HAL/connect/external ping remain `0` |
| readback guard | service `69` readback sends nameservice lookup only, QMI payloads `0` |
| cleanup | reboot returns to healthy native init |

## Interpretation Rules

| outcome | next action |
| --- | --- |
| service `69`, WLFW, BDF, or `wlan0` appears | capture firmware-ready/interface state before any HAL/connect |
| MHI/QCA6390 appears but WLFW stays absent | classify MHI-to-WLFW firmware/runtime gap |
| service publication appears but no MHI/WLFW | classify WLAN-PD/service-publication-to-MHI gap |
| only QRTR TX/sysmon appears | continue lower modem/WLAN-PD publication analysis |
| kernel warning appears | stop and review dmesg before repeating |

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py

python3 scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py \
  --out-dir tmp/wifi/v735-current-cnss-only-observer-plan plan

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v735-v401-current-run \
  --approval-phrase 'approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v735-v490-current-run \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --helper-sha256 547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89 \
  --approval-phrase 'approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py \
  --out-dir tmp/wifi/v735-current-cnss-only-observer run
```
