# Native Init V725 Service-Locator to Modem/QMI Gap Plan

- date: `2026-05-24 KST`
- cycle: `v725`
- runner: `scripts/revalidation/native_wifi_servloc_modem_gap_v725.py`
- evidence target: `tmp/wifi/v725-servloc-modem-gap/`
- gate: host-only Android/native lower Wi-Fi prerequisite classifier

## Goal

V724 moved lower companion startup into the post-ACM boot window and removed the
old service-locator timeout. It still did not publish service `180/74`.

V725 fixes the analysis target before any new live mutation:

```text
service-locator ready
  but no QRTR RX/TX
  but no sysmon modem/esoc0
  but mss/mdm3 still OFFLINING
  but no rpmsg devices
  therefore no service 180/74 publication
```

The model is re-centered on the SM8250/CNSS2 path. Userspace QRTR visibility of
service `180` and kernel CNSS2/SERVREG listener indication are treated as
separate edges.

## Scope

Allowed:

- read existing Android V612/V622 manifests;
- read existing native V724 boot-window evidence;
- optionally read a local, already-captured V725 read-only spot-check bundle;
- write a private host-side manifest and Markdown summary.

Blocked:

- device commands from the classifier;
- daemon starts;
- CNSS daemon retry;
- service-manager start;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up;
- credential use;
- DHCP, route changes, and external ping;
- sysfs/debugfs writes;
- `esoc0` open/hold;
- boot image or partition writes.

## Input Evidence

| source | purpose |
| --- | --- |
| Android V622 | timing from QRTR RX/TX through sysmon, service `180/74`, WLAN-PD, WLFW, BDF, fw-ready, and `wlan0` |
| Android V612/V611 | Android `mss`/`mdm3` ONLINE and QIPCRTR/RPMSG lower surface |
| Native V724 | post-ACM lower companion starts early enough for service-locator but stalls before service `180/74` |
| V725 live spot-check | corroborates current v724 boot still has `mss`/`mdm3` OFFLINING and QIPCRTR present |

## Success Criteria

V725 passes if:

- Android evidence has QRTR RX/TX, sysmon, service-locator, service `180/74`,
  WLAN-PD, WLFW/QMI, BDF, fw-ready, and `wlan0`;
- Android lower subsystem state has `mss=ONLINE` and `mdm3=ONLINE`;
- native V724 has service-locator connected and no `servloc` timeout;
- native V724 still has no QRTR RX/TX, no sysmon, `mss/mdm3=OFFLINING`, zero
  rpmsg devices, and zero service `180/74`;
- no classifier guardrail is crossed.

Decision label:

```text
v725-servloc-live-modem-qmi-readiness-gap-classified
```

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_servloc_modem_gap_v725.py

python3 scripts/revalidation/native_wifi_servloc_modem_gap_v725.py \
  --out-dir tmp/wifi/v725-servloc-modem-gap-plan plan

python3 scripts/revalidation/native_wifi_servloc_modem_gap_v725.py \
  --out-dir tmp/wifi/v725-servloc-modem-gap run

git diff --check
```

## Next Gate

If V725 classifies the gap, V726 should be a bounded post-ACM proof that combines
the safe modem firmware/subsys-modem holder path with the lower companion:

```text
firmware mounts + subsys_modem hold only
  -> qrtr-ns/pd-mapper/rmt_storage/tftp_server
  -> observe QRTR RX/TX, sysmon, service 180/74
```

V726 must not touch `esoc0`, start CNSS daemon, start service-manager, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, or external
ping.
