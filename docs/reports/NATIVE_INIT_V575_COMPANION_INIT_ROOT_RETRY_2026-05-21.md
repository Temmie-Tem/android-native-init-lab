# Native Init V575 Companion Init-root Retry Report

Date: `2026-05-21`

## Goal

Repair the V570/V534 `rmt_storage` and `tftp_server` start contract by matching
Android init semantics: start both services as root in their vendor SELinux
domains, then let each daemon perform its own runtime identity drop.

## Result

- Decision: `v534-companion-start-only-no-fw-marker`
- Pass: `True`
- Reason: all companion children were observable and cleaned up, but no
  QRTR/QMI/WLFW/BDF/FW-ready marker appeared.
- Helper: `a90_android_execns_probe v95`
- Helper SHA-256:
  `d59596a0e951d05db9b4ed7f2099f1043d463f4e3dd1dc5a8fa40887e210f45d`
- Evidence:
  - `tmp/wifi/v575-execns-helper-v95-deploy-preflight`
  - `tmp/wifi/v575-rmt-storage-init-root-start-only-run`
  - `tmp/wifi/v575-companion-init-root-start-only-run`
- Wi-Fi bring-up: not executed

## Scope Confirmation

- V575 deployed only the static execns helper v95 to `/cache/bin`.
- The live proofs started only bounded companion windows.
- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd, scan,
  connect, link-up, credential use, DHCP, routing, external ping, reboot, boot
  partition write, Android partition write, firmware mutation, rfkill write, or
  driver bind/unbind was executed.
- Post-run process cleanup remained safe.
- Post-run network check found no Wi-Fi network device.

## Validation

```text
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v95_deploy_preflight.py \
  scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  scripts/revalidation/native_wifi_companion_start_only_v534.py \
  scripts/revalidation/native_wifi_rmt_storage_start_only_v533.py \
  scripts/revalidation/native_property_runtime_live_v535.py
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v575-a90_android_execns_probe-v95/a90_android_execns_probe
python3 scripts/revalidation/wifi_execns_helper_v95_deploy_preflight.py \
  --transfer-method serial preflight
python3 scripts/revalidation/wifi_execns_helper_v95_deploy_preflight.py \
  --transfer-method serial --serial-chunk-size 1400 \
  --approval-phrase "approve v575 deploy execns helper v95 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_rmt_storage_start_only_v533.py \
  --out-dir tmp/wifi/v575-rmt-storage-init-root-start-only-run \
  --v490-manifest tmp/wifi/v575-v490-policy-load-run-after-layout/manifest.json \
  --approval-phrase "approve v533 rmt-storage start-only proof only; no service-manager, no CNSS daemon, no Wi-Fi HAL start, no scan/connect/link-up and no external ping" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_companion_start_only_v534.py \
  --out-dir tmp/wifi/v575-companion-init-root-start-only-run \
  --v490-manifest tmp/wifi/v575-v490-policy-load-run-after-layout/manifest.json \
  --max-runtime-sec 30 \
  --approval-phrase "approve v534 companion start-only proof only; no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping" \
  --apply --assume-yes run
```

## Contract Repair

V575 corrects the V94/V570 interpretation error:

1. Android init declares `vendor.rmt_storage` and `vendor.tftp_server` as
   root-started services.
2. Android-observed non-root identities are runtime identities after daemon
   self-drop, not identities that init applies before `execve`.
3. V94 pre-dropped `rmt_storage` to its observed runtime UID/GID/groups before
   `execve`, which caused the V575 pre-repair rmt-only proof to exit before the
   observe window.
4. V95 starts both `rmt_storage` and `tftp_server` as root with the correct
   vendor SELinux exec contexts and no pre-supplied runtime groups/caps.

The V95 rmt-only proof now passes:

```text
decision=v533-rmt-storage-window-pass
rmt_storage_start.result=rmt-window-pass
wifi_hal_composite_child.rmt_storage.expected.contract=rmt_storage-init-root
wifi_hal_composite_child.rmt_storage.preexec_status=pass
wifi_hal_composite_child.rmt_storage.selinux.exec=u:r:vendor_rmt_storage:s0
```

The V95 companion proof starts all six companion children and cleans them up:

| child | observable | postflight safe | start order |
|---|---:|---:|---:|
| `qrtr-ns` | `1` | `1` | `1` |
| `rmt_storage` | `1` | `1` | `2` |
| `tftp_server` | `1` | `1` | `3` |
| `pd-mapper` | `1` | `1` | `4` |
| `cnss_diag` | `1` | `1` | `5` |
| `cnss-daemon` | `1` | `1` | `6` |

## Remaining Blocker

The companion window is now cleaner than V570/V534, but firmware readiness is
still absent:

```text
qmi_server_connected=0
qrtr_modem_readiness=0
bdf_regdb=0
bdf_bdwlan=0
wlan_fw_ready=0
wlan0_event=0
```

`cnss_diag` and `cnss-daemon` still reach netlink-heavy activity, but no modem
QRTR/QMI/BDF/WLFW marker appears. `/proc/net/qrtr` is also absent in both the
before and after snapshots.

## Interpretation

The root-start contract mismatch was real and is now fixed. It was a necessary
repair, not the final Wi-Fi blocker.

The remaining blocker is earlier than scan/connect and still before a useful
`qcwlanstate` retry. The strongest current suspects are:

1. QRTR/modem readiness is not entering the Android-equivalent state in native
   init.
2. The QRTR namespace path may require a boot-time or modem-state dependency
   that cannot be reproduced by a late interactive companion window alone.
3. A missing Android companion dependency may still be required before
   `cnss-daemon` can reach WLFW/QMI and BDF fetch.

## Next Gate

Do not retry scan/connect yet. The next loop should focus on a read-only or
bounded classifier around QRTR/modem readiness after the V95 contract repair:

1. compare Android and native `/proc/net`, QRTR socket, service-notifier,
   subsystem, and dmesg surfaces again with V95 as the baseline;
2. classify why `/proc/net/qrtr` is absent even though `AF_QIPCRTR` is
   registered;
3. only after QRTR/QMI/BDF or `wlan0` evidence appears, retry `qcwlanstate`,
   HAL start, scan/connect, DHCP, and external ping.

Wi-Fi objective remains incomplete until native init connects to Wi-Fi and
external ping passes.
