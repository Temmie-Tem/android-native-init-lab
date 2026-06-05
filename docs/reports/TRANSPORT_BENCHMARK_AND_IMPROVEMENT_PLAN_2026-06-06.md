# Transport Benchmark and Improvement Plan (2026-06-06)

## Scope

- Baseline: native `v725-fasttransport`.
- Device transport: USB NCM `ncm0`, TCP command listener disabled (`tcpctl=stopped`).
- Safety: transport/log capture only; no Wi-Fi scan/connect/DHCP/external ping.
- Host stabilization used for this run: a NetworkManager link-local-only profile
  named `a90-v725-ncm-bench` on the NCM interface, because the default
  disconnected NM state removed the host IPv6 link-local address.

## Measurement Method

- Payload size: 4 MiB for symmetric raw/file tests.
- Data plane: device connects to host over NCM IPv6 link-local.
- Control plane: native-init `busybox sh -c` launched through serial `a90ctl`.
- Reported timing:
  - `device_cmd_sec`: native-init child runtime from `A90P1 duration_ms`.
  - `elapsed_sec`: host wall time including `a90ctl` control overhead.
  - `host_stream_sec`: host socket send/receive loop only. For downstream this
    can overstate throughput because host kernel buffers absorb writes before
    the device finishes consuming them; use `device_cmd_sec`/`elapsed_sec` for
    downstream decisions.

## Results

| Direction | Path | Bytes | Device child | Host wall | Data result |
|---|---:|---:|---:|---:|---|
| Host -> device | `nc -w 1` -> `/dev/null` | 4 MiB | 2.103 s | 2.551 s | Succeeds, but EOF wait dominates |
| Host -> device | `nc -w 1` -> `/cache` file | 4 MiB | 2.103 s | 3.108 s | Succeeds, but EOF wait dominates |
| Host -> device | HTTP + BusyBox `wget` -> `/cache` + SHA | 4 MiB | 0.103 s | 1.600 s | SHA OK |
| Device -> host | `dd if=/dev/zero | nc` | 4 MiB | 0.101 s | 0.547 s | Host stream 0.092 s (~43 MiB/s) |
| Device -> host | `/cache` file `cat | nc` | 4 MiB | 0.201 s | 1.195 s | Host stream 0.094 s (~43 MiB/s) |
| Device -> host | generated logs `tar | gzip | nc` | 4 MiB source | 0.100 s | 1.216 s | 7.8 KiB tgz, tar OK |
| Device -> host | actual `/cache` log bundle | 139 KiB tgz | 0.201 s | 0.656 s | 8 entries, tar OK |

## Conclusions

- There is no confirmed fundamental downstream USB/NCM bottleneck.
- Downstream `nc` is the wrong primitive for host-to-device staging: BusyBox
  `nc` waits at EOF even after all data arrives, so it makes downstream look
  slow.
- Downstream HTTP + BusyBox `wget` is the correct current primitive: 4 MiB
  staged to `/cache` with SHA verification in 1.6 s host wall time.
- Upstream `tar | gzip | nc` is already fast enough for logs: the actual
  `/cache` log bundle uploaded and validated in 0.656 s host wall time.
- For current Wi-Fi loops, the dominant cost is now control-plane overhead
  (serial `a90ctl`, per-command process startup, repeated small commands), not
  bulk data transfer.
- The host-side NCM link-local instability is a real reliability bottleneck.
  Default NetworkManager handling left the NCM interface `UP` with no IPv6
  address; a link-local-only NM profile fixed reachability.

## V2167 FastUpload Smoke

- Implementation smoke: `FastUploadSession` was run directly against the live
  `v725-fasttransport` device without flash, Wi-Fi scan, association, DHCP, or
  external ping.
- Result: upload `ok=true`, reason `ok`; archive validation passed.
- Evidence directory: `tmp/wifi/v2167-fastupload-smoke-1780693668`.
- Archive path: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff/fast-upload-v2167-1780693668.tgz`.
- Uploaded entries: `ncm0-ifconfig.txt`, `ncm0-ip-addr.txt`,
  `native-init-netservice.log`, `native-init.log`, `usbnet.log`, and
  `dmesg.txt`.
- Post-smoke device state: `selftest fail=0`, `ncm0=present`,
  `tcpctl=stopped`.

## V725 Flash Transport Validation

- Flash path: `stage3/boot_linux_v725_fasttransport.img` was flashed from the
  running native init through recovery/TWRP, then verified with cmdv1
  `selftest`.
- Flash image SHA-256:
  `4b2835ce3377c34427168170d82fca801e694367dbe3b20e91d49c017deb58d7`.
- Recovery push throughput: 56 MiB image pushed in `0.666 s`
  (`84.7 MB/s`); boot block write path reported `168 MB/s`.
- First validation attempt exposed the known host-side NCM readiness issue
  after USB re-enumeration: NetworkManager attached a generic ethernet profile
  and host-to-device IPv6 link-local ping failed.
- Stabilization used the documented link-local-only profile:
  `a90-v725-ncm-bench` on `enx1e6752cb9fbe`, with
  `ipv4.method=disabled` and `ipv6.method=link-local`.
- Final validation result: `ok=true`, evidence
  `tmp/wifi/v725_transport_validation_20260606_061854`.
- NCM endpoint: host `enx1e6752cb9fbe`
  `fe80::6ea0:69c6:3852:cccc`; device `ncm0`
  `fe80::501a:85ff:fe34:5be9`.
- Downstream result: 4 MiB HTTP + BusyBox `wget` to `/cache`, SHA OK,
  host wall `0.646 s`, device child `200 ms`.
- Upstream result: whitelist log archive `tar | gzip | nc`, 83,345 bytes,
  tar OK, 8 entries, no forbidden entries, no secret hits, host wall `0.661 s`,
  device child `202 ms`.
- Post-validation device state: `A90 Linux init 0.9.244 (v725-fasttransport)`,
  `selftest fail=0`, `ncm0=present`, `tcpctl=stopped`.

## A90 NCM Autodetect Implementation

- V2167 transport now treats only `driver=cdc_ncm` plus Samsung
  `idVendor=04e8` as an automated A90 NCM candidate. Generic USB `cdc_ncm`
  devices are no longer accepted as write targets.
- Host snapshot records the stable USB identity fields exposed by sysfs/udev:
  `idVendor`, `idProduct`, manufacturer, product, serial, interface number,
  interface class/subclass/protocol, `ID_NET_DRIVER`, and `ID_USB_INTERFACES`.
- On this host, the ASIX adapter `0b95:1790` is correctly excluded while the
  A90 endpoint `04e8:6861`, `SAMSUNG_Android`, serial `RFCM90CFWXA`,
  interface `02`, driver `cdc_ncm` is selected.
- If the A90 NCM interface exists without host `fe80::`, or if the
  device-to-host TCP probe fails, the runner attempts one NetworkManager repair:
  recreate `a90-v725-ncm-bench` on the detected interface with
  `ipv4.method=disabled`, `ipv6.method=link-local`, and
  `connection.autoconnect=no`.
- `transfer_file()` now requires the full device-to-host TCP probe before using
  host HTTP + BusyBox `wget`, so downstream staging is gated by the same
  readiness contract as FastUpload.
- Smoke result: `tmp/wifi/v2167-a90-ncm-autorepair-smoke-1780695082`,
  upload `ok=true`, selected host ifname `enx1e6752cb9fbe`, link-local
  `fe80::6ea0:69c6:3852:cccc`.
- Downstream+upstream smoke result:
  `tmp/wifi/v2167-a90-ncm-down-up-smoke-1780695155`, small HTTP+`wget`
  staging `ok=true`, FastUpload `ok=true`, selected host ifname
  `enx1e6752cb9fbe`.

## Web Source Check

- `ip link` supports `addrgenmode { eui64 | none | stable_secret | random }`.
  Its manual says `none` disables automatic IPv6 address generation, while
  `eui64`, `stable_secret`, and `random` generate interface identifiers. This
  matches the observed failure mode where the NCM interface was `UP` but had no
  `fe80::` address.
- NetworkManager's `ipv6.addr-gen-mode` controls interface identifier generation
  for IPv6 SLAAC and IPv6 link-local addresses, and `ipv6.method=link-local` is
  a documented method. This supports the temporary host profile used in this
  run: `ipv4.method=disabled`, `ipv6.method=link-local`, `autoconnect=no`.
- NetworkManager can also ignore devices through `keyfile.unmanaged-devices` or
  per-device `managed=0`. The official manual warns that `unmanaged-devices`
  is strict and cannot be overruled by `nmcli device set ... managed yes`; for
  this project, prefer a temporary link-local profile first, and treat
  unmanaged configuration as a host-admin optional fallback.
- Linux USB gadget configfs composes functions into configurations via
  symlinks, then enables the gadget by writing the UDC name. Therefore changing
  ACM/NCM function composition or rebinding UDC can cause host-side USB
  re-enumeration; avoid doing that once ACM+NCM is already present.
- BusyBox documents `nc -w SEC` as a timeout for connects and final network
  reads. This explains the downstream `nc` EOF-wait artifact and is why
  downstream staging should stay on HTTP + `wget`, not raw `nc`.
- BusyBox documents `tar -f -` and `gzip -c`; the reliable log-upload form is
  explicit `tar -cf - ... | gzip -c | nc ...`, not relying on `tar -z` to find
  an external `gzip` applet through `PATH`.
- The kernel cdc_ncm ABI lists `/sys/class/net/<iface>/cdc_ncm/` knobs including
  `min_tx_pkt`, `rx_max`, `tx_max`, and `tx_timer_usecs`. Snapshot these
  read-only first; tune only if future measurements prove USB aggregation is
  the limiting factor.

## Code Status

- `native_wifi_connect_dhcp_google_ping_handoff_v2167.py` now has the first
  `FastUploadSession` implementation in `collect_post_rollback_result()`: it
  attempts a whitelist-only NCM `tar | gzip | nc` archive first, parses
  `CONNECT_RESULT` from that archive, validates tar/SHA/entry manifest, scans
  decompressed payloads for known secret values, and falls back to serial
  `cat CONNECT_RESULT` only if upload/validation fails.
- `scripts/revalidation/a90_ncm_transport.py` now owns the reusable transport
  layer: strict A90 NCM autodetect, one-shot NetworkManager link-local repair,
  device-to-host TCP probe, IPv6 HTTP download, TCP archive receiver, and archive
  validation helpers. It also records read-only `cdc_ncm` sysfs aggregation
  knobs in host netdev snapshots.
- `scripts/revalidation/a90_ncm_transport_smoke.py` provides a transport-only
  bounded smoke/benchmark runner for host-to-device `ncm-wget` and
  device-to-host raw `cat | nc` verification. It does not perform Wi-Fi
  scan/connect, credential handling, DHCP/routes, or external ping.
- V2167 now uses the shared module for `FastTransferSession`,
  `TcpArchiveReceiver`, and archive validation.
- V2144 now uses the shared module opportunistically for the large recapture
  evidence path. It attempts a whitelist-only NCM archive for V2137 logs,
  helper result, full/filter dmesg, ICNSS debugfs, wlan0 state, and MAC sysfs
  state; any missing item falls back to the existing serial `a90ctl` command
  path.
- `stage3/linux_init/a90_netservice.c` now makes `a90_netservice_start()`
  idempotent: if `/sys/class/net/ncm0` already exists, it skips
  `a90_usbnet ncm` and only reapplies `ifconfig`/tcpctl policy. This avoids USB
  gadget re-enumeration on repeated `netservice start`.
- `native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144.py` no longer has
  serial-only large evidence collection in `collect_test_evidence()`. Descendant
  scripts that override their own collection paths should be audited separately.
- The existing `FastTransferSession` readiness logic is now stricter in V2167:
  host candidate selection requires Samsung `04e8` plus `cdc_ncm`, and both
  download and upload paths require device-to-host TCP reachability.
- Host `addrgenmode` fix is not implemented because the current host session
  lacks passwordless `sudo`. Add an optional branch only when privileged host
  commands are available: `ip link set dev <if> addrgenmode stable_secret`
  or `eui64`, then down/up.
- Persistent NetworkManager unmanaged-device configuration is not implemented.
  It requires host-admin writes under `/etc/NetworkManager/` and may be too
  broad for a portable test runner. Prefer creating/activating a temporary
  link-local-only NM profile for the detected NCM interface.
- `a90_usbnet` itself still has no standalone `status`/`ensure-ncm` subcommand,
  but the native `netservice start` path now avoids calling it when `ncm0` is
  already present. Add a helper-level subcommand only if future direct
  `a90_usbnet ncm` callers need the same behavior outside netservice.
- cdc_ncm sysfs tuning is not implemented. Add a read-only snapshot first; only
  consider writing `tx_timer_usecs`, `tx_max`, or `rx_max` if a later benchmark
  shows raw NCM throughput, not command overhead, is the limiter.
- `FastUploadSession` remains V2167-specific because its whitelist is tied to
  V2167 connect artifacts, but its transport/receiver/validation primitives are
  now shared.
- Historical smoke measurements should be preserved as supporting evidence:
  early log-upload prototypes completed in roughly 0.556-0.557 s wall time with
  tar validation OK, and the later actual `/cache` bundle completed in 0.656 s.
- Post-refactor smoke preserved the behavior through the shared module:
  `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-transport-refactor-clean/transport-refactor-clean-smoke.json`
  reports host-to-device `ncm-wget` OK in `1.143s` and log upload OK in `0.670s`;
  the artifact records `uses_shared_fast_transfer=a90_ncm_transport`.
- Big-file smoke:
  `tmp/wifi/a90-ncm-transport-smoke-bigfile-20260606-065028/manifest.json`
  passed 1/32/128MiB bidirectional verification. The 128MiB run completed
  host-to-device in `2.157s` and device-to-host in `3.049s`.
- NetworkManager recovery smoke:
  `tmp/wifi/a90-ncm-transport-smoke-nm-device-repair-20260606-065109/manifest.json`
  disconnected the A90 NCM host device first, then passed 1MiB bidirectional
  verification through the shared one-shot link-local repair path.
- Cold-reboot smoke:
  after native reboot, status returned at `25s` with
  `selftest fail=0`; `tmp/wifi/a90-ncm-transport-smoke-cold-reboot-20260606-065223/manifest.json`
  passed 1/32MiB bidirectional verification.
- Post-flash idempotent smoke:
  rebuilt/flashed `stage3/boot_linux_v725_fasttransport.img` with SHA-256
  `b9afa0e3c1c677c55a764a0b8dbd7027089dd134318084332bfd52cdf008830f`.
  Repeated `netservice start` returned in `101ms` with the same host USB
  interface index, indicating no re-enumeration. Final
  `tmp/wifi/a90-ncm-transport-smoke-post-flash-idempotent-20260606-065514/manifest.json`
  passed 1/32MiB bidirectional verification; final status was
  `v725-fasttransport`, `selftest fail=0`, `ncm=present`, `tcpctl=stopped`.
- V2144 collector smoke:
  `tmp/wifi/v2144-collector-fastupload-smoke-1780696823/collector-fastupload-smoke.json`
  ran `collect_test_evidence()` without flashing and extracted all ten large
  evidence artifacts through `a90_ncm_transport` in `4.443s`; only the native
  control/status commands stayed on serial.

## V725 Fasttransport Baseline Acceptance

- Acceptance run: `tmp/wifi/v725-fasttransport-baseline-validation-final4-20260606-071359/manifest.json`.
- Decision: `v725-fasttransport-baseline-accepted`; all transport-only gates passed.
- Initial/final guard state: `A90 Linux init 0.9.244 (v725-fasttransport)`,
  `selftest fail=0`, `ncm=present`, `tcpctl=stopped`.
- Idempotency: five consecutive `netservice start` calls completed in `101ms`
  each and preserved the same host USB sysfs path, confirming no gadget
  re-enumeration on the managed path.
- Big-file transport: 1/32/128MiB bidirectional smoke passed. The 128MiB run
  completed host-to-device HTTP+`wget` in `2.162s` and device-to-host
  `cat | nc` in `3.055s`.
- NetworkManager recovery: after host-side device disconnect, the one-shot
  link-local repair recovered NCM and passed 1MiB bidirectional smoke.
- Cold reboot: device became ready after `46.360s` with version/selftest/NCM
  all valid, then passed 1/32MiB bidirectional smoke.
- V2144 collector probe: fast evidence path extracted all ten large artifacts
  through NCM in `1.254s`; serial remains only for small control/status calls.
- Bounded retry policy: `a90_ncm_transport_smoke.py` now records download
  attempts and permits one retry by default. This mitigates the observed
  cold-boot first-command `a90ctl` END-marker race. The accepted final run did
  not need the retry, but the previous blocked run showed HTTP served the file
  while serial parsing lost the command terminator, so the residual risk is
  control-plane, not NCM data-plane integrity.
- Host hardening check: after installing the manual NetworkManager profile,
  `tmp/wifi/a90-ncm-transport-smoke-host-fixed-20260606-072820/manifest.json`
  passed 1MiB bidirectional smoke with host interface `enx566cb8d217e9`,
  link-local `fe80::90e7:a76c:4b48:e1f6`, and `download_attempts=1`.

## Remaining Risks Before Making It The Default

- Cold-boot first command can still race with serial/menu echo. Mitigation is
  now explicit: readiness requires version + `fail=0` + `ncm=present` +
  `tcpctl=stopped`, smoke sends `hide`, and host-to-device transfer has one
  bounded retry. Treat repeated retry use as a regression signal.
- Host NetworkManager policy is still environment-dependent. The runner can
  repair the active session with `a90-v725-ncm-bench`, but persistent
  unmanaged-device configuration remains a host-admin decision outside the
  portable test baseline. The current host now has the recommended
  `a90-v725-ncm-bench` profile and passed smoke without retry.
- Direct callers of `a90_usbnet ncm` can still force gadget reconfiguration;
  baseline-safe callers should use `netservice start` or the shared transport
  module. Add an `a90_usbnet status/ensure-ncm` helper only if direct callers
  remain.
- V2144 full firmware-class handoff was not rerun as a Wi-Fi test in this
  transport acceptance pass. The collector path was verified in-place; Wi-Fi
  scan/connect/DHCP/external ping remain intentionally out of scope here.
- cdc_ncm aggregation tuning remains read-only. Current throughput does not
  justify writing `tx_timer_usecs`, `tx_max`, or `rx_max`; revisit only if
  future measurements show raw NCM throughput, not serial control overhead, is
  the limiter.

## Baseline Recommendation

- Use `v725-fasttransport` as the transport baseline for the next Wi-Fi work.
- Keep the baseline entry path as: flashed `stage3/boot_linux_v725_fasttransport.img`,
  `selftest fail=0`, `netservice start`, shared `a90_ncm_transport` readiness,
  and transport smoke with bounded retry.
- Defer committing this as the long-term default only if a follow-up run shows
  repeated cold-boot transfer retries, NCM candidate misidentification, or
  NetworkManager repair failure. The current acceptance evidence is sufficient
  for using it as the main working baseline.

## FastUploadSession Target Design

- Reuse the `FastTransferSession` host/interface discovery path rather than
  adding a second NCM detector.
- Readiness must require both sides:
  - host has a likely USB NCM interface with a `fe80::` address;
  - device `ncm0` can route/connect to `<host_ll>%ncm0`.
- Host side opens an ephemeral IPv6 TCP receiver bound to `::`, stores the
  incoming archive as `.tgz`, computes SHA-256, and records bytes/elapsed time.
- Device side creates a whitelist-only temp directory under `/cache`, copies or
  generates selected logs into it, then streams:
  `/bin/busybox tar -cf - <dir> | /bin/busybox gzip -c |
  /bin/busybox nc <host_ll>%ncm0 <port>`.
- Never use `tar -z`; this environment already showed that BusyBox may try to
  exec an external `gzip` by name, which fails when `PATH` is not suitable.
- Host side validates the received `.tgz` with `tar -tzf`, records an entry
  manifest, and rejects zero-byte or non-tar archives.
- Secret hygiene is mandatory: never include `CONNECT_CONFIG`, socket
  directories, raw environment dumps, or credentials; scan archive bytes for
  known secret values such as `A90_WIFI_PSK`, and delete/mark failed if found.
- If NCM upload fails, fall back to the current serial `cat` path for the
  minimum required result file so a test run still returns a useful status.

## Improvement Plan

1. Keep host-to-device staging on HTTP + BusyBox `wget`.
   - Do not switch downstream staging to `nc` unless a custom receiver with
     explicit length framing replaces BusyBox `nc`.
   - Reuse one HTTP server/session per run instead of starting a server per
     file when multiple artifacts are staged.

2. Add a reusable host-side NCM readiness layer.
   - Detect the real NCM interface by USB path/name and by absence of normal
     LAN IPv4 lease.
   - Treat `UP` without IPv6 link-local as not ready.
   - If NetworkManager is available, create/activate a temporary
     link-local-only profile for the current NCM interface.
   - If privileged host commands are available, optionally force
     `addrgenmode stable_secret` or `eui64` and cycle the host link.
   - Add a device-side reachability probe from `ncm0` to the selected host
     link-local address before attempting bulk upload.
   - Fall back to `netservice stop/start` re-enumeration only when the host
     cannot assign/retain link-local by local host configuration.

3. Replace serial log collection with NCM upload.
   - V2167 now builds a whitelisted temp directory on device, uploads it over
     NCM, validates it on host, and falls back to serial result retrieval on
     failure.
   - In V2167, include `CONNECT_RESULT`,
     `/cache/a90-wifi/a90_supplicant_execns.log`,
     `/cache/a90-wifi/a90_supplicant_execns_stdio.log`, selected
     `/cache/native-init*.log`, `/cache/usbnet.log`, `netservice status`,
     filtered/full `dmesg`, and selected debugfs snapshots.
   - Next, in V2144-style collectors, replace large serial `cat`/`dmesg` pulls with
     the same archive upload pattern.
   - Exclude `CONNECT_CONFIG`, Wi-Fi config files, environment dumps, control
     sockets, and credentials.
   - Stream with `/bin/busybox tar -cf - ... | /bin/busybox gzip -c |
     /bin/busybox nc <host_ll>%ncm0 <port>`.
   - Validate archive on host, record SHA/entry manifest, scan bytes for known
     secret values, and fall back to serial result retrieval if upload fails.

4. Batch command execution.
   - Collapse repeated `cat`, `dmesg`, `stat`, and state probes into one
     device-side script and one NCM archive.
   - Use serial only to launch the script and report a compact manifest/result.

5. Keep `v725-fasttransport` as the transport baseline.
   - It provides NCM and BusyBox in ramdisk while keeping `tcpctl` stopped in
     NCM-only mode.
   - This is enough for fast staging and upload; no boot-image change is needed
     for the next log-upload optimization beyond keeping the v725 baseline.
   - Add an idempotent `a90_usbnet status` or `ensure-ncm` path so scripts do
     not re-run gadget composition when NCM is already up.

6. Defer lower-priority NCM tuning.
   - Inspect cdc_ncm sysfs parameters (`tx_max`, `rx_max`, `tx_timer_usecs`,
     `min_tx_pkt`) read-only first.
   - MTU/NTB tuning is lower priority because measured raw upstream is already
     ~43 MiB/s and downstream `wget` is dominated by command/session overhead.

## Labels

- `transport-downstream-ok-wget`
- `transport-upstream-ok-nc-targzip`
- `host-ncm-linklocal-nm-profile-needed`
- `next-gate-fastupload-session`

## References

- Linux USB gadget configfs: https://docs.kernel.org/6.8/usb/gadget_configfs.html
- `ip link addrgenmode`: https://man.he.net/man8/ip-link
- NetworkManager IPv6 settings: https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/settings-ipv6.html
- NetworkManager unmanaged devices: https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/NetworkManager.conf.html
- Red Hat unmanaged-device procedure: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/configuring_and_managing_networking/configuring-networkmanager-to-ignore-certain-devices
- BusyBox applet reference: https://busybox.net/downloads/BusyBox.html
- Linux cdc_ncm sysfs ABI: https://kernel.org/doc/html/next/admin-guide/abi-testing-files.html#abi-file-testing-sysfs-class-net-cdc-ncm
