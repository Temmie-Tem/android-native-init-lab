# Native Init Boot And Transport Contract

Updated: `2026-06-12`

This document defines the standing contract between:

1. the native-init boot image;
2. the host serial bridge;
3. the framed command protocol;
4. the fast USB transport path;
5. revalidation runners.

It is the concrete bridge between boot-image work and host communication
tooling. Per-run reports may add evidence, but they should not redefine this
contract.

## 1. Current Boot Baseline Contract

Current verified baseline:

| Field | Value |
| --- | --- |
| Device-visible version | `A90 Linux init 0.9.268` |
| Build tag | `v2237-supplicant-terminate-poll` |
| Boot image | `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img` |
| Boot SHA256 | `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f` |
| Source root | `workspace/public/src/native-init/` |
| Builder | `workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py` |
| Source/build report | `docs/reports/NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_SOURCE_BUILD_2026-06-12.md` |
| Live validation report | `docs/reports/NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_LIVE_VALIDATION_2026-06-12.md` |
| Promotion report | `docs/reports/NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_LIVE_VALIDATION_2026-06-12.md` |
| Previous rollback | `workspace/private/inputs/boot_images/boot_linux_v2236_strict_wifi_connect.img` |
| Known-good fallback | `workspace/private/inputs/boot_images/boot_linux_v48.img` |

The boot image must provide:

- native init as PID 1;
- USB ACM serial shell;
- `version`;
- `status`;
- `selftest`;
- `cmdv1` / `cmdv1x` framed command handling for v73+ images;
- `netservice` controls when the image supports NCM/tcpctl;
- `transport.contract=1` status fields;
- rollback path through TWRP/recovery.

Previous baseline:

| Field | Value |
| --- | --- |
| Build tag | `v2236-strict-wifi-connect` |
| Device-visible version | `A90 Linux init 0.9.267` |
| Boot image | `workspace/private/inputs/boot_images/boot_linux_v2236_strict_wifi_connect.img` |
| Boot SHA256 | `47dea2d602e25b60d7e6cd20619076446de0066fff0ed8b5ac80286f279ccd5b` |
| Current role | Previous strict Wi-Fi connect fallback |

`v2237-supplicant-terminate-poll` is promoted as the current baseline by
V2237. It keeps the V2236 strict Wi-Fi connect validation that rejects stale
carrier unless supplicant reaches `wpa_state=COMPLETED`, and replaces the blind
post-`TERMINATE` delay with a bounded process-exit poll plus SIGKILL escalation.

## 2. Boot-Image Transport Contract

The current and next promoted boot/init baselines must provide device-side
transport status without breaking existing parsers.

Required `status` additions:

```text
transport.contract=1
transport.serial=ready
transport.bridge_endpoint=127.0.0.1:54321
transport.ncm=absent|present|starting|ready|degraded|stopped
transport.ncm.ifname=<device-ifname-or->
transport.ncm.ipv4=<addr-or->
transport.ncm.ipv6_ll=<addr-or->
transport.tcpctl=stopped|starting|ready|degraded
transport.tcpctl.port=<port-or->
transport.upload=serial-only|ncm-ready|tcpctl-ready
transport.preferred=serial|ncm|tcpctl
transport.reason=<short-label>
```

Rules:

- Add these as plain `key=value` lines.
- Do not remove legacy `status`, `netservice`, `wifi`, or storage lines.
- Old parsers must keep passing.
- If the boot image SHA changes and becomes a rollback/test baseline, promote it
  under a new run/build identity.
- Record run ID, native-init semantic version, build tag, helper marker, boot
  image path, and boot SHA256 in the promotion report.

## 3. Host Bridge Contract

Canonical bridge entrypoint:

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status --json
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
```

Bridge wrapper guarantees:

- repository-root aware script resolution;
- default listener `127.0.0.1:54321`;
- private capture path under `workspace/private/logs/bridge/`;
- private metadata under `workspace/private/run/a90_bridge.json`;
- Samsung ACM candidate and selected-realpath reporting;
- ambiguous auto-match refusal unless explicitly overridden;
- bounded `repair-dirs` for root-owned private bridge state;
- `wrapper_contract=1` in text and JSON status;
- opt-in `--pin-selected-realpath` to pass selected serial realpath as
  `serial_tcp_bridge.py --expect-realpath`.

`status --json` consumers may rely on at least:

```json
{
  "wrapper_contract": 1,
  "wrapper_name": "a90_bridge",
  "bridge_process": "running",
  "listen_host": "127.0.0.1",
  "listen_port": 54321,
  "port_listening": true,
  "port_pid_source": "fd|cmdline-fallback|unresolved",
  "selected_device": "/dev/ttyACM0",
  "selected_realpath": "/dev/ttyACM0",
  "ambiguous": false,
  "capture_path": "workspace/private/logs/bridge/..."
}
```

`port_pid_source=cmdline-fallback` is acceptable when the bridge is already
running and `/proc/*/fd` inspection is blocked by process ownership. It is not a
functional failure by itself.

## 4. Serial Wire Contract

Transport:

```text
device /dev/ttyGS0 <-> host /dev/ttyACM0 <-> a90_bridge.py <-> 127.0.0.1:54321
```

Primary command protocol for v73+ images:

```text
cmdv1 <argv...>
cmdv1x <len:hex-utf8-arg>...
```

Success criteria:

- output contains `A90P1 BEGIN`;
- output contains matching `A90P1 END`;
- `A90P1 END ... rc=0`;
- `A90P1 END ... status=ok`;
- for `selftest`, body reports `fail=0`.

Host code should use `a90ctl.py` or `a90_transport.py` rather than parsing raw
`nc` output. Raw `nc` is allowed for manual debugging and pre-v73 fallback only.

Serial bridge transaction rules:

- The serial wire is a single byte stream; host clients must not issue
  concurrent command transactions against `127.0.0.1:54321`.
- `a90ctl.py` serial exchanges must hold the shared lock
  `workspace/private/run/a90-serial-bridge.lock` from TCP connect through final
  response parsing.
- `a90_bridge.py doctor/status` probes must not disturb an active transaction;
  if the shared lock is held, classify the probe as `busy-serial-lock`.
- `serial_tcp_bridge.py` must reject an extra TCP client with
  `[bridge] busy: another client is active; retry later` rather than silently
  closing the connection.
- Runners should treat bridge busy as retryable when no command reached the
  device, but unsafe device commands still must not be replayed after partial
  serial writes.

Retry rules:

- Safe observation commands may retry on transient serial-missing output.
- Unsafe root commands must not be replayed automatically.
- Commands that mutate boot, recovery, partitions, Wi-Fi credentials, routes, or
  power state require explicit runner scope.

## 5. Fast Transport Contract

Host-side selector module:

```python
import a90_transport
selection = a90_transport.select_transport(...)
```

Selector output contract:

```json
{
  "selector_contract": 1,
  "transport_contract": 0,
  "bridge_wrapper_contract": 1,
  "bridge_device": "/dev/ttyACM0",
  "serial_bridge": "ready",
  "device_status": "ready",
  "ncm_host": "ready|present-no-link-local|not-ready",
  "host_ncm_auto_repair": true,
  "host_ncm_repair": null,
  "tcpctl": "ready|not-tested|stopped|starting|degraded",
  "selected": "serial|ncm|tcpctl",
  "fallback_reason": null
}
```

For current `v2237-supplicant-terminate-poll`, `transport_contract=1` is
expected. Older images may still report `transport_contract=0`; that is not a
selector failure if host bridge, version/status, and host NCM are ready.

NCM readiness requires:

- Samsung USB NCM interface detected on the host;
- `cdc_ncm` driver;
- vendor ID `04e8`;
- host IPv6 link-local address exists;
- device-side NCM path is reachable for the bounded transfer being attempted.

If Samsung `04e8` + `cdc_ncm` is present but host `fe80::` is missing, the
selector may run bounded NetworkManager repair before falling back to serial:

- profile: `a90-v725-ncm-bench` for compatibility with existing host setup;
- IPv4 disabled;
- IPv6 link-local enabled;
- `ipv6.addr-gen-mode=stable-privacy`;
- `connection.autoconnect=yes`.

The repair path only targets the detected A90 NCM interface. Disable it with
`A90_TRANSPORT_AUTO_REPAIR_NCM=0` when auditing host NetworkManager behavior.

Fast artifact upload rules:

- Use NCM/tcpctl only after selector readiness passes.
- Upload only whitelisted artifacts.
- Exclude credential env files, generated supplicant configs, PSK, and raw
  connection configs.
- Verify archive/listing/SHA on the host.
- Fall back to serial only for bounded summaries.

## 6. Runner Contract

Active revalidation runners should:

1. call `a90_transport.select_transport()` at the start;
2. save selector output in `manifest.json`;
3. run commands through `a90_transport.run_serial_step()` or a lower-level shared
   helper;
4. record phase timers when the runner spans flash, boot, connect, upload, or
   rollback;
5. record `residual_state_contract=1` when the runner can leave device, host,
   network, or filesystem state behind;
6. keep raw artifacts under private/ignored paths;
7. redact secrets before writing public reports.

Commonization design:

- `docs/plans/NATIVE_INIT_TRANSPORT_COMMONIZATION_DESIGN_2026-06-09.md`
  defines the shared phase timer contract, serial recovery evidence shape, and
  active runner migration order.

New active runners should not:

- directly start `serial_tcp_bridge.py`;
- duplicate bridge/NCM detection logic;
- assume NCM is ready from interface existence alone;
- perform Wi-Fi scan/connect/DHCP/ping unless the runner is explicitly scoped for
  Wi-Fi connectivity;
- retry unsafe commands automatically.

## 7. Flash And Rollback Contract

Boot-image changes require:

- known input boot image;
- generated output path under `workspace/private/builds/native-init/` or
  `workspace/private/inputs/boot_images/`;
- SHA256 for init/helper/ramdisk/boot artifacts when applicable;
- TWRP/recovery path confirmed;
- rollback image path and SHA recorded;
- `version`, `status`, and `selftest fail=0` verified after boot or rollback.

Allowed flash scope:

- approved native test boot image;
- approved rollback image;
- approved Android handoff image only when the runner is explicitly an
  Android-handoff/rollback runner.

Blocked by default:

- unverified boot image flash;
- partition writes outside the approved boot/recovery flow;
- PMIC/GPIO/GDSC/regulator writes;
- eSoC notify/BOOT_DONE;
- PCI rescan;
- platform bind/unbind;
- credentials or raw Wi-Fi configs in tracked files.

## 8. Current State Summary

As of `2026-06-12`:

- Host bridge wrapper contract exists: `wrapper_contract=1`.
- Host transport selector contract exists: `selector_contract=1`.
- NCM smoke runner records transport selection in its manifest.
- Current boot image is `v2237-supplicant-terminate-poll`.
- Device-side `transport.contract=1` is a current baseline guarantee.
- Previous rollback image is `v2236-strict-wifi-connect`;
  known-good fallback remains `v48`.

The next boot-image promotion should preserve the device-side `transport.*`
status lines, the V2237 WLAN startup/connect route, and old parser compatibility.
