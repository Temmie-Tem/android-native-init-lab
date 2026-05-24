# Native Init V724 QRTR/Service-Locator Boot Proof Live Report

- date: `2026-05-24 KST`
- boot artifact: `A90 Linux init 0.9.68 (v724)`
- builder: `scripts/revalidation/build_native_init_boot_v724.py`
- disabled-smoke evidence: `tmp/wifi/v724-disabled-smoke-20260524-122416/`
- armed evidence: `tmp/wifi/v724-armed-boot-proof-20260524-122741/`
- latest pointer: `tmp/wifi/latest-v724-armed-boot-proof.txt`
- decision: `v724-servloc-connected-no-wlanpd-after-timeout-window`
- status: `pass`

## Scope Result

V724 implemented a disabled-by-default post-ACM boot hook. The armed run:

- consumed `/cache/native-init-qrtr-servloc-boot-v724`;
- started only `qrtr-ns`, `pd-mapper`, `rmt_storage`, and `tftp_server`;
- returned PID1 to shell immediately after spawning the helper;
- waited past the previous `servloc` timeout window before final dmesg capture;
- did not start CNSS daemon, service-manager, Wi-Fi HAL, `wificond`,
  scan/connect/link-up, DHCP, routes, credentials, or external ping.

## Build and Flash Evidence

Local build passed marker validation:

| artifact | sha256 |
| --- | --- |
| `stage3/linux_init/init_v724` | `c33ba75518f36fe2da426a0dd99542cd0c619aa6d5e30e9a8c3e1063b248f22e` |
| `stage3/ramdisk_v724.cpio` | `abc5e3a135f67c0559eae4688dcb2b21ffd1f52ddac4e87239d3894efe22f846` |
| `stage3/boot_linux_v724.img` | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |

Disabled-smoke flash verified that the boot partition prefix matches the local
image:

| item | sha256 |
| --- | --- |
| local image | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |
| pushed image | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |
| boot block prefix | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |

Disabled flag absent boot returned to native serial and passed cmdv1
`version/status` verification.

## Armed Boot Timeline

The armed boot reached the shell and spawned the helper before the old
`servloc` timeout window:

| event | time |
| --- | ---: |
| console attached | `3954ms` |
| V724 flag armed | `4239ms` |
| helper spawned | `4246ms` |
| shell ready | `4246ms` |
| service-locator connected | `4.408277s` |
| final observation uptime | `368.41s` |

The important change from V723 is that the kernel `servloc` timeout did not
recur by the final observation point.

## Helper Contract

The helper log confirms the lower-only contract:

| item | value |
| --- | --- |
| mode | `wifi-companion-android-order-post-sysmon-observer-start-only` |
| order | `qrtr_ns,pd_mapper,rmt_storage,tftp_server` |
| child_started | `4` |
| all_observable | `1` |
| all_postflight_safe | `1` |
| result | `companion-window-pass` |
| service_manager | `0` |
| wifi_hal | `0` |
| wificond | `0` |
| scan_connect_linkup | `0` |
| external_ping | `0` |

No lower companion process remained in the post-observation process snapshot.

## Marker Result

Final dmesg capture after the previous timeout window:

| marker | count |
| --- | ---: |
| `service_locator_connected` | `1` |
| `servloc_timeout` | `0` |
| `service_notifier_180` | `0` |
| `service_notifier_74` | `0` |
| `pd_notifier` | `0` |
| `qca6390` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `fw_ready` | `0` |
| `wlan0` | `0` |

Two early boot kernel warnings were present at `0.540250s` and `0.812060s`,
before the V724 helper spawn at `4.246s`; they are not interpreted as helper
window regressions.

## Interpretation

V724 fixed the immediate V723 timing problem:

```text
lower companion startup before timeout -> service-locator connects at 4.408s
```

It did not produce WLAN-PD/service `180/74`:

```text
service-locator connected, no servloc timeout, but no service 180/74,
no CNSS2 callback, no QCA6390/WLFW/BDF/fw-ready/wlan0 progression
```

This means the next blocker is no longer "qrtr-ns too late". The next gate
should focus on why the modem/SERVREG path does not publish WLAN-PD even when
service-locator is available from early native boot.

## Validation Commands

Executed:

```bash
python3 -m py_compile scripts/revalidation/build_native_init_boot_v724.py
python3 scripts/revalidation/build_native_init_boot_v724.py
git diff --check

python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v724.img \
  --expect-version "A90 Linux init 0.9.68 (v724)" \
  --verify-protocol auto \
  --from-native
```

Then the armed proof:

```text
touch /cache/native-init-qrtr-servloc-boot-v724
chmod 600 /cache/native-init-qrtr-servloc-boot-v724
writefile /cache/native-init-qrtr-servloc-boot-v724 run
reboot
collect status, bootstatus, timeline, V724 cache log, process list, QRTR table,
and dmesg after uptime exceeded the old 305s timeout window
```

## Next Gate

V725 should be a host-only Android/native comparison focused on the earliest
SERVREG/WLAN-PD publication prerequisites after service-locator is already
available. Candidate checks:

1. compare Android vs V724 dmesg from service-locator connect through first
   service `180/74`;
2. compare modem, mdm3, sysmon, rpmsg, and remoteproc state at the same window;
3. identify whether an Android-only service or kernel write occurs between
   service-locator connect and WLAN-PD publication;
4. avoid CNSS daemon/HAL/connect retries until service `180/74` is present.
